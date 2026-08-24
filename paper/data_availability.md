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

**DOI minted.**

```
Concept DOI (all versions, always latest):  10.5281/zenodo.22085827
Version DOI (v1.0.1):                       10.5281/zenodo.22085828
Record:                                     https://zenodo.org/records/22085828
```

The manuscript cites the **concept** DOI. That is deliberate: a concept DOI resolves to
the most recent version of the record, so it stays correct when a new version is
deposited — which is exactly what has to happen next (see below). The version DOI is also
given, for anyone who wants the precise snapshot this paper reports.

**The record is not yet complete.** As deposited it contains only `main_cose.tex` and
`main_cose.pdf` — the manuscript, not the artifact. Until the archive below is uploaded as
a new version, the sentence "all raw experimental data are released" is true of GitHub but
not of the Zenodo record. See `paper/SUBMISSION_BLOCKERS.md` item 1.

The deposition package is built and waiting in `release/zenodo/`:

The deposition package is built and waiting in `release/zenodo/`:

| file | what it is |
|---|---|
| `token-accounting-integrity-v1.0.1.zip` | the archive — 334 files, 8.1 MB |
| `SHA256SUMS.txt` | its SHA-256 checksum |
| `ARCHIVE_CONTENTS.md` | complete file list, and what was excluded and why |
| `metadata.md` | every Zenodo form field |

The archive is rebuilt byte-identically from the same tracked content by
`scripts/build_zenodo_archive.py`, so the published checksum stays verifiable by anyone.

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
