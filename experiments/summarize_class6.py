"""Summary generator for flaw class 6. Consumes RAW JSON only.

Reads a ``results/class6_*.json`` file produced by ``run_class6.py`` and emits three
artifacts next to it: ``*.summary.json``, ``*.summary.csv``, ``*.summary.md``. No
experimental number is ever entered by hand -- everything is derived here, and the
per-trial leakage is **re-derived independently** from the per-request ledger and
balance snapshots, then cross-checked against the value the server stored (an
integrity gate that fails loudly on any mismatch).

Metric definitions (authoritative; mirrored in README and paper/class6_methodology.md)
--------------------------------------------------------------------------------------
* dollar_leak (per trial)   = inference_value - actual_debit
                              inference_value = SUM(cost) over served requests
                              actual_debit    = initial_balance - final_balance
* over_served_requests      = max(served - affordable_k, 0)          [budget-relative]
* unpaid_served_requests    = served - actual_debit/unit_cost        [economic]
* invariant_violations      = served requests with applied_debit < cost
                              (a completed response with no committed debit of its cost)
* unauthorized_completion_tokens = completion tokens of invariant-violating served rows
* trial_asr                 = fraction of trials with dollar_leak > 0
* request_asr               = (successful-attack requests) / (issued requests),
                              successful-attack request := served AND applied_debit < cost
* detection_status          = none | partial | full (does the ledger reveal the leak?)

Dispersion: for each (posture, concurrency) cell we report mean, median, sample std
(ddof=1), and p50/p95/p99. Proportions (trial_asr, request_asr) get Wilson 95%
score intervals; mean dollar_leak gets a normal-approximation 95% interval.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from decimal import Decimal
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
Z = 1.959963984540054  # 95%


# --------------------------------------------------------------------------- #
# Small stats helpers
# --------------------------------------------------------------------------- #
def _stats(values: list[float]) -> dict:
    if not values:
        return {k: 0.0 for k in ("mean", "median", "std", "min", "max", "p50", "p95", "p99")}
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "min": float(arr.min()),
        "max": float(arr.max()),
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
    }


def _wilson(k: int, n: int) -> dict:
    """Wilson score 95% interval for a binomial proportion."""
    if n == 0:
        return {"p": 0.0, "lo": 0.0, "hi": 0.0, "k": k, "n": n}
    p = k / n
    denom = 1 + Z * Z / n
    center = (p + Z * Z / (2 * n)) / denom
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denom
    return {"p": p, "lo": max(0.0, center - half), "hi": min(1.0, center + half), "k": k, "n": n}


def _mean_ci(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0, "std": 0.0, "n": 0}
    arr = np.asarray(values, dtype=float)
    n = arr.size
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if n > 1 else 0.0
    half = Z * std / math.sqrt(n) if n > 1 else 0.0
    return {"mean": mean, "lo": mean - half, "hi": mean + half, "std": std, "n": n}


def _D(x) -> Decimal:
    return Decimal(str(x))


# --------------------------------------------------------------------------- #
# Independent re-derivation + integrity check
# --------------------------------------------------------------------------- #
def _rederive(trial: dict) -> dict:
    """Recompute a trial's headline figures from primitives (ledger + snapshots)."""
    unit_cost = _D(trial["unit_cost"])
    initial = _D(trial["initial_balance"])
    final = _D(trial["final_balance"]) if trial["final_balance"] is not None else None

    served_reqs = [r for r in trial["requests"] if r["served"]]
    served = len(served_reqs)
    inference_value = sum((_D(r["cost"]) for r in served_reqs), Decimal("0"))
    applied_total = sum((_D(r["applied_debit"]) for r in served_reqs), Decimal("0"))
    actual_debit = (initial - final) if final is not None else None
    dollar_leak = (inference_value - actual_debit) if actual_debit is not None else None

    violations = [r for r in served_reqs if _D(r["applied_debit"]) < _D(r["cost"])]
    invariant_violations = len(violations)
    unauthorized_tokens = sum(int(r["completion_tokens"]) for r in violations)

    paid = (actual_debit / unit_cost) if (actual_debit is not None and unit_cost > 0) else None
    unpaid_served = (Decimal(served) - paid) if paid is not None else None
    over_served = max(served - int(trial["affordable_k"]), 0)
    reconciled = (actual_debit is not None and actual_debit == applied_total)

    return {
        "served": served,
        "inference_value": inference_value,
        "applied_total": applied_total,
        "actual_debit": actual_debit,
        "dollar_leak": dollar_leak,
        "invariant_violations": invariant_violations,
        "unauthorized_tokens": unauthorized_tokens,
        "paid": paid,
        "unpaid_served": unpaid_served,
        "over_served": over_served,
        "reconciled": reconciled,
    }


def _integrity(trial: dict, rd: dict) -> list[str]:
    """Return a list of human-readable mismatches between stored and re-derived values."""
    problems: list[str] = []
    tid = trial["trial_id"][:8]

    if rd["served"] != trial["server_served_count"]:
        problems.append(f"{tid}: served client-rederived {rd['served']} != server {trial['server_served_count']}")
    if trial["dollar_leak"] is not None and rd["dollar_leak"] is not None:
        if _D(trial["dollar_leak"]) != rd["dollar_leak"]:
            problems.append(f"{tid}: dollar_leak stored {trial['dollar_leak']} != rederived {rd['dollar_leak']}")
    if not rd["reconciled"]:
        problems.append(
            f"{tid}: NOT reconciled -- actual_debit {rd['actual_debit']} != SUM(applied) {rd['applied_total']}"
        )
    if trial["reconciled"] is not True and rd["reconciled"]:
        problems.append(f"{tid}: server flagged reconciled={trial['reconciled']} but re-derivation reconciles")
    return problems


# --------------------------------------------------------------------------- #
# Cell aggregation
# --------------------------------------------------------------------------- #
def _summarize_cell(posture: str, concurrency: int, trials: list[dict]) -> dict:
    rds = [_rederive(t) for t in trials]
    reps = len(trials)

    served = [rd["served"] for rd in rds]
    over_served = [rd["over_served"] for rd in rds]
    leak = [float(rd["dollar_leak"]) for rd in rds if rd["dollar_leak"] is not None]
    unpaid = [float(rd["unpaid_served"]) for rd in rds if rd["unpaid_served"] is not None]
    unauth_tokens = [rd["unauthorized_tokens"] for rd in rds]
    violations = [rd["invariant_violations"] for rd in rds]

    latencies_ms = [
        r["latency_s"] * 1000.0
        for t in trials
        for r in t["requests"]
        if r["served"] and r["latency_s"] is not None
    ]

    leaking_trials = sum(1 for rd in rds if rd["dollar_leak"] is not None and rd["dollar_leak"] > 0)
    issued = sum(t["concurrency"] for t in trials)
    attack_success_reqs = sum(rd["invariant_violations"] for rd in rds)

    detections = [t["detection_status"] for t in trials]
    detection = max(set(detections), key=detections.count) if detections else "none"

    all_reconciled = all(rd["reconciled"] for rd in rds)

    return {
        "posture": posture,
        "concurrency": concurrency,
        "reps": reps,
        "served": _stats([float(x) for x in served]),
        "over_served": _stats([float(x) for x in over_served]),
        "unpaid_served": _stats(unpaid),
        "dollar_leak": _stats(leak),
        "dollar_leak_ci": _mean_ci(leak),
        "unauthorized_completion_tokens": {
            "mean": float(np.mean(unauth_tokens)) if unauth_tokens else 0.0,
            "total": int(sum(unauth_tokens)),
        },
        "invariant_violations": {
            "mean": float(np.mean(violations)) if violations else 0.0,
            "total": int(sum(violations)),
        },
        "trial_asr": _wilson(leaking_trials, reps),
        "request_asr": _wilson(attack_success_reqs, issued),
        "latency_ms": _stats(latencies_ms),
        "detection_status": detection,
        "all_reconciled": all_reconciled,
    }


def summarize(raw: dict) -> dict:
    trials = raw["trials"]
    integrity_problems: list[str] = []
    for t in trials:
        integrity_problems.extend(_integrity(t, _rederive(t)))

    cells: list[dict] = []
    postures = raw["parameters"]["postures"]
    concs = raw["parameters"]["concurrency_levels"]
    for posture in postures:
        for c in concs:
            cell_trials = [t for t in trials if t["posture"] == posture and t["concurrency"] == c]
            if cell_trials:
                cells.append(_summarize_cell(posture, c, cell_trials))

    return {
        "experiment": raw.get("experiment"),
        "schema_version": raw.get("schema_version"),
        "generated_at": raw.get("generated_at"),
        "environment": raw.get("environment"),
        "db_info": raw.get("db_info"),
        "parameters": raw.get("parameters"),
        "integrity": {
            "trials_checked": len(trials),
            "problems": integrity_problems,
            "ok": len(integrity_problems) == 0,
        },
        "cells": cells,
    }


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #
_CSV_COLUMNS = [
    "posture", "concurrency", "reps",
    "served_mean", "served_std",
    "over_served_mean",
    "dollar_leak_mean", "dollar_leak_std", "dollar_leak_ci_lo", "dollar_leak_ci_hi",
    "dollar_leak_p50", "dollar_leak_p95", "dollar_leak_p99",
    "unpaid_served_mean",
    "unauthorized_tokens_total",
    "invariant_violations_total",
    "trial_asr", "trial_asr_lo", "trial_asr_hi",
    "request_asr", "request_asr_lo", "request_asr_hi",
    "latency_ms_mean", "latency_ms_p50", "latency_ms_p95", "latency_ms_p99",
    "detection_status", "all_reconciled",
]


def _csv_row(c: dict) -> dict:
    return {
        "posture": c["posture"],
        "concurrency": c["concurrency"],
        "reps": c["reps"],
        "served_mean": round(c["served"]["mean"], 4),
        "served_std": round(c["served"]["std"], 4),
        "over_served_mean": round(c["over_served"]["mean"], 4),
        "dollar_leak_mean": round(c["dollar_leak"]["mean"], 6),
        "dollar_leak_std": round(c["dollar_leak"]["std"], 6),
        "dollar_leak_ci_lo": round(c["dollar_leak_ci"]["lo"], 6),
        "dollar_leak_ci_hi": round(c["dollar_leak_ci"]["hi"], 6),
        "dollar_leak_p50": round(c["dollar_leak"]["p50"], 6),
        "dollar_leak_p95": round(c["dollar_leak"]["p95"], 6),
        "dollar_leak_p99": round(c["dollar_leak"]["p99"], 6),
        "unpaid_served_mean": round(c["unpaid_served"]["mean"], 4),
        "unauthorized_tokens_total": c["unauthorized_completion_tokens"]["total"],
        "invariant_violations_total": c["invariant_violations"]["total"],
        "trial_asr": round(c["trial_asr"]["p"], 4),
        "trial_asr_lo": round(c["trial_asr"]["lo"], 4),
        "trial_asr_hi": round(c["trial_asr"]["hi"], 4),
        "request_asr": round(c["request_asr"]["p"], 4),
        "request_asr_lo": round(c["request_asr"]["lo"], 4),
        "request_asr_hi": round(c["request_asr"]["hi"], 4),
        "latency_ms_mean": round(c["latency_ms"]["mean"], 2),
        "latency_ms_p50": round(c["latency_ms"]["p50"], 2),
        "latency_ms_p95": round(c["latency_ms"]["p95"], 2),
        "latency_ms_p99": round(c["latency_ms"]["p99"], 2),
        "detection_status": c["detection_status"],
        "all_reconciled": c["all_reconciled"],
    }


def render_csv(summary: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        for c in summary["cells"]:
            writer.writerow(_csv_row(c))


def render_markdown(summary: dict, path: Path) -> None:
    p = summary["parameters"]
    lines: list[str] = []
    lines.append("# Class 6 — credit-decrement race: results\n")
    lines.append(f"- Generated: `{summary['generated_at']}`")
    lines.append(
        f"- Fixed affordable budget k = **{p['affordable_k']}** requests "
        f"(unit_cost = {p['unit_cost']}, prompt_tokens = {p['prompt_tokens']}, "
        f"completion_tokens = {p['completion_tokens']})"
    )
    lines.append(f"- Reps per cell: **{p['reps_per_cell']}**  |  concurrency levels: {p['concurrency_levels']}")
    if summary.get("db_info"):
        di = summary["db_info"]
        lines.append(
            f"- PostgreSQL: `{di.get('server_version','?').split(' on ')[0]}`, "
            f"isolation = `{di.get('transaction_isolation','?')}`"
        )
    integ = summary["integrity"]
    badge = "PASS ✅" if integ["ok"] else f"FAIL ❌ ({len(integ['problems'])} problems)"
    lines.append(f"- Integrity re-derivation check: **{badge}** over {integ['trials_checked']} trials\n")

    header = (
        "| posture | conc | reps | served | over-served | $-leak (mean ± 95% CI) | "
        "trial ASR | request ASR | unauth. tok | inv. viol | detect | reconciled | p95 lat (ms) |"
    )
    sep = "|" + "|".join(["---"] * 13) + "|"
    lines.append(header)
    lines.append(sep)
    for c in summary["cells"]:
        dl = c["dollar_leak_ci"]
        tasr = c["trial_asr"]
        rasr = c["request_asr"]
        lines.append(
            f"| {c['posture']} | {c['concurrency']} | {c['reps']} "
            f"| {c['served']['mean']:.1f} "
            f"| {c['over_served']['mean']:.1f} "
            f"| {dl['mean']:.4f} ± {(dl['hi']-dl['mean']):.4f} "
            f"| {tasr['p']:.2f} [{tasr['lo']:.2f},{tasr['hi']:.2f}] "
            f"| {rasr['p']:.3f} [{rasr['lo']:.3f},{rasr['hi']:.3f}] "
            f"| {c['unauthorized_completion_tokens']['total']} "
            f"| {c['invariant_violations']['total']} "
            f"| {c['detection_status']} "
            f"| {'yes' if c['all_reconciled'] else 'NO'} "
            f"| {c['latency_ms']['p95']:.1f} |"
        )
    lines.append("")
    if not integ["ok"]:
        lines.append("## Integrity problems\n")
        for prob in integ["problems"][:50]:
            lines.append(f"- {prob}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _latest_raw() -> Path:
    candidates = [
        p for p in RESULTS_DIR.glob("class6_*.json") if not p.name.endswith(".summary.json")
    ]
    if not candidates:
        raise SystemExit("no results/class6_*.json found; run experiments.run_class6 first")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize class-6 raw results (raw JSON in only).")
    parser.add_argument("--input", default=None, help="raw JSON (default: latest results/class6_*.json)")
    parser.add_argument("--outdir", default=None, help="output dir (default: alongside input)")
    args = parser.parse_args()

    in_path = Path(args.input) if args.input else _latest_raw()
    raw = json.loads(in_path.read_text(encoding="utf-8"))
    summary = summarize(raw)

    outdir = Path(args.outdir) if args.outdir else in_path.parent
    outdir.mkdir(exist_ok=True)
    stem = in_path.stem
    json_path = outdir / f"{stem}.summary.json"
    csv_path = outdir / f"{stem}.summary.csv"
    md_path = outdir / f"{stem}.summary.md"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    render_csv(summary, csv_path)
    render_markdown(summary, md_path)

    integ = summary["integrity"]
    print(f"input : {in_path}")
    print(f"json  : {json_path}")
    print(f"csv   : {csv_path}")
    print(f"md    : {md_path}")
    print(f"integrity: {'PASS' if integ['ok'] else 'FAIL'} ({len(integ['problems'])} problems)")
    if not integ["ok"]:
        for prob in integ["problems"][:20]:
            print(f"  - {prob}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
