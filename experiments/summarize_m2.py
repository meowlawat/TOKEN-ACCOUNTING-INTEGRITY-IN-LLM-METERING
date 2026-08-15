"""Summarize M2 (usage-record authority) raw results. Raw JSON in only.

Independently re-derives per-record leak from primitives and cross-checks against
the server-stored value (integrity gate). Aggregates per (architecture, price_tier,
manipulation) cell with dispersion + Wilson CIs. Emits processed JSON/CSV/MD.

Metrics
  leak (per record)         = authoritative_cost - net_debit           (signed)
  leakage_efficiency        = max(leak,0) / authoritative_cost         (fraction of value evaded)
  request_ASR (per cell)    = fraction of records with leak > 0        (Wilson 95%)
  invariant_violation_rate  = fraction of records with net_debit < authoritative_cost
  detection                 = modal detection level among leaking records
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


def _D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


def _rederive(rec: dict) -> dict:
    auth = _D(rec["authoritative_cost"])
    net = _D(rec["net_debit"])
    served = rec["served"]
    leak = (auth - net) if served else -net
    eff = float(max(leak, Decimal("0")) / auth) if auth > 0 else 0.0
    return {"leak": leak, "leak_pos": float(max(leak, Decimal("0"))), "eff": eff,
            "violation": served and net < auth}


def _integrity(records: list[dict]) -> list[str]:
    problems = []
    for r in records:
        rd = _rederive(r)
        if _D(r["leak"]) != rd["leak"]:
            problems.append(f"{r['request_id'][:8]}: stored leak {r['leak']} != rederived {rd['leak']}")
        if bool(r["invariant_ok"]) == rd["violation"]:
            problems.append(f"{r['request_id'][:8]}: invariant_ok {r['invariant_ok']} inconsistent with net<auth")
    return problems


def _cell(records: list[dict]) -> dict:
    rds = [_rederive(r) for r in records]
    leaks_pos = [rd["leak_pos"] for rd in rds]
    effs = [rd["eff"] for rd in rds]
    n = len(records)
    leaking = sum(1 for rd in rds if rd["leak"] > 0)
    violations = sum(1 for rd in rds if rd["violation"])
    det = [r["detection_level"] for r in records if _rederive(r)["leak"] > 0]
    detection = Counter(det).most_common(1)[0][0] if det else "n/a"
    return {
        "n": n,
        "leak": S.describe(leaks_pos),
        "leak_ci": S.mean_ci(leaks_pos),
        "leakage_efficiency": S.describe(effs),
        "request_asr": S.wilson(leaking, n),
        "invariant_violation_rate": violations / n if n else 0.0,
        "invariant_violations": violations,
        "detection": detection,
        "reconciled_records": True,  # trial-level reconciliation is checked separately
    }


def summarize(raw: dict) -> dict:
    trials = raw["trials"]
    problems: list[str] = []
    all_reconciled = True
    for t in trials:
        problems.extend(_integrity(t["records"]))
        if t.get("reconciled") is not True:
            all_reconciled = False

    # group records by (architecture, tier, manipulation)
    cells = []
    p = raw["parameters"]
    for arch in p["architectures"]:
        for tier in p["tiers"]:
            trs = [t for t in trials if t["architecture"] == arch and t["price_tier"] == tier]
            recs_by_manip: dict[str, list] = {}
            safe_arch = None
            for t in trs:
                for r in t["records"]:
                    recs_by_manip.setdefault(r["manipulation"], []).append(r)
            for manip in p["manipulations"]:
                recs = recs_by_manip.get(manip, [])
                if not recs:
                    continue
                c = _cell(recs)
                c.update({"architecture": arch, "price_tier": tier, "manipulation": manip})
                cells.append(c)

    return {
        "experiment": raw.get("experiment"), "generated_at": raw.get("generated_at"),
        "environment": raw.get("environment"), "db_info": raw.get("db_info"),
        "parameters": p,
        "integrity": {"records_checked": sum(len(t["records"]) for t in trials),
                      "problems": problems, "ok": len(problems) == 0,
                      "all_trials_reconciled": all_reconciled},
        "cells": cells,
    }


_CSV_COLS = ["architecture", "price_tier", "manipulation", "n", "leak_mean", "leak_std",
             "leakage_efficiency_mean", "request_asr", "request_asr_lo", "request_asr_hi",
             "invariant_violation_rate", "detection"]


def render_csv(summary: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_CSV_COLS)
        w.writeheader()
        for c in summary["cells"]:
            w.writerow({
                "architecture": c["architecture"], "price_tier": c["price_tier"],
                "manipulation": c["manipulation"], "n": c["n"],
                "leak_mean": round(c["leak"]["mean"], 6), "leak_std": round(c["leak"]["std"], 6),
                "leakage_efficiency_mean": round(c["leakage_efficiency"]["mean"], 4),
                "request_asr": round(c["request_asr"]["p"], 4),
                "request_asr_lo": round(c["request_asr"]["lo"], 4),
                "request_asr_hi": round(c["request_asr"]["hi"], 4),
                "invariant_violation_rate": round(c["invariant_violation_rate"], 4),
                "detection": c["detection"],
            })


def render_md(summary: dict, path: Path) -> None:
    integ = summary["integrity"]
    lines = ["# M2 — usage-record authority: results\n",
             f"- Generated: `{summary['generated_at']}`",
             f"- Integrity re-derivation: **{'PASS' if integ['ok'] else 'FAIL'}** "
             f"over {integ['records_checked']} records; all trials reconciled: "
             f"**{integ['all_trials_reconciled']}**\n",
             "Leakage efficiency = fraction of the true inference value the client evaded "
             "(price-tier invariant). Medium tier shown; see CSV for all tiers.\n",
             "| architecture | manipulation | n | leak eff. | request ASR (95% CI) | inv.viol | detect | safe |",
             "|---|---|---|---|---|---|---|---|"]
    for c in summary["cells"]:
        if c["price_tier"] != "medium":
            continue
        asr = c["request_asr"]
        safe = "yes" if c["request_asr"]["p"] == 0 else "NO"
        lines.append(
            f"| {c['architecture']} | {c['manipulation']} | {c['n']} "
            f"| {c['leakage_efficiency']['mean']:.2f} "
            f"| {asr['p']:.2f} [{asr['lo']:.2f},{asr['hi']:.2f}] "
            f"| {c['invariant_violation_rate']:.2f} | {c['detection']} | {safe} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _latest() -> Path:
    raw = Path(__file__).resolve().parents[1] / "results" / "raw"
    cands = sorted(raw.glob("m2_*.json"))
    if not cands:
        raise SystemExit("no results/raw/m2_*.json; run experiments.run_m2 first")
    return max(cands, key=lambda p: p.stat().st_mtime)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None)
    args = ap.parse_args()
    inp = Path(args.input) if args.input else _latest()
    raw = json.loads(inp.read_text(encoding="utf-8"))
    summary = summarize(raw)
    PROC.mkdir(parents=True, exist_ok=True)
    stem = inp.stem
    (PROC / f"{stem}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    render_csv(summary, PROC / f"{stem}.summary.csv")
    render_md(summary, PROC / f"{stem}.summary.md")
    integ = summary["integrity"]
    print(f"input: {inp}")
    print(f"integrity: {'PASS' if integ['ok'] else 'FAIL'} ({len(integ['problems'])} problems); "
          f"reconciled={integ['all_trials_reconciled']}")
    print(f"processed -> {PROC}/{stem}.summary.{{json,csv,md}}")
    if not integ["ok"]:
        for p in integ["problems"][:10]:
            print("  -", p)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
