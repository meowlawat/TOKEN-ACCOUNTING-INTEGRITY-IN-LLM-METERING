"""Export the request-lifecycle TikZ diagram as a standalone submission figure.

Elsevier asks for figures as separate files. Figure 1 in the manuscript is drawn in TikZ
rather than loaded from an image, so it has no file of its own. This script extracts the
exact TikZ picture from `paper/main_cose.tex` -- it does not redraw or restyle it -- wraps
it in a `standalone` document, and compiles it to vector PDF plus a 600 dpi PNG.

Vector PDF is preferred for line art (Elsevier's line-art tier asks for >= 1000 dpi
equivalent, which vector satisfies exactly). The PNG is provided as a fallback for
submission systems that reject PDF artwork.

The manuscript itself keeps drawing the figure inline, so the compiled paper is unchanged;
this only produces the separate artwork file the submission package needs.

Usage:
    python scripts/render_tikz_figure1.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "paper" / "main_cose.tex"
OUT = ROOT / "paper" / "figures_cose"

PREAMBLE = r"""\documentclass[border=4pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,calc}
\begin{document}
"""


def extract_tikzpicture(tex: str) -> str:
    """Pull the tikzpicture verbatim out of the first figure environment."""
    start = tex.index(r"\begin{tikzpicture}")
    end = tex.index(r"\end{tikzpicture}") + len(r"\end{tikzpicture}")
    return tex[start:end]


def main() -> None:
    tex = SRC.read_text(encoding="utf-8")
    pic = extract_tikzpicture(tex)

    # \textsc inside the picture needs no extra package; \color does not either.
    doc = PREAMBLE + pic + "\n\\end{document}\n"

    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "fig1.tex").write_text(doc, encoding="utf-8")
        r = subprocess.run(["tectonic", "-X", "compile", "fig1.tex"],
                           cwd=td, capture_output=True, text=True)
        pdf = td / "fig1.pdf"
        if not pdf.exists():
            print("COMPILE FAILED")
            print((r.stdout + r.stderr)[-2000:])
            sys.exit(1)

        shutil.copyfile(pdf, OUT / "Figure_1.pdf")
        print(f"  wrote figures_cose/Figure_1.pdf (vector)")

        # 600 dpi raster fallback. Open the COPY, not the file inside the temp dir --
        # leaving a handle open there makes TemporaryDirectory cleanup fail on Windows.
        try:
            import pymupdf
            d = pymupdf.open(OUT / "Figure_1.pdf")
            d[0].get_pixmap(dpi=600).save(OUT / "Figure_1.png")
            d.close()
            print(f"  wrote figures_cose/Figure_1.png (600 dpi fallback)")
        except ImportError:
            print("  pymupdf unavailable; PNG fallback skipped")

    print("\nFigure 1 (request lifecycle) exported. The manuscript still draws it inline;")
    print("this file exists only for separate-artwork submission.")


if __name__ == "__main__":
    main()
