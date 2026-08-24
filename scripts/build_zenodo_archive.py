"""Build the Zenodo deposition archive for the frozen v1.0.1 artifact.

The archive contents are taken from `git ls-files` at HEAD rather than from a
directory walk. That is deliberate: `.gitignore` already encodes every exclusion the
deposition needs -- secrets and key material, Docker and tokenizer caches, model
weights, the TLA+ tools jar, LaTeX intermediates, OS metadata, experiment scratch --
so archiving the tracked set means the exclusions cannot silently drift apart from the
repository's own rules. A file that is in the archive is a file that is in the frozen,
published artifact.

A small set of further exclusions is applied on top, for files that are tracked but
are working context rather than archival record.

This script does not read, regenerate, or modify any experimental data; it only copies
already-committed bytes into a zip and hashes the result.

Usage:
    python scripts/build_zenodo_archive.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "zenodo"
VERSION = "v1.0.1"
STEM = f"token-accounting-integrity-{VERSION}"

# Tracked, but not part of the archival record.
EXCLUDE_EXACT = {
    "CLAUDE.md",          # working context; supersession noted in RELEASE_FREEZE.md
}
EXCLUDE_PREFIX = (
    "scripts/_patch_",    # one-shot manuscript patch scripts, already applied
    "release/zenodo/",    # describes this archive; including it would be circular
)


def tracked_files() -> list[str]:
    r = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                       capture_output=True, text=True, check=True)
    return [f for f in r.stdout.split("\0") if f]


def wanted(path: str) -> bool:
    if path in EXCLUDE_EXACT:
        return False
    return not any(path.startswith(p) for p in EXCLUDE_PREFIX)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        print("REFUSING: working tree is not clean. The archive must correspond to a")
        print("committed state, or its checksum documents nothing.")
        print(dirty)
        sys.exit(1)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()

    files = [f for f in tracked_files() if wanted(f)]
    skipped = [f for f in tracked_files() if not wanted(f)]

    OUT.mkdir(parents=True, exist_ok=True)
    zip_path = OUT / f"{STEM}.zip"

    # Deterministic ordering, fixed timestamps: rebuilding from the same commit yields
    # the same bytes, so the published checksum stays verifiable.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(files):
            info = zipfile.ZipInfo(f"{STEM}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (ROOT / rel).read_bytes())

    digest = sha256(zip_path)
    size = zip_path.stat().st_size

    (OUT / "SHA256SUMS.txt").write_text(
        f"{digest}  {zip_path.name}\n", encoding="utf-8")

    manifest = [
        f"# Archive contents -- {STEM}.zip",
        "",
        f"Built from git commit `{commit}` (tag `{VERSION}`).",
        f"{len(files)} files, {size:,} bytes compressed.",
        "",
        f"SHA-256: `{digest}`",
        "",
        "Excluded by `.gitignore` (all regenerable; commands in the READMEs):",
        "",
        "- `tokenizer_cache/` -- `scripts/populate_tokenizer_cache.sh`",
        "- `vendor/`, `*.gguf` -- llama.cpp binary and model weights; download commands in `README.md`",
        "- `formal/tools/*.jar` -- TLA+ tools; download command in `formal/README.md`",
        "- `.env`, key material, credentials -- never tracked",
        "- LaTeX intermediates, Docker volumes, editor and OS metadata, experiment scratch",
        "",
        "Excluded additionally by this script:",
        "",
    ] + [f"- `{f}`" for f in sorted(skipped)] + ["", "## File list", ""]
    manifest += [f"- `{f}`" for f in sorted(files)]
    (OUT / "ARCHIVE_CONTENTS.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    print(f"  {zip_path.relative_to(ROOT)}")
    print(f"  {len(files)} files, {size:,} bytes")
    print(f"  sha256 {digest}")
    print(f"  -> release/zenodo/SHA256SUMS.txt")
    print(f"  -> release/zenodo/ARCHIVE_CONTENTS.md")
    if skipped:
        print(f"  excluded on top of .gitignore: {len(skipped)}")


if __name__ == "__main__":
    main()
