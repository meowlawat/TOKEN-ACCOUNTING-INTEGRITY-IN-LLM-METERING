# Formalization Audit — The Actual Async-Settlement TOCTOU Mechanism

This document follows directly from `EXPERIMENTAL_STRENGTHENING_AUDIT.md` §9, which found
that the existing formal model (`formal/TokenAccounting.tla`) does not model the mechanism
the two-machine experiment actually exercises. This phase builds a separate, faithful model
of that mechanism from the implementation and the T1–T7 instrumentation directly — not a
simplification chosen because it is easier to verify — and model-checks it.

**The discrepancy, stated precisely, before anything else:**

| | `TokenAccounting.tla` (existing, unmodified) | `AsyncSettlementTOCTOU.tla` (new, this phase) |
|---|---|---|
| mechanism | blind absolute overwrite | relative (additive) decrement |
| race type | lost update | TOCTOU admission race |
| invariant violated | `LedgerConservation` | `Solvency` |
| balance sign after violation | stays non-negative | goes negative |
| corresponds to | the original, synchronous Class-6 baseline | the async-settlement path this entire two-machine experiment studies |

Both are real, both are correctly modeled for what they each model — they are simply
**different mechanisms that happen to share the taxonomic label "B0."** The old model is
not wrong and is not edited. See §8 for exactly what it does and does not support.

---

## Step 1 — Implementation → T1–T7 → TLA+ mapping

Traced directly from the code (file:line references below are exact, re-verified while
writing this document, not quoted from memory):

| Implementation event | Code location | T timestamp | TLA+ action/state | Justification |
|---|---|---|---|---|
| Authorization read begins | `app/async_routes.py:220` (`time.perf_counter_ns()` before `ledger.read_balance`) | T1 | `Authorize(r)` entry, `pc[r]="CREATED"` | Start of the only read of shared state before a decision |
| Authorization read completes | `app/async_routes.py:222`, calls `app/accounting/backends.py::_mutable_read` (`SELECT balance FROM credits WHERE account_id=:a`, line 48) | T2 | still inside `Authorize(r)` | A plain `SELECT` — confirmed by reading `backends.py` directly — touches nothing; modeled as `UNCHANGED balance` |
| Authorization decision | `app/async_routes.py:223-226` (`if balance < cost: return ... else t3_decision_ns = ...`) | T3 | `Authorize(r)` → `pc[r]="ADMITTED"` or `"REJECTED"` | T1/T2/T3 collapse into one TLA+ step: nothing observable to any *other* request happens between them (three `perf_counter_ns()` samples around one `SELECT` and one `if`, not three separate writes) |
| Request admission | implicit — the `if` branch taken at T3 | — | `pc[r]="ADMITTED"` | The state itself |
| Settlement event created | `app/async_routes.py:228-233`, calls `app/accounting/async_worker.py:163-172` (`aw.new_event`) | T4 | `Release(r)` entry | `new_event()` reads `time.time_ns()` once (line 166) — this is the wall-clock anchor (`created_ns`) used for cross-process comparison in Steps 2/7 |
| Event handed to the queue | `app/async_routes.py:234` → `app/accounting/async_worker.py:84-86` (`redis.rpush`) | T4b | still inside `Release(r)` | A Redis push — touches `balance` not at all, confirmed by reading `emit()` directly (it takes no DB session) |
| Value release (response returned) | `app/async_routes.py:255-262` (`MRecord` write, `s.commit()`, `return {...served: True...}`) | T5 | `Release(r)` → `pc[r]="RELEASED"` | T4/T4b/T5 collapse for the same reason as T1-T3: the `MRecord` insert records the request, it does not touch `credits.balance` (confirmed: no `ledger.debit_unchecked`/`credit` call anywhere in `async_b0_complete`) |
| Event queued, not yet due | `app/accounting/async_worker.py:163-172`, `deliver_after_ns = created_ns + delay_ms*1e6` | (between T5 and T6) | `SettlementPending(r)` | Models "sitting in Redis" as a distinct reachable state, not a numeric delay — see §9 |
| Worker receipt (due-check passes) | `app/accounting/async_worker.py:125,134` (`time.time_ns() < ev.deliver_after_ns` fails, `popped_ns = time.time_ns()`) | T6 | `Settle(r)` entry | The moment the worker commits to applying this event |
| Balance update (durable) | `app/accounting/async_worker.py:135` → `app/accounting/worker_main.py:52-55` (`ledger.debit_unchecked` → `app/accounting/backends.py::_mutable_debit`: `UPDATE credits SET balance = balance - :c WHERE account_id=:a RETURNING balance`, then `session.commit()`) | T7 | `Settle(r)`: `balance' = balance - Value`, `pc[r]="SETTLED"` | T6/T7 collapse into one atomic TLA+ step because the `UPDATE...RETURNING` plus the immediately-following `commit()` is one atomic database transaction from every other transaction's point of view — PostgreSQL serializes concurrent writers to the same row |
| Ledger update | same as above (one statement does both) | T7 | same | `debit_unchecked`'s name is itself the specification: an *unchecked*, relative decrement, never an absolute overwrite |

No mapping above was invented; every "Justification" cell names the file read to establish
it, and every one was re-read while writing this table (`app/async_routes.py`,
`app/accounting/async_worker.py`, `app/accounting/worker_main.py`,
`app/accounting/backends.py::_mutable_read/_mutable_debit/_mutable_reserve`).

**The structural fact this table establishes, stated once, precisely:** between T1 and T5,
*nothing* writes `balance`. The only write to `balance` in the entire vulnerable path is
`Settle`'s relative decrement at T6/T7. This is the single fact the whole model rests on,
and it is a fact about the code, not a modeling choice.

---

## Step 2 — The actual TOCTOU, with real numbers

Both examples below use real `extra` JSON pulled directly from `m_records` (local topology,
single clock domain — chosen deliberately over the real Azure topology's data for this
section, because the local topology's gateway and worker share one wall clock, making the
cross-process T4→T7 comparison exact rather than bounded by the ~800-1000ms cross-host
discrepancy documented in `EXPERIMENTAL_STRENGTHENING_AUDIT.md` §3).

### Over-serving execution (`C1_concurrent_20261007T004629Z`, D=2ms, rep=0 — one of the 55 cells from the Tier-1 delay sweep)

Two of the six concurrent requests in this cell, by `request_id`:

```
Request X (e2674860...): balance_seen=0.162  t1=15925940903937  t4=15925943855979(created_ns=...285559753)  t7=...291297435
Request Y (b7be5a56...): balance_seen=0.162  t1=15925942759932  t4=15925944978020(created_ns=...286688508)  t7=...305240122
```

(`unit_cost = 0.081`, `InitialBalance = 0.162 = 2×unit_cost`, i.e. budget for exactly 2.)

Both X and Y observed `balance_seen = 0.162` — the full, **undrained** initial balance —
despite being two of six concurrent requests against a 2-unit budget. Translating Y's
perf_counter-based T1 into the same wall-clock frame as its own `created_ns` (valid because
both are samples a few hundred microseconds apart in the same process):
`Y.T1 ≈ Y.created_ns − (Y.T4 − Y.T1) = 1791333997286688508 − 2218088 ≈ 1791333997284470420`.

Compared against X's settlement, `X.T7 = 1791333997291297435`: **Y's authorization read
happened roughly 6.8ms *before* X's settlement landed** — despite a configured
`reconcile_delay_ms = 2`. The extra ~4.8ms beyond the configured delay is the gateway's own
per-request overhead (read + event-create + emit + MRecord-write, measured at T1→T4b
≈2.2–3.8ms per request here under 6-way concurrent load) — this is exactly the mechanism
behind the "~2ms local threshold" finding in the prior phase: once the configured delay is
smaller than the gateway's own concurrent-request overhead, the overhead itself, not the
configured delay, determines whether the race is won.

**The precise answer to "what economic state does request B observe when request A has
already been admitted but not yet durably committed?":** B observes the account's balance
exactly as if A did not exist yet — because A's admission (`Authorize`) never wrote
`balance`, there is nothing in the database for B's `SELECT` to see differently. B is not
reading stale data in the sense of a replication lag or a cache; it is reading **correct,
fully up-to-date data that simply does not yet reflect a commitment A has made but not yet
kept**.

### Safe (non-racing) execution (`C1_concurrent_20261007T004629Z`, D=0ms, rep=2)

```
Admitted:  198aacd0... balance_seen=0.204   9680bd4d... balance_seen=0.204
Rejected:  4 other requests, balance_seen=0.000 (client-observed; no MRecord/T1-T5 exists
           for rejected requests -- see limitation below)
```

Here only 2 of 6 were admitted (both correctly, each seeing the full undrained budget), and
the other 4 correctly saw `balance_seen = 0` (fully drained) and were rejected. **Honest
limitation, stated directly:** the rejected branch of `async_b0_complete` returns before
`aw.new_event`/the `MRecord` insert, so no T1–T5 instrumentation exists for rejected
requests — the only evidence for them is the client-observed `balance_seen` in the raw
response JSON, which is sufficient to show *what* they saw, but not precisely *when* (no
`perf_counter_ns` samples were captured on that return path). This is reported, not
glossed over: the "TOCTOU was avoided for the 4 rejected requests" claim rests on the
`balance_seen` signal alone for this specific example.

---

## Step 3 — Deriving the scaling law

**Claim under test:** `over_served = max(0, concurrency − budget)`, observed across
concurrency 1–32 in the prior phase (`EXPERIMENTAL_STRENGTHENING_AUDIT.md` §4/§5).

**Derivation.** Let `N` = number of concurrently-issued requests, `v` = uniform per-request
value, `B` = initial balance, `k = ⌊B/v⌋` = budget in units. Consider the specific
interleaving in which **every** `Authorize` action for every one of the `N` requests fires
before **any** `Settle` action fires (TLC confirms this interleaving is reachable — see
Step 4). Because `Authorize(r)` only reads `balance` and never writes it
(`UNCHANGED balance` — Step 1's structural fact), every one of the `N` authorization checks
evaluates `balance ≥ v` against the *same*, unmodified value `B`. If `B ≥ v`, every single
one of the `N` requests is admitted, regardless of `N`. Once all `N` eventually reach
`Settle` (in any order — `Settle` is a pure relative decrement, order-independent for the
final value), the final balance is `B − N·v`. Over-serving, defined as requests served
beyond what the budget affords, is `N − k` whenever `N > k`, and `0` otherwise:

```
over_served = max(0, N − k)        ... under the "fully-raced" interleaving
```

**This is the formula's upper bound, achieved with equality exactly when the race is fully
saturated** (zero settlements visible to any authorization check in the cell — precisely
the `settlements_visible_during_cell_authorization = 0` condition the mechanism-analysis
tool already measures per cell). It is **not** a law that holds unconditionally: Step 2's
"safe execution" example is a direct empirical counterexample to unconditional equality (2
of 6 served, not 6), because that cell's interleaving was *not* fully raced — two
settlements landed before the remaining four authorizations ran. **The exact bounded
proposition:**

> For `N` requests of equal value `v` against a shared budget for `k = ⌊B/v⌋` units,
> `over_served ≤ max(0, N − k)`, with equality holding if and only if every request's
> `Authorize` action precedes every settled request's `Settle` action (the fully-raced
> interleaving). TLC confirms this interleaving is reachable for every tested `(N, k)` pair
> (§4); the empirical delay sweep shows it is the *typical* realized outcome once the
> configured settlement delay exceeds the gateway's own per-request authorization overhead
> (≈2ms locally — `EXPERIMENTAL_STRENGTHENING_AUDIT.md` §3).

**Assumptions this derivation requires, made explicit (do not assume more than these):**

1. **Equal request value** (`v` identical across all `N`) — confirmed by the harness
   (`price_tier` is fixed per cell; mixed-value concurrent requests were not tested).
2. **Fixed initial balance**, no concurrent credits/refunds during the cell — true of the
   harness's `new_account` setup, not a general claim about the account model.
3. **No request failures unrelated to budget** (network errors, invalid trial IDs) — the
   `valid` flag in every reported cell already screens these out; an errored cell is marked
   invalid, not silently averaged in.
4. **The specific "fully-raced" interleaving**, i.e. no settlement becomes visible to any
   sibling's authorization check before that check runs — this is an *assumption about
   timing*, not a structural guarantee, and the model does **not** derive *when* this holds
   in real milliseconds (that is the empirical delay-sweep's job, not this derivation's).
5. **Relative decrement semantics** (`Settle` never overwrites, only subtracts) — if this
   assumption were false (i.e. if settlement were a blind overwrite, as in the *other*
   model), the formula would not hold in this form at all; see §8.

If assumption 4 is relaxed, the relationship becomes the inequality above, not an equality
— and the model and the empirical data agree on this exact distinction (§7).

---

## Step 4 — The TLA+ models

New file: `formal/AsyncSettlementTOCTOU.tla` (kept entirely separate from
`formal/TokenAccounting.tla` — neither file was edited to produce the other).

States: `CREATED, ADMITTED, REJECTED, RELEASED, SETTLEMENT_PENDING, SETTLED` (per Step 1's
collapsed-event mapping). Variables: `pc` (per-request control state), `balance` (shared),
`debited` (per-request, for a genuinely checkable `AccountingIntegrity`, not a bare `TRUE`).

**Vulnerable path** (`AtomicCommit = FALSE`): `Authorize` reads and decides, `UNCHANGED
balance`; `Release`/`SettlementPending` are bookkeeping states that also leave `balance`
untouched; `Settle` is the *only* action that touches `balance`, via
`balance' = balance - Value` (relative, matching `_mutable_debit` exactly).

**Atomic defense** (`AtomicCommit = TRUE`): `AtomicAdmit` performs the check and the
decrement in **one** TLA+ step — `balance ≥ Value /\ balance' = balance - Value` — matching
`_mutable_reserve`'s single `UPDATE ... WHERE balance >= :c RETURNING balance` exactly: no
request can observe, or be observed in, a state where the check passed but the decrement
has not happened, because no such intermediate state exists in the implementation.

Configs (`formal/cfg_async/`, hand-written, explicitly marked as such — not generated by
`formal/check.py`, which is wired to `TokenAccounting.tla`'s constant set and was not
touched):

| config | `Requests` | `Value` | `InitialBalance` | `AtomicCommit` |
|---|---|---|---|---|
| `vulnerable_n6_k2.cfg` | `{r1..r6}` | 1 | 2 | FALSE |
| `atomic_n6_k2.cfg` | `{r1..r6}` | 1 | 2 | TRUE |
| `vulnerable_n4_k2.cfg` | `{r1..r4}` | 1 | 2 | FALSE |
| `atomic_n4_k2.cfg` | `{r1..r4}` | 1 | 2 | TRUE |

`N=6,k=2` matches the primary empirical workload exactly (`B0_REQUESTS=6`,
`B0_BUDGET_UNITS=2`). `N=4,k=2` is a second `(N,k)` point matching an actual empirical
Tier-2 concurrency-scaling cell (`over_served=2` observed,
`results/two_machine/C1_concurrent_20261007T004838Z.summary.json`), included to
cross-check the Step 3 derivation against a second model-checked data point — this is a
few-second TLC run on a tiny state space, not a new large experiment.

---

## Step 5 — The atomic model (C3)

Described above; `AtomicAdmit`/`AtomicReject` use the identical workload assumptions
(`Requests`, `Value`, `InitialBalance`) as the vulnerable configs at the same `(N,k)` point
— a genuine controlled comparison, not a different-shaped model.

---

## Step 6 — TLC results

Run via the project's existing TLC invocation pattern (`formal/check.py`'s own command,
replicated directly against the new spec file since `check.py` itself is wired to
`TokenAccounting.tla`):

```
java -XX:+UseParallelGC -cp formal/tools/tla2tools.jar tlc2.TLC \
     -config formal/cfg_async/<name>.cfg -workers 1 -cleanup -deadlock \
     formal/AsyncSettlementTOCTOU.tla
```

| config | states generated | distinct states | `Solvency` | `AccountingIntegrity` | `LedgerConservation` |
|---|---|---|---|---|---|
| `vulnerable_n6_k2` | 29,820 | 7,869 | **VIOLATED** (depth 13) | HOLDS (verified separately, exhaustive: 91,921 generated / 22,521 distinct) | HOLDS (same exhaustive run) |
| `atomic_n6_k2` | 517 | 247 | HOLDS | HOLDS | HOLDS |
| `vulnerable_n4_k2` | 1,750 | 598 | **VIOLATED** (depth 13) | HOLDS | HOLDS |
| `atomic_n4_k2` | 41 | 29 | HOLDS | HOLDS | HOLDS |

(`AccountingIntegrity`/`LedgerConservation` for the vulnerable configs were re-run in
isolation, one invariant per TLC run — the same methodology `formal/check.py` already uses
for `TokenAccounting.tla` — specifically so that a `Solvency` violation could not hide a
*different* invariant also being violated at some other reachable state. Full run: TLC
explored the complete, loop-free state space, 91,921 states generated for `vulnerable_n6_k2`
checking `AccountingIntegrity` alone, with **no error found** in either of the two
isolation runs.)

**Counterexample for `vulnerable_n6_k2`** (full trace:
`formal/async_settlement_vulnerable_n6_k2_counterexample.txt`), the *shortest* one TLC's
breadth-first search finds — notably **not** a maximally-parallel 6-way race, which is
itself a finding (see below): `r1` is admitted, released, queued, and settles
(`balance: 2→1`); `r2` is then admitted (balance still 1, ≥ `Value=1`), released, queued;
`r3` is admitted (balance still 1, because `r2` has not yet settled) **before `r2`
settles**; `r2` then settles (`balance: 1→0`); `r3` proceeds to settle
(`balance: 0→−1`, **`Solvency` violated**). Three requests (`r1,r2,r3`) are fully served
against a budget for two, with no six-way simultaneous firing required — only one
overlapping "admitted but not yet settled" window, repeated. This is a **stronger, more
general** finding than the empirical harness's always-maximally-concurrent workload shows:
the bug does not require N-way simultaneity, only staggered overlap, and the model
surfaces this because TLC explores the *shortest* path to the violation, not the path the
empirical harness happens to always exercise.

---

## Step 7 — Empirical ↔ formal cross-check

| Empirical event (D=2ms cell, request Y) | Formal counterpart |
|---|---|
| Y's `read_balance` call sees `balance_seen=0.162` (undrained) | `Authorize(Y)`: `balance ≥ Value` evaluated against the *unmodified* `InitialBalance` |
| Y admitted, event queued (`t4b_emitted_ns`) | `Release(Y)` → `SettlementPending(Y)`, `UNCHANGED balance` throughout |
| Y's debit lands at `t7=...305240122`, well after X's `t7=...291297435` | `Settle(Y)`: fires strictly after `Settle(X)` in wall-clock terms, but this ordering is **irrelevant** to the outcome — `Authorize(Y)` already succeeded before either settled |
| Final: both X and Y served against a 2-unit budget, balance driven negative once all six settle | `AllDone ⟹ Solvency` fails in the model exactly as in the real account |

| Empirical event (C3 real-topology run, any request) | Formal counterpart |
|---|---|
| `reserve_atomic` / `ledger.reserve_atomic` — single `UPDATE...WHERE balance>=:c RETURNING balance`, `served=2, over_served=0` in every one of 150+ cells across both topologies (`EXPERIMENTAL_STRENGTHENING_AUDIT.md` §7) | `AtomicAdmit(r)`: check and decrement as one TLA+ step; TLC confirms `Solvency` holds in every reachable state for both tested `(N,k)` pairs |

This establishes the correspondence is not merely "same final outcome, different
mechanism": the model's state-touching behavior (`Authorize`/`Release` never write
`balance`; only `Settle` does, relatively) is the directly-cited structural fact from the
code (Step 1), and the counterexample's shape (admit-before-settle, staggered, not
necessarily simultaneous) is consistent with — and sharpens — the real traced execution.

---

## Step 8 — Reassessing the old model

`formal/TokenAccounting.tla` was **not edited**. What it actually models, checked directly
against its own source (`AuthorizeRead`/`ReserveWrite`, lines 90-104): a **synchronous**
request path where the authorization step reads a balance *snapshot*, and a *separate*,
later step **overwrites** `balance` with an absolute value computed from that stale
snapshot (`balance' = snapshot[r] - Cost(Chunks)`). Two overlapping instances of this lose
one decrement entirely — confirmed by `results/formal/model_check_results.json`:
`b0_vulnerable → {AccountingIntegrity: HOLDS, Solvency: HOLDS, LedgerConservation:
VIOLATED}`. This is the correct, already-published, machine-checked model of the
**original, synchronous Class-6 baseline** (the lost-update race on a mutable balance row
under `READ COMMITTED`, studied before the asynchronous-settlement family existed) — it
remains fully valid for that mechanism and nothing here changes its result or its standing.

**It does not, and structurally cannot, model the asynchronous-settlement TOCTOU race**:
there is no queue, no `deliver_after`/settlement-delay concept, and critically, its unsafe
path's write semantics (absolute overwrite) are the opposite of the actual async
implementation's (`debit_unchecked`'s relative decrement). Applying `b0_vulnerable`'s
result to the async-settlement mechanism would be a category error.

**Does the manuscript currently attribute the wrong mechanism to the old model?** Checked
directly: `main_fgcs.tex`'s Threats-to-Validity "Distribution" paragraph (the one
`EXPERIMENTAL_STRENGTHENING_AUDIT.md` §9 already flagged as stale) does not cite
`TokenAccounting.tla` or any formal result in connection with the two-machine/async
experiment — it is purely an empirical limitations paragraph. **No manuscript claim is
currently unsafe because of this discrepancy** — but the manuscript also does not yet
state that the async-settlement mechanism is formally verified at all, because until this
phase, it was not. Any future manuscript edit that describes the two-machine result must
not imply `TokenAccounting.tla`'s existing formal guarantees extend to it; this new model
is the one that does, and its scope (Step 9) must be stated alongside it.

---

## Step 9 — Formal limitations (stated directly, not buried)

- **Finite, small request counts.** Checked at `N=6` and `N=4`; not checked for arbitrary
  `N`. The Step 3 derivation is a hand-proof for general `N,k`, not a TLC-checked universal
  result — TLC verifies two *instances* of it.
- **Bounded concurrency, no parameterized/inductive proof.** Scaling the derivation to
  arbitrary `N` is the Step 3 argument, which is elementary (it follows directly from
  `Authorize` never writing `balance`) but is not itself machine-checked for all `N`.
- **Unit value, single budget.** `Value` is a single constant per run; mixed-value
  concurrent requests (Tier 2's price-tier scaling varied value *across cells*, never
  *within* one concurrent batch) are outside both the empirical tests and this model.
- **No liveness proof.** Only safety invariants (`Solvency`, `AccountingIntegrity`,
  `LedgerConservation`) are checked, matching `TokenAccounting.tla`'s own scope — no claim
  is made that every request eventually reaches a terminal state under fairness beyond
  what `WF_vars(Next)` already provides for `Spec` itself to be well-formed.
- **No mechanized refinement proof.** The Step 1 table is a manually-constructed,
  file-and-line-cited correspondence, not a machine-checked refinement mapping from
  `AsyncSettlementTOCTOU.tla` to the Python implementation. This is the same limitation
  `journal_reviewer_attack_v2.md`'s Reviewer C already conceded in full for the *old*
  model's relationship to its implementation; it applies identically here and is not a new
  gap introduced by this phase.
- **No real-time/probabilistic model.** The model proves over-serving is *reachable* under
  some interleaving; it does not reproduce the empirically-measured ~2ms local threshold or
  any quantitative relationship between the configured delay `D` (in milliseconds) and the
  probability of the race. That relationship is, and remains, an empirical finding
  (`EXPERIMENTAL_STRENGTHENING_AUDIT.md` §3), not a formal one. A timed-automata or
  stochastic model would be needed to close this gap formally, and was not attempted.
- **Database/network behavior abstracted entirely.** `Settle`/`AtomicAdmit` are modeled as
  indivisible steps on the strength of PostgreSQL's row-level write serialization for a
  single `UPDATE` statement (cited directly from `backends.py`, not assumed) — connection
  pooling, retries, and network partitions (all empirically exercised in Phase 6's failure
  injection) are not modeled here at all.
- **The Step 3 derivation's five assumptions** (equal value, fixed initial balance, no
  unrelated failures, the fully-raced interleaving, relative-decrement semantics) are
  exactly the conditions under which `over_served = N − k` holds as an *equality*; relaxing
  any of them weakens it to the inequality `over_served ≤ max(0, N−k)`, which is what the
  model and the data both actually support unconditionally.

---

## Summary: what this phase supports, and what it narrows

**Now supported, with a TLC-verified model, not just an empirical measurement:**
- The async-settlement mechanism's vulnerability is a `Solvency` violation via a TOCTOU
  admission race on a genuinely-correct relative decrement — reachable, model-checked, and
  distinct from the historical lost-update race.
- The atomic defense (C3) closes this exact violation — model-checked at two `(N,k)`
  points, matching the empirical zero-over-serving result exactly.
- `over_served = N − k` is now a derived consequence of the implementation's own
  structural fact (admission never writes `balance`), not merely an observed regularity —
  with its governing assumptions stated explicitly, and its boundedness
  (`≤`, not unconditional `=`) established by a direct empirical counterexample from the
  project's own data (Step 2's safe-execution example).
- The formal model's shortest counterexample reveals the vulnerability needs only
  *staggered* overlap, not N-way simultaneity — a finding the empirical campaign's
  always-fully-concurrent workload design could not have surfaced on its own.

**Narrowed or newly limited:**
- No claim that `TokenAccounting.tla`'s existing model-checked results apply to the
  asynchronous-settlement mechanism; they apply only to the synchronous Class-6 baseline
  they were built for.
- No claim of a mechanized refinement proof between either model and its implementation —
  both rest on a cited, file-and-line correspondence argument.
- No formal (only empirical) account of *when*, in real milliseconds, the race becomes
  reliable — that remains Tier 1/2's result, not this phase's.

## Git

New commit on top of `1aeb97e` (current HEAD at the start of this phase), not amending it:
`formal/AsyncSettlementTOCTOU.tla`, `formal/cfg_async/*.cfg`,
`formal/async_settlement_vulnerable_n6_k2_counterexample.txt`, this document.
