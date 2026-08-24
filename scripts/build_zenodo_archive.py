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

Once the archive has been published to Zenodo, this script refuses to rebuild it: the
published checksum must keep describing the published file. Pass --rebuild to override,
and only when a new Zenodo version is going to be published for the new bytes.

Usage:
    python scripts/build_zenodo_archive.py
    python scripts/build_zenodo_archive.py --rebuild   # after clearing DEPOSITED_*
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

# Set once the archive is published. Guards against rebuilding it out from under the
# checksum that the Zenodo record and SHA256SUMS.txt both publish. Clear these (or pass
# --rebuild) only when deliberately preparing a new deposition.
DEPOSITED_DOI = "10.5281/zenodo.22086254"
DEPOSITED_SHA256 = "d8147287e9a26bcf2e4e50d198c634e3a095ca3fd6a6bbdcd5db51fdd24971bc"

# Tracked, but not part of the archival record.
EXCLUDE_EXACT = {
    "CLAUDE.md",          # working context; supersession noted in RELEASE_FREEZE.md
}
EXCLUDE_PREFIX = (
    "scripts/_patch_",    # one-shot manuscript patch scripts, already applied
    "release/zenodo/",    # describes this archive; including it would be circular
    # Journal submission materials, not research artifacts. The author's photograph and a
    # signed declaration of interests have no place in a public dataset deposition -- the
    # archive is evidence for the paper's claims, not a copy of the submission envelope.
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


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    # The archive this script builds has been PUBLISHED to Zenodo. Rebuilding it from a
    # tree that has moved on produces different bytes, and SHA256SUMS.txt would then
    # describe a file nobody can download -- the published checksum would stop verifying
    # the published deposit. That is a silent integrity failure of exactly the kind this
    # project is about, so it needs an explicit override rather than a warning.
    if DEPOSITED_SHA256 and "--rebuild" not in sys.argv:
        current = sha256(OUT / f"{STEM}.zip") if (OUT / f"{STEM}.zip").exists() else None
        print(f"REFUSING: this archive is already deposited at DOI {DEPOSITED_DOI}.")
        print()
        print(f"  deposited sha256  {DEPOSITED_SHA256}")
        print(f"  local sha256      {current or '(archive missing)'}")
        print(f"  agree             {current == DEPOSITED_SHA256}")
        print()
        print("Rebuilding would change SHA256SUMS.txt so it no longer describes the file")
        print("published at that DOI. If you genuinely need a new archive, publish a new")
        print("Zenodo version for it too, then update DEPOSITED_DOI/DEPOSITED_SHA256 here.")
        print()
        print("To rebuild anyway: python scripts/build_zenodo_archive.py --rebuild")
        sys.exit(1)

    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        print("REFUSING: working tree is not clean. The archive must correspond to a")
        print("committed state, or its checksum documents nothing.")
        print(dirty)
        sys.exit(1)

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
        f"Built from the tracked tree at tag `{VERSION}`.",
        f"{len(files)} files, {size:,} bytes compressed.",
        "",
        "The archive's identity is its SHA-256, not a commit hash: recording HEAD here",
        "would be self-referential, since committing this file changes HEAD and the file",
        "would never settle. The zip is built with sorted entries and fixed timestamps, so",
        "rebuilding it from the same tracked content reproduces the checksum below exactly.",
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
