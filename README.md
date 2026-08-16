# LLM Metering-Evasion Testbed

A vulnerable-by-construction LLM-SaaS gateway for studying **client-side
metering evasion** — how a dishonest *client* can obtain paid inference while
under-paying. See [`CLAUDE.md`](./CLAUDE.md) for the full research framing,
taxonomy, threat model, and ethics guardrails.

> **Ethics (hard rule):** everything here targets only the locally-built testbed.
> Never point the attack harness at any third-party, live, or production system.

## Status — full study (B0 baseline + M1 + M2; M3 killed)

**Thesis:** LLM metering creates an accounting-security boundary spanning **state
synchronization** (B0), **economic commitment timing** (M1), and **usage authority**
(M2). M1/M2 are type-B *systematization/reframing* contributions; **B0 is a known
baseline**. No new attack primitives are claimed.

- [x] Repo, `docker-compose.yml` (FastAPI + PostgreSQL + Redis), deterministic mock LLM
- [x] **Formal model**: request-lifecycle state machine + accounting model
      (`paper/accounting_state_model.{md,tex}`), localizing each mechanism to a transition
- [x] **B0 — credit/quota-decrement race** (baseline): per-request ledger, DB-level
      lost-update verified, concurrency sweep, 19/19 controls
- [x] **M1 — metering-commit timing**: real SSE streaming + client abort, **5**
      architectures (`pre_debit`, `reserve_reconcile`, `post_completion`,
      `reserve_refund_on_abort`, `no_reserve_settle`), leak-vs-abort curve,
      controlled-concurrency sweep (1–100)
- [x] **M2 — usage-record authority**: 6 architectures, 8 usage manipulations, formal
      `P(T(U))` analysis, detection spectrum (D0–D3), concurrency sweep
- [x] **Architectural ablation**: which primitive closes which property
      (finalization ⇒ integrity; reservation ⇒ solvency; recount must be the *billing basis*)
- [x] **Real-tokenizer + gateway + local real-model** cost measurement (three levels)
- [x] **Harness validation**: fault injection (gates fail closed) + metamorphic properties
- [x] **Independent implementation** cross-check (`defenses/m2_independent_checker.py`)
- [x] **Lifecycle failure injection** (9 modes) and **statistical analysis** (scipy/statsmodels)
- [x] **M3 — inference-cache billing: KILLED** at its decision gate (`paper/m3_decision.md`)

See `FINAL_RESEARCH_REPORT.md`, `paper/main.pdf`, `paper/claim_evidence_matrix.md`.

Defense write-ups: `defenses/credit_decrement.py` (B0),
`defenses/m1_commit_timing.py` (M1), `defenses/m2_usage_authority.py` (M2),
`defenses/m2_independent_checker.py` (independent reference checker).

## Reproduce everything

```bash
# one-time, needs network: fetch tokenizer artifacts into a local cache
bash scripts/populate_tokenizer_cache.sh

bash scripts/reproduce_all.sh          # or: powershell scripts/reproduce_all.ps1
```

The pipeline runs every regression, sweep, benchmark, ablation, failure-injection,
validation and analysis stage, regenerates all figures/tables from raw data, and
compiles `paper/main.pdf`. Host needs `httpx numpy matplotlib scipy statsmodels
tiktoken transformers tokenizers sentencepiece torch`; `tectonic` is optional (PDF only).

## Quickstart

```bash
# 1. Bring up the stack (gateway :8000, Postgres :5432, Redis :6379)
docker compose up --build -d

# 2. From the repo root, install host client deps
python -m pip install "httpx[http2]" numpy

# 3. Controls + safety-invariant checks (must be all PASS)
python -m experiments.regression_class6

# 4. Full concurrency sweep -> results/class6_<ts>.json (raw data only)
python -m experiments.run_class6 --affordable 10 --concurrency 1 2 5 10 20 30 50 --reps 30

# 5. Derive every figure from the raw JSON -> *.summary.{json,csv,md} + integrity gate
python -m experiments.summarize_class6
```

`run_class6` first calls `POST /admin/reset-db`, so the run is clean regardless of
prior state. The **summarizer never takes hand-entered numbers**: it re-derives each
trial's leakage from the per-request ledger and fails if it disagrees with the
server-stored value. Full methodology: [`paper/class6_methodology.md`](./paper/class6_methodology.md).

## What class 6 demonstrates (fixed budget k = 10, 30 reps/cell)

| posture    | concurrency | served | \$-leak (per trial) | trial ASR | safety invariant |
|------------|-------------|--------|---------------------|-----------|------------------|
| vulnerable | 1           | 1      | 0.000               | 0.00      | holds            |
| vulnerable | 2           | 2      | 0.099               | 1.00      | violated         |
| vulnerable | 30          | 30     | 2.871               | 1.00      | violated         |
| vulnerable | 50          | 50     | 4.851               | 1.00      | violated         |
| hardened   | 50          | 10     | 0.000               | 0.00      | holds            |

- **Vulnerable path** (`read → check → stream → blind stale write`): concurrent
  handlers read the same balance before any writes; their decrements overwrite one
  another (**lost update**), so `served` completions are served but only **one**
  debit survives → `dollar_leak ≈ (served − 1) · unit_cost`. Needs ≥ 2 concurrent
  requests (concurrency 1 never leaks).
- **Hardened path**: atomic compare-and-decrement
  (`UPDATE … SET balance = balance - cost WHERE balance >= cost RETURNING …`)
  committed *before* streaming. Exactly `min(concurrency, k)` succeed, 0 leak.

### Metric definitions (authoritative copy in the methodology doc)

- **dollar_leak** = `inference_value − actual_debit`; `inference_value = SUM(cost)`
  over served requests; `actual_debit = initial_balance − final_balance`. Derived
  mechanically, cross-checked against `SUM(applied_debit)` (must reconcile).
- **over-served** = `max(served − k, 0)` (budget-relative).
- **unpaid-served** = `served − actual_debit/unit_cost` (economic).
- **invariant violation** = a served request with `applied_debit < cost`.
- **trial ASR** = fraction of trials with `dollar_leak > 0` (Wilson 95% CI).
- **request ASR** = invariant-violating served ÷ issued requests (Wilson 95% CI).
- **detection status** = `partial` here: the live balance under-reports, but the
  ledger logs every served debit, so reconciliation reveals the leak.

## Layout

```
app/            FastAPI gateway
  config.py       VULNERABLE <-> HARDENED posture toggles (per flaw class)
  db.py           async SQLAlchemy engine/session
  models/         accounts, credits, trials, usage_records (per-request ledger)
  llm/mock.py     deterministic streaming mock model
  metering/       pricing + debit primitives (vulnerable & hardened)
  main.py         /complete + /admin surface (trials, audit, db-info, reset-db)
attacks/        one module per taxonomy class (class 6 = baseline)
defenses/       server-side enforcement primitives per class
experiments/    run_class6 (raw data) · summarize_class6 (stats) · regression_class6
results/        raw JSON + *.summary.{json,csv,md} (figures regenerate from data)
paper/          class6_methodology.md + draft/figures
```

## Local (non-Docker) run

Point `DATABASE_URL` / `REDIS_URL` at your own Postgres/Redis (see `.env.example`),
then:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Reproducibility

The mock model's token counts and text are a pure function of `(prompt, seed)`, so
identical requests cost identically. Mock prices are chosen so per-request cost is
exactly representable in `NUMERIC(18,6)`, keeping `balance = k · cost` exact for
clean attack arithmetic. Every experiment logs its config alongside raw results.
