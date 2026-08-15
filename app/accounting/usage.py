"""Realistic LLM usage vectors and multi-category pricing (exact Decimal).

A usage record is not a single scalar: real LLM billing distinguishes input,
output, cached-input (discounted), and reasoning/hidden tokens, with a minimum
charge and rounding. Modeling these categories is what makes M2 (usage-record
authority) a substantive integrity question rather than "client sends tokens=1":
a dishonest client can under-report a *subtotal*, drop a *category*, or make the
declared *total* disagree with the subtotals, and whether that is exploitable
depends on which quantity the server actually bills and whether it recounts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal

CENTS = Decimal("0.000001")


def D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


@dataclass(frozen=True)
class Prices:
    """Per-1k-token prices for each usage category (mock dollars)."""

    input_per_1k: Decimal
    output_per_1k: Decimal
    cached_input_per_1k: Decimal
    reasoning_per_1k: Decimal
    min_charge: Decimal = Decimal("0")

    @staticmethod
    def tier(name: str) -> "Prices":
        """Synthetic price tiers shaped like real cheap/mid/frontier models."""
        t = {
            "low": ("0.05", "0.15", "0.005", "0.15"),
            "medium": ("0.5", "1.5", "0.05", "1.5"),
            "high": ("3.0", "15.0", "0.30", "15.0"),
        }[name]
        return Prices(D(t[0]), D(t[1]), D(t[2]), D(t[3]), Decimal("0"))

    def as_dict(self) -> dict:
        return {k: str(v) for k, v in asdict(self).items()}


@dataclass
class Usage:
    """A token-usage vector. All fields are non-negative integers."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    # `declared_total` lets a dishonest client assert a total that disagrees with
    # the subtotals (a real manipulation); None means "derive from subtotals".
    declared_total: int | None = None

    @property
    def subtotal_total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cached_input_tokens
            + self.reasoning_tokens
        )

    @property
    def total(self) -> int:
        return self.declared_total if self.declared_total is not None else self.subtotal_total

    def cost(self, prices: Prices) -> Decimal:
        """Category-wise cost (the authoritative pricing function)."""
        c = (
            D(self.input_tokens) / 1000 * prices.input_per_1k
            + D(self.output_tokens) / 1000 * prices.output_per_1k
            + D(self.cached_input_tokens) / 1000 * prices.cached_input_per_1k
            + D(self.reasoning_tokens) / 1000 * prices.reasoning_per_1k
        )
        c = c.quantize(CENTS)
        return max(c, prices.min_charge)

    def cost_on_total(self, prices: Prices) -> Decimal:
        """Naive pricing that bills the (possibly declared) total at the output rate.

        Some real meters collapse usage to a single number and price it uniformly;
        this is exactly the anti-pattern that lets `declared_total` manipulation pay
        off. Provided so architectures can choose their billing basis explicitly.
        """
        c = (D(self.total) / 1000 * prices.output_per_1k).quantize(CENTS)
        return max(c, prices.min_charge)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["total"] = self.total
        d["subtotal_total"] = self.subtotal_total
        return d

    def copy(self) -> "Usage":
        return Usage(
            self.input_tokens,
            self.output_tokens,
            self.cached_input_tokens,
            self.reasoning_tokens,
            self.declared_total,
        )
