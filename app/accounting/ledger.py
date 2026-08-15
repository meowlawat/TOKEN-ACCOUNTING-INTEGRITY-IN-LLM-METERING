"""Async DB ledger primitives for the M-mechanisms.

Deliberately small and explicit so each architecture's commit semantics are
visible. Reuses the same atomic compare-and-decrement as the B0 defense.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def read_balance(session: AsyncSession, account_id: int) -> Decimal | None:
    row = (
        await session.execute(
            text("SELECT balance FROM credits WHERE account_id = :a"), {"a": account_id}
        )
    ).first()
    return None if row is None else row[0]


async def reserve_atomic(session: AsyncSession, account_id: int, amount: Decimal) -> tuple[bool, Decimal | None]:
    """Atomic compare-and-decrement reserve (row-count semantics: 1=ok, 0=insufficient)."""
    row = (
        await session.execute(
            text(
                "UPDATE credits SET balance = balance - :c "
                "WHERE account_id = :a AND balance >= :c RETURNING balance"
            ),
            {"c": amount, "a": account_id},
        )
    ).first()
    return (row is not None), (row[0] if row else None)


async def debit_unchecked(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    """Decrement without a floor (may go negative). Returns new balance."""
    row = (
        await session.execute(
            text("UPDATE credits SET balance = balance - :c WHERE account_id = :a RETURNING balance"),
            {"c": amount, "a": account_id},
        )
    ).first()
    return row[0]


async def credit(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    """Refund / add back. Returns new balance."""
    row = (
        await session.execute(
            text("UPDATE credits SET balance = balance + :c WHERE account_id = :a RETURNING balance"),
            {"c": amount, "a": account_id},
        )
    ).first()
    return row[0]


async def set_balance(session: AsyncSession, account_id: int, amount: Decimal) -> None:
    await session.execute(
        text("UPDATE credits SET balance = :b WHERE account_id = :a"), {"b": amount, "a": account_id}
    )
