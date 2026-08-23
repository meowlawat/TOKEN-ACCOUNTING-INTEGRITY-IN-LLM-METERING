"""Compute the release inventory from git and patch the numbers into the release docs.

The counts in `RELEASE_MANIFEST.md` and `GITHUB_RELEASE_REPORT.md` were typed by hand and
were already wrong by the time they were committed: 302 and 310 tracked files against an
actual 311, and a raw-data count that missed the topology sub-sweeps. A release that claims
rigour should not carry hand-typed inventory numbers.

This script derives every count from `git ls-files` and rewrites the specific figures in
place, so re-running it after any change keeps the documentation honest.

Usage:
    python scripts/release_inventory.py            # patch the docs
    python scripts/release_inventory.py --check    # report drift, change nothing
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tracked(pattern: str = "") -> list[str]:
    cmd = ["git", "ls-files"] + ([pattern] if pattern else [])
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT).stdout
    return [x for x in out.split("\n") if x.strip()]


def inventory() -> dict:
    return {
        "total": len(tracked()),
        "raw": len(tracked("results/raw")),
        "processed": len(tracked("results/processed")),
        "tables": len(tracked("results/tables")),
        "figures": len(tracked("results/figures")),
        "formal_out": len(tracked("results/formal")),
        "paper": len(tracked("paper")),
        "app": len(tracked("app")),
        "experiments": len(tracked("experiments")),
        "formal": len(tracked("formal")),
        "audit": len(tracked("audit")),
        "scripts": len(tracked("scripts")),
    }


def patch(inv: dict, check: bool) -> list[str]:
    drift: list[str] = []

    def sub(path: Path, pattern: str, replacement: str, label: str) -> None:
        s = path.read_text(encoding="utf-8")
        new = re.sub(pattern, replacement, s, count=1)
        if new != s:
            drift.append(f"{path.name}: {label}")
            if not check:
                path.write_bytes(new.replace("\r\n", "\n").encode("utf-8"))

    man = ROOT / "RELEASE_MANIFEST.md"
    rep = ROOT / "GITHUB_RELEASE_REPORT.md"

    sub(man, r"why each part is there\. \d+ tracked files\.",
        f"why each part is there. {inv['total']} tracked files.", "total")
    sub(man, r"\| `results/raw/` \| \d+ \|",
        f"| `results/raw/` | {inv['raw']} |", "raw count")
    sub(man, r"\| `results/processed/` \| \d+ \|",
        f"| `results/processed/` | {inv['processed']} |", "processed count")
    sub(man, r"\| `results/tables/` \| \d+ \|",
        f"| `results/tables/` | {inv['tables']} |", "tables count")
    sub(man, r"\| `results/figures/` \| \d+ \|",
        f"| `results/figures/` | {inv['figures']} |", "figures count")

    # section headings in the manifest also carry counts
    sub(man, r"## `results/` \(\d+\) — the scientific evidence",
        f"## `results/` ({len(tracked('results'))}) — the scientific evidence",
        "results heading")
    sub(man, r"## `scripts/` \(\d+\)",
        f"## `scripts/` ({inv['scripts']})", "scripts heading")
    sub(man, r"## `app/` \(\d+ files\) — the testbed",
        f"## `app/` ({inv['app']} files) — the testbed", "app heading")
    sub(man, r"## `experiments/` \(\d+\) — runners",
        f"## `experiments/` ({inv['experiments']}) — runners", "experiments heading")
    sub(man, r"## `formal/` \(\d+\) — TLA\+ model",
        f"## `formal/` ({inv['formal']}) — TLA+ model", "formal heading")
    sub(man, r"## `audit/` \(\d+\) — independent verification",
        f"## `audit/` ({inv['audit']}) — independent verification", "audit heading")
    sub(man, r"## `paper/` \(\d+\)",
        f"## `paper/` ({inv['paper']})", "paper heading")

    sub(rep, r"\*\*All of it\.\*\* \d+ tracked files\.",
        f"**All of it.** {inv['total']} tracked files.", "total")
    sub(rep, r"\| Raw data \| \d+ datasets in `results/raw/`[^|]*\|",
        f"| Raw data | {inv['raw']} files in `results/raw/` covering B0, M1, M2, the "
        f"topology sweeps, backend comparison, real serving stack, asynchronous "
        f"accounting, the cached-split probe and cross-validation |", "raw count")
    sub(rep, r"\| Processed summaries \| \d+ files",
        f"| Processed summaries | {inv['processed']} files", "processed count")
    sub(rep, r"\| Tables \| \d+ generated",
        f"| Tables | {inv['tables']} generated", "tables count")
    sub(rep, r"\| Figures \| \d+ generated",
        f"| Figures | {inv['figures']} generated", "figures count")
    return drift


def main() -> None:
    check = "--check" in sys.argv
    inv = inventory()
    print("release inventory (from git ls-files):")
    for k, v in inv.items():
        print(f"  {k:<12} {v}")
    drift = patch(inv, check)
    if drift:
        print(("\ndrift found (not corrected, --check):" if check
               else "\ncorrected in the release docs:"))
        for d in drift:
            print("  ", d)
    else:
        print("\nrelease docs already match the repository.")
    sys.exit(1 if (check and drift) else 0)


if __name__ == "__main__":
    main()
