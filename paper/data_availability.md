# Data availability statement

## What is released, and where

**GitHub (source code and artifact).**
https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING, tagged release
`v1.0.0`. This contains:

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

**Not yet created.** A Zenodo archival snapshot of the `v1.0.0` release is planned prior
to journal submission, following the standard GitHub-to-Zenodo archiving process
(Zenodo mints a DOI for a tagged release and preserves it independently of GitHub).
Until that snapshot exists, the manuscript's data-availability statement reads:

> [ZENODO DOI TO BE INSERTED]

This is a real, tracked blocker. See `paper/SUBMISSION_BLOCKERS.md`.

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
