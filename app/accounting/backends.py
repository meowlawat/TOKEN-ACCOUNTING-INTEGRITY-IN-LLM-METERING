"""Two accounting BACKENDS behind one semantic interface (Phase 3).

The question is architectural generality: do the accounting-security results depend on
storing the balance as a mutable row, or do they follow from *where* synchronization,
commitment and authority sit --- independently of how the money is stored?

Backend A --- ``mutable`` (the original)
    A single mutable ``credits.balance`` row. Reads observe the current value; debits
    and refunds mutate it in place. Atomicity comes from a row-level
    compare-and-decrement.

Backend B --- ``ledger`` (append-only, derived balance)
    ``credits.balance`` is never mutated by the accounting path. Instead every movement
    is an immutable row in ``ledger_entries`` (positive = credit, negative = debit), and
    the balance is a *derived* quantity: ``SUM(delta)`` over the account's entries. This
    is the event-sourced design common in billing systems.

    The atomic reserve is expressed differently: rather than a conditional UPDATE on a
    row, it is a conditional INSERT guarded by a serialized read of the derived balance
    (``SELECT ... FOR UPDATE`` on the account's anchor row), which is the standard way to
    keep an append-only ledger consistent.

Both backends expose the SAME four operations, so the attack harness and the
architectures (M1/M2/B0) are unchanged:

    read_balance(session, account_id)                -> Decimal
    reserve_atomic(session, account_id, amount)      -> (ok, new_balance)
    debit_unchecked(session, account_id, amount)     -> new_balance
    credit(session, account_id, amount)              -> new_balance

Selection is per-request via a shared runtime setting so a single deployment can be
switched between backends without redeploying.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_KEY = "tai:accounting_backend"
VALID = ("mutable", "ledger")


# --------------------------------------------------------------------------- #
# Backend A: mutable balance row (original semantics)
# --------------------------------------------------------------------------- #
async def _mutable_read(session: AsyncSession, account_id: int) -> Decimal | None:
    row = (await session.execute(
        text("SELECT balance FROM credits WHERE account_id = :a"), {"a": account_id})).first()
    return None if row is None else row[0]


async def _mutable_reserve(session: AsyncSession, account_id: int, amount: Decimal):
    row = (await session.execute(
        text("UPDATE credits SET balance = balance - :c "
             "WHERE account_id = :a AND balance >= :c RETURNING balance"),
        {"c": amount, "a": account_id})).first()
    return (row is not None), (row[0] if row else None)


async def _mutable_debit(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    row = (await session.execute(
        text("UPDATE credits SET balance = balance - :c WHERE account_id = :a RETURNING balance"),
        {"c": amount, "a": account_id})).first()
    return row[0]


async def _mutable_credit(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    row = (await session.execute(
        text("UPDATE credits SET balance = balance + :c WHERE account_id = :a RETURNING balance"),
        {"c": amount, "a": account_id})).first()
    return row[0]


# --------------------------------------------------------------------------- #
# Backend B: append-only ledger with derived balance
# --------------------------------------------------------------------------- #
async def _ledger_read(session: AsyncSession, account_id: int) -> Decimal | None:
    """Balance is DERIVED: opening balance + sum of immutable entries."""
    row = (await session.execute(
        text("SELECT c.opening_balance + COALESCE("
             "  (SELECT SUM(le.delta) FROM ledger_entries le WHERE le.account_id = c.account_id), 0) "
             "FROM credits c WHERE c.account_id = :a"),
        {"a": account_id})).first()
    return None if row is None else row[0]


async def _ledger_reserve(session: AsyncSession, account_id: int, amount: Decimal):
    """Conditional append: serialize on the anchor row, then insert iff funds suffice.

    The anchor `SELECT ... FOR UPDATE` is what makes the check-and-append atomic with
    respect to competing transactions; it is the append-only analogue of the mutable
    backend's conditional UPDATE.
    """
    await session.execute(
        text("SELECT account_id FROM credits WHERE account_id = :a FOR UPDATE"),
        {"a": account_id})
    bal = await _ledger_read(session, account_id)
    if bal is None or bal < amount:
        return False, bal
    await session.execute(
        text("INSERT INTO ledger_entries (account_id, delta, kind) "
             "VALUES (:a, :d, 'reserve')"),
        {"a": account_id, "d": -amount})
    return True, (bal - amount)


async def _ledger_debit(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    await session.execute(
        text("INSERT INTO ledger_entries (account_id, delta, kind) VALUES (:a, :d, 'debit')"),
        {"a": account_id, "d": -amount})
    return await _ledger_read(session, account_id)


async def _ledger_credit(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    await session.execute(
        text("INSERT INTO ledger_entries (account_id, delta, kind) VALUES (:a, :d, 'refund')"),
        {"a": account_id, "d": amount})
    return await _ledger_read(session, account_id)


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
_IMPL = {
    "mutable": (_mutable_read, _mutable_reserve, _mutable_debit, _mutable_credit),
    "ledger": (_ledger_read, _ledger_reserve, _ledger_debit, _ledger_credit),
}


async def read_balance(session: AsyncSession, account_id: int, backend: str) -> Decimal | None:
    return await _IMPL[backend][0](session, account_id)


async def reserve_atomic(session: AsyncSession, account_id: int, amount: Decimal, backend: str):
    return await _IMPL[backend][1](session, account_id, amount)


async def debit_unchecked(session: AsyncSession, account_id: int, amount: Decimal, backend: str) -> Decimal:
    return await _IMPL[backend][2](session, account_id, amount)


async def credit(session: AsyncSession, account_id: int, amount: Decimal, backend: str) -> Decimal:
    return await _IMPL[backend][3](session, account_id, amount)


async def set_balance(session: AsyncSession, account_id: int, amount: Decimal, backend: str) -> None:
    """Reset an account to an exact balance (experiment setup, not an accounting op)."""
    if backend == "ledger":
        await session.execute(
            text("DELETE FROM ledger_entries WHERE account_id = :a"), {"a": account_id})
        await session.execute(
            text("UPDATE credits SET opening_balance = :b, balance = :b WHERE account_id = :a"),
            {"b": amount, "a": account_id})
    else:
        await session.execute(
            text("UPDATE credits SET balance = :b, opening_balance = :b WHERE account_id = :a"),
            {"b": amount, "a": account_id})
