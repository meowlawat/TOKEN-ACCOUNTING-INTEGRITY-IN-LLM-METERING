"""Independent M2 accounting model (audit fix F4).

Derives true usage, attacker transformations, pricing and billed cost **from the
documented specification**, importing nothing from the project. In particular it does
NOT read `extra["true"]` — the gateway's own ground-truth field — which is what made the
previous "independent" checker only partially independent.

Specification re-implemented here (from the mock-model documentation, not from code):

    input_tokens     = max(1, whitespace word count of the prompt)
    output_tokens    = MIN + (int(sha256(f"{seed}:{prompt}").hexdigest()[:16], 16) % SPAN)
                       with MIN = 40, MAX = 80, SPAN = MAX - MIN + 1
    reasoning_tokens = output_tokens // 2
    cached_input     = 0

    cost_category(U) = quantize6( in/1000*p_in + out/1000*p_out
                                + cached/1000*p_cache + reason/1000*p_reason )
    cost_flat_total(U) = quantize6( total/1000 * p_out )

Declared-usage transformations are re-implemented from their documented definitions.

Dependency note: no third-party tokenizer is required here, because the mock model's
token counts are defined arithmetically. The only dependency is `hashlib`.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, getcontext

getcontext().prec = 50

CENTS = Decimal("0.000001")
MIN_TOK, MAX_TOK = 40, 80
CATS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")

# (input, output, cached_input, reasoning) per 1k tokens
TIERS = {
    "low":    ("0.05", "0.15", "0.005", "0.15"),
    "medium": ("0.5", "1.5", "0.05", "1.5"),
    "high":   ("3.0", "15.0", "0.30", "15.0"),
}

# Which billing basis each architecture uses. This is a *specification* fact taken from
# the paper's taxonomy; the CONSEQUENCE (billed cost, leak) is computed here.
BASIS = {
    "client": "category",
    "client_logged": "category",
    "client_total": "flat_total",
    "server_recount": "server",
    "hybrid_reconcile": "server",
    "upstream": "server",
}


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


# --------------------------------------------------------------------------- #
# Ground truth from first principles
# --------------------------------------------------------------------------- #
def input_tokens(prompt: str) -> int:
    return max(1, len(prompt.split()))


def output_tokens(prompt: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{prompt}".encode("utf-8")).hexdigest()
    return MIN_TOK + (int(digest[:16], 16) % (MAX_TOK - MIN_TOK + 1))


def true_usage(prompt: str, seed: int) -> dict:
    out = output_tokens(prompt, seed)
    return {"input_tokens": input_tokens(prompt), "output_tokens": out,
            "cached_input_tokens": 0, "reasoning_tokens": out // 2,
            "declared_total": None}


def subtotal(u: dict) -> int:
    return sum(int(u.get(c, 0)) for c in CATS)


def total(u: dict) -> int:
    dt = u.get("declared_total")
    return int(dt) if dt is not None else subtotal(u)


# --------------------------------------------------------------------------- #
# Pricing
# --------------------------------------------------------------------------- #
def cost_category(u: dict, tier: str) -> Decimal:
    p_in, p_out, p_cache, p_reason = (D(x) for x in TIERS[tier])
    c = (D(u.get("input_tokens", 0)) / 1000 * p_in
         + D(u.get("output_tokens", 0)) / 1000 * p_out
         + D(u.get("cached_input_tokens", 0)) / 1000 * p_cache
         + D(u.get("reasoning_tokens", 0)) / 1000 * p_reason)
    return c.quantize(CENTS)


def cost_flat_total(u: dict, tier: str) -> Decimal:
    _, p_out, _, _ = (D(x) for x in TIERS[tier])
    return (D(total(u)) / 1000 * p_out).quantize(CENTS)


# --------------------------------------------------------------------------- #
# Attacker transformations (re-implemented from their documented definitions)
# --------------------------------------------------------------------------- #
def transform(u: dict, manip: str) -> dict:
    m = dict(u)
    if manip == "honest":
        return m
    if manip == "under_report_output_50":
        m["output_tokens"] = int(u["output_tokens"] * 0.5)
    elif manip == "under_report_output_90":
        m["output_tokens"] = int(u["output_tokens"] * 0.1)
    elif manip == "under_report_input_50":
        m["input_tokens"] = int(u["input_tokens"] * 0.5)
    elif manip == "drop_reasoning":
        m["reasoning_tokens"] = 0
    elif manip == "inflate_cached":
        shift = u["output_tokens"] // 2
        m["output_tokens"] = u["output_tokens"] - shift
        m["cached_input_tokens"] = u.get("cached_input_tokens", 0) + shift
    elif manip == "total_mismatch":
        m["declared_total"] = max(1, subtotal(u) // 4)
    elif manip == "rounding_shave":
        m["output_tokens"] = max(0, u["output_tokens"] - 3)
        m["input_tokens"] = max(0, u["input_tokens"] - 1)
    return m


# --------------------------------------------------------------------------- #
# The model's prediction for a given (architecture, manipulation, tier)
# --------------------------------------------------------------------------- #
def predict(prompt: str, seed: int, arch: str, manip: str, tier: str) -> dict:
    tu = true_usage(prompt, seed)
    du = transform(tu, manip)
    authoritative = cost_category(tu, tier)

    basis = BASIS[arch]
    if basis == "server":
        billed = cost_category(tu, tier)
    elif basis == "flat_total":
        billed = cost_flat_total(du, tier)
    else:
        billed = cost_category(du, tier)

    leak = authoritative - billed
    eff = float(leak / authoritative) if authoritative > 0 else 0.0
    return {"true_usage": tu, "declared_usage": du,
            "authoritative_cost": authoritative, "billed_cost": billed,
            "leak": leak, "leakage_efficiency": eff,
            "integrity_ok": billed >= authoritative,
            "basis": basis}


# --------------------------------------------------------------------------- #
# Attacker-knowledge model (audit fix F5)
# --------------------------------------------------------------------------- #
KNOWLEDGE_LEVELS = {
    "K0": "client-observable only: prompt text, response text, and its own balance",
    "K1": "provider-reported usage: whatever usage the architecture returns to the client",
    "K2": "oracle: exact server-side true usage vector (what the current experiment grants)",
}


def knowledge_required(manip: str) -> tuple[str, str]:
    """What must the attacker know to construct this transformation?

    Judged from the transformation's definition, not from experimental outcome.
    """
    if manip == "honest":
        return "K0", "no manipulation required"
    if manip in ("under_report_output_50", "under_report_output_90"):
        return ("K0", "scales the OUTPUT count, which the client can count from the "
                      "response it received")
    if manip == "under_report_input_50":
        return ("K0", "scales the INPUT count, which the client computes from its own prompt")
    if manip == "rounding_shave":
        return ("K0", "small absolute decrements to input/output, both client-countable")
    if manip == "total_mismatch":
        return ("K0", "derives a total from client-countable subtotals")
    if manip == "inflate_cached":
        return ("K1", "requires knowing the cached-token split, which the client cannot "
                      "observe from the response alone; needs provider-reported usage")
    if manip == "drop_reasoning":
        return ("K2", "requires knowing the hidden reasoning-token count, which is not "
                      "in the response and is not client-derivable in this model")
    return "K2", "unclassified; assume oracle knowledge"
