"""Summarize M1 (metering-commit timing) raw results. Raw JSON in only.

INTEGRITY GATES (the summarizer FAILS, non-zero exit, if any is violated):
  G1  per record:  stored leak == independently recomputed leak
  G2  per record:  invariant_ok is consistent with (net_debit >= authoritative_cost)
  G3  per trial:   SUM(net_debit over records) == initial_balance - final_balance
                   (ledger conservation, recomputed here from raw rows -- NOT taken
                    from the server's own `reconciled` flag)

Aggregates per (architecture, price_tier, concurrency, abort_bin) with dispersion +
Wilson CIs, and reports BOTH absolute and normalized leakage so that "more requests
were attempted" is never confused with "each request became more vulnerable".
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
TOL = Decimal("0.000001")  # NUMERIC(18,6) quantum


def _D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


def _bin(rec: dict, bins: list[float]) -> float:
    if rec["completed"]:
        return 100.0
    ap = rec.get("abort_pct")
    return 100.0 if ap is None else min(bins, key=lambda b: abs(b - ap))


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
            # G1
            if _D(r["leak"]) != rd["leak"]:
                problems.append(f"G1 {r['request_id'][:8]}: stored leak {r['leak']} != recomputed {rd['leak']}")
            # G2
            if bool(r["invariant_ok"]) == rd["violation"]:
                problems.append(f"G2 {r['request_id'][:8]}: invariant_ok={r['invariant_ok']} inconsistent")
            net_sum += _D(r["net_debit"])
        # G3 -- recomputed conservation, independent of the server's flag
        if t.get("final_balance") is not None:
            delta = _D(t["initial_balance"]) - _D(t["final_balance"])
            if abs(delta - net_sum) > TOL:
                problems.append(
                    f"G3 {t['trial_id'][:8]}: balance delta {delta} != SUM(net_debit) {net_sum}")
    return problems


def _cell(records: list[dict], requests_issued: int) -> dict:
    rds = [_rederive(r) for r in records]
    leaks_pos = [rd["leak_pos"] for rd in rds]
    n = len(records)
    leaking = sum(1 for rd in rds if rd["leak"] > 0)
    violations = sum(1 for rd in rds if rd["violation"])
    det = [r["detection_level"] for r, rd in zip(records, rds) if rd["leak"] > 0]
    lat = [r["client_latency_ms"] for r in records if r.get("client_latency_ms") is not None]
    c2c = [r["extra"].get("cancel_to_commit_ms") for r in records
           if isinstance(r.get("extra"), dict) and r["extra"].get("cancel_to_commit_ms") is not None]
    sdur = [r["extra"].get("stream_duration_ms") for r in records
            if isinstance(r.get("extra"), dict) and r["extra"].get("stream_duration_ms") is not None]
    total_leak = sum(leaks_pos)
    return {
        "n_records": n, "requests_issued": requests_issued,
        # absolute (scales with volume -- do NOT compare across different volumes)
        "total_leak_absolute": total_leak,
        # normalized (the comparable quantities)
        "leak_per_request": total_leak / n if n else 0.0,
        "leak": S.describe(leaks_pos), "leak_ci": S.mean_ci(leaks_pos),
        "leakage_efficiency": S.describe([rd["eff"] for rd in rds]),
        "request_asr": S.wilson(leaking, n),
        "invariant_violation_rate": violations / n if n else 0.0,
        "invariant_violations": violations,
        "tokens_delivered": S.describe([float(r["tokens_delivered"]) for r in records]),
        "client_latency_ms": S.describe(lat),
        "cancel_to_commit_ms": S.describe(c2c),
        "stream_duration_ms": S.describe(sdur),
        "detection": Counter(det).most_common(1)[0][0] if det else "n/a",
    }


def summarize(raw: dict) -> dict:
    trials = raw["trials"]
    p = raw["parameters"]
    problems = integrity_check(trials)
    bins = list(p["abort_pcts"])

    cells = []
    for t in trials:
        by_bin: dict[float, list] = {}
        for r in t["records"]:
            by_bin.setdefault(_bin(r, bins), []).append(r)
        for b, recs in sorted(by_bin.items()):
            c = _cell(recs, t.get("requests_issued", len(recs)))
            c.update({"architecture": t["architecture"], "price_tier": t["price_tier"],
                      "concurrency": t.get("concurrency", 1), "abort_bin": b,
                      "client_type": t.get("client_type", "attacker"),
                      "throughput_rps": t.get("throughput_rps"),
                      "trial_reconciled": t.get("reconciled")})
            cells.append(c)

    return {
        "experiment": raw.get("experiment"), "generated_at": raw.get("generated_at"),
        "environment": raw.get("environment"), "db_info": raw.get("db_info"),
        "design_note": raw.get("design_note"), "parameters": p,
        "integrity": {"records_checked": sum(len(t["records"]) for t in trials),
                      "trials_checked": len(trials), "problems": problems,
                      "ok": len(problems) == 0,
                      "gates": ["G1 leak recomputation", "G2 invariant consistency",
                                "G3 ledger conservation (recomputed)"]},
        "cells": cells,
    }


_COLS = ["architecture", "price_tier", "concurrency", "abort_bin", "client_type", "n_records",
         "requests_issued", "total_leak_absolute", "leak_per_request", "leakage_efficiency_mean",
         "request_asr", "request_asr_lo", "request_asr_hi", "invariant_violation_rate",
         "tokens_delivered_mean", "client_latency_p50", "client_latency_p95",
         "cancel_to_commit_mean_ms", "throughput_rps", "detection"]


def render_csv(summary: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_COLS)
        w.writeheader()
        for c in summary["cells"]:
            w.writerow({
                "architecture": c["architecture"], "price_tier": c["price_tier"],
                "concurrency": c["concurrency"], "abort_bin": c["abort_bin"],
                "client_type": c["client_type"], "n_records": c["n_records"],
                "requests_issued": c["requests_issued"],
                "total_leak_absolute": round(c["total_leak_absolute"], 6),
                "leak_per_request": round(c["leak_per_request"], 6),
                "leakage_efficiency_mean": round(c["leakage_efficiency"]["mean"], 4),
                "request_asr": round(c["request_asr"]["p"], 4),
                "request_asr_lo": round(c["request_asr"]["lo"], 4),
                "request_asr_hi": round(c["request_asr"]["hi"], 4),
                "invariant_violation_rate": round(c["invariant_violation_rate"], 4),
                "tokens_delivered_mean": round(c["tokens_delivered"]["mean"], 2),
                "client_latency_p50": round(c["client_latency_ms"]["p50"], 2),
                "client_latency_p95": round(c["client_latency_ms"]["p95"], 2),
                "cancel_to_commit_mean_ms": round(c["cancel_to_commit_ms"]["mean"], 3),
                "throughput_rps": round(c["throughput_rps"], 2) if c["throughput_rps"] else "",
                "detection": c["detection"]})


def render_md(summary: dict, path: Path) -> None:
    integ = summary["integrity"]
    lines = ["# M1 — metering-commit timing: results\n",
             f"- Generated: `{summary['generated_at']}`",
             f"- Integrity gates (G1 leak, G2 invariant, G3 conservation): "
             f"**{'PASS' if integ['ok'] else 'FAIL'}** over {integ['records_checked']} records / "
             f"{integ['trials_checked']} trials\n",
             "`leak_per_request` and `leakage efficiency` are the normalized metrics; "
             "`total_leak_absolute` scales with request volume and must not be compared "
             "across cells with different volumes.\n",
             "| arch | conc | abort% | client | n | leak/req | eff | request ASR | inv.viol | cancel→commit ms | detect |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in summary["cells"]:
        a = c["request_asr"]
        lines.append(
            f"| {c['architecture']} | {c['concurrency']} | {c['abort_bin']:.0f} | {c['client_type']} "
            f"| {c['n_records']} | {c['leak_per_request']:.4f} "
            f"| {c['leakage_efficiency']['mean']:.2f} "
            f"| {a['p']:.2f} [{a['lo']:.2f},{a['hi']:.2f}] "
            f"| {c['invariant_violation_rate']:.2f} "
            f"| {c['cancel_to_commit_ms']['mean']:.2f} | {c['detection']} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _latest() -> Path:
    raw = Path(__file__).resolve().parents[1] / "results" / "raw"
    c = sorted(raw.glob("m1_*.json"))
    if not c:
        raise SystemExit("no results/raw/m1_*.json; run experiments.run_m1 first")
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
