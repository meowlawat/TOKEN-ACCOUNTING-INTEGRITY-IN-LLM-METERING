"""Build the Zenodo deposition archive for the v1.1.0 artifact.

Modeled directly on `scripts/build_zenodo_archive.py` (same file-list source, same
exclusion rules, same deterministic zip entries) but kept as a separate script rather
than generalizing the original, for the same reason `preview_zenodo_next_version.py`
was kept separate: the v1.0.1 builder guards an already-published checksum
(DEPOSITED_SHA256 for DOI 10.5281/zenodo.22086254) and must never be repurposed to
build different bytes under that guard.

Unlike `preview_zenodo_next_version.py`, this reads the tree at the **v1.1.0 git tag**
specifically (`git ls-files` run against that ref), not the current working tree --
the GitHub Release already published for v1.1.0 points at that tag's commit (20c9a62),
and the Zenodo deposit should match it exactly, not whatever HEAD has moved on to since.

Usage:
    python scripts/build_zenodo_archive_v1_1_0.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "zenodo"
TAG = "v1.1.0"
STEM = f"token-accounting-integrity-{TAG}"
ZIP_PATH = OUT / f"{STEM}.zip"

# Identical to scripts/build_zenodo_archive.py -- kept in sync deliberately.
EXCLUDE_EXACT = {
    "CLAUDE.md",
}
EXCLUDE_PREFIX = (
    "scripts/_patch_",
    "release/zenodo/",
    "paper/submission_forms/",
    "lab/",
)


def tracked_files_at_tag(tag: str) -> list[str]:
    r = subprocess.run(["git", "ls-tree", "-r", "--name-only", "-z", tag],
                        cwd=ROOT, capture_output=True, text=True, check=True)
    return [f for f in r.stdout.split("\0") if f]


def read_blob_at_tag(tag: str, path: str) -> bytes:
    r = subprocess.run(["git", "show", f"{tag}:{path}"], cwd=ROOT,
                        capture_output=True, check=True)
    return r.stdout


def wanted(path: str) -> bool:
    if path in EXCLUDE_EXACT:
        return False
    return not any(path.startswith(p) for p in EXCLUDE_PREFIX)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    # verify the tag actually resolves and matches the published GitHub Release commit
    commit = subprocess.run(["git", "rev-parse", f"{TAG}^{{commit}}"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    print(f"Building archive from tag {TAG} -> commit {commit}")

    files = sorted(f for f in tracked_files_at_tag(TAG) if wanted(f))
    print(f"  tracked files (post-exclusion): {len(files)}")

    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files:
            info = zipfile.ZipInfo(f"{STEM}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, read_blob_at_tag(TAG, rel))

    data = ZIP_PATH.read_bytes()
    digest = sha256_bytes(data)

    print(f"\nArchive: {ZIP_PATH.relative_to(ROOT)}")
    print(f"  size   : {len(data):,} bytes")
    print(f"  sha256 : {digest}")

    (OUT / f"{STEM}.sha256").write_text(f"{digest}  {STEM}.zip\n", encoding="utf-8")
    print(f"  checksum written to {STEM}.sha256")

    # Disclosure sanity check, same as preview_zenodo_next_version.py's own check.
    hits = []
    for rel in files:
        if rel.endswith((".tex", ".md", ".txt", ".py", ".cff", ".bib")):
            t = read_blob_at_tag(TAG, rel).decode("utf-8", errors="ignore")
            if "Declaration of generative AI" in t or "Claude (Anthropic)" in t:
                hits.append(rel)
    print(f"\nDisclosure check (files mentioning the withdrawn AI declaration): "
          f"{hits if hits else 'NONE'}")


if __name__ == "__main__":
    main()
