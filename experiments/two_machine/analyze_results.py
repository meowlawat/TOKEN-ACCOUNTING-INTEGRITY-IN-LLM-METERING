"""Aggregate statistics over one or more run_distributed_experiment.py summary files.

Every number in the output table is computed here, directly from the raw per-cell data
in the summary JSON (which itself was written directly from the per-request JSONL) --
nothing is hand-entered. Invalid cells are reported, never silently dropped from the
count (they're excluded from the mean/stdev, which is called out in the invalid_cells
column rather than hidden).

Usage:
    python -m experiments.two_machine.analyze_results results/two_machine/C0_sequential_*.summary.json
"""

from __future__ import annotations

import argparse
import glob
import json
import statistics
from pathlib import Path


def percentile(data: list[float], p: float) -> float:
    if not data:
        return float("nan")
    data = sorted(data)
    k = (len(data) - 1) * p
    f, c = int(k), min(int(k) + 1, len(data) - 1)
    return data[f] if f == c else data[f] + (data[c] - data[f]) * (k - f)


def load_cells(paths: list[str]) -> list[dict]:
    cells = []
    for pattern in paths:
        for p in glob.glob(pattern):
            doc = json.loads(Path(p).read_text(encoding="utf-8"))
            manifest = doc["manifest"]
            for cell in doc["cells"]:
                cell = {**cell, "_condition": manifest["condition"],
                       "_arrival": manifest["arrival"], "_source_file": p}
                cells.append(cell)
    return cells


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("summary_globs", nargs="+",
                    help="summary.json file(s) or glob pattern(s)")
    args = ap.parse_args()

    cells = load_cells(args.summary_globs)
    if not cells:
        print("No cells loaded -- check the glob pattern(s).")
        return

    groups: dict[tuple, list[dict]] = {}
    for c in cells:
        key = (c["_condition"], c["_arrival"], c.get("delay_ms"))
        groups.setdefault(key, []).append(c)

    print(f"{'condition':<6}{'arrival':<12}{'delay_ms':>9}{'n':>4}{'valid':>7}"
          f"{'over_svc_mean':>14}{'over_svc_median':>16}{'over_svc_stdev':>15}"
          f"{'over_svc_p95':>13}")
    rows_out = []
    for (cond, arrival, delay), group in sorted(groups.items(), key=lambda k: (k[0][0], k[0][1], k[0][2] or 0)):
        valid = [c for c in group if c.get("valid")]
        n = len(group)
        nv = len(valid)
        over = [c["over_served"] for c in valid if c.get("over_served") is not None]
        row = {
            "condition": cond, "arrival": arrival, "delay_ms": delay,
            "n_total": n, "n_valid": nv, "n_invalid": n - nv,
            "over_served_mean": statistics.mean(over) if over else None,
            "over_served_median": statistics.median(over) if over else None,
            "over_served_stdev": statistics.stdev(over) if len(over) > 1 else (0.0 if over else None),
            "over_served_p95": percentile([float(x) for x in over], 0.95) if over else None,
            "over_served_raw": over,
            "source_files": sorted(set(c["_source_file"] for c in group)),
        }
        rows_out.append(row)
        def fmt(v, nd=2):
            return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "-"
        print(f"{cond:<6}{arrival:<12}{str(delay):>9}{n:>4}{nv:>7}"
              f"{fmt(row['over_served_mean']):>14}{fmt(row['over_served_median']):>16}"
              f"{fmt(row['over_served_stdev']):>15}{fmt(row['over_served_p95']):>13}")

    out_path = Path("results/two_machine/analysis_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows_out, indent=2, default=str), encoding="utf-8")
    print(f"\n-> {out_path}")

    total_invalid = sum(r["n_invalid"] for r in rows_out)
    if total_invalid:
        print(f"\nWARNING: {total_invalid} invalid cell(s) across all loaded runs -- "
              f"excluded from the statistics above but NOT deleted from the raw data.")


if __name__ == "__main__":
    main()
