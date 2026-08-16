"""Independently-implemented reference checker for the M2 defense (Phase G).

PURPOSE: reduce self-confirmation bias. The production defense
(`app/architectures/usage_authority.py` + `app/m_routes.py`) decides billing inside
the gateway. If we validated it using the same code, we would only be proving the code
agrees with itself.

This module re-derives the correct billed cost **from scratch**, deliberately sharing
NO code path with the gateway:

  * it does NOT import `app.accounting.usage`, `app.architectures.*`, or call any
    gateway helper that computes cost;
  * it re-implements tokenization-independent pricing arithmetic directly from the
    per-trial price vector reported by the API;
  * it recomputes the authoritative usage from the *observed server truth* recorded in
    each ledger row rather than from the architecture's own decision.

It then answers, independently: given this trial's prices and this request's true
usage, what SHOULD the net debit have been, and did the observed ledger satisfy the
integrity property?

Any disagreement with the gateway's own verdict is reported as a discrepancy.
"""

from __future__ import annotations

from decimal import Decimal, getcontext

getcontext().prec = 40

CENTS = Decimal("0.000001")


def _d(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


def independent_expected_cost(true_usage: dict, prices: dict) -> Decimal:
    """Recompute the authoritative cost from primitives, independently.

    Deliberately written as an explicit sum over categories with its own rounding,
    rather than reusing the application's `Usage.cost`.
    """
    per_1k = {
        "input_tokens": _d(prices["input_per_1k"]),
        "output_tokens": _d(prices["output_per_1k"]),
        "cached_input_tokens": _d(prices["cached_input_per_1k"]),
        "reasoning_tokens": _d(prices["reasoning_per_1k"]),
    }
    total = Decimal("0")
    for field, rate in per_1k.items():
        n = _d(true_usage.get(field, 0))
        total += (n * rate) / Decimal(1000)
    total = total.quantize(CENTS)
    floor = _d(prices.get("min_charge", 0))
    return total if total > floor else floor


def check_record(record: dict, prices: dict) -> dict:
    """Independently verify one M2 ledger row.

    Returns a verdict dict; `agrees` is False when our independent conclusion differs
    from the gateway's recorded `invariant_ok`.
    """
    extra = record.get("extra") or {}
    true_usage = extra.get("true") or {}
    expected = independent_expected_cost(true_usage, prices)

    observed_net = _d(record.get("net_debit"))
    observed_auth = _d(record.get("authoritative_cost"))
    served = bool(record.get("served"))

    # Independent integrity decision: a served request must be net-charged at least
    # the cost of the value it actually received.
    indep_integrity_ok = (not served) or (observed_net >= expected)
    indep_leak = (expected - observed_net) if served else -observed_net

    return {
        "request_id": record.get("request_id"),
        "independent_expected_cost": str(expected),
        "gateway_authoritative_cost": str(observed_auth),
        "cost_models_agree": expected == observed_auth,
        "observed_net_debit": str(observed_net),
        "independent_leak": str(indep_leak),
        "gateway_leak": str(_d(record.get("leak"))),
        "leaks_agree": indep_leak == _d(record.get("leak")),
        "independent_integrity_ok": indep_integrity_ok,
        "gateway_integrity_ok": bool(record.get("invariant_ok")),
        "agrees": (indep_integrity_ok == bool(record.get("invariant_ok"))
                   and indep_leak == _d(record.get("leak"))
                   and expected == observed_auth),
    }


def check_trial(audit: dict, prices: dict) -> dict:
    """Verify a whole trial: per-record agreement plus independent conservation."""
    rows = audit.get("rows", [])
    verdicts = [check_record(r, prices) for r in rows]
    disagreements = [v for v in verdicts if not v["agrees"]]

    # Independent conservation: recompute the balance delta from the ledger ourselves.
    net_sum = sum(_d(r.get("net_debit")) for r in rows)
    initial = _d(audit.get("initial_balance"))
    final = _d(audit.get("final_balance"))
    delta = (initial - final).quantize(CENTS)
    conservation_ok = (delta == net_sum.quantize(CENTS))

    # Two aggregates with DIFFERENT meanings; both are reported so the comparison is
    # made on a like-for-like basis:
    #   * signed total   -- sums over/under-payment (matches the gateway's convention)
    #   * underpay total -- sums ONLY under-payment (the security-relevant quantity)
    # Under flat-total pricing an honest client can be systematically OVERCHARGED
    # (negative leak); comparing a signed total against an underpay-only total would
    # produce a spurious "mismatch", so we compare signed-to-signed.
    indep_signed_leak = sum(_d(v["independent_leak"]) for v in verdicts)
    indep_underpay_leak = sum(_d(v["independent_leak"]) for v in verdicts
                              if _d(v["independent_leak"]) > 0)

    return {
        "trial_id": audit.get("trial_id"),
        "architecture": audit.get("architecture"),
        "records": len(rows),
        "disagreements": len(disagreements),
        "disagreement_details": disagreements[:5],
        "independent_total_leak": str(indep_signed_leak),
        "independent_underpayment_only": str(indep_underpay_leak),
        "gateway_total_leak": str(_d(audit.get("total_leak"))),
        "total_leak_agrees": indep_signed_leak == _d(audit.get("total_leak")),
        "overcharges_honest_client": indep_signed_leak < 0,
        "independent_conservation_ok": conservation_ok,
        "gateway_reconciled": audit.get("reconciled"),
        "verdict_agrees": (not disagreements
                           and conservation_ok
                           and indep_signed_leak == _d(audit.get("total_leak"))),
    }
