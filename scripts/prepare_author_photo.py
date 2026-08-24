"""Prepare the author photograph for journal submission.

Takes the supplied portrait and produces a passport-style headshot at the resolution and
format Elsevier asks for. This is framing and format work only -- no retouching, no
alteration of the subject, no change to the face.

What it does:
  * flattens the transparent background onto white (JPEG carries no alpha channel);
  * crops to a 3:4 portrait, head-and-shoulders, with conventional headroom;
  * resizes to 1200x1600 px and stamps 300 dpi, which is 4 x 5.33 inches at print size --
    comfortably above Elsevier's 300 dpi minimum for a printed headshot;
  * writes JPEG at quality 95.

Note on provenance: the supplied file was processed through Google's Gemini (background
removal on a real photograph, per the author). The head-and-shoulders crop necessarily
excludes the lower corners of the frame, where the visible Gemini marker sits. Any
invisible SynthID watermark in the remaining pixels is left untouched -- provenance
marking is not something to strip, and there is no reason to: the subject is a real
photograph of the author.

Usage:
    python scripts/prepare_author_photo.py <source-image>
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "paper" / "submission_forms" / "author_photo.jpg"

# Crop geometry, as fractions of the source. Derived from the measured subject box:
# head top at y=88, shoulders spanning x=126..1875 in a 2048px square.
HEAD_TOP = 88
HEADROOM = 70          # px of white above the crown -- conventional for passport framing
TARGET_W, TARGET_H = 1200, 1600
DPI = 300


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/prepare_author_photo.py <source-image>")
    src = Path(sys.argv[1])
    im = Image.open(src)

    # Flatten onto white. JPEG has no alpha, and a transparent background would otherwise
    # composite as black.
    flat = Image.new("RGB", im.size, "white")
    flat.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)

    w, h = flat.size
    top = max(0, HEAD_TOP - HEADROOM)
    # 3:4 portrait anchored at the crown, centred horizontally on the subject.
    crop_h = min(h - top, int(w * 4 / 3))
    crop_w = int(crop_h * 3 / 4)
    left = max(0, (w - crop_w) // 2)
    box = (left, top, left + crop_w, top + crop_h)
    cropped = flat.crop(box)

    out = cropped.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT, "JPEG", quality=95, dpi=(DPI, DPI), subsampling=0)

    print(f"  source  {src.name}  {im.size[0]}x{im.size[1]} {im.mode}")
    print(f"  crop    {box}  ({crop_w}x{crop_h})")
    print(f"  output  {OUT.relative_to(OUT.parents[2])}  "
          f"{TARGET_W}x{TARGET_H} @ {DPI} dpi  ({OUT.stat().st_size/1e6:.2f} MB)")
    print(f"  print   {TARGET_W/DPI:.2f} x {TARGET_H/DPI:.2f} inches at {DPI} dpi")


if __name__ == "__main__":
    main()
