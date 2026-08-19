"""Summarize the asynchronous-accounting experiment.

Three separable findings, reported as such:

  1. With an honest pipeline, asynchronous accounting is **late, not lossy**: the mean
     exposure window tracks the configured delay and the leak reconciles to exactly zero.
  2. B0's over-serving under asynchrony is **not a concurrency race**. Requests are issued
     strictly sequentially, so any over-serving is an architectural window governed by the
     reconciliation delay relative to the inter-arrival time.
  3. M2 is unchanged by the delay, confirming analytically-predicted independence.

One measurement caveat is made explicit rather than buried: the `delayed_event` straggler
is only "reconciled" when the observation horizon (4x the delay, floored at 400 ms)
exceeds its 1 s delay. Whether a straggler looks lost or late is a property of how long
you watch, and the table says so.

Writes:
    results/tables/table_async_m1.{md,tex}
    results/tables/table_async_b0.{md,tex}
    results/processed/async_accounting.summary.json
"""

from __future__ import annotations

import glob
import json
import os
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
PROC = ROOT / "results" / "processed"
TAB = ROOT / "results" / "tables"


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


def latest(pattern: str):
    c = [p for p in glob.glob(str(RAW / pattern)) if ".summary." not in os.path.basename(p)]
    return Path(max(c, key=os.path.getmtime)) if c else None


def write_table(name, header, rows, caption, label):
    TAB.mkdir(parents=True, exist_ok=True)
    md = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    (TAB / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    def esc(x):
        # Escape the literal dollar FIRST: the > / < replacements below deliberately
        # introduce math mode, so escaping afterwards would mangle them.
        return (str(x).replace("$", r"\$").replace("_", r"\_").replace("%", r"\%")
                .replace("&", r"\&").replace(">", r"$>$").replace("<", r"$<$"))
    tex = [r"\begin{table}[t]\centering", r"\caption{" + esc(caption) + "}",
           r"\label{" + label + "}", r"\resizebox{\linewidth}{!}{%",
           r"\begin{tabular}{" + "l" * len(header) + "}", r"\toprule",
           " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
    tex += [" & ".join(esc(c) for c in r) + r" \\" for r in rows]
    tex += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    (TAB / f"{name}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


def main() -> None:
    src = latest("async_accounting_*.json")
    if not src:
        raise SystemExit("no async_accounting_*.json in results/raw")
    d = json.loads(src.read_text(encoding="utf-8"))

    # ---------------- M1 ----------------------------------------------------
    m1_rows = []
    window_by_delay = {}
    for r in d["m1"]:
        w = r["exposure_window_ms"]
        mean_w = w.get("mean")
        if r["fault"] == "none" and mean_w is not None:
            window_by_delay[r["delay_ms"]] = mean_w
        m1_rows.append([
            f"{r['delay_ms']:.0f}", r["fault"], r["delivered_value"], r["charged"],
            r["leak"], "-" if mean_w is None else f"{mean_w:.1f}",
            "-" if w.get("p95") is None else f"{w['p95']:.1f}",
            "yes" if r["reconciled"] else "NO",
        ])
    write_table("table_async_m1",
                ["delay (ms)", "fault", "delivered ($)", "charged ($)", "leak ($)",
                 "window mean (ms)", "window p95 (ms)", "reconciled"],
                m1_rows,
                "M1 under asynchronous settlement with a continuously running accounting "
                "worker. With an honest pipeline the mean exposure window tracks the "
                "configured reconciliation delay and the leak reconciles to exactly zero: "
                "asynchronous accounting is late, not lossy. Duplicate events are "
                "suppressed idempotently. A lost event leaks permanently. Whether the "
                "`delayed_event' straggler (fixed 1 s) appears lost or merely late "
                "depends on the observation horizon (4x the delay, floored at 400 ms), "
                "which is a property of the observer, not of the architecture.",
                "tab:asyncm1")

    # ---------------- B0 ----------------------------------------------------
    b0_rows = []
    for r in d["b0"]:
        b0_rows.append([f"{r['delay_ms']:.0f}", f"{r['interarrival_ms']:.0f}",
                        r["issued"], r["served"], r["affordable"], r["over_served"],
                        r["final_balance"]])
    write_table("table_async_b0",
                ["delay (ms)", "inter-arrival (ms)", "issued", "served", "affordable",
                 "over-served", "final balance ($)"],
                b0_rows,
                "B0 under asynchronous settlement. Requests are issued STRICTLY "
                "SEQUENTIALLY, 20 ms apart, so no two are ever in flight together: any "
                "over-serving here cannot be a concurrency race. Over-serving instead "
                "appears once the reconciliation delay exceeds the inter-arrival time, "
                "and the balance goes negative. Decoupling settlement converts a timing "
                "race into an architectural window.",
                "tab:asyncb0")

    m2_effs = sorted({round(x["leakage_efficiency"], 6) for x in d["m2"]})
    honest = [r for r in d["m1"] if r["fault"] == "none"]
    lost = [r for r in d["m1"] if r["fault"] == "lost_event"]
    dup = [r for r in d["m1"] if r["fault"] == "duplicate_event"]

    summary = {
        "source": src.name,
        "parameters": d["parameters"],
        "m1_honest_all_reconciled": all(r["reconciled"] for r in honest),
        "m1_lost_event_all_leak": all(D(r["leak"]) > 0 for r in lost),
        "m1_duplicate_all_reconciled": all(r["reconciled"] for r in dup),
        "m1_duplicates_suppressed": sum(r["duplicates_suppressed"] for r in dup),
        "exposure_window_mean_ms_by_delay": window_by_delay,
        "b0_over_serving_threshold_ms": next(
            (r["delay_ms"] for r in sorted(d["b0"], key=lambda x: x["delay_ms"])
             if r["over_served"] > 0), None),
        "b0_max_over_served": max(r["over_served"] for r in d["b0"]),
        "b0_sequential": True,
        "m2_distinct_efficiencies": m2_effs,
        "m2_delay_independent": len(m2_effs) == 1,
    }
    PROC.mkdir(parents=True, exist_ok=True)
    (PROC / "async_accounting.summary.json").write_text(json.dumps(summary, indent=2,
                                                                   default=str),
                                                        encoding="utf-8")

    print("=" * 78)
    print("ASYNCHRONOUS ACCOUNTING")
    print("=" * 78)
    print("M1  honest pipeline reconciles to zero leak at every delay : "
          f"{summary['m1_honest_all_reconciled']}")
    print("    exposure window (mean ms) by configured delay          : "
          + ", ".join(f"{int(k)}->{v:.1f}" for k, v in sorted(window_by_delay.items())))
    print(f"    lost event leaks permanently at every delay            : "
          f"{summary['m1_lost_event_all_leak']}")
    print(f"    duplicate events suppressed (idempotent), leak zero    : "
          f"{summary['m1_duplicate_all_reconciled']} "
          f"({summary['m1_duplicates_suppressed']} suppressed)")
    print(f"\nB0  arrivals are SEQUENTIAL ({d['parameters']['b0_interarrival_ms']:.0f} ms apart) "
          f"-- no concurrency at all")
    print(f"    over-serving begins at delay                           : "
          f"{summary['b0_over_serving_threshold_ms']} ms")
    print(f"    worst case                                             : "
          f"{summary['b0_max_over_served']} requests over budget, balance negative")
    print(f"\nM2  distinct leakage efficiencies across delays           : "
          f"{m2_effs}  (delay-independent: {summary['m2_delay_independent']})")
    print("\ntables -> table_async_m1, table_async_b0")


if __name__ == "__main__":
    main()
