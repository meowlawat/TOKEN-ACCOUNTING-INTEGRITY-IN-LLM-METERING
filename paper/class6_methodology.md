# Class 6 Methodology — Limit-Overrun Race on Credit Decrement

**Status:** KNOWN BASELINE (not a contribution). Reproduced end-to-end to validate
the measurement rig before Phase 1. Prior art: Kettle's work on web race conditions (which introduces the single-packet attack)
(PortSwigger, 2023) and ***(CVE citation withdrawn — the identifier belongs to an unrelated advisory)*** (Tyk API Gateway, 2026, CVSS 7.5 — a
non-atomic `GET`-then-`DECR` quota-decrement race), both confirmed in the Phase 1
audit. (An earlier draft cited an unverified "2025 *Computers & Security*
race-condition methodology paper"; it was not found in the Phase 1 search and has
been dropped — see `paper/phase1_conclusion.md`.)

This document is the authoritative description of the class-6 experiment. Every
number in the paper is produced by `experiments/summarize_class6.py` from the raw
JSON emitted by `experiments/run_class6.py`; none is entered by hand.

---

## 1. Threat model

Honest provider, **dishonest client**. The client holds a funded account and wants
to receive metered inference while under-paying. It may issue many concurrent
requests but cannot see or modify server state except through the public API. The
attack is run only against the locally-built testbed; no third-party or live system
is ever contacted.

## 2. Workload

A single deterministic prompt is issued repeatedly:

- prompt = `"benchmark the credit decrement race please"` → **6 prompt tokens**
- completion length is a pure function of `(prompt, model_seed)` → **64 completion
  tokens** at `model_seed = 1337`
- unit cost is therefore constant: **0.099000** mock dollars per request (see §5).

Using an identical prompt makes the per-request cost constant, so the affordable
budget `k` and the leakage arithmetic are exact and every trial is comparable.

## 3. Mock-model determinism

The mock LLM (`app/llm/mock.py`) derives both the completion length and each token
from `SHA-256(seed:text)`, and streams tokens one at a time with a fixed
inter-token delay (default 5 ms). Consequences:

- **Reproducible cost:** `plan_completion` (used for the pre-serve estimate) and
  `stream_completion` (the actual stream) share one length function, so the
  server-side recount equals the estimate for a given prompt.
- **A real race window:** the ~64 × 5 ms ≈ 320 ms streaming interval is the window
  between the vulnerable path's balance *check* and its *debit*.

No GPU is used; Ollama is not involved in this experiment.

## 4. Database configuration

- **Engine:** PostgreSQL 16.15 (Alpine), one shared row per account in `credits`.
- **Isolation:** `read committed` (PostgreSQL default; confirmed live via
  `GET /admin/db-info`).
- **Driver / sessions:** SQLAlchemy 2.0 async + asyncpg. Each HTTP request runs in
  its own `AsyncSession` (its own pooled connection and transaction). The pool is
  sized above the maximum tested concurrency (`pool_size=50`, `max_overflow=50`).
- **Transaction boundaries:** the gateway commits explicitly; autocommit is off.

### Why the vulnerable path permits a lost update

The vulnerable `/complete` does, per request (`app/metering/debit.py`,
`app/main.py::_complete_vulnerable`):

1. `SELECT balance FROM credits WHERE account_id=:a` — a **lock-free** read
   (the TOCTOU check). Under `read committed` every concurrent transaction that
   reads before any writer commits observes the *same* starting balance `B`.
2. stream the completion (~320 ms) — the check-to-write window.
3. `SELECT balance ... FOR UPDATE` — take the row lock and observe the true
   pre-image (`balance_before`); this is observational only.
4. `UPDATE credits SET balance = :new` where `:new = B − cost` was computed from
   the **stale** step-1 read.

Step 4 is a *blind absolute write*: it does not re-read the current balance, it
overwrites it with a value derived from `B`. PostgreSQL still serializes the writes
(row lock), so exactly one writer's decrement survives while the rest overwrite it
with the same stale `B − cost`. This is a classic **lost update** — a *within-one-
isolation-level* anomaly that `read committed` does **not** prevent (only
`repeatable read`/`serializable`, or explicit locking / atomic decrement, would).

Persisted evidence (one vulnerable trial, concurrency 5, `k=10`, from the ledger):

```
initial_balance 0.990000  final_balance 0.891000  unit_cost 0.099000
actual_debit 0.099000  inference_value 0.495000  dollar_leak 0.396000  reconciled True

request  status    before      after   applied     cost
cb8b1f49   200   0.990000   0.891000  0.099000  0.099000   <- the one debit that survives
5d33e8dc   200   0.891000   0.891000  0.000000  0.099000   <- lost update (free)
537bf88a   200   0.891000   0.891000  0.000000  0.099000   <- lost update (free)
370c09e2   200   0.891000   0.891000  0.000000  0.099000   <- lost update (free)
e98b630b   200   0.891000   0.891000  0.000000  0.099000   <- lost update (free)
```

Five completions served; one debit of 0.099 survives; `SUM(applied) = 0.099`
reconciles exactly to `initial − final`. The other four are served with
`applied_debit = 0` — completed responses with no committed debit of their cost.

### Why the hardened path is safe under concurrency

The hardened path reserves atomically **before** streaming:

```sql
UPDATE credits SET balance = balance - :cost
WHERE account_id = :id AND balance >= :cost
RETURNING balance
```

The compare (`balance >= :cost`) and the decrement are a single row-locked
statement, so two concurrent transactions cannot both pass the check on the same
funds. Affected-row count is 1 on success (reserve) and 0 on insufficient funds
(→ HTTP 402). The reserve is committed immediately so the lock is not held across
the streaming window. This is verified empirically: at concurrency 50 with `k=10`,
exactly 10 requests are served across all repetitions and no trial leaks (§ results).

## 5. Pricing model

`cost = prompt_tokens/1000 · price_prompt + completion_tokens/1000 · price_completion`,
computed in `Decimal` and quantized to 6 places (`NUMERIC(18,6)`). Mock prices are
`price_prompt = 0.5`, `price_completion = 1.5` mock dollars / 1k tokens, chosen so
the per-request cost (0.099000) is exactly representable — no float drift, exact
`k · cost`. Prices and token counts are recorded per trial, so leakage can be
restated in any currency by rescaling.

## 6. Concurrency model

Per trial the harness fires `concurrency` identical `/complete` calls with
`asyncio.gather` over a shared `httpx.AsyncClient` (HTTP/1.1, connection pool ≥
concurrency). Levels tested: **1, 2, 5, 10, 20, 30, 50**. Fixed affordable budget
**k = 10** (balance = `10 · 0.099`). 30 repetitions per (posture, concurrency) cell.

## 7. Metrics (definitions)

Per trial (all derived mechanically from persisted ledger rows + balance snapshots):

| metric | definition |
|---|---|
| `inference_value` | `SUM(cost)` over served requests (value the client received) |
| `actual_debit` | `initial_balance − final_balance` (money actually taken) |
| **`dollar_leak`** | `inference_value − actual_debit` |
| `over_served_requests` | `max(served − k, 0)` — served beyond the paid budget |
| `paid_requests` | `actual_debit / unit_cost` |
| `unpaid_served_requests` | `served − paid_requests` (economic) |
| `invariant_violations` | served requests with `applied_debit < cost` |
| `unauthorized_completion_tokens` | completion tokens of invariant-violating served rows |

Across a (posture, concurrency) cell:

| metric | definition |
|---|---|
| **trial ASR** | fraction of trials with `dollar_leak > 0` (Wilson 95% CI) |
| **request ASR** | (served requests with `applied_debit < cost`) / (issued requests), Wilson 95% CI |
| **detection status** | `none` / `partial` / `full` — does the ledger reveal the leak? Here `partial`: the live balance under-reports but every served debit is logged, so reconciliation catches it. |
| **defense overhead** | served-request latency mean / p50 / p95 / p99 per posture |

Dispersion for `served`, `dollar_leak`, `over_served`, latency: mean, median,
sample std (ddof=1), p50/p95/p99. Mean `dollar_leak` gets a normal-approx 95% CI.

`over_served` (budget-relative) and `trial_asr` (leak > 0) are reported separately
because they **diverge**: at `2 ≤ concurrency ≤ k` the lost update under-charges
(leak > 0) even though nothing is served beyond budget (`over_served = 0`).

## 8. Safety invariant

> **No completed response without a committed, non-refunded debit.**

Operationally, a served request satisfies the invariant iff `applied_debit ≥ cost`
(the balance actually dropped by at least the request's cost) with
`committed = true, refunded = false`. The hardened path satisfies it for every
served request (0 violations at all tested concurrencies). The vulnerable path
violates it exactly on the lost-update rows; the count is reported as
`invariant_violations` rather than being silently accepted.

A second, independent consistency check is enforced by the summarizer's integrity
gate: for every trial, `SUM(applied_debit)` over served rows must equal
`initial_balance − final_balance`. All 420 trials reconcile.

## 9. Reproducibility procedure

From a clean checkout with Docker running:

```bash
docker compose up --build -d                 # gateway :8000, Postgres, Redis
python -m pip install "httpx[http2]" numpy    # host client deps
python -m experiments.regression_class6       # controls + invariants (must be all PASS)
python -m experiments.run_class6 --affordable 10 \
       --concurrency 1 2 5 10 20 30 50 --reps 30   # -> results/class6_<ts>.json
python -m experiments.summarize_class6        # -> *.summary.{json,csv,md}, integrity gate
```

`run_class6` calls `POST /admin/reset-db` first, so the schema and data are clean
regardless of prior state. Determinism: fixed `model_seed`; the only stochastic
element is OS/network scheduling of concurrent requests, which is characterized by
the 30 repetitions per cell (observed std = 0 for served/leak at these timings).

## 10. Known limitations

1. **Identical-workload assumption.** Constant per-request cost keeps the arithmetic
   exact; heterogeneous prompt/response sizes are deferred (they would exercise the
   estimate-vs-recount reconciliation path, which is a no-op here).
2. **Single-node Postgres, one shared credit row.** No replication / read-replica
   lag; results characterize a single primary under `read committed`.
3. **Observation lock in the vulnerable path.** The `SELECT … FOR UPDATE` used to
   record `balance_before` serializes the *debit* section (not streaming). It does
   not repair the race (the written value is still the stale absolute), but it does
   mean the vulnerable path is measured with a short serialized critical section
   rather than a fully lock-free write; the lost update is preserved and confirmed.
4. **Timing-dependent race.** The lost update requires reads to precede writes; the
   streaming delay makes this reliable here (std = 0), but the magnitude of leakage
   is a function of the check-to-write window, not a fixed constant.
5. **HTTP/1.1 concurrency**, not HTTP/2 single-packet. Single-packet timing would
   tighten the window further; the current rig already saturates the effect
   (trial ASR = 1.0 for concurrency ≥ 2), so HTTP/2 is not required for class 6.
6. **Mock latency.** Absolute latencies reflect the mock's inter-token delay, not a
   real model; only *relative* overhead between postures is meaningful.
```
