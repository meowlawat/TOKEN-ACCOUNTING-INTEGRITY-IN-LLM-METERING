"""Summarize M1 (metering-commit timing) raw results. Raw JSON in only.

Independently re-derives per-record leak and cross-checks the stored value
(integrity gate). Aggregates per (architecture, price_tier, abort_bin) cell,
producing the leak-vs-abort-timing curve with dispersion + Wilson CIs.

  leak (per record)     = (served ? authoritative_cost : 0) - net_debit   (signed)
  abort_bin             = nearest swept abort percentage (completed -> 100)
  request_ASR           = fraction of records with leak > 0                (Wilson 95%)
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


def _bin(rec: dict, bins: list[float]) -> float:
    if rec["completed"]:
        return 100.0
    ap = rec.get("abort_pct")
    if ap is None:
        return 100.0
    return min(bins, key=lambda b: abs(b - ap))


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
    return problems


def _cell(records: list[dict]) -> dict:
    rds = [_rederive(r) for r in records]
    leaks_pos = [rd["leak_pos"] for rd in rds]
    delivered = [float(r["tokens_delivered"]) for r in records]
    n = len(records)
    leaking = sum(1 for rd in rds if rd["leak"] > 0)
    violations = sum(1 for rd in rds if rd["violation"])
    det = [r["detection_level"] for r in records if _rederive(r)["leak"] > 0]
    detection = Counter(det).most_common(1)[0][0] if det else "n/a"
    return {"n": n, "leak": S.describe(leaks_pos), "leak_ci": S.mean_ci(leaks_pos),
            "tokens_delivered": S.describe(delivered),
            "request_asr": S.wilson(leaking, n),
            "invariant_violation_rate": violations / n if n else 0.0,
            "invariant_violations": violations, "detection": detection}


def summarize(raw: dict) -> dict:
    trials = raw["trials"]
    p = raw["parameters"]
    bins = list(p["abort_pcts"])
    problems, all_recon = [], True
    for t in trials:
        problems.extend(_integrity(t["records"]))
        if t.get("reconciled") is not True:
            all_recon = False

    cells = []
    for arch in p["architectures"]:
        for tier in p["tiers"]:
            trs = [t for t in trials if t["architecture"] == arch and t["price_tier"] == tier]
            by_bin: dict[float, list] = {}
            for t in trs:
                for r in t["records"]:
                    by_bin.setdefault(_bin(r, bins), []).append(r)
            for b in sorted(by_bin):
                c = _cell(by_bin[b])
                c.update({"architecture": arch, "price_tier": tier, "abort_bin": b})
                cells.append(c)

    return {
        "experiment": raw.get("experiment"), "generated_at": raw.get("generated_at"),
        "environment": raw.get("environment"), "db_info": raw.get("db_info"), "parameters": p,
        "integrity": {"records_checked": sum(len(t["records"]) for t in trials),
                      "problems": problems, "ok": len(problems) == 0,
                      "all_trials_reconciled": all_recon},
        "cells": cells,
    }


_CSV_COLS = ["architecture", "price_tier", "abort_bin", "n", "tokens_delivered_mean",
             "leak_mean", "leak_std", "request_asr", "request_asr_lo", "request_asr_hi",
             "invariant_violation_rate", "detection"]


def render_csv(summary: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_CSV_COLS)
        w.writeheader()
        for c in summary["cells"]:
            w.writerow({
                "architecture": c["architecture"], "price_tier": c["price_tier"],
                "abort_bin": c["abort_bin"], "n": c["n"],
                "tokens_delivered_mean": round(c["tokens_delivered"]["mean"], 2),
                "leak_mean": round(c["leak"]["mean"], 6), "leak_std": round(c["leak"]["std"], 6),
                "request_asr": round(c["request_asr"]["p"], 4),
                "request_asr_lo": round(c["request_asr"]["lo"], 4),
                "request_asr_hi": round(c["request_asr"]["hi"], 4),
                "invariant_violation_rate": round(c["invariant_violation_rate"], 4),
                "detection": c["detection"]})


def render_md(summary: dict, path: Path) -> None:
    integ = summary["integrity"]
    lines = ["# M1 — metering-commit timing: results\n",
             f"- Generated: `{summary['generated_at']}`",
             f"- Integrity re-derivation: **{'PASS' if integ['ok'] else 'FAIL'}** over "
             f"{integ['records_checked']} records; all trials reconciled: "
             f"**{integ['all_trials_reconciled']}**\n",
             "Leak vs abort timing (medium tier). Vulnerable architectures leak the value of "
             "tokens delivered before the (missing/late) commit; safe ones do not.\n",
             "| architecture | abort% | n | delivered | mean leak | request ASR | inv.viol | detect |",
             "|---|---|---|---|---|---|---|---|"]
    for c in summary["cells"]:
        if c["price_tier"] != "medium":
            continue
        asr = c["request_asr"]
        lines.append(
            f"| {c['architecture']} | {c['abort_bin']:.0f} | {c['n']} "
            f"| {c['tokens_delivered']['mean']:.0f} | {c['leak']['mean']:.4f} "
            f"| {asr['p']:.2f} [{asr['lo']:.2f},{asr['hi']:.2f}] "
            f"| {c['invariant_violation_rate']:.2f} | {c['detection']} |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _latest() -> Path:
    raw = Path(__file__).resolve().parents[1] / "results" / "raw"
    cands = sorted(raw.glob("m1_*.json"))
    if not cands:
        raise SystemExit("no results/raw/m1_*.json; run experiments.run_m1 first")
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
        raise SystemExit(1)


if __name__ == "__main__":
    main()
