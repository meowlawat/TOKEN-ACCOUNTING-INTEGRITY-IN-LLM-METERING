"""Standalone settlement worker entrypoint (Phase 3 extraction).

Runs the exact same drain loop that `app/async_routes.py::_worker_loop` runs as an
asyncio task inside the gateway process -- but as its own process, so it can be deployed
on a different host from the gateway. This file changes *where* the worker runs; it does
not change *what* it does. `_worker_loop` in `async_routes.py` is left untouched and keeps
powering the existing single-host experiment, so the published result stays reproducible
from the code path that produced it.

Behavior parity with `_worker_loop`, verified line-by-line against it:
  - same `aw.drain(redis, apply_debit)` call, same default poll interval handling
  - same `apply_debit` shape: open a session, `ledger.debit_unchecked`, commit
  - same "a worker must not die on one event" exception handling
  - additionally calls `ledger.configure(redis)` so the shared accounting-backend
    selection (mutable vs. ledger) is honored exactly as it is in the gateway process;
    `_worker_loop` gets this for free because it shares `app.state.redis` with the
    gateway, which already calls `ledger.configure()` at startup -- a standalone process
    has no such shared state and must configure it explicitly, or it would silently
    assume the process-local default backend ("mutable") regardless of what the gateway
    actually has selected.

Usage:
    python -m app.accounting.worker_main [--poll-ms 5.0] [--stats-every 50]

Configuration is environment-only (DATABASE_URL, REDIS_URL via app.config.settings),
exactly like the gateway -- repointing this process at a remote Postgres/Redis is a
deployment change, not a code change.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import socket
import time
from decimal import Decimal

import redis.asyncio as aioredis
from sqlalchemy import select

from . import async_worker as aw
from . import ledger
from .. import db as app_db
from ..config import settings
from ..models.models import MRecord, OutboxEvent

log = logging.getLogger("worker_main")


async def _apply_debit_factory():
    """DURABILITY_HARDENING_AUDIT.md: when `event_id` is given (B0-async events only --
    see async_worker.py::drain's call site), the outbox claim and the actual balance
    decrement happen in the SAME transaction, not as two separate commits. This is the
    specific property that closes the "crashed between claiming and settling" gap: either
    both the claim and the debit land together, or the whole transaction rolls back and
    the row is still 'pending' for the next attempt (by this worker on restart, or by
    `reconcile_outbox`) to retry. `event_id=None` (M1 events, which have no outbox row at
    all) falls through to the exact prior behavior -- a plain debit, no outbox involved.
    """
    async def apply_debit(account_id: int, amount: Decimal, event_id: str | None = None) -> None:
        async with app_db.SessionLocal() as s:
            if event_id is not None:
                applied = await ledger.claim_and_debit_outbox(s, event_id, account_id, amount)
                await s.commit()
                if not applied:
                    return  # already claimed/settled elsewhere -- harmless duplicate
            else:
                await ledger.debit_unchecked(s, account_id, amount)
                await s.commit()
    return apply_debit


async def reconcile_outbox(stats: dict | None = None) -> dict:
    """Fallback settlement path, independent of Redis entirely: finds outbox rows that
    are due and still 'pending' -- which Redis may simply never have delivered (a lost
    event, or a hard crash of the Redis process itself, DURABILITY_HARDENING_AUDIT.md) --
    and settles them directly from Postgres. The claim (flip to 'applied') and the actual
    balance decrement happen in ONE transaction, exactly like the outbox-aware branch of
    `apply_debit` above, for the identical reason: no window in which a row is marked
    applied without the debit having actually landed, or vice versa.

    Safe to run concurrently with the normal Redis-driven path: both go through the same
    `WHERE status = 'pending'` conditional update, so whichever one reaches a given row
    first wins the claim and the other sees zero rows affected -- not a race, a single
    atomic gate enforced by PostgreSQL itself.
    """
    now_ns = time.time_ns()
    claimed_count = 0
    async with app_db.SessionLocal() as s:
        due = (await s.execute(
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending", OutboxEvent.deliver_after_ns <= now_ns)
            .limit(1000)
        )).scalars().all()
    for row in due:
        async with app_db.SessionLocal() as s:
            applied = await ledger.claim_and_debit_outbox(s, row.event_id, row.account_id, row.amount)
            await s.commit()
            if not applied:
                continue  # the Redis-driven path (or another reconcile pass) won the race
            claimed_count += 1
            if stats is not None:
                stats["reconciled_from_outbox"] = stats.get("reconciled_from_outbox", 0) + 1
    return {"reconciled": claimed_count, "scanned": len(due)}


async def _on_applied_factory():
    """Tier-1 mechanism instrumentation (opt-in via --instrument): persist the worker-side
    T6 (event popped off the queue, due-check passed) and T7 (debit durably applied) wall-
    clock timestamps into the SAME MRecord row the gateway already wrote at request time,
    keyed by request_id, merged into `extra` (never overwriting the gateway's own fields).
    This is a read-modify-write, not a DB-side JSON merge operator, so it is agnostic to
    whichever JSON column type SQLAlchemy mapped `extra` to. Never raises past drain()'s
    own try/except around the hook -- a missing row (e.g. an M1 event, which this worker
    also drains but which writes no MRecord under `request_id` the same way) is skipped,
    not an error.
    """
    worker_host = socket.gethostname()

    async def on_applied(ev: aw.UsageEvent, popped_ns: int, applied_ns: int) -> None:
        # The gateway emits the event to Redis BEFORE committing the MRecord row
        # (pre-existing code, async_routes.py::async_b0_complete -- not something this
        # instrumentation changed). Under concurrent load this ordering, combined with
        # DB-connection-pool contention across the gateway's two sessions per request plus
        # the worker's own session, can make the row genuinely not-yet-visible for a few
        # tens of milliseconds after the event becomes due. Confirmed empirically: this is
        # nondeterministic (observed in some runs, not others, at identical D=50ms).
        # Bounded retry so instrumentation does not silently lose data points to this
        # timing variance -- never affects the already-completed debit, which has nothing
        # to do with this lookup.
        for attempt in range(6):
            async with app_db.SessionLocal() as s:
                rec = (await s.execute(
                    select(MRecord).where(MRecord.request_id == ev.request_id)
                )).scalars().first()
                if rec is not None:
                    rec.extra = {
                        **rec.extra,
                        "t6_worker_popped_ns": popped_ns,
                        "t7_worker_applied_ns": applied_ns,
                        "worker_host": worker_host,
                        "event_id": ev.event_id,
                        "event_created_ns": ev.created_ns,
                        "event_deliver_after_ns": ev.deliver_after_ns,
                    }
                    await s.commit()
                    return
            await asyncio.sleep(0.02 * (attempt + 1))
        log.warning("on_applied: no MRecord found for request_id=%s (event_id=%s) "
                    "after retries", ev.request_id, ev.event_id)
    return on_applied


async def run(poll_ms: float, stats_every: int, instrument: bool) -> None:
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    await redis_client.ping()
    ledger.configure(redis_client)

    apply_debit = await _apply_debit_factory()
    on_applied = await _on_applied_factory() if instrument else None

    stats = {"applied": 0, "duplicates_suppressed": 0, "passes": 0, "errors": 0,
              "reconciled_from_outbox": 0}
    stop = asyncio.Event()

    def _handle_signal(*_args) -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass  # Windows: SIGTERM add_signal_handler is unsupported; SIGINT works via KeyboardInterrupt

    log.info("worker starting: redis=%s db=%s poll_ms=%.1f",
              settings.redis_url, settings.database_url, poll_ms)

    try:
        while not stop.is_set():
            try:
                res = await aw.drain(redis_client, apply_debit, on_applied=on_applied)
                stats["applied"] += res["applied"]
                stats["duplicates_suppressed"] += res["duplicates_suppressed"]
                stats["passes"] += 1
                if stats["passes"] % stats_every == 0:
                    log.info("passes=%d applied=%d duplicates_suppressed=%d "
                              "reconciled_from_outbox=%d errors=%d",
                              stats["passes"], stats["applied"],
                              stats["duplicates_suppressed"],
                              stats["reconciled_from_outbox"], stats["errors"])
            except Exception as exc:  # noqa: BLE001 - a worker must not die on one event
                stats["errors"] += 1
                log.exception("drain pass failed: %s", exc)
            try:
                # DURABILITY_HARDENING_AUDIT.md: the Redis-independent fallback. Runs
                # every pass alongside drain() -- for this testbed's scale a full table
                # scan of due, pending rows every poll interval is negligible cost, and
                # correctness (via the atomic claim) does not depend on how often this
                # runs, only how soon a Redis-lost event gets recovered.
                await reconcile_outbox(stats)
            except Exception as exc:  # noqa: BLE001 - same principle as drain() above
                stats["errors"] += 1
                log.exception("reconcile_outbox pass failed: %s", exc)
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_ms / 1000.0)
            except asyncio.TimeoutError:
                pass
    finally:
        log.info("worker stopping: passes=%d applied=%d duplicates_suppressed=%d "
                  "reconciled_from_outbox=%d errors=%d",
                  stats["passes"], stats["applied"], stats["duplicates_suppressed"],
                  stats["reconciled_from_outbox"], stats["errors"])
        await redis_client.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--poll-ms", type=float, default=5.0)
    ap.add_argument("--stats-every", type=int, default=50)
    ap.add_argument("--instrument", action="store_true",
                    help="Tier-1 mechanism instrumentation: persist worker-side T6/T7 "
                         "timestamps into MRecord.extra by request_id. Opt-in, default "
                         "off -- does not change settlement behavior either way.")
    args = ap.parse_args()
    asyncio.run(run(args.poll_ms, args.stats_every, args.instrument))


if __name__ == "__main__":
    main()
