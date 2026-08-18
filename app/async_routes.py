"""Asynchronous-accounting architecture: execution and settlement decoupled in time.

Adds a third accounting family alongside the mutable-balance row and the append-only
ledger. Here the gateway does not settle at all: it emits a usage event and returns, and a
separate worker applies the debit after a controlled delay.

Two endpoints, one per question:

* `/async/m1/stream` -- what does the delay do to commitment timing? Value is delivered,
  then an event is emitted; between those two moments there is an **exposure window** in
  which the client holds inference that no debit covers. The window exists even when every
  component works correctly, which is the point.

* `/async/b0/complete` -- does decoupling change the *nature* of the shared-credit race?
  The authorization check still reads the balance synchronously, but the debit lands
  later, so the stale-read window is no longer microseconds of transaction overlap: it is
  the reconciliation delay. This is a prediction the experiment can refute.

Fault injection is part of the architecture, not an add-on: real event pipelines lose,
duplicate and delay messages, and an accounting design is only as good as its behaviour
when they do.

ETHICS: local testbed only.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .accounting import async_worker as aw
from .accounting import ledger
from .accounting.usage import CENTS, Prices, Usage, D
from .db import SessionLocal, get_session
from .llm import mock
from .models.models import Account, MRecord, MTrial

router = APIRouter(tags=["async-accounting"])

# Injectable pipeline faults. `none` is the honest pipeline.
FAULTS = ("none", "lost_event", "duplicate_event", "delayed_event", "abort_before_event")


class AsyncRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    trial_id: str
    seed: int | None = None
    request_id: str | None = None
    reconcile_delay_ms: float = 0.0
    fault: str = "none"
    abort_after: int | None = None   # server-side abort simulation for B0 workloads


async def _account(session: AsyncSession, key: str) -> Account:
    acct = (await session.execute(select(Account).where(Account.api_key == key))).scalar_one_or_none()
    if acct is None:
        raise HTTPException(401, "invalid api key")
    return acct


def _prices(trial: MTrial) -> Prices:
    p = trial.prices
    return Prices(D(p["input_per_1k"]), D(p["output_per_1k"]), D(p["cached_input_per_1k"]),
                  D(p["reasoning_per_1k"]), D(p["min_charge"]))


async def _emit(request: Request, ev: aw.UsageEvent, fault: str) -> None:
    """Hand the event to the queue, applying the requested pipeline fault."""
    redis = request.app.state.redis
    if fault == "lost_event":
        return                                   # emitted nowhere; the debit never happens
    await aw.emit(redis, ev)
    if fault == "duplicate_event":
        await aw.emit(redis, ev)                 # at-least-once delivery


# --------------------------------------------------------------------------- #
# M1 under asynchronous settlement
# --------------------------------------------------------------------------- #
@router.post("/async/m1/stream")
async def async_m1_stream(
    req: AsyncRequest,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
):
    if req.fault not in FAULTS:
        raise HTTPException(400, f"unknown fault {req.fault}")
    account = await _account(session, x_api_key)
    trial = await session.get(MTrial, req.trial_id)
    if trial is None:
        raise HTTPException(404, "trial not found")
    prices = _prices(trial)
    seed = req.seed if req.seed is not None else trial.model_seed
    request_id = req.request_id or secrets.token_hex(8)

    input_tokens = mock.count_prompt_tokens(req.prompt)
    n_out = mock.plan_completion(req.prompt, seed, 40, 80)

    state = {"delivered": 0, "completed": False,
             "stream_start_ns": time.perf_counter_ns(), "emitted_ns": None}

    async def gen():
        try:
            for i in range(n_out):
                if await request.is_disconnected():
                    break
                yield f"data: token_{i}\n\n".encode()
                state["delivered"] += 1
            else:
                state["completed"] = True
            yield b"data: [DONE]\n\n"
        finally:
            await asyncio.shield(_emit_m1(
                request=request, account_id=account.id, trial=trial, prices=prices,
                request_id=request_id, input_tokens=input_tokens, n_out=n_out,
                state=state, req=req))

    return StreamingResponse(gen(), media_type="text/event-stream")


async def _emit_m1(*, request, account_id, trial, prices, request_id, input_tokens,
                   n_out, state, req) -> None:
    delivered = state["delivered"]
    served = delivered > 0
    authoritative = (Usage(input_tokens=input_tokens, output_tokens=delivered).cost(prices)
                     if served else Decimal("0"))

    # `abort_before_event` models a pipeline where the disconnect prevents the event from
    # ever being constructed -- the asynchronous analogue of M1's post-completion commit
    # that never fires.
    if req.fault == "abort_before_event" and not state["completed"]:
        amount = Decimal("0")
        emit_event = False
    else:
        amount = authoritative
        emit_event = served

    delay = req.reconcile_delay_ms
    if req.fault == "delayed_event":
        delay = max(delay, 1000.0)               # a straggler far beyond the SLA

    if emit_event:
        ev = aw.new_event(
            account_id=account_id, request_id=request_id, trial_id=trial.id,
            architecture="async_settle", delivered_tokens=delivered, amount=amount,
            authoritative=authoritative, delay_ms=delay,
            meta={"fault": req.fault, "completed": state["completed"]})
        await _emit(request, ev, req.fault)
        state["emitted_ns"] = time.perf_counter_ns()

    async with SessionLocal() as s:
        balance_now = await ledger.read_balance(s, account_id)
        s.add(MRecord(
            trial_id=trial.id, account_id=account_id, request_id=request_id,
            mechanism="async_m1", architecture="async_settle",
            tokens_generated=delivered, tokens_delivered=delivered, tokens_billed=0,
            authoritative_cost=authoritative, committed_debit=Decimal("0"),
            refund=Decimal("0"),
            # At response time NOTHING has been committed. That is the architecture, not
            # a defect: the debit exists only as a queued event.
            net_debit=Decimal("0"), leak=authoritative,
            balance_before=balance_now, balance_after=balance_now,
            served=served, completed=state["completed"], invariant_ok=not served,
            detection_level="D0", abort_pct=None, manipulation=None,
            extra={"fault": req.fault, "reconcile_delay_ms": req.reconcile_delay_ms,
                   "event_emitted": emit_event, "n_out": n_out,
                   "stream_start_ns": state["stream_start_ns"],
                   "emitted_ns": state["emitted_ns"],
                   "pending_amount": str(amount)},
        ))
        await s.commit()


# --------------------------------------------------------------------------- #
# B0 under asynchronous settlement
# --------------------------------------------------------------------------- #
@router.post("/async/b0/complete")
async def async_b0_complete(
    req: AsyncRequest,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Authorize against the CURRENT balance, serve, and queue the debit.

    The check is honest and atomic-looking -- it reads a committed balance. What makes it
    unsafe is that the corresponding debit is applied later, so every request that arrives
    inside the reconciliation window authorizes against a balance that does not yet
    reflect its predecessors.
    """
    account = await _account(session, x_api_key)
    trial = await session.get(MTrial, req.trial_id)
    if trial is None:
        raise HTTPException(404, "trial not found")
    prices = _prices(trial)
    seed = req.seed if req.seed is not None else trial.model_seed
    request_id = req.request_id or secrets.token_hex(8)

    input_tokens = mock.count_prompt_tokens(req.prompt)
    n_out = mock.plan_completion(req.prompt, seed, 40, 80)
    cost = Usage(input_tokens=input_tokens, output_tokens=n_out).cost(prices)

    balance = await ledger.read_balance(session, account.id) or Decimal("0")
    if balance < cost:
        return {"request_id": request_id, "served": False, "reason": "insufficient",
                "balance_seen": str(balance)}

    ev = aw.new_event(
        account_id=account.id, request_id=request_id, trial_id=trial.id,
        architecture="async_b0", delivered_tokens=n_out, amount=cost,
        authoritative=cost, delay_ms=req.reconcile_delay_ms,
        meta={"fault": req.fault, "balance_seen": str(balance)})
    await _emit(request, ev, req.fault)

    async with SessionLocal() as s:
        s.add(MRecord(
            trial_id=trial.id, account_id=account.id, request_id=request_id,
            mechanism="async_b0", architecture="async_b0",
            tokens_generated=n_out, tokens_delivered=n_out, tokens_billed=0,
            authoritative_cost=cost, committed_debit=Decimal("0"), refund=Decimal("0"),
            net_debit=Decimal("0"), leak=cost,
            balance_before=balance, balance_after=balance,
            served=True, completed=True, invariant_ok=False,
            detection_level="D0", abort_pct=None, manipulation=None,
            extra={"fault": req.fault, "reconcile_delay_ms": req.reconcile_delay_ms,
                   "balance_seen": str(balance), "pending_amount": str(cost)},
        ))
        await s.commit()

    return {"request_id": request_id, "served": True, "cost": str(cost),
            "balance_seen": str(balance)}


# --------------------------------------------------------------------------- #
# Worker / admin
# --------------------------------------------------------------------------- #
@router.post("/admin/async/drain")
async def async_drain(request: Request, idempotent: bool = True) -> dict:
    """Run the accounting worker until the queue is empty of due events."""
    async def apply_debit(account_id: int, amount: Decimal) -> None:
        async with SessionLocal() as s:
            await ledger.debit_unchecked(s, account_id, amount)
            await s.commit()

    res = await aw.drain(request.app.state.redis, apply_debit, idempotent=idempotent)
    w = res.pop("exposure_windows_ms")
    res["exposure_window_ms"] = {
        "n": len(w),
        "min": round(min(w), 3) if w else None,
        "max": round(max(w), 3) if w else None,
        "mean": round(sum(w) / len(w), 3) if w else None,
    }
    res["queue_depth_after"] = await aw.queue_depth(request.app.state.redis)
    return res


@router.get("/admin/async/state")
async def async_state(request: Request) -> dict:
    return {"queue_depth": await aw.queue_depth(request.app.state.redis)}


@router.post("/admin/async/reset")
async def async_reset(request: Request) -> dict:
    await aw.reset(request.app.state.redis)
    return {"reset": True}


# --------------------------------------------------------------------------- #
# Continuously running accounting worker
# --------------------------------------------------------------------------- #
#
# A manually triggered drain cannot measure this architecture. The exposure window would
# be "however long the experimenter waited before draining", and the reconciliation delay
# would have no observable effect at all because no debit lands while requests are in
# flight. The window is only meaningful against a worker that is actually running, so the
# worker runs.
async def _worker_loop(app, poll_ms: float) -> None:
    async def apply_debit(account_id: int, amount: Decimal) -> None:
        async with SessionLocal() as s:
            await ledger.debit_unchecked(s, account_id, amount)
            await s.commit()

    try:
        while True:
            try:
                res = await aw.drain(app.state.redis, apply_debit)
                st = app.state.async_worker_stats
                st["applied"] += res["applied"]
                st["duplicates_suppressed"] += res["duplicates_suppressed"]
                st["windows_ms"].extend(res["exposure_windows_ms"])
                st["passes"] += 1
            except Exception as exc:  # noqa: BLE001 - a worker must not die on one event
                app.state.async_worker_stats["errors"] += 1
                app.state.async_worker_stats["last_error"] = str(exc)
            await asyncio.sleep(poll_ms / 1000.0)
    except asyncio.CancelledError:
        raise


@router.post("/admin/async/worker/start")
async def worker_start(request: Request, poll_ms: float = 5.0) -> dict:
    app = request.app
    task = getattr(app.state, "async_worker_task", None)
    if task is not None and not task.done():
        return {"running": True, "already": True, "poll_ms": app.state.async_worker_poll_ms}
    app.state.async_worker_stats = {"applied": 0, "duplicates_suppressed": 0,
                                    "windows_ms": [], "passes": 0, "errors": 0}
    app.state.async_worker_poll_ms = poll_ms
    app.state.async_worker_task = asyncio.create_task(_worker_loop(app, poll_ms))
    return {"running": True, "already": False, "poll_ms": poll_ms}


@router.post("/admin/async/worker/stop")
async def worker_stop(request: Request) -> dict:
    task = getattr(request.app.state, "async_worker_task", None)
    if task is None or task.done():
        return {"running": False}
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    request.app.state.async_worker_task = None
    return {"running": False}


@router.get("/admin/async/worker/stats")
async def worker_stats(request: Request) -> dict:
    st = getattr(request.app.state, "async_worker_stats", None) or {}
    w = st.get("windows_ms", [])
    task = getattr(request.app.state, "async_worker_task", None)
    return {
        "running": bool(task and not task.done()),
        "poll_ms": getattr(request.app.state, "async_worker_poll_ms", None),
        "applied": st.get("applied", 0),
        "duplicates_suppressed": st.get("duplicates_suppressed", 0),
        "passes": st.get("passes", 0),
        "errors": st.get("errors", 0),
        "queue_depth": await aw.queue_depth(request.app.state.redis),
        # The exposure window: event creation -> durable debit. Under a running worker
        # this is a property of the architecture, not of when the experimenter looked.
        "exposure_window_ms": {
            "n": len(w),
            "min": round(min(w), 3) if w else None,
            "max": round(max(w), 3) if w else None,
            "mean": round(sum(w) / len(w), 3) if w else None,
            "p95": (round(sorted(w)[int(0.95 * (len(w) - 1))], 3) if w else None),
        },
    }


@router.get("/admin/async/balance/{account_id}")
async def live_balance(account_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    """Live balance straight from the active backend (not a trial snapshot)."""
    return {"account_id": account_id,
            "balance": str(await ledger.read_balance(session, account_id))}
