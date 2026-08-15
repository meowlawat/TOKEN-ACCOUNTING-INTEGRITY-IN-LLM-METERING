"""Token -> money conversion, in exact decimal arithmetic."""

from __future__ import annotations

from decimal import Decimal

# All money is quantized to 6 fractional digits to match NUMERIC(18,6).
_CENTS = Decimal("0.000001")


def _d(value: float | str | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def cost_of(
    prompt_tokens: int,
    completion_tokens: int,
    price_prompt_per_1k: float,
    price_completion_per_1k: float,
) -> Decimal:
    """Return the server-side recomputed cost of a completion (mock dollars).

    This is the honest, server-side metering used by the class-6 experiments; it
    never trusts a client-declared token count (that is the separate class-2
    flaw). The result is quantized so ``k * cost_of(...)`` is exact.
    """
    cost = (
        _d(prompt_tokens) / Decimal(1000) * _d(price_prompt_per_1k)
        + _d(completion_tokens) / Decimal(1000) * _d(price_completion_per_1k)
    )
    return cost.quantize(_CENTS)
