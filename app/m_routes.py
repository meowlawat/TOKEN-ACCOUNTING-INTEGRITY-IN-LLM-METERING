"""M1 (metering-commit timing) and M2 (usage-record authority) endpoints.

Mounted as a router by ``app.main`` so the validated B0 endpoints are untouched.

M1 is a real Server-Sent-Events stream; the client aborts mid-stream by closing the
connection, and the server settles the account according to the trial's commit-timing
architecture. Settlement runs in a fresh, cancellation-shielded DB session so a debit
(or refund) is recorded even when the request task is cancelled by the disconnect.

M2 is a normal request whose billed usage is determined by the trial's usage-authority
architecture; the client may submit a manipulated declared-usage vector.
"""

from __future__ import annotations

import asyncio
import secrets
import time
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .accounting import ledger
from .accounting.usage import CENTS, Prices, Usage, D
from .architectures import commit_timing, usage_authority
from .config import settings
from .db import SessionLocal, get_session
from .llm import mock
from .models.models import Account, Credit, MRecord, MTrial
from .schemas import (
    M1Request,
    M2Request,
    MRecordOut,
    MTrialAudit,
    MTrialCreate,
    MTrialOut,
)

router = APIRouter()


def _worker_id() -> str:
    """Identify the serving process (evidence that load spread across workers)."""
    import os
    return f"{os.environ.get('GATEWAY_NAME', 'gw')}-{os.getpid()}"



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


def _prices_from(trial: MTrial) -> Prices:
    p = trial.prices
    return Prices(
        D(p["input_per_1k"]), D(p["output_per_1k"]), D(p["cached_input_per_1k"]),
        D(p["reasoning_per_1k"]), D(p["min_charge"]),
    )


def _server_truth(prompt: str, seed: int) -> tuple[int, int, int]:
    """Authoritative server-side token truth: (input, output, reasoning)."""
    input_tokens = mock.count_prompt_tokens(prompt)
    output_tokens = mock.plan_completion(prompt, seed, settings.mock_min_tokens, settings.mock_max_tokens)
    reasoning_tokens = output_tokens // 2  # deterministic hidden-reasoning stand-in
    return input_tokens, output_tokens, reasoning_tokens


# --------------------------------------------------------------------------- #
# Admin: M-trials
# --------------------------------------------------------------------------- #
@router.post("/admin/m-trials", response_model=MTrialOut, status_code=201)
async def create_m_trial(body: MTrialCreate, session: AsyncSession = Depends(get_session)) -> MTrialOut:
    account = await session.get(Account, body.account_id)
    if account is None:
        raise HTTPException(404, "account not found")
    if body.mechanism == "m1" and body.architecture not in commit_timing.ARCHES:
        raise HTTPException(400, f"unknown m1 architecture {body.architecture}")
    if body.mechanism == "m2" and body.architecture not in usage_authority.ARCHES:
        raise HTTPException(400, f"unknown m2 architecture {body.architecture}")

    seed = body.seed if body.seed is not None else settings.seed
    prices = Prices.tier(body.price_tier)
    initial = D(body.initial_credits).quantize(CENTS)

    # Set the starting balance THROUGH the active backend so the append-only
    # backend resets its entries rather than mutating a row it never uses.
    await ledger.set_balance(session, body.account_id, initial)

    trial = MTrial(
        id=uuid.uuid4().hex,
        account_id=body.account_id,
        mechanism=body.mechanism,
        architecture=body.architecture,
        price_tier=body.price_tier,
        model_seed=seed,
        prompt=body.prompt,
        prices=prices.as_dict(),
        params=body.params or {},
        initial_balance=initial,
    )
    session.add(trial)
    await session.commit()
    return MTrialOut(
        trial_id=trial.id, account_id=trial.account_id, mechanism=trial.mechanism,
        architecture=trial.architecture, price_tier=trial.price_tier, model_seed=trial.model_seed,
        prices=trial.prices, prompt=trial.prompt, initial_balance=trial.initial_balance,
    )


@router.post("/admin/m-trials/{trial_id}/finalize", response_model=MTrialAudit)
async def finalize_m_trial(trial_id: str, session: AsyncSession = Depends(get_session)) -> MTrialAudit:
    trial = await session.get(MTrial, trial_id)
    if trial is None:
        raise HTTPException(404, "trial not found")
    trial.final_balance = await ledger.read_balance(session, trial.account_id)
    trial.finalized_at = func.now()
    await session.commit()
    return await _build_m_audit(session, trial)


@router.get("/admin/m-trials/{trial_id}/audit", response_model=MTrialAudit)
async def m_trial_audit(trial_id: str, session: AsyncSession = Depends(get_session)) -> MTrialAudit:
    trial = await session.get(MTrial, trial_id)
    if trial is None:
        raise HTTPException(404, "trial not found")
    return await _build_m_audit(session, trial)


async def _build_m_audit(session: AsyncSession, trial: MTrial) -> MTrialAudit:
    rows = (
        await session.execute(select(MRecord).where(MRecord.trial_id == trial.id).order_by(MRecord.id))
    ).scalars().all()
    net_total = sum((r.net_debit for r in rows), Decimal("0")).quantize(CENTS)
    leak_total = sum((r.leak for r in rows), Decimal("0")).quantize(CENTS)
    auth_total = sum((r.authoritative_cost for r in rows), Decimal("0")).quantize(CENTS)
    served = sum(1 for r in rows if r.served)
    violations = sum(1 for r in rows if not r.invariant_ok)
    final_balance = trial.final_balance
    delta = None if final_balance is None else (trial.initial_balance - final_balance).quantize(CENTS)
    reconciled = None if delta is None else (delta == net_total)
    return MTrialAudit(
        trial_id=trial.id, mechanism=trial.mechanism, architecture=trial.architecture,
        price_tier=trial.price_tier, initial_balance=trial.initial_balance, final_balance=final_balance,
        balance_delta=delta, net_debit_total=net_total, reconciled=reconciled,
        record_count=len(rows), served_count=served, total_authoritative_cost=auth_total,
        total_leak=leak_total, invariant_violations=violations,
        rows=[_record_out(r) for r in rows],
    )


def _record_out(r: MRecord) -> MRecordOut:
    return MRecordOut(
        request_id=r.request_id, mechanism=r.mechanism, architecture=r.architecture,
        tokens_generated=r.tokens_generated, tokens_delivered=r.tokens_delivered,
        tokens_billed=r.tokens_billed, authoritative_cost=r.authoritative_cost,
        committed_debit=r.committed_debit, refund=r.refund, net_debit=r.net_debit, leak=r.leak,
        balance_before=r.balance_before, balance_after=r.balance_after, served=r.served,
        completed=r.completed, invariant_ok=r.invariant_ok, detection_level=r.detection_level,
        abort_pct=r.abort_pct, manipulation=r.manipulation, extra=r.extra,
    )


# --------------------------------------------------------------------------- #
# M1 — streaming with commit-timing architectures
# --------------------------------------------------------------------------- #
@router.post("/m1/stream")
async def m1_stream(
    req: M1Request,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
):
    account = await _account_by_key(session, x_api_key)
    if req.trial_id is None:
        raise HTTPException(400, "trial_id required")
    trial = await session.get(MTrial, req.trial_id)
    if trial is None or trial.mechanism != "m1":
        raise HTTPException(404, "m1 trial not found")
    arch = commit_timing.ARCHES[trial.architecture]
    prices = _prices_from(trial)
    seed = req.seed if req.seed is not None else trial.model_seed
    request_id = req.request_id or secrets.token_hex(8)

    input_tokens, n_out, _reasoning = _server_truth(req.prompt, seed)
    est_full_cost = Usage(input_tokens=input_tokens, output_tokens=n_out).cost(prices)

    balance_before = await ledger.read_balance(session, account.id)
    reserved = Decimal("0")
    if arch.reserve_before:
        ok, _ = await ledger.reserve_atomic(session, account.id, est_full_cost)
        await session.commit()
        if not ok:
            # A reservation architecture MUST refuse to serve when funds are
            # insufficient; serving anyway would deliver value with no hold and is
            # not what "reserve before inference" means.
            raise HTTPException(status_code=402, detail="insufficient credits")
        reserved = est_full_cost

    delay_s = max(0.0, settings.mock_inter_token_delay_ms) / 1000.0
    state = {"delivered": 0, "completed": False, "settled": False,
             "stream_start_ns": time.perf_counter_ns(), "disconnect_ns": None,
             "stream_end_ns": None, "settle_commit_ns": None}

    async def gen():
        try:
            for i in range(n_out):
                if await request.is_disconnected():
                    state["disconnect_ns"] = time.perf_counter_ns()
                    break
                word = mock._det_int(f"{req.prompt}:{i}", seed, 0, 21)  # noqa: SLF001 - deterministic index
                yield f"data: token_{word}\n\n".encode()
                state["delivered"] += 1
                if delay_s:
                    await asyncio.sleep(delay_s)
            else:
                state["completed"] = True
            yield b"data: [DONE]\n\n"
        finally:
            state["stream_end_ns"] = time.perf_counter_ns()
            # Settle even if the task is being cancelled by the client disconnect.
            await asyncio.shield(
                _settle_m1(
                    account_id=account.id, trial_id=trial.id, request_id=request_id, arch=arch,
                    prices=prices, input_tokens=input_tokens, n_out=n_out, est_full_cost=est_full_cost,
                    reserved=reserved, balance_before=balance_before, state=state,
                )
            )

    return StreamingResponse(gen(), media_type="text/event-stream")


async def _settle_m1(*, account_id, trial_id, request_id, arch, prices, input_tokens, n_out,
                     est_full_cost, reserved, balance_before, state) -> None:
    if state["settled"]:
        return
    state["settled"] = True
    settle_start_ns = time.perf_counter_ns()
    delivered = state["delivered"]
    completed = state["completed"]

    delivered_usage = Usage(input_tokens=input_tokens, output_tokens=delivered)
    delivered_cost = delivered_usage.cost(prices)
    served = delivered > 0 or completed
    authoritative = delivered_cost if served else Decimal("0")

    committed = Decimal("0")
    refund = Decimal("0")

    async with SessionLocal() as s:
        if arch.reserve_before:
            committed = reserved  # already debited before streaming
            if completed:
                if arch.on_complete == "reconcile":
                    refund = max(reserved - delivered_cost, Decimal("0"))
                    if refund:
                        await ledger.credit(s, account_id, refund)
                # keep_reserve: no change
            else:  # disconnected
                if arch.on_disconnect == "reconcile_delivered":
                    refund = max(reserved - delivered_cost, Decimal("0"))
                    if refund:
                        await ledger.credit(s, account_id, refund)
                elif arch.on_disconnect == "refund_all":
                    refund = reserved
                    if refund:
                        await ledger.credit(s, account_id, refund)
                # keep_reserve: no change
        else:  # no reserve (post_completion, no_reserve_settle)
            if completed and arch.on_complete == "debit_actual":
                await ledger.debit_unchecked(s, account_id, delivered_cost)
                committed = delivered_cost
            elif (not completed) and arch.on_disconnect == "debit_delivered":
                # Ablation: finalize on the abort path too, without any reservation.
                await ledger.debit_unchecked(s, account_id, delivered_cost)
                committed = delivered_cost
            # on_disconnect == "no_debit": nothing charged

        net_debit = (committed - refund).quantize(CENTS)
        leak = (authoritative - net_debit).quantize(CENTS)
        invariant_ok = not (served and net_debit < authoritative)
        balance_after = await ledger.read_balance(s, account_id)
        abort_pct = None if completed else (100.0 * delivered / n_out if n_out else 0.0)

        s.add(MRecord(
            trial_id=trial_id, account_id=account_id, request_id=request_id, mechanism="m1",
            architecture=arch.name, tokens_generated=delivered, tokens_delivered=delivered,
            tokens_billed=(delivered if net_debit > 0 else 0),
            authoritative_cost=authoritative, committed_debit=committed, refund=refund,
            net_debit=net_debit, leak=leak, balance_before=balance_before, balance_after=balance_after,
            served=served, completed=completed, invariant_ok=invariant_ok,
            # NOT a measurement. This restates the architecture's own `safe` flag and is
            # retained only so historical raw data remains byte-reproducible. The paper
            # makes no detectability claim; see experiments/detectability.py for the
            # evidence-only classifier that superseded this field (audit fix F1).
            detection_level=("D3" if arch.safe else "D0"), abort_pct=abort_pct, manipulation=None,
            extra={"worker": _worker_id(),
                   "n_out": n_out, "est_full_cost": str(est_full_cost),
                   "delivered_cost": str(delivered_cost), "reserved": str(reserved),
                   # Timing instrumentation (monotonic ns, same process clock).
                   "stream_start_ns": state.get("stream_start_ns"),
                   "disconnect_detected_ns": state.get("disconnect_ns"),
                   "stream_end_ns": state.get("stream_end_ns"),
                   "settle_start_ns": settle_start_ns,
                   "stream_duration_ms": (
                       (state["stream_end_ns"] - state["stream_start_ns"]) / 1e6
                       if state.get("stream_end_ns") and state.get("stream_start_ns") else None),
                   # cancellation -> accounting-commit interval (the exposure window)
                   "cancel_to_commit_ms": (
                       (time.perf_counter_ns() - state["disconnect_ns"]) / 1e6
                       if state.get("disconnect_ns") else None)},
        ))
        await s.commit()
        state["settle_commit_ns"] = time.perf_counter_ns()


# --------------------------------------------------------------------------- #
# M2 — usage-record authority
# --------------------------------------------------------------------------- #
@router.post("/m2/complete", response_model=MRecordOut)
async def m2_complete(
    req: M2Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> MRecordOut:
    account = await _account_by_key(session, x_api_key)
    if req.trial_id is None:
        raise HTTPException(400, "trial_id required")
    trial = await session.get(MTrial, req.trial_id)
    if trial is None or trial.mechanism != "m2":
        raise HTTPException(404, "m2 trial not found")
    arch = usage_authority.ARCHES[trial.architecture]
    prices = _prices_from(trial)
    seed = req.seed if req.seed is not None else trial.model_seed
    request_id = req.request_id or secrets.token_hex(8)

    input_tokens, output_tokens, reasoning_tokens = _server_truth(req.prompt, seed)
    true_usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens, reasoning_tokens=reasoning_tokens)
    authoritative_cost = true_usage.cost(prices)  # value the client obtained

    # Declared usage: what the client sent. Priority: explicit client_usage vector;
    # else apply the named manipulation strategy to the true usage (equivalent to a
    # client that computed the manipulated vector itself); else honest.
    if req.client_usage is not None:
        declared = Usage(
            req.client_usage.input_tokens, req.client_usage.output_tokens,
            req.client_usage.cached_input_tokens, req.client_usage.reasoning_tokens,
            req.client_usage.declared_total,
        )
    elif req.manipulation in usage_authority.STRATEGIES:
        declared = usage_authority.STRATEGIES[req.manipulation](true_usage)
    else:
        declared = true_usage.copy()

    recount = true_usage  # server's independent recount == truth (deterministic mock)
    corrected = False
    if arch.basis == "client":
        if trial.architecture == "client_total":
            billed_cost = declared.cost_on_total(prices)
        else:
            billed_cost = declared.cost(prices)
        if arch.corrects and abs(billed_cost - recount.cost(prices)) > CENTS:
            billed_cost = recount.cost(prices)
            corrected = True
    elif arch.basis == "upstream":
        billed_cost = true_usage.cost(prices)  # honest provider metadata
    else:  # recount
        billed_cost = recount.cost(prices)

    billed_cost = billed_cost.quantize(CENTS)

    balance_before = await ledger.read_balance(session, account.id)
    await ledger.debit_unchecked(session, account.id, billed_cost)
    balance_after = await ledger.read_balance(session, account.id)

    net_debit = billed_cost
    leak = (authoritative_cost - net_debit).quantize(CENTS)
    invariant_ok = not (net_debit < authoritative_cost)
    if leak <= 0:
        detection = "D3"
    elif corrected:
        detection = "D3"
    else:
        detection = arch.detection  # D0 (client) or D1 (client_logged)

    rec = MRecord(
        trial_id=trial.id, account_id=account.id, request_id=request_id, mechanism="m2",
        architecture=arch.name, tokens_generated=true_usage.subtotal_total,
        tokens_delivered=true_usage.subtotal_total, tokens_billed=declared.subtotal_total,
        authoritative_cost=authoritative_cost, committed_debit=net_debit, refund=Decimal("0"),
        net_debit=net_debit, leak=leak, balance_before=balance_before, balance_after=balance_after,
        # NOT a measurement: `detection` is static architecture metadata. Retained for
        # raw-data reproducibility only; superseded by experiments/detectability.py.
        served=True, completed=True, invariant_ok=invariant_ok, detection_level=detection,
        abort_pct=None, manipulation=req.manipulation,
        extra={"worker": _worker_id(),
               "declared": declared.as_dict(), "true": true_usage.as_dict(),
               "corrected": corrected, "billed_cost": str(billed_cost)},
    )
    session.add(rec)
    await session.commit()
    return _record_out(rec)
