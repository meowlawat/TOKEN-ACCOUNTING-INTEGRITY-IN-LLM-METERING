"""Render the manuscript figures at Elsevier-required resolution for submission packaging.

`experiments/figures.py` is the frozen research figure generator (140 dpi, screen-quality).
This script does not modify it or the raw data it reads; it imports the same plotting
functions and calls them with `matplotlib.rcParams` overridden to 600 dpi, writing to
`paper/figures_cose/` under Elsevier's requested filenames (Figure_1, Figure_2, ...). Same
data, same plot code, higher render resolution -- a packaging step, not a research change.

Elsevier raster/halftone minimum is 300 dpi; 600 dpi clears that with margin and also
clears the 500 dpi "combination" tier. These are matplotlib raster PNGs, not vector line
art, so the 1000 dpi line-art tier does not apply.

Usage:
    python scripts/render_cose_figures.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "figures_cose"

import sys
sys.path.insert(0, str(ROOT))
from experiments import figures as F  # noqa: E402
from benchmarks import summarize_benchmarks as B  # noqa: E402

# Manuscript figure numbering. Figure 1 is the TikZ request-lifecycle diagram, drawn
# inline in the manuscript and exported separately by scripts/render_tikz_figure1.py --
# so the raster figures below start at Figure_2. Getting this mapping wrong is exactly
# the off-by-one that would ship artwork whose filenames disagree with the printed
# figure numbers.
ORDER = [
    ("fig_b0_concurrency.png", "Figure_2", F),
    ("fig_m1_abort_curve.png", "Figure_3", F),
    ("fig_m1_concurrency.png", "Figure_4", F),
    ("fig_m2_efficiency_heatmap.png", "Figure_5", F),
    ("tokenizer_latency.png", "Figure_6", B),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Redirect each generator's output directory to a scratch location so
    # results/figures/ (the frozen, tracked research artifact) is never written to by
    # this script. Same data, same plotting code -- only the destination and DPI change.
    scratch = OUT / "_scratch_600dpi"
    scratch.mkdir(parents=True, exist_ok=True)
    for mod in (F, B):
        mod.FIG = scratch
        mod.plt.rcParams.update({"figure.dpi": 600, "savefig.dpi": 600})
    F.main()
    B.main()

    n = 0
    for src_name, dst_name, _mod in ORDER:
        src = scratch / src_name
        if not src.exists():
            print(f"  MISSING: {src_name}")
            continue
        dst = OUT / f"{dst_name}.png"
        shutil.copyfile(src, dst)
        n += 1
        print(f"  {src_name} -> figures_cose/{dst_name}.png (600 dpi)")

    shutil.rmtree(scratch, ignore_errors=True)
    print(f"\n{n}/{len(ORDER)} figures rendered to {OUT}")
    print("Note: results/figures/*.png (140 dpi, frozen research artifact) is UNCHANGED --")
    print("this script only writes to paper/figures_cose/.")


if __name__ == "__main__":
    main()
