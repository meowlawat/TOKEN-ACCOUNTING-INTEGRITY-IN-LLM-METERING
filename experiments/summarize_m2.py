"""Summarize M2 (usage-record authority) raw results. Raw JSON in only.

INTEGRITY GATES (summarizer FAILS with non-zero exit if violated):
  G1  per record: stored leak == independently recomputed leak
  G2  per record: invariant_ok consistent with (net_debit >= authoritative_cost)
  G3  per trial:  SUM(net_debit) == initial_balance - final_balance, recomputed here

Aggregates per (architecture, price_tier, concurrency, manipulation). Reports both
absolute and normalized leakage, plus capacity data (throughput, latency, error and
timeout rates) as a SECONDARY observation -- the primary question is whether
concurrency changes accounting-integrity failure or defense overhead.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from experiments import _stats as S

PROC = Path(__file__).resolve().parents[1] / "results" / "processed"
TOL = Decimal("0.000001")


def _D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


def _rederive(rec: dict) -> dict:
    auth = _D(rec["authoritative_cost"])
    net = _D(rec["net_debit"])
    served = rec["served"]
    leak = (auth - net) if served else -net
    eff = float(max(leak, Decimal("0")) / auth) if auth > 0 else 0.0
    return {"leak": leak, "leak_pos": float(max(leak, Decimal("0"))), "eff": eff,
            "violation": bool(served and net < auth)}


def integrity_check(trials: list[dict]) -> list[str]:
    problems: list[str] = []
    for t in trials:
        net_sum = Decimal("0")
        for r in t["records"]:
            rd = _rederive(r)
            if _D(r["leak"]) != rd["leak"]:
                problems.append(f"G1 {r['request_id'][:8]}: stored {r['leak']} != recomputed {rd['leak']}")
            if bool(r["invariant_ok"]) == rd["violation"]:
                problems.append(f"G2 {r['request_id'][:8]}: invariant_ok inconsistent")
            net_sum += _D(r["net_debit"])
        if t.get("final_balance") is not None:
            delta = _D(t["initial_balance"]) - _D(t["final_balance"])
            if abs(delta - net_sum) > TOL:
                problems.append(f"G3 {t['trial_id'][:8]}: delta {delta} != SUM(net_debit) {net_sum}")
    return problems


def _cell(t: dict) -> dict:
    records = t["records"]
    rds = [_rederive(r) for r in records]
    leaks_pos = [rd["leak_pos"] for rd in rds]
    n = len(records)
    leaking = sum(1 for rd in rds if rd["leak"] > 0)
    violations = sum(1 for rd in rds if rd["violation"])
    det = [r["detection_level"] for r, rd in zip(records, rds) if rd["leak"] > 0]
    total = sum(leaks_pos)
    lat = t.get("latency_ms", {}) or {}
    return {
        "architecture": t["architecture"], "price_tier": t["price_tier"],
        "concurrency": t.get("concurrency", 1), "manipulation": t.get("manipulation"),
        "client_type": t.get("client_type", "attacker"),
        "n_records": n, "requests_issued": t.get("requests_issued", n),
        "total_leak_absolute": total,
        "leak_per_request": total / n if n else 0.0,
        "leak": S.describe(leaks_pos), "leak_ci": S.mean_ci(leaks_pos),
        "leakage_efficiency": S.describe([rd["eff"] for rd in rds]),
        "request_asr": S.wilson(leaking, n),
        "invariant_violation_rate": violations / n if n else 0.0,
        "invariant_violations": violations,
        "detection": Counter(det).most_common(1)[0][0] if det else "n/a",
        # secondary capacity observations
        "throughput_rps": t.get("throughput_rps"),
        "latency_p50_ms": lat.get("p50"), "latency_p95_ms": lat.get("p95"),
        "latency_p99_ms": lat.get("p99"),
        "error_rate": t.get("error_rate", 0.0), "timeouts": t.get("timeouts", 0),
        "trial_reconciled": t.get("reconciled"),
    }


def summarize(raw: dict) -> dict:
    trials = raw["trials"]
    problems = integrity_check(trials)
    return {
        "experiment": raw.get("experiment"), "generated_at": raw.get("generated_at"),
        "environment": raw.get("environment"), "db_info": raw.get("db_info"),
        "design_note": raw.get("design_note"), "parameters": raw.get("parameters"),
        "integrity": {"records_checked": sum(len(t["records"]) for t in trials),
                      "trials_checked": len(trials), "problems": problems,
                      "ok": len(problems) == 0,
                      "gates": ["G1 leak recomputation", "G2 invariant consistency",
                                "G3 ledger conservation (recomputed)"]},
        "cells": [_cell(t) for t in trials],
    }


_COLS = ["architecture", "price_tier", "concurrency", "manipulation", "client_type", "n_records",
         "total_leak_absolute", "leak_per_request", "leakage_efficiency_mean", "request_asr",
         "request_asr_lo", "request_asr_hi", "invariant_violation_rate", "throughput_rps",
         "latency_p50_ms", "latency_p95_ms", "latency_p99_ms", "error_rate", "timeouts", "detection"]


def render_csv(summary: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_COLS)
        w.writeheader()
        for c in summary["cells"]:
            w.writerow({
                "architecture": c["architecture"], "price_tier": c["price_tier"],
                "concurrency": c["concurrency"], "manipulation": c["manipulation"],
                "client_type": c["client_type"], "n_records": c["n_records"],
                "total_leak_absolute": round(c["total_leak_absolute"], 6),
                "leak_per_request": round(c["leak_per_request"], 6),
                "leakage_efficiency_mean": round(c["leakage_efficiency"]["mean"], 4),
                "request_asr": round(c["request_asr"]["p"], 4),
                "request_asr_lo": round(c["request_asr"]["lo"], 4),
                "request_asr_hi": round(c["request_asr"]["hi"], 4),
                "invariant_violation_rate": round(c["invariant_violation_rate"], 4),
                "throughput_rps": round(c["throughput_rps"], 2) if c["throughput_rps"] else "",
                "latency_p50_ms": round(c["latency_p50_ms"], 2) if c["latency_p50_ms"] else "",
                "latency_p95_ms": round(c["latency_p95_ms"], 2) if c["latency_p95_ms"] else "",
                "latency_p99_ms": round(c["latency_p99_ms"], 2) if c["latency_p99_ms"] else "",
                "error_rate": round(c["error_rate"], 4), "timeouts": c["timeouts"],
                "detection": c["detection"]})


def render_md(summary: dict, path: Path) -> None:
    integ = summary["integrity"]
    lines = ["# M2 — usage-record authority: results\n",
             f"- Generated: `{summary['generated_at']}`",
             f"- Integrity gates (G1/G2/G3): **{'PASS' if integ['ok'] else 'FAIL'}** over "
             f"{integ['records_checked']} records / {integ['trials_checked']} trials\n",
             "Leakage efficiency = fraction of true inference value evaded (price-invariant).\n",
             "| arch | conc | manipulation | client | n | eff | request ASR | inv.viol | rps | p95 ms | err | detect |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in summary["cells"]:
        a = c["request_asr"]
        lines.append(
            f"| {c['architecture']} | {c['concurrency']} | {c['manipulation']} | {c['client_type']} "
            f"| {c['n_records']} | {c['leakage_efficiency']['mean']:.2f} "
            f"| {a['p']:.2f} [{a['lo']:.2f},{a['hi']:.2f}] "
            f"| {c['invariant_violation_rate']:.2f} "
            f"| {c['throughput_rps']:.1f} | {c['latency_p95_ms']:.1f} "
            f"| {c['error_rate']:.2f} | {c['detection']} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _latest() -> Path:
    raw = Path(__file__).resolve().parents[1] / "results" / "raw"
    c = sorted(raw.glob("m2_*.json"))
    if not c:
        raise SystemExit("no results/raw/m2_*.json; run experiments.run_m2 first")
    return max(c, key=lambda p: p.stat().st_mtime)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None)
    args = ap.parse_args()
    inp = Path(args.input) if args.input else _latest()
    summary = summarize(json.loads(inp.read_text(encoding="utf-8")))
    PROC.mkdir(parents=True, exist_ok=True)
    stem = inp.stem
    (PROC / f"{stem}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    render_csv(summary, PROC / f"{stem}.summary.csv")
    render_md(summary, PROC / f"{stem}.summary.md")
    integ = summary["integrity"]
    print(f"input: {inp}")
    print(f"integrity: {'PASS' if integ['ok'] else 'FAIL'} ({len(integ['problems'])} problems)")
    print(f"processed -> {PROC}/{stem}.summary.{{json,csv,md}}")
    if not integ["ok"]:
        for p in integ["problems"][:10]:
            print("  -", p)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
