# Artifact README

This artifact accompanies **"Token-Accounting Integrity: Measuring Client-Side
Under-Payment in LLM Metering Architectures."** It contains a
vulnerable-by-construction LLM gateway, an attack harness, defense implementations,
every experiment, and the scripts that regenerate all figures, tables, statistics and
the paper PDF from raw data.

This document assumes **no prior Docker experience**.

---

## 1. What this artifact does

It measures whether a *dishonest client* can obtain LLM inference while under-paying an
*honest provider*, across three architectural dimensions:

| id | dimension | question |
|---|---|---|
| **B0** | state synchronization | is the authorize-and-decrement transition atomic? *(known baseline)* |
| **M1** | commitment timing | is the charge irrevocable before value is delivered? |
| **M2** | usage authority | who decides the billed quantity? |

Everything runs **locally**. No third-party or production system is ever contacted.

## 2. Hardware and software used for the reported results

| item | value |
|---|---|
| CPU | Intel i5-13450HX, 16 logical cores |
| RAM | 16 GB |
| OS | Windows 11 (build 26200) + Docker Desktop (Linux VM backend) |
| Docker | 29.7.2, Compose 5.3.1 |
| PostgreSQL / Redis | 16.15 / 7.4.10 (via Compose) |
| Python (host) | 3.13 |
| Python (container) | 3.11 |

Exact versions and artifact hashes for the run that produced the shipped results are in
**`results/reproduction_manifest.json`**.

A Linux or macOS host works too; see §9 for platform differences.

## 3. Prerequisites

1. **Docker Desktop** (or Docker Engine + Compose v2) installed and *running*.
   Verify: `docker info` prints server details without error.
2. **Python 3.11+** on the host with these packages:

```bash
python -m pip install "httpx[http2]" numpy matplotlib scipy statsmodels \
                      tiktoken transformers tokenizers sentencepiece torch psutil
```

`torch` is CPU-only and is needed **solely** for the small real-model experiment
(§6, stage 7e). Everything else works without it.

3. *(Optional, for the PDF)* [`tectonic`](https://tectonic-typesetting.github.io) on
   `PATH`. Without it every experiment still runs; only PDF compilation is skipped.

## 4. One-time setup: tokenizer cache

The gateway performs real tokenizer recounts **offline**, from a mounted cache. Populate
it once (this step needs network access; it downloads *tokenizer artifacts only*, no
model weights, ~8 MB):

```bash
bash scripts/populate_tokenizer_cache.sh
```

This fetches tiktoken `cl100k_base`/`o200k_base` and
`hf-internal-testing/llama-tokenizer` (an open, non-gated Llama tokenizer) into
`tokenizer_cache/`, which `docker-compose.yml` mounts read-only at `/tokcache`.

The real-model experiment additionally downloads `HuggingFaceTB/SmolLM2-135M`
(~270 MB) on first run.

## 5. Quick start (5 minutes)

```bash
docker compose up --build -d          # start gateway :8000, Postgres :5432, Redis :6379
curl http://localhost:8000/health     # {"status":"ok","db":"ok","redis":"ok"}

python -m experiments.regression_class6   # B0 controls   -> expect 19/19 PASS
python -m experiments.regression_m        # M1/M2 controls -> expect 16/16 PASS
```

If both suites pass, the testbed is working. Stop with `docker compose down`
(add `-v` to also delete the database volume).

## 6. Full reproduction

```bash
bash scripts/reproduce_all.sh          # Linux/macOS/Git-Bash
powershell scripts/reproduce_all.ps1   # Windows PowerShell
```

Stages, in order, with approximate runtimes on the reference hardware:

| # | stage | ~time |
|---|---|---|
| 1–3 | build stack, clean schema, regression suites | 3 min |
| 4 | B0 concurrency sweep (420 trials) + summary | 9 min |
| 5 | M1 sweep, concurrency 1–100 (120 cells) | 4 min |
| 6 | M2 sweep, concurrency 1–100 (240 cells) | 5 min |
| 7 | mock-path defense overhead | 2 min |
| 7b | **tokenizer benchmark** (100 cells) + **gateway recount** (4 chunks) | 17 + 24 min |
| 7c | ablation, failure modes, cross-validation | 10 min |
| 7d | economic sensitivity (3 price tiers) | 5 min |
| 7e | **local real-model experiment** | 20 min |
| 7f | fault injection + metamorphic validation | 3 min |
| 8 | figures, tables, statistics, claim matrix | 2 min |
| 9 | compile paper PDF | 1 min |

**Total ≈ 1 h 45 m.** Stages are independent; you can run any single one on its own
(see the commands listed in `results/reproduction_manifest.json` → `stages`).

## 7. Outputs and how to regenerate them

```
results/raw/          raw JSON, one file per experiment  (the ONLY source of truth)
results/processed/    summaries + integrity verdicts derived from raw
results/tables/       .md and .tex tables + stats_output.txt
results/figures/      .png figures
paper/main.pdf        compiled paper
results/reproduction_manifest.json   provenance: commit, env, versions, file hashes
```

Regenerate derived artifacts **without** re-running experiments:

```bash
python -m experiments.summarize_class6      # B0 summary (+ integrity gates)
python -m experiments.summarize_m1          # M1 summary
python -m experiments.summarize_m2          # M2 summary
python -m benchmarks.summarize_benchmarks   # tokenizer + gateway tables/figures
python -m experiments.summarize_ablation    # ablation + lifecycle failure tables
python -m experiments.economic_analysis     # formal M2 + economic tables
python -m experiments.figures               # all .png figures
python -m experiments.tables                # all .tex/.md tables
python -m experiments.statistical_analysis  # results/tables/stats_output.txt
python -m experiments.build_claim_matrix    # paper/claim_evidence_matrix.{csv,md}
```

Compile the PDF:

```bash
cd paper && tectonic main.tex && tectonic main.tex   # twice, for cross-references
```

Tables and figures are **generated**, never hand-edited. Editing a `.tex` table by hand
is a bug — fix the generator in `experiments/tables.py`,
`experiments/summarize_ablation.py` or `experiments/economic_analysis.py` instead.

## 8. How to verify the results are trustworthy

The artifact is designed so you do not have to take its word for anything:

```bash
python -m experiments.metamorphic_checks       # gates fail closed + metamorphic properties
python -m experiments.run_cross_validation     # independent re-implementation agrees
python -m experiments.build_claim_matrix       # every paper claim -> evidence file
```

- **Integrity gates.** Every summarizer recomputes each record's leakage from primitives,
  checks the invariant flag, and verifies ledger conservation
  (`Σ net-debit == initial − final`) *without trusting the application*. A mismatch exits
  non-zero and fails the pipeline.
- **Fault injection.** `metamorphic_checks.py` corrupts copies of real result files (leak
  value, debit, served flag, balance, invariant flag, deleted row) and requires each
  corruption to be detected — proving the gates can fail.
- **Independent implementation.** `defenses/m2_independent_checker.py` re-derives the M2
  verdict sharing no code path with the gateway; `run_cross_validation.py` compares them.

## 9. Known platform differences

- **Windows + Docker Desktop** adds ~45 ms per request through the VM loopback. This
  inflates *absolute* latencies and makes the gateway recount ratios *conservative* for
  small inputs. Linux with native Docker will show lower absolute latency; relative
  comparisons are unaffected.
- **`docker compose` v1 (`docker-compose`)** is not supported; use Compose v2 syntax.
- **CPU core count** changes the real-model experiment's absolute speed. It pins
  `torch.set_num_threads(4)` for stability; the reported *ratio* is the meaningful output.
- **Apple Silicon / ARM**: images are `python:3.11-slim`, `postgres:16-alpine`,
  `redis:7-alpine`, all multi-arch. `torch` CPU wheels exist for ARM64 macOS.

## 10. Known sources of timing variance

Deterministic quantities (leakage, efficiency, ASR, invariant violations) are exactly
reproducible — they depend only on inputs and code paths, not timing. The following
**will** vary between runs and are reported with intervals, not frozen numbers:

- gateway throughput ratios (worst at concurrency ≥ 50: repeat spread up to ~17 %),
- client-observed latency percentiles,
- tokenizer wall-clock timings (CPU contention, cache state),
- real-model end-to-end timings (±10 % band).

`paper/reproduction_consistency.md` records the observed run-to-run intervals from an
actual clean re-run. If a *deterministic* metric changes between runs, that is a bug and
the audit flags it as one.

## 11. Ethics and scope

All attacks target only the local testbed shipped here. The harness defaults to
`http://localhost:8000` and contains no third-party endpoints. No credentials, real user
data, or production billing APIs are used. Every attack is paired with a defense.
Referenced public artifacts (a GitHub issue, a PR, a CVE) were public before this work
and are cited as prior evidence, not as findings of ours. See
`paper/responsible_disclosure.md`.

## 12. Where to start reading

| question | file |
|---|---|
| What is the research question and threat model? | `paper/threat_model.md` |
| What exactly is being measured, and how? | `paper/experimental_methodology.md` |
| Why are B0/M1/M2 distinct? | `paper/accounting_state_model.md` |
| How is leakage defined and computed? | `paper/accounting_state_model.md` §5 |
| What is known already vs. what we add? | `paper/novelty_matrix.md`, `paper/novelty_reattack.md` |
| How do the defenses work, and what do they cost? | `paper/defense_evaluation.md` |
| What are the limitations? | `paper/threats_to_validity.md` |
| Does every claim have evidence? | `paper/claim_evidence_matrix.md` |
| Overall summary | `FINAL_RESEARCH_REPORT.md` |

## 13. Model and tokenizer artifacts

None of the third-party binaries or weights are committed. Each has a documented download,
and the research reproduces without them being redistributed here.

| artifact | identifier | how to obtain |
|---|---|---|
| TLC model checker | `tla2tools.jar`, TLC 2.19 | `curl -sSL -o formal/tools/tla2tools.jar https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar` |
| Java runtime | Temurin 25 via `jdk4py` | `pip install jdk4py` — no system JRE needed |
| Inference server | `llama.cpp` release `b10488` | see the README's real-serving section |
| Model weights | `unsloth/SmolLM2-135M-Instruct-GGUF`, file `SmolLM2-135M-Instruct-Q8_0.gguf` (Q8_0, 138 MiB) | `curl -L -o vendor/models/SmolLM2-135M-Instruct-Q8_0.gguf https://huggingface.co/unsloth/SmolLM2-135M-Instruct-GGUF/resolve/main/SmolLM2-135M-Instruct-Q8_0.gguf` |
| Transformers model (timing experiment) | `HuggingFaceTB/SmolLM2-135M` | fetched by `scripts/populate_tokenizer_cache.sh` |
| Tokenizers | tiktoken `cl100k_base` / `o200k_base`, HF fast Llama tokenizer, SentencePiece | `bash scripts/populate_tokenizer_cache.sh` (one-time, needs network) |

The container runs with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` and mounts
`tokenizer_cache/` read-only, so no network access happens at request time. That is what
makes the tokenizer benchmark timings meaningful.

**Expected fingerprints.** `results/reproduction_manifest.json` records a SHA-256 for every
tracked artifact plus the compiled PDF, and `results/environment.json` records the
environment the reported numbers came from. Compare against those rather than against
wall-clock timings, which vary by host.
