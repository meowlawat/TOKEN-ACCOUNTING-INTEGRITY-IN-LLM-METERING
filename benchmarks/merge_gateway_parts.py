"""Merge per-size gateway_recount partial runs into one raw file.

The gateway sweep is run in per-size chunks (each chunk contains every engine and
concurrency for that size, so the within-chunk throughput ratios are already valid).
This merges the chunks into a single `gateway_recount_<ts>.json` for summarizing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"


def main() -> None:
    parts = sorted(RAW.glob("gw_part_*.json"))
    if not parts:
        raise SystemExit("no results/raw/gw_part_*.json found")
    base = json.loads(parts[0].read_text(encoding="utf-8"))
    cells: list[dict] = []
    sizes: list[int] = []
    for p in parts:
        d = json.loads(p.read_text(encoding="utf-8"))
        cells.extend(d["cells"])
        sizes.extend(d["parameters"]["sizes"])
    base["cells"] = cells
    base["parameters"]["sizes"] = sorted(set(sizes))
    base["generated_at"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base["merged_from"] = [p.name for p in parts]
    out = RAW / f"gateway_recount_{base['generated_at']}.json"
    out.write_text(json.dumps(base, indent=2), encoding="utf-8")
    print(f"merged {len(parts)} parts, {len(cells)} cells, sizes={base['parameters']['sizes']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
