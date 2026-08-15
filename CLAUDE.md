# CLAUDE.md — Token-Accounting Integrity Research Project

> Drop this file in the root of your project folder. Claude Code reads it automatically
> and uses it as persistent context. Update it as the project evolves.

---

## What this project is

A security research paper + open-source artifact studying **client-side metering evasion
in LLM-powered applications** — i.e., how a dishonest *user* can exploit flaws specific to
LLM billing to consume paid inference while under-paying.

**Deliverables:** (1) a research paper targeting a security workshop or a Q1 journal
(*Computers & Security* tier), and (2) a reproducible open-source testbed + attack harness
+ defense reference implementation.

---

## Problem statement

**One line:** LLM apps bill by metering token/inference consumption, but no one has
systematically studied whether a dishonest *client* can exploit flaws specific to LLM
billing to obtain paid inference while evading or under-reporting payment.

**Formal:** Existing security work on LLM billing runs in two directions only — dishonest
*providers* inflating charges against honest users (CoIn, "Invisible Tokens, Visible Bills"),
and attackers inflating a *victim's* bill (Denial-of-Wallet). The inverse — a dishonest
*client* exploiting LLM-billing-specific weaknesses to under-pay — has no taxonomy, no
benchmark, no financial-impact measurement, and no defense evaluation. Generic limit-overrun
race conditions are well studied; the AI-specific evasion surface is not.

## Research questions

- **RQ1 (Taxonomy):** What classes of client-side metering-evasion flaws are specific to LLM
  billing, beyond generic limit-overrun races?
- **RQ2 (Measurement):** On a controlled testbed, what are the attack success rate and
  dollar-leakage of each class across common metering architectures?
- **RQ3 (Defense):** Which server-side enforcement primitives close each class, and at what
  latency/throughput cost?

## Threat model

Honest provider, **dishonest client** whose goal is to receive metered inference while
under-paying. Distinct from:

|                     | Inflate cost                     | Evade cost                    |
|---------------------|----------------------------------|-------------------------------|
| **Provider dishonest** | CoIn / Invisible Tokens (covered) | —                             |
| **Client dishonest**   | Denial-of-Wallet (covered)        | **← this project (the gap)**  |

---

## Attack taxonomy — REVISED after Phase 1 novelty audit (2026-08-15)

> The original five "novel core" classes did **not** survive the Phase 1 literature
> audit intact. Two were killed, three survive only as **mechanism-based reframes**
> (type B: known/observed mechanism, not systematically studied in LLM billing under
> the dishonest-client model with measurement + defense). **No survivor is a wholly
> novel primitive.** The contribution is **systematization + reproducible measurement
> + defense evaluation**, not new-primitive discovery. Full evidence:
> `paper/novelty_matrix.{csv,md}`, `paper/false_positive_check.md`,
> `paper/phase1_conclusion.md`, `paper/phase1_sources.json`.

**Unifying safety property (all classes violate it):** *no served/completed inference
without a committed, non-refunded, server-authoritative debit.* (This is the exact
invariant the class-6 rig already checks.)

Revised taxonomy (honest provider, dishonest client, goal = underpay):

- **M1 — Metering-commit-timing evasion** *(reframe of old Class 1; SURVIVES, medium-high
  confidence)* — accounting-after-completion vs accounting-before-inference. Client aborts/
  disconnects mid-stream so the post-hoc usage commit never fires, or triggers a reserve
  refund. Reviewer will cite: `new-api` #5235 (in-the-wild bug), the "Cancellation Tax"
  writeup. Defense: pre-authorize/reserve-before-inference + reconcile-on-completion.
- **M2 — Usage-record authority evasion** *(reframe of old Class 2; SURVIVES, strongest)* —
  server-authoritative recount vs client/upstream-declared usage. Client under-reports the
  billed token count; LLM hook = tokenization nondeterminism. Mirror of Token Inflation's
  measured provider over-report margin (~50.85%). Reviewer will cite: CWE-807, Token Inflation.
  Defense: server-side authoritative recount.
- **M3 — Inference-cache billing evasion** *(reframe of old Class 3; **KILLED at the Phase 2
  decision gate** — see `paper/m3_decision.md`)* — reduces to solved billing idempotency
  (Stripe), generic cache authorization (overlaps killed Class 5), and a billing-policy choice
  (semantic-cache hits bill 0 by design). No residual LLM-specific accounting-integrity
  violation distinct from M2. **Not implemented.**
- **B0 — Credit/quota-decrement race** *(KNOWN BASELINE — not a contribution; was Class 6,
  now ABSORBS old Class 4)* — non-atomic check+decrement TOCTOU on a credit/quota counter,
  incl. shared/multi-tenant pools. Cite: Kettle single-packet attack (PortSwigger, 2023) +
  **CVE-2026-31873 (Tyk Gateway, 2026, CVSS 7.5)**. Already implemented + measured in Phase 0.

**KILLED classes (do NOT implement as contributions):**
- ~~Class 4 (Adversarial retry on shared quota)~~ → **merged into B0**. Identical TOCTOU
  quota-decrement race (CVE-2026-31873, Kettle). Type D (rebrand).
- ~~Class 5 (Entitlement-metadata tampering)~~ → **removed**. Textbook OWASP API3:2023
  (BOPLA / mass assignment) + API1:2023 (BOLA). Non-LLM. Type D (rebrand).

**Phase 2 result (2026-08-15): M1 + M2 IMPLEMENTED and MEASURED; M3 KILLED at gate.**
The taxonomy narrowed to **2 novel reframes (M1, M2) + 1 baseline (B0)**. Real data
(integrity-gated, all trials reconcile): M1 — vulnerable commit-timing archs
(`post_completion`, `reserve_refund_on_abort`) leak the value of tokens delivered before
the commit, peaking at abort~90% then collapsing to $0 at completion (request-ASR 1.0,
invariant violated); safe archs (`pre_debit`, `reserve_reconcile`) leak $0. M2 —
client-authoritative billing leaks up to 0.58 (90% output under-report) / 0.74
(total/subtotal mismatch under flat total pricing) leakage efficiency, and the
exploitable manipulation set depends on the billing basis; server-authoritative archs
(`server_recount`, `hybrid_reconcile`, `upstream`) leak 0 across all 8 manipulations.
Defense overhead: M1 reserve-reconcile +9.8 ms; M2 recount +0.1 ms (mock; tokenizer cost
NOT captured — key limitation). Impl: `app/architectures/`, `app/accounting/`,
`app/m_routes.py`; experiments `run_m1/run_m2/run_overhead`, summarizers, `regression_m`
(16/16), figures/tables/power_analysis. Paper: `paper/main.tex` → `paper/main.pdf`
(compiled with tectonic). Contribution framing = systematization + measurement + defense,
NOT new primitives. Do NOT implement M3.

**Novelty gate (Phase 1) result: PASS (conditional)** — was 3 mechanisms; after the M3
kill it is **2 novel reframes (M1, M2) + baseline B0**, still PASS under the
systematization/measurement framing. **Note (correction from Phase 0):** the
earlier CLAUDE.md line citing "the 2025 *Computers & Security* race-condition
methodology paper" was **not verified** in the Phase 1 search and should not be cited;
use Kettle (2023) + CVE-2026-31873 (2026) for the baseline instead.

---

## Non-goals & ethics guardrails (HARD RULES)

- **Testbed only.** All attacks run against the locally-built vulnerable app. **Never** write
  code that probes, scans, or attacks any third-party / live / production system.
- No credential harvesting, no real-user data, no attacks against real provider billing APIs.
- Real-world findings go in the paper only where explicit authorization exists (responsible
  disclosure appendix).
- This is defensive security research: every attack must be paired with a defense.

---

## Tech stack

- **Language:** Python 3.11+
- **Gateway/API:** FastAPI + uvicorn (async)
- **DB:** PostgreSQL (credits/quota tables, transactional tests)
- **Cache:** Redis (for the cache-dodging class)
- **LLM backend:** deterministic **mock model** by default (streams fake tokens with realistic
  timing + reports counts) — zero GPU, fully reproducible. Optional adapter to Ollama
  (small quantized model, e.g. Llama 3.2 3B) for one realism experiment only.
- **Attack harness:** async `httpx` / `h2` (HTTP/2 single-packet), custom asyncio clients.
- **Load/endurance:** `locust` or `k6` or custom asyncio (100+ trials, p50/p95/p99).
- **Infra:** Docker + docker-compose. Everything runs locally on a laptop.

## Repo structure

```
.
├── CLAUDE.md
├── docker-compose.yml
├── app/                    # vulnerable-by-construction LLM-SaaS testbed
│   ├── main.py             # FastAPI gateway
│   ├── metering/           # metering middleware — flaw classes as config toggles
│   ├── models/             # DB models: accounts, credits, usage_records
│   ├── llm/                # mock model (default) + ollama adapter
│   └── config.py           # VULNERABLE ↔ HARDENED toggles per flaw class
├── attacks/                # one module per attack class (1–6 above)
├── defenses/               # server-side enforcement primitives per class
├── experiments/            # measurement runners → results matrix
├── results/                # raw data + generated figures/tables
└── paper/                  # LaTeX / markdown draft, figures
```

## Metrics (define once, use everywhere)

- **ASR** — Attack Success Rate (% of trials that under-pay).
- **$-leak** — dollar value of inference obtained but not billed, per attack.
- **Detectability** — does the app's own metering log the discrepancy? (yes/no/partial)
- **Defense overhead** — added latency (mean + p50/p95/p99) and sustained throughput (ops/sec),
  measured with the endurance-trial methodology (100+ trials).
- **Safety property** to verify for defenses: *no completed response without a committed,
  non-refunded debit.*

---

## Roadmap & gates

- **Phase 0 (done):** repo + docker-compose (FastAPI + Postgres + Redis) + mock-LLM stub +
  minimal `/complete` + credits table + class-6 baseline reproduced to validate the rig.
- **Phase 1:** lit review, freeze taxonomy, threat model. **GATE 1 (novelty):** ≥3 of classes
  1–5 confirmed unstudied, else reframe.
- **Phase 2:** build testbed, vulnerable+hardened toggles. Reproduce class 6 baseline to validate rig.
- **Phase 3:** attack harness + measurement. **GATE 2:** ≥2 novel classes actually leak, else pivot.
- **Phase 4:** defenses + overhead benchmarks + safety property.
- **Phase 5:** paper draft + release artifact + disclosure appendix.
- **Compressed MVP fallback:** ship Phases 0–3 as a workshop paper; hold defenses for a follow-up.

---

## Coding standards

- Production quality: type hints, error handling, input validation, docstrings.
- **Determinism first** — experiments must be repeatable; seed randomness; log configs with results.
- No placeholder/stub logic in shipped code paths (mock LLM is intentional, not a placeholder).
- Each flaw class: a `vulnerable` and a `hardened` implementation behind the same interface.
- Every experiment writes raw data to `results/` so figures regenerate from data, not by hand.

## Hardware context

Runs on: i5-13450HX / RTX 3050 6GB / 16GB DDR5. GPU is **not** needed for the core study
(mock model). Use the mock model — not the local LLM — during high-concurrency load tests to
avoid RAM contention. Reproducibility on commodity hardware is a stated selling point.

---

## Implementation notes (Phase 0 → publication-grade class-6 foundation)

- **Posture toggles** live in `app/config.py` as `Mode` enums (one per class). The process
  seeds its posture from env/`.env`; the runtime posture is mutable per class via
  `POST /admin/config`, which is how experiments A/B a single class without a restart.
- **Class 6** is implemented as two *structurally different* code paths in `app/main.py`
  (not a single branch on a flag): the vulnerable path is a read-modify-write **lost update**
  on `credits.balance` (lock-free stale read → check → stream → blind absolute write); the
  hardened path is the atomic compare-and-decrement `UPDATE … SET balance = balance - :cost
  WHERE account_id=:id AND balance >= :cost RETURNING balance`, committed before streaming
  (`app/metering/debit.py`, written up in `defenses/credit_decrement.py`).
- **Auditable ledger.** `usage_records` stores per served request the observed
  `balance_before`/`balance_after` and `applied_debit` alongside the intended `cost`; a
  `trials` table pins each repetition's posture/concurrency/prices/seed and the
  `initial`/`final` balance snapshots. Leakage is derived two independent ways
  (`initial − final` and `SUM(applied_debit)`) and must reconcile.
- **`$-leak` is mechanical**, never inferred from the final balance alone:
  `dollar_leak = inference_value − actual_debit`, where `inference_value = SUM(cost)` over
  served rows and `actual_debit = initial − final`. `summarize_class6.py` re-derives it from
  the per-request ledger and fails loudly if it disagrees with the server-stored value.
- **Metrics are separated** (defined in `summarize_class6.py` and `paper/class6_methodology.md`):
  trial ASR (fraction of trials that leak) vs request ASR (invariant-violating served /
  issued), over-served (budget-relative) vs unpaid-served (economic), unauthorized completion
  tokens, dollar leakage, detection status. `over_served` and `trial_asr` **diverge** for
  `2 ≤ concurrency ≤ k` (the lost update under-charges within budget).
- **Safety invariant** *completed ⇒ committed, non-refunded debit* is checked programmatically:
  hardened has 0 violations at all tested concurrency; vulnerable violations are **quantified**
  (`invariant_violations`), not silently accepted.
- **DB semantics (verified, not asserted):** PostgreSQL `read committed` (confirmed live via
  `GET /admin/db-info`) does **not** prevent the lost update because the vulnerable write is a
  blind absolute write of a stale value; the row lock only serializes writers so one decrement
  survives. Demonstrated by persisted before/after rows. See `paper/class6_methodology.md` §4.
- **Runner / summarizer / regression.** `run_class6.py` sweeps concurrency {1,2,5,10,20,30,50}
  × {vulnerable,hardened} × 30 reps and writes raw JSON only. `summarize_class6.py` (raw-JSON-in)
  emits CSV + Markdown + JSON with mean/median/std/p50/p95/p99 and Wilson/normal 95% CIs, plus
  an integrity gate. `regression_class6.py` runs the controls (conc=1 does not race; insufficient
  balance cannot over-serve; hardened safe at max concurrency) and the invariant checks.

### Assumptions discovered during the audit
- Leakage magnitude is `(served − 1) · unit_cost` for the vulnerable path (the lost update
  collapses **all** concurrent debits to a single surviving one), independent of `k` as long as
  the stale check passes — so the affordable budget `k` governs `over_served` but not
  `dollar_leak`. The earlier "$57.42 total, 100% ASR" figure = 20 rounds × `29 · 0.099` at
  concurrency 30; it is reproduced and now decomposed (per-trial leak `$2.871`, trial ASR 1.00,
  request ASR 0.967).
- The lost update requires ≥ 2 concurrent transactions; concurrency = 1 never leaks (control).
- Observed std = 0 for served/leak at these timings (streaming delay makes reads reliably
  precede writes); the phenomenon is deterministic here, and the 30 reps characterize scheduling
  variance rather than reveal it.
