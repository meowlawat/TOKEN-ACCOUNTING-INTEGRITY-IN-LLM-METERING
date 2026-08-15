# Experimental Methodology

## Testbed

FastAPI + uvicorn gateway, PostgreSQL 16 (credits/quota, `READ COMMITTED`), Redis 7,
deterministic mock LLM, all via Docker Compose on a single commodity host
(i5-13450HX / 16 GB). The mock streams tokens as a pure function of `(prompt, seed)`
with a fixed inter-token delay, so token counts and costs are reproducible and the
only stochastic element is OS/network scheduling of requests.

The B0 tables (`credits`, `usage_records`, `trials`) are frozen from the validated
Phase 0 baseline. M1/M2 use separate tables (`m_trials`, `m_records`) so the baseline
cannot regress.

## Formal model and metrics

Per request `r`: served flag `S(r)`, authoritative value `C(r)` (cost of the inference
actually obtained), committed debit and legitimate refund → `NetDebit(r)`.

- **Leak** `Leak(r) = S(r)·C(r) − NetDebit(r)` (signed; positive = under-payment).
- **Leakage efficiency** `= max(Leak,0)/C(r)` — the fraction of value evaded
  (price-tier invariant; the key normalized metric so raw dollars don't confound).
- **request-ASR** (per cell) = fraction of records with `Leak > 0` (Wilson 95% CI).
- **trial-ASR** (B0) = fraction of trials with total leak > 0.
- **invariant violation** = served record with `NetDebit < C` (safety-property breach).
- **detection level** D0 (invisible) / D1 (reconcilable from logs) / D2 (logged at
  request time) / D3 (prevented or corrected in real time).
- **accounting conservation** (integrity gate): per trial,
  `initial_balance − final_balance == Σ NetDebit`. Every trial must reconcile.

Every figure/number is **re-derived from the per-request ledger** by the summarizers
and cross-checked against the server-stored value; a mismatch fails the build.

## Pricing (economic sensitivity)

Category-wise exact-`Decimal` pricing over `{input, output, cached_input, reasoning}`
with three synthetic tiers (`low` 0.05/0.15, `medium` 0.5/1.5, `high` 3/15 per 1k
input/output; cached at ~10%). Leakage efficiency is tier-invariant by construction;
raw dollar leak scales with tier, which is why efficiency is the headline metric.

## Workloads

- **B0:** fixed prompt, affordable budget k=10, concurrency ∈ {1,2,5,10,20,30,50},
  30 reps/cell (420 trials). (Phase 0, unchanged.)
- **M1:** architecture ×4 × abort% ∈ {0,10,25,50,75,90,100} × tier ×3 × 10 reps
  (840 records). The client opens a real SSE stream and closes the connection after a
  computed number of tokens; the server settles per architecture in a
  cancellation-shielded path.
- **M2:** architecture ×6 × manipulation ×8 × tier ×3 × 10 reps (1440 records). The
  client declares a manipulated usage vector.
- **Overhead (RQ4):** 200 M2 requests and 40 full-completion M1 streams per
  architecture, client-side latency.

## Sample size

Justified from measured dispersion (`experiments/power_analysis.py`), not a fixed
"100 trials". The leak magnitude is **deterministic** (observed per-record std = 0 in
all cells), so a single rep pins the mean; reps guard only against scheduling
artifacts. The limiting precision is the ASR proportion: at n=10 the Wilson interval
at p=0.5 is ±0.31, but the observed ASRs sit at 0 or 1 where the intervals are tight
([0, 0.28] and [0.72, 1.0]). B0 uses 30 reps for the same reason.

## Controls (distinguish exploitation from ordinary behavior)

`experiments/regression_m.py` (16 checks) and `experiments/regression_class6.py`
(19 checks): honest client → no leak (M1 completion, M2 honest, B0 concurrency 1);
insufficient balance cannot over-serve; hardened/safe architecture leaks nothing at
the strongest attack; vulnerable architecture produces a measurable, reconciling
violation. Every trial's accounting conservation is asserted.

## Reproducibility

`run_*` writes raw JSON to `results/raw/` (config, seeds, DB/env metadata, every
record); `summarize_*` derives `results/processed/`; `figures.py`/`tables.py`
regenerate `results/figures,tables/` from processed data. `scripts/reproduce_all.*`
runs the whole pipeline from a clean checkout.
