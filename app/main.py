"""FastAPI gateway for the LLM metering-evasion testbed.

Exposes a metered ``/complete`` endpoint plus an unauthenticated ``/admin`` surface
(testbed only) for provisioning accounts, quoting cost, running *trials*, reading a
mechanically-derived per-trial audit, and flipping the per-class
VULNERABLE/HARDENED posture at runtime.

Only flaw class 6 (credit-decrement race) is wired up. Its two code paths differ
*structurally*, not by a flag check:

  * vulnerable: lock-free read -> check -> stream -> observe -> stale absolute write
  * hardened:   atomic compare-and-decrement (commit) -> stream -> record (commit)

Every served completion writes a ledger row (``usage_records``) carrying the
observed ``balance_before``/``balance_after`` and the applied debit, so leakage and
the safety invariant are auditable from persisted data alone.
"""

from __future__ import annotations

import os
import secrets
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .accounting import backends as acct_backends
from .accounting import ledger as acct_ledger
from .config import Mode, settings
from .db import Base, engine, get_session
from .llm import mock
from .metering import debit as debit_ops
from .metering.pricing import cost_of
from .models.models import Account, Credit, Trial, UsageRecord
from .schemas import (
    AccountCreate,
    AccountOut,
    CompleteRequest,
    CompleteResponse,
    ConfigOut,
    ConfigUpdate,
    DbInfo,
    QuoteOut,
    ResetRequest,
    TopupRequest,
    TrialAudit,
    TrialCreate,
    TrialOut,
    UsageRow,
)

_CENTS = Decimal("0.000001")

# Shared-state key for the B0 runtime posture. Must be shared (not per-process) so
# that every gateway worker in a multi-worker or multi-instance deployment agrees.
POSTURE_KEY = "tai:posture:class6_credit_race"

# Advisory-lock key serializing concurrent schema creation across workers.
SCHEMA_LOCK_KEY = 0x7A1_ACC7

# Identifies which OS process served a request, so cross-topology experiments can
# confirm that load actually spread across workers/instances.
WORKER_ID = f"{os.environ.get('GATEWAY_NAME', 'gw')}-{os.getpid()}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables, initialize runtime posture, and open the Redis connection.

    Schema creation is serialized with a PostgreSQL advisory lock. Without it, a
    multi-worker deployment has every worker run ``create_all`` concurrently at boot
    and the losers crash with ``UniqueViolationError`` on ``pg_class`` -- observed
    directly when first bringing up the 4-worker topology. The lock is transaction
    scoped, so it is released automatically when the block exits.
    """
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": SCHEMA_LOCK_KEY})
        await conn.run_sync(Base.metadata.create_all)

    # Per-process fallback copy of the runtime posture. In a MULTI-WORKER deployment
    # this is NOT sufficient: `POST /admin/config` would reach only one worker, so the
    # posture must live in shared state. We therefore keep the authoritative value in
    # Redis and use this dict only when Redis is unavailable (single-worker fallback).
    app.state.mode = {"class6_credit_race": settings.class6_credit_race}

    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await app.state.redis.ping()
        app.state.redis_ok = True
        # Seed the shared posture only if no worker has set it yet (SETNX semantics),
        # so restarting a worker never silently reverts a running experiment.
        await app.state.redis.setnx(POSTURE_KEY, settings.class6_credit_race.value)
    except Exception:  # noqa: BLE001 - Redis is optional for class 6
        app.state.redis_ok = False

    # Share the accounting-backend selector across workers/instances.
    acct_ledger.configure(app.state.redis if app.state.redis_ok else None)

    yield

    try:
        await app.state.redis.aclose()
    except Exception:  # noqa: BLE001
        pass
    await engine.dispose()


app = FastAPI(
    title="LLM Metering-Evasion Testbed",
    version="0.3.0",
    summary="Vulnerable-by-construction LLM-SaaS gateway for client-side metering-evasion research.",
    lifespan=lifespan,
)

# M1 (metering-commit timing) and M2 (usage-record authority) endpoints.
from .m_routes import router as m_router  # noqa: E402
from .async_routes import router as async_router  # noqa: E402

app.include_router(m_router)
app.include_router(async_router)

# Benchmark-only endpoints (real-tokenizer recount overhead). Optional: if the
# tokenizer libraries are absent the router still loads; engines report unavailable.
from .bench_routes import router as bench_router  # noqa: E402

app.include_router(bench_router)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _account_by_key(session: AsyncSession, api_key: str) -> Account:
    account = (
        await session.execute(select(Account).where(Account.api_key == api_key))
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=401, detail="invalid api key")
    return account


async def _consume_stream(prompt: str, seed: int) -> tuple[str, int]:
    """Fully consume the mock stream, returning (text, completion_token_count)."""
    parts: list[str] = []
    count = 0
    async for token in mock.stream_completion(
        prompt,
        seed,
        settings.mock_inter_token_delay_ms,
        settings.mock_min_tokens,
        settings.mock_max_tokens,
    ):
        parts.append(token)
        count += 1
    return "".join(parts), count


def _prices() -> tuple[Decimal, Decimal]:
    return (
        Decimal(str(settings.price_prompt_per_1k)),
        Decimal(str(settings.price_completion_per_1k)),
    )


def _quote(prompt: str, seed: int) -> tuple[int, int, Decimal]:
    prompt_tokens = mock.count_prompt_tokens(prompt)
    completion_tokens = mock.plan_completion(
        prompt, seed, settings.mock_min_tokens, settings.mock_max_tokens
    )
    cost = cost_of(
        prompt_tokens,
        completion_tokens,
        settings.price_prompt_per_1k,
        settings.price_completion_per_1k,
    )
    return prompt_tokens, completion_tokens, cost


async def _account_out(session: AsyncSession, account: Account) -> AccountOut:
    balance = (
        await session.execute(select(Credit.balance).where(Credit.account_id == account.id))
    ).scalar_one()
    count, total = (
        await session.execute(
            select(
                func.count(UsageRecord.id),
                func.coalesce(func.sum(UsageRecord.cost), 0),
            ).where(UsageRecord.account_id == account.id)
        )
    ).one()
    return AccountOut(
        id=account.id,
        name=account.name,
        plan=account.plan,
        api_key=account.api_key,
        balance=balance,
        usage_count=int(count),
        usage_sum=Decimal(total),
    )


# --------------------------------------------------------------------------- #
# Health, config, DB introspection
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(select(1))
    return {"status": "ok", "db": "ok", "redis": "ok" if app.state.redis_ok else "down",
            "worker": WORKER_ID}


@app.get("/admin/accounting-backend")
async def get_accounting_backend() -> dict:
    """Which accounting backend is active (shared across all workers)."""
    return {"backend": await acct_ledger.active_backend(),
            "available": list(acct_backends.VALID), "worker": WORKER_ID}


@app.post("/admin/accounting-backend")
async def set_accounting_backend(body: dict) -> dict:
    """Switch the accounting backend for every worker (testbed only)."""
    name = body.get("backend", "")
    if name not in acct_backends.VALID:
        raise HTTPException(400, f"backend must be one of {acct_backends.VALID}")
    await acct_ledger.set_backend(name)
    return {"backend": await acct_ledger.active_backend()}


@app.get("/admin/db-info", response_model=DbInfo)
async def db_info(session: AsyncSession = Depends(get_session)) -> DbInfo:
    """Expose the live PostgreSQL isolation level and version (evidence for the paper)."""
    version = (await session.execute(select(func.version()))).scalar_one()
    txn_iso = (
        await session.execute(select(func.current_setting("transaction_isolation")))
    ).scalar_one()
    default_iso = (
        await session.execute(select(func.current_setting("default_transaction_isolation")))
    ).scalar_one()
    return DbInfo(
        server_version=str(version),
        transaction_isolation=str(txn_iso),
        default_transaction_isolation=str(default_iso),
    )


async def current_posture() -> Mode:
    """Read the B0 posture from SHARED state so every worker agrees.

    Redis is authoritative; the per-process copy is only a fallback for a
    single-worker deployment with Redis unavailable.
    """
    if getattr(app.state, "redis_ok", False):
        try:
            v = await app.state.redis.get(POSTURE_KEY)
            if v:
                return Mode(v)
        except Exception:  # noqa: BLE001
            pass
    return app.state.mode["class6_credit_race"]


@app.get("/admin/config", response_model=ConfigOut)
async def get_config() -> ConfigOut:
    return ConfigOut(class6_credit_race=await current_posture())


@app.post("/admin/config", response_model=ConfigOut)
async def set_config(update: ConfigUpdate) -> ConfigOut:
    if update.class6_credit_race is not None:
        app.state.mode["class6_credit_race"] = update.class6_credit_race
        if getattr(app.state, "redis_ok", False):
            try:
                await app.state.redis.set(POSTURE_KEY, update.class6_credit_race.value)
            except Exception:  # noqa: BLE001
                pass
    return ConfigOut(class6_credit_race=await current_posture())


@app.post("/admin/reset-db", status_code=200)
async def reset_db() -> dict:
    """Drop and recreate all tables (testbed only) for a clean, reproducible run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return {"status": "reset"}


# --------------------------------------------------------------------------- #
# Admin: accounts
# --------------------------------------------------------------------------- #
@app.post("/admin/accounts", response_model=AccountOut, status_code=201)
async def create_account(
    body: AccountCreate, session: AsyncSession = Depends(get_session)
) -> AccountOut:
    account = Account(name=body.name, plan=body.plan, api_key=secrets.token_hex(16))
    session.add(account)
    await session.flush()
    session.add(Credit(account_id=account.id, balance=Decimal(str(body.balance)),
                       opening_balance=Decimal(str(body.balance))))
    await session.commit()
    await session.refresh(account)
    return await _account_out(session, account)


@app.get("/admin/accounts/{account_id}", response_model=AccountOut)
async def get_account(account_id: int, session: AsyncSession = Depends(get_session)) -> AccountOut:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    return await _account_out(session, account)


@app.post("/admin/accounts/{account_id}/reset", response_model=AccountOut)
async def reset_account(
    account_id: int, body: ResetRequest, session: AsyncSession = Depends(get_session)
) -> AccountOut:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    await session.execute(delete(UsageRecord).where(UsageRecord.account_id == account_id))
    credit = await session.get(Credit, account_id)
    credit.balance = Decimal(str(body.balance))
    await session.commit()
    return await _account_out(session, account)


@app.post("/admin/accounts/{account_id}/topup", response_model=AccountOut)
async def topup_account(
    account_id: int, body: TopupRequest, session: AsyncSession = Depends(get_session)
) -> AccountOut:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    credit = await session.get(Credit, account_id)
    credit.balance = credit.balance + Decimal(str(body.amount))
    await session.commit()
    return await _account_out(session, account)


@app.get("/admin/quote", response_model=QuoteOut)
async def quote(prompt: str, seed: int | None = None) -> QuoteOut:
    pt, ct, cost = _quote(prompt, seed if seed is not None else settings.seed)
    pp, pc = _prices()
    return QuoteOut(
        prompt_tokens=pt,
        completion_tokens=ct,
        cost=cost,
        price_prompt_per_1k=pp,
        price_completion_per_1k=pc,
    )


# --------------------------------------------------------------------------- #
# Admin: trials (one experiment repetition)
# --------------------------------------------------------------------------- #
@app.post("/admin/trials", response_model=TrialOut, status_code=201)
async def create_trial(
    body: TrialCreate, session: AsyncSession = Depends(get_session)
) -> TrialOut:
    """Pin starting conditions for one repetition and set the affordable balance.

    The posture recorded is the gateway's *current* runtime posture. Balance is set
    to ``affordable * unit_cost`` so exactly ``affordable`` requests are payable.
    """
    account = await session.get(Account, body.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")

    seed = body.seed if body.seed is not None else settings.seed
    _pt, _ct, unit_cost = _quote(body.prompt, seed)
    pp, pc = _prices()
    initial_balance = (unit_cost * body.affordable).quantize(_CENTS)

    credit = await session.get(Credit, body.account_id)
    credit.balance = initial_balance

    posture: Mode = await current_posture()
    trial = Trial(
        id=uuid.uuid4().hex,
        account_id=body.account_id,
        posture=posture.value,
        concurrency=body.concurrency,
        affordable=body.affordable,
        model_seed=seed,
        prompt=body.prompt,
        unit_cost=unit_cost,
        price_prompt_per_1k=pp,
        price_completion_per_1k=pc,
        initial_balance=initial_balance,
    )
    session.add(trial)
    await session.commit()

    return TrialOut(
        trial_id=trial.id,
        account_id=trial.account_id,
        posture=posture,
        concurrency=trial.concurrency,
        affordable=trial.affordable,
        model_seed=trial.model_seed,
        unit_cost=trial.unit_cost,
        price_prompt_per_1k=pp,
        price_completion_per_1k=pc,
        initial_balance=trial.initial_balance,
        final_balance=None,
    )


@app.post("/admin/trials/{trial_id}/finalize", response_model=TrialAudit)
async def finalize_trial(
    trial_id: str, session: AsyncSession = Depends(get_session)
) -> TrialAudit:
    """Snapshot the final balance, then return the mechanical per-trial audit."""
    trial = await session.get(Trial, trial_id)
    if trial is None:
        raise HTTPException(status_code=404, detail="trial not found")
    final_balance = await debit_ops.snapshot_balance(session, trial.account_id)
    trial.final_balance = final_balance
    trial.finalized_at = func.now()
    await session.commit()
    return await _build_trial_audit(session, trial)


@app.get("/admin/trials/{trial_id}/audit", response_model=TrialAudit)
async def trial_audit(trial_id: str, session: AsyncSession = Depends(get_session)) -> TrialAudit:
    trial = await session.get(Trial, trial_id)
    if trial is None:
        raise HTTPException(status_code=404, detail="trial not found")
    return await _build_trial_audit(session, trial)


async def _build_trial_audit(session: AsyncSession, trial: Trial) -> TrialAudit:
    """Derive every trial-level figure mechanically from persisted ledger rows."""
    rows = (
        await session.execute(
            select(UsageRecord)
            .where(UsageRecord.trial_id == trial.id)
            .order_by(UsageRecord.id)
        )
    ).scalars().all()

    served_rows = [r for r in rows if r.served]
    served_count = len(served_rows)

    intended_total = sum((r.cost for r in served_rows), Decimal("0"))
    applied_total = sum(
        ((r.applied_debit or Decimal("0")) for r in served_rows), Decimal("0")
    )

    final_balance = trial.final_balance
    actual_debit: Decimal | None = None
    if final_balance is not None:
        actual_debit = (trial.initial_balance - final_balance).quantize(_CENTS)

    reconciled: bool | None = None
    if actual_debit is not None:
        reconciled = actual_debit == applied_total.quantize(_CENTS)

    inference_value = intended_total.quantize(_CENTS)
    dollar_leak: Decimal | None = None
    paid_requests: Decimal | None = None
    unpaid_served: Decimal | None = None
    if actual_debit is not None:
        dollar_leak = (inference_value - actual_debit).quantize(_CENTS)
        if trial.unit_cost > 0:
            paid_requests = (actual_debit / trial.unit_cost).quantize(Decimal("0.0001"))
            unpaid_served = Decimal(served_count) - paid_requests

    # Invariant: a served request must have applied a debit >= its cost.
    violations = [r for r in served_rows if (r.applied_debit or Decimal("0")) < r.cost]
    invariant_violations = len(violations)
    unauthorized_completion_tokens = sum(r.completion_tokens for r in violations)

    over_served = max(served_count - trial.affordable, 0)

    if dollar_leak is None or dollar_leak <= 0:
        detection_status = "none"
    elif intended_total > (actual_debit or Decimal("0")):
        # Live balance under-reports, but the ledger records every served debit ->
        # reconciliation reveals the discrepancy.
        detection_status = "partial"
    else:
        detection_status = "full"  # leaked and not even the ledger records it

    return TrialAudit(
        trial_id=trial.id,
        posture=Mode(trial.posture),
        concurrency=trial.concurrency,
        affordable=trial.affordable,
        unit_cost=trial.unit_cost,
        initial_balance=trial.initial_balance,
        final_balance=final_balance,
        actual_debit=actual_debit,
        applied_debit_total=applied_total.quantize(_CENTS),
        reconciled=reconciled,
        served_count=served_count,
        rejected_or_absent=len(rows) - served_count,
        intended_debit_total_served=inference_value,
        inference_value=inference_value,
        dollar_leak=dollar_leak,
        paid_requests=paid_requests,
        unpaid_served=unpaid_served,
        over_served=over_served,
        invariant_violations=invariant_violations,
        unauthorized_completion_tokens=unauthorized_completion_tokens,
        detection_status=detection_status,
        rows=[
            UsageRow(
                request_id=r.request_id,
                posture=r.posture,
                concurrency=r.concurrency,
                prompt_tokens=r.prompt_tokens,
                completion_tokens=r.completion_tokens,
                price_prompt_per_1k=r.price_prompt_per_1k,
                price_completion_per_1k=r.price_completion_per_1k,
                cost=r.cost,
                balance_before=r.balance_before,
                balance_after=r.balance_after,
                applied_debit=r.applied_debit,
                served=r.served,
                committed=r.committed,
                refunded=r.refunded,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )


# --------------------------------------------------------------------------- #
# Metered completion endpoint
# --------------------------------------------------------------------------- #
@app.post("/complete", response_model=CompleteResponse)
async def complete(
    req: CompleteRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> CompleteResponse:
    account = await _account_by_key(session, x_api_key)
    seed = req.seed if req.seed is not None else settings.seed
    request_id = req.request_id or secrets.token_hex(8)

    prompt_tokens = mock.count_prompt_tokens(req.prompt)
    est_completion = mock.plan_completion(
        req.prompt, seed, settings.mock_min_tokens, settings.mock_max_tokens
    )
    est_cost = cost_of(
        prompt_tokens, est_completion, settings.price_prompt_per_1k, settings.price_completion_per_1k
    )

    mode: Mode = await current_posture()
    if mode is Mode.hardened:
        return await _complete_hardened(
            session, account, req, seed, request_id, prompt_tokens, est_cost
        )
    return await _complete_vulnerable(
        session, account, req, seed, request_id, prompt_tokens, est_cost
    )


async def _complete_vulnerable(
    session: AsyncSession,
    account: Account,
    req: CompleteRequest,
    seed: int,
    request_id: str,
    prompt_tokens: int,
    est_cost: Decimal,
) -> CompleteResponse:
    """lock-free read -> check -> stream -> observe -> stale absolute write."""
    balance = await debit_ops.read_balance(session, account.id)
    if balance is None or balance < est_cost:
        raise HTTPException(status_code=402, detail="insufficient credits")

    # Serving happens between the (lock-free) check and the debit; concurrent
    # handlers all captured the same `balance` and will each overwrite it below.
    text_out, completion_tokens = await _consume_stream(req.prompt, seed)
    pp, pc = _prices()
    actual_cost = cost_of(prompt_tokens, completion_tokens, settings.price_prompt_per_1k, settings.price_completion_per_1k)

    before, after = await debit_ops.debit_stale_absolute(session, account.id, balance, actual_cost)
    debit_ops.record_usage(
        session,
        account_id=account.id,
        trial_id=req.trial_id,
        request_id=request_id,
        posture=Mode.vulnerable.value,
        concurrency=req.concurrency,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        price_prompt_per_1k=pp,
        price_completion_per_1k=pc,
        cost=actual_cost,
        balance_before=before,
        balance_after=after,
        committed=True,
        refunded=False,
        served=True,
    )
    await session.commit()

    return CompleteResponse(
        request_id=request_id,
        completion=text_out,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=actual_cost,
        balance_before=before,
        balance_after=after,
        applied_debit=before - after,
        committed=True,
        refunded=False,
        served=True,
        mode=Mode.vulnerable,
    )


async def _complete_hardened(
    session: AsyncSession,
    account: Account,
    req: CompleteRequest,
    seed: int,
    request_id: str,
    prompt_tokens: int,
    est_cost: Decimal,
) -> CompleteResponse:
    """atomic compare-and-decrement (commit) -> stream -> record (commit)."""
    ok, before, after = await debit_ops.reserve_hardened(session, account.id, est_cost)
    if not ok:
        raise HTTPException(status_code=402, detail="insufficient credits")
    # Commit the reserve immediately so the row lock is not held during streaming.
    await session.commit()

    try:
        text_out, completion_tokens = await _consume_stream(req.prompt, seed)
    except Exception:
        # Safety property: a response that did not complete must not be billed.
        await debit_ops.refund_hardened(session, account.id, est_cost)
        await session.commit()
        raise

    pp, pc = _prices()
    actual_cost = cost_of(prompt_tokens, completion_tokens, settings.price_prompt_per_1k, settings.price_completion_per_1k)
    # For identical prompts est_cost == actual_cost, so the reserve is exact.
    debit_ops.record_usage(
        session,
        account_id=account.id,
        trial_id=req.trial_id,
        request_id=request_id,
        posture=Mode.hardened.value,
        concurrency=req.concurrency,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        price_prompt_per_1k=pp,
        price_completion_per_1k=pc,
        cost=actual_cost,
        balance_before=before,
        balance_after=after,
        committed=True,
        refunded=False,
        served=True,
    )
    await session.commit()

    return CompleteResponse(
        request_id=request_id,
        completion=text_out,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=actual_cost,
        balance_before=before,
        balance_after=after,
        applied_debit=(before - after) if (before is not None and after is not None) else None,
        committed=True,
        refunded=False,
        served=True,
        mode=Mode.hardened,
    )
