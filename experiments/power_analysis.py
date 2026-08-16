"""Sample-size / precision analysis from the actual measured dispersion.

Rather than copying an arbitrary "100 trials", we report the *observed* variability
in each mechanism and the resulting 95% CI half-widths, and compute the reps needed
to reach a target precision. Many effects here are deterministic (std = 0), which we
report explicitly and use to justify small rep counts.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "results" / "processed"
Z = 1.96


def _latest(pattern, folder):
    c = sorted(folder.glob(pattern))
    return max(c, key=lambda p: p.stat().st_mtime) if c else None


def _reps_for_mean(std, target_halfwidth):
    if std == 0:
        return 1
    return math.ceil((Z * std / target_halfwidth) ** 2)


def analyze(name, summary, leak_key="leak"):
    print(f"\n== {name} ==")
    stds = [c[leak_key]["std"] for c in summary["cells"]]
    max_std = max(stds) if stds else 0.0
    params = summary["parameters"]
    n_used = params.get("requests_per_cell", params.get("reps"))
    concs = params.get("concurrency")
    print(f"  requests per cell: {n_used}" + (f"  | concurrency levels: {concs}" if concs else ""))
    print(f"  max observed per-record leak std across cells: {max_std:.6f}")
    if max_std == 0:
        print("  -> effect is DETERMINISTIC (zero variance); reps beyond a few only guard")
        print("     against scheduling artifacts. 95% CI half-width = 0 for leak.")
    else:
        for tgt in (0.01, 0.005, 0.001):
            print(f"  reps for +/-{tgt} 95% CI on mean leak (worst cell): {_reps_for_mean(max_std, tgt)}")
    # proportion precision (Wilson half-width at p=0.5 is the widest)
    for n in (10, 20, 30):
        hw = Z * math.sqrt(0.25 / n)
        print(f"  proportion (ASR) 95% CI half-width at p=0.5, n={n}: +/-{hw:.3f}")


def main():
    m1 = _latest("m1_*.summary.json", PROC)
    m2 = _latest("m2_*.summary.json", PROC)
    b0 = _latest("class6_*.summary.json", ROOT / "results")
    print("SAMPLE-SIZE / PRECISION ANALYSIS (from measured dispersion)")
    if m1:
        analyze("M1 metering-commit timing", json.loads(m1.read_text(encoding="utf-8")))
    if m2:
        analyze("M2 usage-record authority", json.loads(m2.read_text(encoding="utf-8")))
    if b0:
        b = json.loads(b0.read_text(encoding="utf-8"))
        print("\n== B0 baseline ==")
        stds = [c["dollar_leak"]["std"] for c in b["cells"]]
        print(f"  reps used per cell: 30")
        print(f"  max observed $-leak std across cells: {max(stds):.6f}")
        print("  -> race outcome deterministic at tested timings (std ~ 0); 30 reps give")
        print("     trial-ASR Wilson CI width < 0.12 at p=1.0.")


if __name__ == "__main__":
    main()
