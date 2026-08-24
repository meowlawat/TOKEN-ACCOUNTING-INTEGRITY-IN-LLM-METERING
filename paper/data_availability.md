# Data availability statement

## What is released, and where

**GitHub (source code and artifact).**
https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING, tagged release
`v1.0.1`, which is the version reported in the manuscript. Tag `v1.0.0` is preserved
unchanged as the earlier historical snapshot; it differs only in how the B0 condition is
stated in the accompanying manuscript, and in no measured value. This contains:

- the testbed source code (gateway, architectures, accounting backends);
- the attack harness and defense implementations;
- the TLA+ specification and TLC checking driver;
- all raw experimental data (`results/raw/`), processed summaries
  (`results/processed/`), and generated tables/figures (`results/tables/`,
  `results/figures/`);
- the independent audit code (`audit/`), which imports nothing from the project and
  re-derives every reported quantity from raw data;
- both manuscript sources (`paper/main_ieee.tex`, `paper/main_cose.tex`) and their
  compiled PDFs.

GitHub provides version history and a permanent tag, but a repository can in principle
be renamed, transferred, or (in extreme cases) removed by its owner, which is why an
archival copy is also intended.

## Archival repository (dataset DOI)

**Prepared, not yet deposited. No DOI exists.**

The deposition package is built and waiting in `release/zenodo/`:

| file | what it is |
|---|---|
| `token-accounting-integrity-v1.0.1.zip` | the archive, built from the tagged commit |
| `SHA256SUMS.txt` | its SHA-256 checksum |
| `ARCHIVE_CONTENTS.md` | complete file list, and what was excluded and why |
| `metadata.md` | every Zenodo form field, filled in |

The archive is rebuilt byte-identically from the same commit by
`scripts/build_zenodo_archive.py`, so the published checksum stays verifiable by anyone.

What remains requires the author's Zenodo account: create a GitHub release for tag
`v1.0.1` (Zenodo archives on release creation, not on existing tags), enter the fields
from `metadata.md`, and publish. Zenodo mints the DOI at that point.

Until then the manuscript's data-availability statement carries an explicit placeholder:

> [ZENODO DOI TO BE INSERTED]

That placeholder is deliberate. A DOI that has not been minted must not appear anywhere
in the manuscript, the artifact, or `CITATION.cff`, in any form that could be mistaken
for a real identifier. This is a real, tracked blocker. See
`paper/SUBMISSION_BLOCKERS.md`.

## What is NOT included

No model weights are redistributed in the repository. The real-serving validation uses
third-party software (`llama.cpp`) and third-party weights
(`unsloth/SmolLM2-135M-Instruct-GGUF`) that are downloaded via documented commands in
`README.md` rather than vendored, to keep the repository at a reasonable size and avoid
redistributing someone else's model weights. The TLC model checker
(`tla2tools.jar`) is likewise downloaded rather than committed.

## Reproducibility

`results/reproduction_manifest.json` records a SHA-256 fingerprint for every tracked
artifact plus the compiled PDFs, and `results/environment.json` records the environment
the reported numbers came from. `README.md` documents the exact commands to regenerate
every experiment, table, and figure from raw data.
