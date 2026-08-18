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
                idempotent: bool = True) -> dict:
    """Worker side: apply every event whose delay has elapsed.

    `apply_debit(account_id, amount) -> None` performs the durable ledger write.

    Returns counters describing what happened, including the observed exposure window
    per event (creation -> application), which is the quantity the experiment measures.
    """
    applied = duplicates = skipped = 0
    windows_ms: list[float] = []
    remaining: list[str] = []

    for _ in range(max_events):
        raw = await redis.lpop(QUEUE_KEY)
        if raw is None:
            break
        if isinstance(raw, bytes):
            raw = raw.decode()
        ev = UsageEvent.from_json(raw)

        if time.perf_counter_ns() < ev.deliver_after_ns:
            remaining.append(raw)       # not due yet; put back after the pass
            skipped += 1
            continue

        if idempotent and await redis.sismember(APPLIED_KEY, ev.event_id):
            duplicates += 1             # at-least-once delivery, applied exactly once
            continue

        await apply_debit(ev.account_id, Decimal(ev.amount))
        if idempotent:
            await redis.sadd(APPLIED_KEY, ev.event_id)
        applied += 1
        windows_ms.append((time.perf_counter_ns() - ev.created_ns) / 1e6)

    for raw in remaining:
        await redis.rpush(QUEUE_KEY, raw)

    return {"applied": applied, "duplicates_suppressed": duplicates,
            "not_yet_due": skipped, "exposure_windows_ms": windows_ms}


async def reset(redis) -> None:
    await redis.delete(QUEUE_KEY, APPLIED_KEY, DEADLETTER_KEY)


def new_event(*, account_id: int, request_id: str, trial_id: str, architecture: str,
              delivered_tokens: int, amount: Decimal, authoritative: Decimal,
              delay_ms: float, meta: dict | None = None) -> UsageEvent:
    now = time.perf_counter_ns()
    return UsageEvent(
        event_id=uuid.uuid4().hex,
        account_id=account_id, request_id=request_id, trial_id=trial_id,
        architecture=architecture, delivered_tokens=delivered_tokens,
        amount=str(amount), authoritative=str(authoritative),
        created_ns=now, deliver_after_ns=now + int(delay_ms * 1e6),
        meta=meta or {},
    )
