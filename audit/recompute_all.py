"""INDEPENDENT AUDIT RECOMPUTATION.

Written by the auditor. Imports NOTHING from app/, attacks/, defenses/, experiments/
or benchmarks/. Every quantity is re-derived from (a) the raw JSON schema and
(b) first principles, so that a bug in the project's own code cannot propagate into
this check.

Crucially, this does NOT trust `extra["true"]` (the usage vector the gateway wrote).
It re-derives the true usage from the prompt and seed using an independent
implementation of the documented mock-model specification:

    input_tokens  = max(1, number of whitespace-separated words in the prompt)
    output_tokens = 40 + (int(sha256(f"{seed}:{prompt}").hexdigest()[:16],16) % 41)
    reasoning     = output_tokens // 2

and an independent implementation of the pricing function and of each attacker
transformation. It then compares, per record:

    auditor-derived expected cost   vs   gateway 'authoritative_cost'
    auditor-derived billed cost     vs   gateway 'net_debit'
    auditor-derived leak            vs   gateway 'leak'
    auditor-derived invariant       vs   gateway 'invariant_ok'

and, per trial, ledger conservation recomputed from the rows.

Usage:  python audit/recompute_all.py
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
from collections import defaultdict
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
CENTS = Decimal("0.000001")

# Independent copy of the documented constants (NOT imported).
MIN_TOK, MAX_TOK = 40, 80
TIERS = {
    "low":    ("0.05", "0.15", "0.005", "0.15"),
    "medium": ("0.5", "1.5", "0.05", "1.5"),
    "high":   ("3.0", "15.0", "0.30", "15.0"),
}
CATS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


# --------------------------------------------------------------------------- #
# First-principles ground truth (independent re-implementation of the spec)
# --------------------------------------------------------------------------- #
def audit_input_tokens(prompt: str) -> int:
    return max(1, len(prompt.split()))


def audit_output_tokens(prompt: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{prompt}".encode("utf-8")).hexdigest()
    span = MAX_TOK - MIN_TOK + 1
    return MIN_TOK + (int(digest[:16], 16) % span)


def audit_true_usage(prompt: str, seed: int) -> dict:
    out = audit_output_tokens(prompt, seed)
    return {"input_tokens": audit_input_tokens(prompt), "output_tokens": out,
            "cached_input_tokens": 0, "reasoning_tokens": out // 2}


def audit_cost(u: dict, tier: str) -> Decimal:
    p_in, p_out, p_cache, p_reason = (D(x) for x in TIERS[tier])
    c = (D(u.get("input_tokens", 0)) / 1000 * p_in
         + D(u.get("output_tokens", 0)) / 1000 * p_out
         + D(u.get("cached_input_tokens", 0)) / 1000 * p_cache
         + D(u.get("reasoning_tokens", 0)) / 1000 * p_reason)
    return c.quantize(CENTS)


def audit_cost_on_total(u: dict, tier: str) -> Decimal:
    """Flat-total basis: bill the declared total at the output rate."""
    _, p_out, _, _ = (D(x) for x in TIERS[tier])
    total = u.get("declared_total")
    if total is None:
        total = sum(int(u.get(c, 0)) for c in CATS)
    return (D(total) / 1000 * p_out).quantize(CENTS)


# Independent re-implementation of every attacker transformation.
def audit_transform(u: dict, manip: str) -> dict:
    m = dict(u)
    m.setdefault("declared_total", None)
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
        subtotal = sum(int(u.get(c, 0)) for c in CATS)
        m["declared_total"] = max(1, subtotal // 4)
    elif manip == "rounding_shave":
        m["output_tokens"] = max(0, u["output_tokens"] - 3)
        m["input_tokens"] = max(0, u["input_tokens"] - 1)
    else:
        return m
    return m


# Which architectures bill on what basis (read from the paper's own taxonomy, but
# the CONSEQUENCE is computed independently below).
CLIENT_BASIS = {"client", "client_logged"}       # category pricing on declared usage
TOTAL_BASIS = {"client_total"}                   # flat-total pricing on declared total
SERVER_BASIS = {"server_recount", "hybrid_reconcile", "upstream"}


def audit_expected_billed(true_u: dict, manip: str, arch: str, tier: str) -> Decimal:
    """What SHOULD this architecture bill, derived independently?"""
    decl = audit_transform(true_u, manip)
    if arch in SERVER_BASIS:
        return audit_cost(true_u, tier)
    if arch in TOTAL_BASIS:
        return audit_cost_on_total(decl, tier)
    return audit_cost(decl, tier)


def latest(pattern: str, folder: Path):
    c = [p for p in glob.glob(str(folder / pattern)) if ".summary." not in os.path.basename(p)]
    return max(c, key=os.path.getmtime) if c else None


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if p else None


# --------------------------------------------------------------------------- #
# Audits
# --------------------------------------------------------------------------- #
def audit_m2(path) -> dict:
    d = load(path)
    seed = d["parameters"]["model_seed"]
    prompt = d["parameters"]["prompt"]
    true_u = audit_true_usage(prompt, seed)

    findings = defaultdict(int)
    problems, cells = [], defaultdict(lambda: {"leak": Decimal(0), "auth": Decimal(0), "n": 0})

    for t in d["trials"]:
        tier, arch, manip = t["price_tier"], t["architecture"], t["manipulation"]
        net_sum = Decimal(0)
        for r in t["records"]:
            findings["records"] += 1
            # (1) does the gateway's stored "true" usage match first principles?
            gw_true = (r.get("extra") or {}).get("true") or {}
            if any(int(gw_true.get(c, 0)) != true_u[c] for c in CATS):
                problems.append(f"TRUE-USAGE MISMATCH {r['request_id'][:8]}: "
                                f"gateway={{{','.join(f'{c}:{gw_true.get(c)}' for c in CATS)}}} "
                                f"audit={true_u}")
                findings["true_usage_mismatch"] += 1

            # (2) independent authoritative cost
            exp_auth = audit_cost(true_u, tier)
            if exp_auth != D(r["authoritative_cost"]):
                problems.append(f"AUTH-COST MISMATCH {r['request_id'][:8]} {arch}/{manip}/{tier}: "
                                f"gateway={r['authoritative_cost']} audit={exp_auth}")
                findings["auth_cost_mismatch"] += 1

            # (3) independent expected billed amount for this architecture
            exp_bill = audit_expected_billed(true_u, manip, arch, tier)
            if exp_bill != D(r["net_debit"]):
                problems.append(f"BILLED MISMATCH {r['request_id'][:8]} {arch}/{manip}/{tier}: "
                                f"gateway={r['net_debit']} audit={exp_bill}")
                findings["billed_mismatch"] += 1

            # (4) independent leak + invariant
            exp_leak = exp_auth - exp_bill
            if exp_leak != D(r["leak"]):
                problems.append(f"LEAK MISMATCH {r['request_id'][:8]} {arch}/{manip}: "
                                f"gateway={r['leak']} audit={exp_leak}")
                findings["leak_mismatch"] += 1
            exp_inv_ok = not (r["served"] and exp_bill < exp_auth)
            if exp_inv_ok != bool(r["invariant_ok"]):
                problems.append(f"INVARIANT MISMATCH {r['request_id'][:8]}: "
                                f"gateway={r['invariant_ok']} audit={exp_inv_ok}")
                findings["invariant_mismatch"] += 1

            net_sum += D(r["net_debit"])
            k = (arch, manip, tier)
            cells[k]["leak"] += exp_leak
            cells[k]["auth"] += exp_auth
            cells[k]["n"] += 1

        # (5) conservation, recomputed
        if t.get("final_balance") is not None:
            delta = D(t["initial_balance"]) - D(t["final_balance"])
            if abs(delta - net_sum) > CENTS:
                problems.append(f"CONSERVATION {t['trial_id'][:8]}: delta={delta} sum={net_sum}")
                findings["conservation_fail"] += 1

    eff = {f"{a}/{m}/{ti}": (float(v["leak"] / v["auth"]) if v["auth"] > 0 else 0.0)
           for (a, m, ti), v in cells.items()}
    return {"file": os.path.basename(path), "findings": dict(findings),
            "problems": problems[:25], "problem_count": len(problems),
            "audit_efficiency": eff, "audit_true_usage": true_u}


def audit_m1(path) -> dict:
    d = load(path)
    seed = d["parameters"]["model_seed"]
    prompt = d["parameters"]["prompt"]
    in_tok = audit_input_tokens(prompt)
    n_out_audit = audit_output_tokens(prompt, seed)

    findings = defaultdict(int)
    problems = []
    curve = defaultdict(list)

    if d["parameters"].get("n_out") != n_out_audit:
        problems.append(f"N_OUT MISMATCH: runner={d['parameters'].get('n_out')} audit={n_out_audit}")
        findings["n_out_mismatch"] += 1

    for t in d["trials"]:
        tier, arch = t["price_tier"], t["architecture"]
        net_sum = Decimal(0)
        for r in t["records"]:
            findings["records"] += 1
            delivered = int(r["tokens_delivered"])
            # independent value delivered = cost of prompt + delivered output tokens
            exp_auth = audit_cost({"input_tokens": in_tok, "output_tokens": delivered,
                                   "cached_input_tokens": 0, "reasoning_tokens": 0}, tier)
            if r["served"] and exp_auth != D(r["authoritative_cost"]):
                problems.append(f"M1 AUTH MISMATCH {r['request_id'][:8]} {arch}: "
                                f"gateway={r['authoritative_cost']} audit={exp_auth} delivered={delivered}")
                findings["auth_mismatch"] += 1
            exp_leak = (exp_auth - D(r["net_debit"])) if r["served"] else -D(r["net_debit"])
            if exp_leak != D(r["leak"]):
                problems.append(f"M1 LEAK MISMATCH {r['request_id'][:8]} {arch}: "
                                f"gateway={r['leak']} audit={exp_leak}")
                findings["leak_mismatch"] += 1
            exp_inv = not (r["served"] and D(r["net_debit"]) < exp_auth)
            if exp_inv != bool(r["invariant_ok"]):
                problems.append(f"M1 INVARIANT MISMATCH {r['request_id'][:8]} {arch}")
                findings["invariant_mismatch"] += 1
            net_sum += D(r["net_debit"])
            curve[(arch, round(float(t["abort_pct"])), t["concurrency"])].append(float(exp_leak))
        if t.get("final_balance") is not None:
            delta = D(t["initial_balance"]) - D(t["final_balance"])
            if abs(delta - net_sum) > CENTS:
                problems.append(f"M1 CONSERVATION {t['trial_id'][:8]}: delta={delta} sum={net_sum}")
                findings["conservation_fail"] += 1

    curve_mean = {f"{a}@{p}%|c{c}": (sum(v) / len(v)) for (a, p, c), v in curve.items()}
    return {"file": os.path.basename(path), "findings": dict(findings),
            "problems": problems[:25], "problem_count": len(problems),
            "audit_n_out": n_out_audit, "audit_curve": curve_mean}


def audit_b0(path) -> dict:
    d = load(path)
    unit = D(d["parameters"]["unit_cost"])
    findings = defaultdict(int)
    problems = []
    by = defaultdict(list)
    for t in d["trials"]:
        served = [r for r in t["requests"] if r["served"]]
        # independent: value obtained = served * unit cost; paid = initial - final
        exp_value = unit * len(served)
        paid = D(t["initial_balance"]) - D(t["final_balance"])
        exp_leak = exp_value - paid
        if exp_leak != D(t["dollar_leak"]):
            problems.append(f"B0 LEAK MISMATCH {t['trial_id'][:8]} {t['posture']}/c{t['concurrency']}: "
                            f"file={t['dollar_leak']} audit={exp_leak}")
            findings["leak_mismatch"] += 1
        # conservation from the per-request applied debits
        applied = sum(D(r["applied_debit"]) for r in t["requests"] if r["served"])
        if abs(applied - paid) > CENTS:
            problems.append(f"B0 CONSERVATION {t['trial_id'][:8]}: applied={applied} paid={paid}")
            findings["conservation_fail"] += 1
        findings["trials"] += 1
        by[(t["posture"], t["concurrency"])].append(float(exp_leak))
    means = {f"{p}/c{c}": sum(v) / len(v) for (p, c), v in by.items()}
    # independent slope for the vulnerable posture
    xs = [c for (p, c) in by if p == "vulnerable"]
    slope = None
    if len(xs) > 2:
        pts = sorted(((c, sum(by[("vulnerable", c)]) / len(by[("vulnerable", c)])) for c in xs))
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        num = sum((x - mx) * (y - my) for x, y in pts)
        den = sum((x - mx) ** 2 for x, _ in pts)
        slope = num / den if den else None
        ss_tot = sum((y - my) ** 2 for _, y in pts)
        inter = my - slope * mx
        ss_res = sum((y - (slope * x + inter)) ** 2 for x, y in pts)
        r2 = 1 - ss_res / ss_tot if ss_tot else None
    else:
        r2 = None
    return {"file": os.path.basename(path), "findings": dict(findings),
            "problems": problems[:25], "problem_count": len(problems),
            "audit_means": means, "audit_slope": slope, "audit_r2": r2}


def main() -> None:
    out = {}
    print("=" * 78)
    print("INDEPENDENT AUDIT RECOMPUTATION (no project imports)")
    print("=" * 78)

    m2p = latest("m2_2*.json", RAW)
    if m2p:
        out["m2"] = audit_m2(m2p)
        f = out["m2"]
        print(f"\nM2  <- {f['file']}")
        print(f"  records checked      : {f['findings'].get('records', 0)}")
        print(f"  audit true usage     : {f['audit_true_usage']}")
        for k in ("true_usage_mismatch", "auth_cost_mismatch", "billed_mismatch",
                  "leak_mismatch", "invariant_mismatch", "conservation_fail"):
            print(f"  {k:<22}: {f['findings'].get(k, 0)}")
        for p in f["problems"][:5]:
            print("   !", p)

    m1p = latest("m1_2*.json", RAW)
    if m1p:
        out["m1"] = audit_m1(m1p)
        f = out["m1"]
        print(f"\nM1  <- {f['file']}")
        print(f"  records checked      : {f['findings'].get('records', 0)}")
        print(f"  audit n_out          : {f['audit_n_out']}")
        for k in ("n_out_mismatch", "auth_mismatch", "leak_mismatch",
                  "invariant_mismatch", "conservation_fail"):
            print(f"  {k:<22}: {f['findings'].get(k, 0)}")
        for p in f["problems"][:5]:
            print("   !", p)

    b0p = latest("class6_2*.json", ROOT / "results")
    if b0p:
        out["b0"] = audit_b0(b0p)
        f = out["b0"]
        print(f"\nB0  <- {f['file']}")
        print(f"  trials checked       : {f['findings'].get('trials', 0)}")
        for k in ("leak_mismatch", "conservation_fail"):
            print(f"  {k:<22}: {f['findings'].get(k, 0)}")
        print(f"  audit slope          : {f['audit_slope']}")
        print(f"  audit R^2            : {f['audit_r2']}")
        for p in f["problems"][:5]:
            print("   !", p)

    (Path(__file__).parent / "recompute_results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8")
    total = sum(v.get("problem_count", 0) for v in out.values())
    print(f"\nTOTAL INDEPENDENT DISCREPANCIES: {total}")
    print(f"-> audit/recompute_results.json")


if __name__ == "__main__":
    main()
