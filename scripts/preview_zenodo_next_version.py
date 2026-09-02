"""Build a PREVIEW of the next Zenodo archive, without committing or publishing anything.

Why this exists separately from `scripts/build_zenodo_archive.py`:

  * that builder refuses to run against a dirty working tree, by design, because a
    checksum over uncommitted bytes documents nothing permanent;
  * it also guards the already-deposited archive so it cannot be silently rebuilt out
    from under the checksum published at DOI 10.5281/zenodo.22086254.

Both guards are correct and are left intact. This script does not modify, overwrite, or
replace either the deposited archive or `SHA256SUMS.txt`. It writes one clearly-named
preview file so the author can inspect exactly what a corrected deposition would contain
before deciding whether to publish a new Zenodo version.

It mirrors the real builder's behaviour exactly -- same exclusion rules, same file list
source (`git ls-files`), same deterministic entry ordering and fixed timestamps -- and
differs only in reading the current working tree rather than requiring a clean one.

Usage:
    python scripts/preview_zenodo_next_version.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "zenodo"

# The currently published deposition, for comparison. Not modified.
PUBLISHED_ZIP = OUT / "token-accounting-integrity-v1.0.1.zip"
PUBLISHED_DOI = "10.5281/zenodo.22086254"

# Proposed next Zenodo record version. The published record is 1.0.2.
NEXT_VERSION = "1.0.3"
STEM = f"token-accounting-integrity-v{NEXT_VERSION}"
PREVIEW_ZIP = OUT / f"{STEM}.PREVIEW.zip"

# Identical to scripts/build_zenodo_archive.py -- kept in sync deliberately.
EXCLUDE_EXACT = {"CLAUDE.md"}
EXCLUDE_PREFIX = (
    "scripts/_patch_",
    "release/zenodo/",
    "paper/submission_forms/",
)


def tracked_files() -> list[str]:
    r = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                       capture_output=True, text=True, check=True)
    return [f for f in r.stdout.split("\0") if f]


def wanted(path: str) -> bool:
    if path in EXCLUDE_EXACT:
        return False
    return not any(path.startswith(p) for p in EXCLUDE_PREFIX)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    files = sorted(f for f in tracked_files() if wanted(f))

    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PREVIEW_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files:
            info = zipfile.ZipInfo(f"{STEM}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (ROOT / rel).read_bytes())

    data = PREVIEW_ZIP.read_bytes()
    digest = sha256_bytes(data)

    print(f"PREVIEW archive : {PREVIEW_ZIP.relative_to(ROOT)}")
    print(f"  proposed Zenodo record version : {NEXT_VERSION}")
    print(f"  files                          : {len(files)}")
    print(f"  size                           : {len(data):,} bytes")
    print(f"  sha256                         : {digest}")
    print()

    # ---- compare against the published deposition -----------------------------------
    if not PUBLISHED_ZIP.exists():
        print("published archive not present locally; skipping comparison")
        return

    pub = zipfile.ZipFile(PUBLISHED_ZIP)
    new = zipfile.ZipFile(PREVIEW_ZIP)

    def strip(names, stem):
        return {n[len(stem) + 1:]: n for n in names if n.startswith(stem + "/")}

    pub_map = strip(pub.namelist(), "token-accounting-integrity-v1.0.1")
    new_map = strip(new.namelist(), STEM)

    added = sorted(set(new_map) - set(pub_map))
    removed = sorted(set(pub_map) - set(new_map))
    common = sorted(set(pub_map) & set(new_map))

    changed = []
    for rel in common:
        a = pub.read(pub_map[rel])
        b = new.read(new_map[rel])
        if a != b:
            changed.append((rel, len(a), len(b)))

    print(f"Compared against published deposition (DOI {PUBLISHED_DOI}):")
    print(f"  files added   : {len(added)}")
    for f in added:
        print(f"      + {f}")
    print(f"  files removed : {len(removed)}")
    for f in removed:
        print(f"      - {f}")
    print(f"  files changed : {len(changed)}")
    for rel, na, nb in changed:
        print(f"      ~ {rel}   ({na:,} -> {nb:,} bytes)")

    print()
    print("Disclosure check inside the PREVIEW archive:")
    hits = []
    for rel, n in new_map.items():
        if rel.endswith((".tex", ".md", ".txt", ".py", ".cff", ".bib")):
            t = new.read(n).decode("utf-8", errors="ignore")
            if "Declaration of generative AI" in t or "Claude (Anthropic)" in t:
                hits.append(rel)
    print(f"  files containing the disclosure: {hits if hits else 'NONE'}")

    pub.close()
    new.close()

    print()
    print("Nothing was published. The deposited archive and SHA256SUMS.txt are untouched.")


if __name__ == "__main__":
    main()
