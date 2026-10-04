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
from decimal import Decimal

import redis.asyncio as aioredis

from . import async_worker as aw
from . import ledger
from .. import db as app_db
from ..config import settings

log = logging.getLogger("worker_main")


async def _apply_debit_factory():
    async def apply_debit(account_id: int, amount: Decimal) -> None:
        async with app_db.SessionLocal() as s:
            await ledger.debit_unchecked(s, account_id, amount)
            await s.commit()
    return apply_debit


async def run(poll_ms: float, stats_every: int) -> None:
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    await redis_client.ping()
    ledger.configure(redis_client)

    apply_debit = await _apply_debit_factory()

    stats = {"applied": 0, "duplicates_suppressed": 0, "passes": 0, "errors": 0}
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
                res = await aw.drain(redis_client, apply_debit)
                stats["applied"] += res["applied"]
                stats["duplicates_suppressed"] += res["duplicates_suppressed"]
                stats["passes"] += 1
                if stats["passes"] % stats_every == 0:
                    log.info("passes=%d applied=%d duplicates_suppressed=%d errors=%d",
                              stats["passes"], stats["applied"],
                              stats["duplicates_suppressed"], stats["errors"])
            except Exception as exc:  # noqa: BLE001 - a worker must not die on one event
                stats["errors"] += 1
                log.exception("drain pass failed: %s", exc)
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_ms / 1000.0)
            except asyncio.TimeoutError:
                pass
    finally:
        log.info("worker stopping: passes=%d applied=%d duplicates_suppressed=%d errors=%d",
                  stats["passes"], stats["applied"], stats["duplicates_suppressed"],
                  stats["errors"])
        await redis_client.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--poll-ms", type=float, default=5.0)
    ap.add_argument("--stats-every", type=int, default=50)
    args = ap.parse_args()
    asyncio.run(run(args.poll_ms, args.stats_every))


if __name__ == "__main__":
    main()
