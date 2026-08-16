"""Accounting primitives used by the M-mechanisms.

This module is a thin façade over the pluggable accounting BACKENDS
(`app/accounting/backends.py`). The M1/M2 architectures and the attack harness call
these functions and are unaware of whether the balance is stored as a mutable row or
derived from an append-only ledger --- which is exactly what lets us test whether the
accounting-security results depend on the storage architecture.

The active backend is shared runtime state (Redis), so every worker and every gateway
instance agrees; it falls back to the process default when Redis is unavailable.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from . import backends

# Process-local fallback; the authoritative value lives in Redis under BACKEND_KEY.
_DEFAULT_BACKEND = "mutable"
_state = {"backend": _DEFAULT_BACKEND, "redis": None}


def configure(redis_client, default: str = _DEFAULT_BACKEND) -> None:
    """Attach the shared-state client used to resolve the active backend."""
    _state["redis"] = redis_client
    _state["backend"] = default


async def active_backend() -> str:
    """Resolve the active accounting backend from shared state."""
    r = _state.get("redis")
    if r is not None:
        try:
            v = await r.get(backends.BACKEND_KEY)
            if v in backends.VALID:
                return v
        except Exception:  # noqa: BLE001
            pass
    return _state["backend"]


async def set_backend(name: str) -> str:
    if name not in backends.VALID:
        raise ValueError(f"unknown accounting backend {name!r}")
    _state["backend"] = name
    r = _state.get("redis")
    if r is not None:
        try:
            await r.set(backends.BACKEND_KEY, name)
        except Exception:  # noqa: BLE001
            pass
    return name


# --------------------------------------------------------------------------- #
# The interface the architectures use (unchanged signatures)
# --------------------------------------------------------------------------- #
async def read_balance(session: AsyncSession, account_id: int) -> Decimal | None:
    return await backends.read_balance(session, account_id, await active_backend())


async def snapshot_balance(session: AsyncSession, account_id: int) -> Decimal | None:
    return await read_balance(session, account_id)


async def reserve_atomic(session: AsyncSession, account_id: int, amount: Decimal):
    """Atomic compare-and-reserve. Returns (ok, new_balance)."""
    return await backends.reserve_atomic(session, account_id, amount, await active_backend())


async def debit_unchecked(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    """Decrement without a floor (may go negative). Returns the new balance."""
    return await backends.debit_unchecked(session, account_id, amount, await active_backend())


async def credit(session: AsyncSession, account_id: int, amount: Decimal) -> Decimal:
    """Refund / add back. Returns the new balance."""
    return await backends.credit(session, account_id, amount, await active_backend())


async def set_balance(session: AsyncSession, account_id: int, amount: Decimal) -> None:
    """Experiment setup: force an exact balance under the active backend."""
    await backends.set_balance(session, account_id, amount, await active_backend())
