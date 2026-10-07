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

## 14. Post-v1.0.0 reproducibility extensions

**Everything in Sections 1-13 above describes the v1.0.0 frozen artifact** (release tag
`v1.0.0`, freeze commit `8775e26`; `v1.0.1` is a documentation-only correction of v1.0.0
for submission use, same scientific content). The manuscript this repository now builds
is `paper/main_fgcs.tex` — a later, FGCS-targeted retitling of the same project — and it
cites five pieces of evidence that were added **after** both tags, on top of 72
commits of post-v1.0.1 history. This section is their index. Nothing below was part of
the v1.0.0 or v1.0.1 release; none of the file paths, scripts, or results in this section
existed at either tag, and `RELEASE_MANIFEST.md`'s file inventory (312 files, "formal/
(13)") predates all of it. Every path below was checked to exist in the current working
tree before this section was written.

### 14.1 What was added, and in which commits

| area | first commit | last commit (so far) |
|---|---|---|
| Two-machine harness and Azure infrastructure | `6fbca90` | `785bf80` (pre-dates the result commits below; infrastructure only) |
| Real two-machine B0/C3 reproduction, Tier 1-3 instrumentation | `8545e59` … `31bdaf2` | `1aeb97e` |
| Second TLA+ model (`AsyncSettlementTOCTOU.tla`) | `0a0753d` | `0a0753d` |
| Sequential-arrival pacing-confound fix + strict-serial control | `f0a41ba` | `f0a41ba` |
| Corrected two-machine sweep + strict-serial data, baseline audit | `0e9d384` | `5deca0b` |
| Final hardening audit (durability gap identified, not yet fixed) | `a6039c2` | `a6039c2` |
| Transactional-outbox durability fix | `15def0a` | `15def0a` |
| Manuscript integration (`main_fgcs.tex`) | `098e09b` | `098e09b` |

`git log --oneline v1.0.1..HEAD` lists all 72 commits since the last tag; most of the
others are submission-packaging and venue-retargeting history (C&S, JISA, Computer
Networks, JSS, FGCS reformatting, Zenodo archive builds) unrelated to the experiments
indexed here.

### 14.2 Reproducibility map

| claim/result | script | raw data | commit |
|---|---|---|---|
| 1. Existing single-host B0 baseline (unchanged; `tab:asyncb0`) | `experiments/run_async_accounting.py` (v1.0.0-era, untouched) | `results/raw/async_accounting_*.json` | pre-dates `v1.0.0` |
| 2. Corrected two-machine sequential sweep (deferred settlement, real Azure network) | `experiments/two_machine/run_distributed_experiment.py` | `results/two_machine/C2_sequential_20261007T123546Z.summary.json` (derived); `experiments/two_machine/raw/C2_sequential_20261007T123546Z.{jsonl,manifest.json}` (raw, per-request) | `f0a41ba` (fix), `0e9d384` (this run) |
| 3. Strict-serial negative control (same topology) | `experiments/two_machine/run_distributed_experiment.py` | `results/two_machine/C2_strict-serial_20261007T125009Z.summary.json` (derived); `experiments/two_machine/raw/C2_strict-serial_20261007T125009Z.{jsonl,manifest.json}` (raw); 1-rep pilot: `..._C1_strict-serial_20261007T123415Z.*` in both locations | `f0a41ba` |
| 4. Redis SIGKILL durability failure (pre-fix) | `experiments/two_machine/redis_crash_durability_check.py` | recorded inline in `FINAL_HARDENING_AUDIT.md` §"Completed experiments" (direct queue/balance observation, not a JSON artifact — see §14.4) | `a6039c2` (documented), fixed in `15def0a` |
| 5. Hardened recovery (outbox) — tests A and the atomic-defense cross-check | `experiments/two_machine/run_distributed_experiment.py`, `experiments/two_machine/failure_injection*.py` | `results/two_machine/C1_concurrent_20261007T211320Z.summary.json` (test A), `results/two_machine/C3_concurrent_20261007T211848Z.summary.json` (atomic defense, unaffected) | `15def0a` |
| 5b. Hardened recovery — worker-kill/Redis-SIGKILL/duplicate-delivery tests B,D,E,G,H,I,J | manual procedure in `DURABILITY_HARDENING_AUDIT.md` §"Tests performed" | recorded inline there (worker log lines, balance checks — see §14.4) | `15def0a` |
| 6. Async TLA+ model, both `(N,k)` points, vulnerable and atomic | `java -cp formal/tools/tla2tools.jar tlc2.TLC -config formal/cfg_async/<name>.cfg -workers 1 -cleanup -deadlock formal/AsyncSettlementTOCTOU.tla` (four configs: `vulnerable_n6_k2`, `atomic_n6_k2`, `vulnerable_n4_k2`, `atomic_n4_k2`) | `formal/async_settlement_vulnerable_n6_k2_counterexample.txt` (counterexample trace); TLC's own console output for the rest, transcribed in `FORMALIZATION_AUDIT.md` §"Step 6" | `0a0753d` |

Full narrative and the complete audit trail for each row: `FINAL_HARDENING_BASELINE.md`,
`FINAL_HARDENING_AUDIT.md`, `DURABILITY_HARDENING_AUDIT.md`, `FORMALIZATION_AUDIT.md`,
`FINAL_EXPERIMENT_AUDIT.md` (contains two inline retractions of an earlier
mischaracterization — not deleted, corrected in place), `experiments/two_machine/
RESEARCH_LOG.md`, and the manuscript-side `MANUSCRIPT_INTEGRATION_PLAN.md` /
`POST_INTEGRATION_AUDIT.md`. All are in the repository root except the last two, which
sit alongside `MANUSCRIPT_INTEGRATION_PLAN.md`.

### 14.3 Which experiments need two machines/Azure, which run locally

- **Need a real second host (Azure or equivalent):** row 2 and row 3 above — the
  network-separated topology is the entire point of those two results. Reproducing the
  *exact* numbers requires `experiments/two_machine/REPRODUCIBILITY.md`'s full sequence
  (your own Azure for Students account or equivalent cloud VM; the original VM used to
  produce the shipped numbers is not shipped with this repository and
  `experiments/two_machine/azure_vm_info.json` is git-ignored local state, not a
  reusable credential or endpoint). A qualitatively similar result — the mechanism is a
  property of settlement being separated from authorization, not of Azure specifically
  — should reproduce on any two independently-clocked hosts reachable over a real
  network; the specific achieved-gap numbers (513-857 ms) and the specific per-delay
  over-served counts are tied to that one cloud-region pair and will differ on different
  infrastructure.
- **Local only, no cloud account needed:** row 1 (pre-existing), row 4 (Redis SIGKILL —
  `redis_crash_durability_check.py`'s own docstring confirms it targets
  `docker compose up -d app worker`, i.e. the local dev stack), row 5/5b's test A and the
  worker-kill/duplicate-delivery tests (condition `C1` = "separate worker process, same
  host, same clock domain," per `run_distributed_experiment.py`'s own docstring — not
  Azure), and row 6 (TLC runs against a local `.tla` file, no network of any kind). Row
  5's atomic-defense cross-check specifically (`C3_concurrent_20261007T211848Z`) *was*
  run against Azure in this case, since it was convenient to re-check while that VM was
  still provisioned; it is not Azure-dependent in principle — `C1`/`C0` conditions
  exercise the same atomic-defense code path locally elsewhere in the existing results.
- **Authentication/environment requirements beyond §3 of this document:** the two-machine
  rows need `az` CLI login (`az login`, interactive, yours to run — see
  `experiments/two_machine/REPRODUCIBILITY.md` §1) and your own Azure subscription; the
  formal-model row needs only `jdk4py` and `tla2tools.jar`, both already documented in
  §13 above and in `formal/README.md`. Nothing in this section requires any credential,
  API key, or account beyond what §3 and §13 already list.

### 14.4 Evidence that is prose/log-transcript, not a JSON artifact

Rows 4 and 5b above are recorded as direct terminal output quoted inline in
`FINAL_HARDENING_AUDIT.md` and `DURABILITY_HARDENING_AUDIT.md` respectively (queue-depth
and balance checks via `curl`, and worker log lines), not as `results/` JSON files. This
is not an omission: these are one-shot fault-injection observations (kill a process, read
a balance, restart it), not swept experiments with per-cell JSON the way rows 1-3 and 6
are. A reader who wants to regenerate this evidence rather than read the transcript can
follow the exact manual steps in each script's own docstring
(`redis_crash_durability_check.py`) or in the audit document's "Tests performed" section
(`DURABILITY_HARDENING_AUDIT.md`).

### 14.5 Superseded artifact: do not reproduce the queue-depth-based strict-serial harness

An early implementation of the strict-serial control polled the settlement queue's
reported depth (`queue_depth == 0`) as a proxy for "settlement confirmed," rather than
polling the account's authoritative balance. This was found to have a real, confirmed
race — `async_worker.py`'s drain loop pops a not-yet-due event into a local list and only
re-queues it after the full scan completes, so `queue_depth` can read 0 while an event is
still in flight — and the buggy run measured over-serving at a control that should show
none. **This version is retained for auditability, not as a result to reproduce:**

```
experiments/two_machine/raw/C1_strict-serial_20261007T123240Z.SUPERSEDED_QUEUEDEPTH_BUG.jsonl
experiments/two_machine/raw/C1_strict-serial_20261007T123240Z.SUPERSEDED_QUEUEDEPTH_BUG.manifest.json
results/two_machine/C1_strict-serial_20261007T123240Z.SUPERSEDED_QUEUEDEPTH_BUG.summary.json
```

The filename tag `SUPERSEDED_QUEUEDEPTH_BUG` is deliberate and should not be stripped or
renamed. The current `run_distributed_experiment.py`'s `--arrival strict-serial` mode
(see its own `--help` text, quoted in §14.3) implements the corrected, balance-based
mechanism; the queue-depth approach was never a separate script, so there is nothing to
delete or disable — running `--arrival strict-serial` today always gets the corrected
behavior. Do not use the three files above as a reference implementation.

### 14.6 Exact reproduction commands (real commands, reconstructed from each run's own manifest — none invented)

```bash
# Row 2 (corrected two-machine sequential sweep): matches C2_sequential_20261007T123546Z's
# own manifest exactly (delays_ms, repetitions_requested). Requires a provisioned Host B
# per experiments/two_machine/REPRODUCIBILITY.md steps 1-7 first.
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival sequential --delays 0,200,500,1000,2000,5000,10000 --reps 5 \
    --endpoint /async/b0/complete

# Row 3 (strict-serial control, same topology): matches C2_strict-serial_20261007T125009Z.
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*" python -m experiments.two_machine.run_distributed_experiment \
    --condition C2 --arrival strict-serial --delays 0,500,2000,10000 --reps 3 \
    --endpoint /async/b0/complete

# Row 4 (Redis SIGKILL): local, no Host B needed. Run against the local dev stack
# (docker compose up -d app worker), then follow the printed instructions.
python -m experiments.two_machine.redis_crash_durability_check

# Row 6 (async TLA+ model): local, no network. Run once per config.
java -XX:+UseParallelGC -cp formal/tools/tla2tools.jar tlc2.TLC \
     -config formal/cfg_async/vulnerable_n6_k2.cfg -workers 1 -cleanup -deadlock \
     formal/AsyncSettlementTOCTOU.tla
```

These are the literal commands recorded in each run's own manifest/audit file (cited in
§14.2), copied here rather than paraphrased so a reader can run them verbatim.
