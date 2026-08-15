"""Credit-decrement primitives for flaw class 6 (limit-overrun race).

Both postures return the observed ``(balance_before, balance_after)`` so the caller
can persist an auditable ledger row and compute the *applied* debit
(``balance_before - balance_after``) independently of the intended cost.

VULNERABLE -- read-modify-write with a blind stale write::

    bal = SELECT balance                      # (1) lock-free stale read (the TOCTOU check)
    if bal >= cost: stream(...)               # (2) check, then stream (widens the window)
    SELECT balance FOR UPDATE                  # (3) observe the *current* balance (before)
    UPDATE balance = bal - cost                # (4) write a value derived from the STALE read

Step (4) writes an absolute value computed from the step-(1) read, so two handlers
that both observed ``bal`` overwrite each other's decrement (a lost update). The
``FOR UPDATE`` in step (3) only lets us *observe* the pre-image under the row lock;
it does not repair the race, because the written value still comes from the stale
read. Streaming happens before the lock is taken, so the critical section is short.

HARDENED -- atomic compare-and-decrement, committed before streaming::

    UPDATE credits SET balance = balance - :cost
    WHERE account_id = :id AND balance >= :cost
    RETURNING balance

The compare and the decrement are one serialized, row-locked statement, so no two
concurrent handlers can both pass the check on the same funds. Affected-row count
is 1 on success and 0 on insufficient funds. This is the reference defense and it
enforces: *no completed response without a committed, non-refunded debit.*
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import UsageRecord


async def read_balance(session: AsyncSession, account_id: int) -> Decimal | None:
    """Lock-free read of the current balance (the stale value in the vulnerable check)."""
    row = (
        await session.execute(
            text("SELECT balance FROM credits WHERE account_id = :a"),
            {"a": account_id},
        )
    ).first()
    return None if row is None else row[0]


async def snapshot_balance(session: AsyncSession, account_id: int) -> Decimal | None:
    """Alias for a plain balance read (used at trial finalize)."""
    return await read_balance(session, account_id)


async def debit_stale_absolute(
    session: AsyncSession, account_id: int, balance_at_check: Decimal, cost: Decimal
) -> tuple[Decimal, Decimal]:
    """VULNERABLE debit. Returns the observed ``(before, after)`` balances.

    ``balance_at_check`` is the stale, lock-free value read before streaming. The
    row is locked to observe the true pre-image (``before``), then overwritten with
    the *stale* absolute ``balance_at_check - cost`` (``after``). Concurrent
    handlers that read the same ``balance_at_check`` therefore clobber one another.
    """
    before = (
        await session.execute(
            text("SELECT balance FROM credits WHERE account_id = :a FOR UPDATE"),
            {"a": account_id},
        )
    ).scalar_one()
    after = balance_at_check - cost  # STALE absolute write value (the bug)
    await session.execute(
        text("UPDATE credits SET balance = :b WHERE account_id = :a"),
        {"b": after, "a": account_id},
    )
    return before, after


async def reserve_hardened(
    session: AsyncSession, account_id: int, cost: Decimal
) -> tuple[bool, Decimal | None, Decimal | None]:
    """HARDENED reserve: atomic compare-and-decrement.

    Returns ``(ok, before, after)``. ``ok`` is ``True`` iff exactly one row was
    updated (sufficient balance); on success ``after`` is the post-debit balance
    and ``before = after + cost``. Caller must commit promptly so the row lock is
    not held across the streaming window.
    """
    result = await session.execute(
        text(
            "UPDATE credits SET balance = balance - :c "
            "WHERE account_id = :a AND balance >= :c "
            "RETURNING balance"
        ),
        {"c": cost, "a": account_id},
    )
    row = result.first()
    if row is None:  # affected rows = 0 -> insufficient funds
        return False, None, None
    after: Decimal = row[0]
    before = after + cost
    return True, before, after


async def refund_hardened(session: AsyncSession, account_id: int, cost: Decimal) -> None:
    """Return a previously reserved amount when a served response fails to complete."""
    await session.execute(
        text("UPDATE credits SET balance = balance + :c WHERE account_id = :a"),
        {"c": cost, "a": account_id},
    )


def record_usage(
    session: AsyncSession,
    *,
    account_id: int,
    trial_id: str | None,
    request_id: str,
    posture: str,
    concurrency: int | None,
    prompt_tokens: int,
    completion_tokens: int,
    price_prompt_per_1k: Decimal,
    price_completion_per_1k: Decimal,
    cost: Decimal,
    balance_before: Decimal | None,
    balance_after: Decimal | None,
    committed: bool = True,
    refunded: bool = False,
    served: bool = True,
) -> None:
    """Append a per-request ledger row.

    ``applied_debit`` is derived as ``balance_before - balance_after`` so the true
    effect of this request on the live balance is recorded alongside the intended
    ``cost``; the two diverge exactly when a lost update occurs.
    """
    applied = None
    if balance_before is not None and balance_after is not None:
        applied = balance_before - balance_after
    session.add(
        UsageRecord(
            account_id=account_id,
            trial_id=trial_id,
            request_id=request_id,
            posture=posture,
            concurrency=concurrency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            price_prompt_per_1k=price_prompt_per_1k,
            price_completion_per_1k=price_completion_per_1k,
            cost=cost,
            balance_before=balance_before,
            balance_after=balance_after,
            applied_debit=applied,
            committed=committed,
            refunded=refunded,
            served=served,
        )
    )
