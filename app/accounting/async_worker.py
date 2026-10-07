"""Asynchronous accounting: inference and settlement decoupled in time.

Both existing accounting backends are strongly consistent -- settlement completes before
the request does. Real metering pipelines frequently are not: the gateway emits a usage
*event*, and a separate worker applies it to the ledger some time later. The paper cannot
claim architectural generality while quietly assuming the easy case, so this module adds a
controlled asynchronous path.

The goal is NOT to simulate a cloud provider. It is to answer one question:

    what changes when inference execution and financial accounting are
    decoupled in time?

Design, deliberately minimal:

    gateway --(usage event)--> Redis queue --(delay D)--> worker --> durable ledger

`D` is a controlled reconciliation delay, not a race we hope to observe. Between event
creation and event application there is an **exposure window** in which value has been
delivered and no debit exists. That window is the object of study: it is a property of the
architecture, and it exists even when every component behaves correctly.

Failure modes are injectable because they are the interesting part: an event may be lost,
duplicated, delayed, or created only after the client has already disconnected.

CLOCK SOURCE. `created_ns`/`deliver_after_ns` are `time.time_ns()` (wall-clock, UTC epoch),
not `time.perf_counter_ns()`. This module originally used `perf_counter_ns()`, which is a
monotonic clock with an arbitrary, process-and-boot-local origin: on Linux it is
`CLOCK_MONOTONIC` relative to that kernel's boot time, and two different Linux kernels
(e.g. two containers, or two VMs, or two physical hosts) do not share an origin at all.
This was safe only by accident, as long as the worker ran as an asyncio task inside the
same process that created the event (`app/async_routes.py::_worker_loop`). The moment the
worker becomes a separate OS process -- even still on the "same machine," if that machine
runs the gateway inside a container or VM with its own boot time, which is exactly what
Docker Desktop on Windows does -- the comparison `perf_counter_ns() < deliver_after_ns`
compares two unrelated numbers and the result depends on which process happened to boot
more recently, not on elapsed wall time since the event was created. Confirmed empirically
during the two-machine experiment (see experiments/two_machine/RESEARCH_LOG.md, Phase 3
attempt 4): a host-side worker's `perf_counter_ns()` measured ~104x larger than the
gateway container's, so every event looked instantly due regardless of the configured
delay. `time.time_ns()` is the UTC epoch in nanoseconds, which every process and host
agrees on up to their system clocks' actual synchronization (NTP et al.) -- the quantity
that is genuinely shared, rather than an artifact of process/VM/machine boot order.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from decimal import Decimal

QUEUE_KEY = "accounting:queue"
APPLIED_KEY = "accounting:applied"      # event ids already applied (idempotency set)
DEADLETTER_KEY = "accounting:deadletter"


@dataclass
class UsageEvent:
    """A usage record in flight between the gateway and the ledger."""

    event_id: str
    account_id: int
    request_id: str
    trial_id: str
    architecture: str
    delivered_tokens: int
    amount: str                  # Decimal serialized; the debit to apply
    authoritative: str           # value actually delivered, for the integrity check
    created_ns: int
    deliver_after_ns: int        # when the worker is allowed to apply it
    attempt: int = 0
    meta: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "UsageEvent":
        return UsageEvent(**json.loads(s))


async def emit(redis, ev: UsageEvent) -> None:
    """Gateway side: hand the usage event off and return. No ledger write happens here."""
    await redis.rpush(QUEUE_KEY, ev.to_json())


async def queue_depth(redis) -> int:
    return int(await redis.llen(QUEUE_KEY))


async def drain(redis, apply_debit, *, max_events: int = 10_000,
                idempotent: bool = True, on_applied=None) -> dict:
    """Worker side: apply every event whose delay has elapsed.

    `apply_debit(account_id, amount, event_id=None) -> None` performs the durable ledger
    write. `event_id` is passed for B0-async events only (those with a durable outbox row,
    DURABILITY_HARDENING_AUDIT.md) so an outbox-aware implementation can atomically claim
    the outbox row in the same transaction as the debit; an implementation that ignores
    the parameter (every pre-existing one) behaves exactly as before.

    `on_applied`, if given, is an optional `async (ev, popped_ns, applied_ns) -> None`
    hook called after a debit is successfully applied (never for duplicates/not-yet-due
    events). It exists for the Tier-1 mechanism instrumentation added in the experimental-
    strengthening phase (see EXPERIMENTAL_STRENGTHENING_AUDIT.md) and changes nothing about
    existing behavior when omitted: every pre-existing caller passes no `on_applied`, so
    `drain()`'s core timing/counters (including `exposure_windows_ms`, unchanged) are
    identical to before this parameter existed. A failure inside the hook is caught and
    counted but never aborts the drain pass -- the same "a worker must not die on one
    event" principle the rest of this function already follows.

    Returns counters describing what happened, including the observed exposure window
    per event (creation -> application), which is the quantity the experiment measures.
    """
    applied = duplicates = skipped = 0
    windows_ms: list[float] = []
    hook_errors = 0
    remaining: list[str] = []

    for _ in range(max_events):
        raw = await redis.lpop(QUEUE_KEY)
        if raw is None:
            break
        if isinstance(raw, bytes):
            raw = raw.decode()
        ev = UsageEvent.from_json(raw)

        if time.time_ns() < ev.deliver_after_ns:
            remaining.append(raw)       # not due yet; put back after the pass
            skipped += 1
            continue

        if idempotent and await redis.sismember(APPLIED_KEY, ev.event_id):
            duplicates += 1             # at-least-once delivery, applied exactly once
            continue

        popped_ns = time.time_ns()
        # `event_id` is passed only for B0-async events (the ones with a durable outbox
        # row, DURABILITY_HARDENING_AUDIT.md) -- every pre-existing `apply_debit`
        # implementation accepts and ignores this as an optional keyword argument, so
        # callers that pass none (M1's settlement path, which has no outbox row) are
        # completely unaffected. Only an outbox-aware `apply_debit` acts on it.
        event_id_for_outbox = ev.event_id if ev.architecture == "async_b0" else None
        await apply_debit(ev.account_id, Decimal(ev.amount), event_id=event_id_for_outbox)
        applied_ns = time.time_ns()
        if idempotent:
            await redis.sadd(APPLIED_KEY, ev.event_id)
        applied += 1
        windows_ms.append((applied_ns - ev.created_ns) / 1e6)

        if on_applied is not None:
            try:
                await on_applied(ev, popped_ns, applied_ns)
            except Exception as exc:  # noqa: BLE001 - instrumentation must not break settlement
                hook_errors += 1
                import logging
                logging.getLogger("async_worker").exception(
                    "on_applied hook failed for request_id=%s: %s", ev.request_id, exc)

    for raw in remaining:
        await redis.rpush(QUEUE_KEY, raw)

    return {"applied": applied, "duplicates_suppressed": duplicates,
            "not_yet_due": skipped, "exposure_windows_ms": windows_ms,
            "on_applied_errors": hook_errors}


async def reset(redis) -> None:
    await redis.delete(QUEUE_KEY, APPLIED_KEY, DEADLETTER_KEY)


def new_event(*, account_id: int, request_id: str, trial_id: str, architecture: str,
              delivered_tokens: int, amount: Decimal, authoritative: Decimal,
              delay_ms: float, meta: dict | None = None) -> UsageEvent:
    now = time.time_ns()
    return UsageEvent(
        event_id=uuid.uuid4().hex,
        account_id=account_id, request_id=request_id, trial_id=trial_id,
        architecture=architecture, delivered_tokens=delivered_tokens,
        amount=str(amount), authoritative=str(authoritative),
        created_ns=now, deliver_after_ns=now + int(delay_ms * 1e6),
        meta=meta or {},
    )
