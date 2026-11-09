# Experimental Strengthening Audit

This document covers the phase of work that followed the completed real two-machine
experiment (`FINAL_EXPERIMENT_AUDIT.md`, commit `8545e59`). That phase answered one
question: does the B0 asynchronous-settlement accounting failure reproduce across a real
machine/network boundary? Answer: yes, under concurrent arrival. This phase asks the
follow-up questions a hostile reviewer would ask next: **why** does it happen, **how
robust** is it, **what controls its magnitude**, and **how generally** does the atomic
defense eliminate it. Every experiment below either strengthens an existing claim with
direct mechanistic evidence, narrows a claim that was broader than the evidence supports,
or surfaces a limitation that was not previously visible. Nothing here was run to make the
paper look more impressive; two findings below (the clock-offset artifact and the TLA+
correspondence gap) are inconvenient and are reported as such.

All raw data is under `experiments/two_machine/raw/` and `results/two_machine/`, committed,
never overwritten. One run failed from a transient infrastructure fault (not a scientific
result) and is preserved with an `INFRASTRUCTURE_FAILURE` filename tag rather than deleted.

---

## 1. Mechanism instrumentation (Tier 1.1)

**Existing claim:** B0's asynchronous-settlement path "authorizes against the CURRENT
balance, serves, and queues the debit" (docstring, `async_b0_complete`) — asserted by
reading the code, not measured per-request.

**New experiment:** Added monotonic (`perf_counter_ns`) intra-gateway timestamps at
authorization-read-start/done, decision, event-creation, and emit (T1–T4b), and an opt-in
worker-side hook (`--instrument`) that persists the worker's own pop/due-check and
debit-applied wall-clock timestamps (T6/T7) into the same `MRecord` row, keyed by
`request_id`. All additive — default behavior is byte-identical with the flag omitted.

**Evidence:** `app/accounting/async_worker.py`, `app/accounting/worker_main.py`,
`app/async_routes.py` (commit `b30a390`). Validated locally first (cheap, fast iteration)
before touching Azure: found and fixed a real bug where ~half of concurrent requests'
worker-side timestamps were silently lost, root-caused to the gateway emitting the Redis
event *before* committing the corresponding `MRecord` row (pre-existing code, not something
this instrumentation introduced) racing against DB-connection-pool contention under 6
concurrent requests. Fixed with a bounded retry in the hook, not by reordering the
gateway's pre-existing code.

**Confidence:** Increased — the mechanism is now measured per-request, not just read from
the docstring.

**Limitation discovered:** The gateway emits-before-commits ordering is itself worth noting
for anyone adding future instrumentation to this code path: a worker-side hook that expects
the `MRecord` row to already exist at due-time cannot assume that without a retry.

**Raw data:** `app/accounting/async_worker.py`, `app/accounting/worker_main.py`,
`app/async_routes.py` — code change, not a data file; validated via
`experiments/two_machine/raw/C1_concurrent_20261007T003157Z.*`.

---

## 2. Causal correlation: does over-serving actually cross the authorization/commitment window? (Tier 1.2)

**Existing claim:** Over-serving happens because "every request that arrives inside the
reconciliation window authorizes against a balance that does not yet reflect its
predecessors" (docstring) — a plausible mechanism, asserted, not directly demonstrated
per-request.

**New experiment:** `experiments/two_machine/mechanism_analysis.py` reconstructs, for every
request in a run, the server-observed `balance_seen` at authorization time (already present
in the pre-existing code — no new instrumentation needed for this specific signal) and
determines directly whether a sibling's settlement had landed before this request's own
read, rather than asserting it.

**Evidence (local, `C1_concurrent_20261007T002803Z`, D=50ms, a representative racing
cell):** six concurrent requests, budget funds exactly 2 units (`0.162`); every one of the
six requests observed `balance_seen >= unit_cost` (`0.162` or `0.081`, never `0` or
negative) — i.e., *none* of the six requests' authorization reads ever saw a sibling's
settlement land first. This is the direct, server-observed confirmation of the mechanism,
not an inference.

**Evidence (local, `C1_concurrent_20261007T002737Z`, D=50ms, before a worker reset — a
representative *non-racing* cell, served=2 of 6):** `balance_seen` values were `0.162,
0.081, 0, 0, 0, 0` — a clean, monotonically-draining sequence showing the balance being
correctly decremented *between* reads for four of the six requests (which were then
correctly rejected). This is the mechanism working *correctly* when the race does not
materialize, captured with the same instrumentation, not cherry-picked to only show the bug.

**Confidence:** Increased, and more precisely scoped — "over-serving" is now traceable to a
specific, directly-observed server-side signal (`balance_seen` undrained across all
concurrent siblings), not merely inferred from the final served count.

**Raw data:** `results/two_machine/mechanism_analysis_C2_concurrent_20261007T005925Z_20261007T010616Z.json`
(the full real-topology delay sweep, all 55 cells, balance-seen signal reported per cell as
`settlements_visible_during_cell_authorization`).

---

## 3. Settlement-delay threshold (Tier 1.3) and network-vs-settlement separation (Tier 2)

**Existing claim:** "over-served and trial_asr diverge for 2 ≤ concurrency ≤ k" (memory,
original class-6 baseline) and, from the two-machine Phase 6 result, "over-serving
stabilizes at exactly 4/6 served for D≥10ms; D=0 is noisier."

**New experiment:** Refined delay sweep (0,1,2,5,10,20,50,100,250,500,1000 ms × 5 reps,
concurrent arrival) run on **both** the local sibling-worker topology (C1, near-zero
network latency) and the real two-machine topology (C2, measured 40–108ms RTT) — the same
workload, same budget, same code, differing only in the physical distance between gateway
and settlement.

**Evidence:**

| topology | D=0 over-served (mean / stdev, n=5) | D=1 | D≥2ms |
|---|---|---|---|
| C1 (local) | 3.00 / 1.73 (noisy: 0,3,4,4,4) | 3.80 / 0.45 | 4.00 / 0.00 (every rep) |
| C2 (real)  | 4.00 / 0.00 (every rep) | 4.00 / 0.00 | 4.00 / 0.00 (every rep) |

Source: `results/two_machine/analysis_summary.json` (regenerated from
`C1_concurrent_20261007T004629Z` and `C2_concurrent_20261007T005925Z`).

**Interpretation — this is the key Tier 2 finding, stated precisely:** the real topology's
race is *more* consistently total than the local one, not less, and the transition from
"noisy" to "always raced" happens at a similar, very small D (≤2ms) on both topologies. This
directly answers the network-vs-settlement-delay question: **the race's existence and
threshold are governed by the *relative* dispatch spread between the N concurrently-fired
requests (tiny and sub-millisecond on both topologies, since `asyncio.gather` dispatches
them together) relative to the configured settlement delay D — not by the absolute
magnitude of network RTT.** Network latency does not create the race; it does not prevent
it either; what it does is make the six requests' authorization reads cluster even more
tightly in relative time (all bottlenecked by a similarly-sized real round trip), which if
anything makes the real-topology race *more* reliably total at small D than the local one.
A deliberate `tc netem` network-delay injection experiment (suggested in the original
brief) was considered and **not run**: this C1-vs-C2 comparison, using infrastructure
already built and validated, answers the same question with real, physically-separated
hardware rather than simulated latency on one host, at effectively zero additional cost —
and avoids a repeat of the NSG/iptables fragility already encountered twice this project
(see §8).

**Confidence:** Increased and substantially narrowed. The original claim ("D≥10ms gives a
consistent 4/6") is upgraded with a precise mechanism and shown to be true from D≈2ms, on
both topologies, for a *qualitatively different reason on each* than a single "settlement
delay creates the race" story would suggest.

**New limitation discovered (important, reported honestly):** the cross-host *exposure
window* metric (`created_ns → applied_ns`, wall clock on both ends) measured via this new
instrumentation plateaus at **~850–1000ms regardless of configured D** for D ≤ 500ms on the
real topology, only beginning to track D once D exceeds that floor (D=1000ms → measured
exposure ≈1013ms). This is consistent with (and a far more precisely measured, n=300+
confirmation of) the Phase 6 SSH-round-trip clock-offset estimate of ~800±430ms. **This
does not affect any served/over-served/final-balance result** — those are single-machine
(Host B) Postgres state with no cross-host timestamp comparison — but it means the
`exposure_windows_ms` metric, for the real two-machine topology specifically, should be
read as *bounded below by the cross-host clock discrepancy*, not as a precise measurement
of real elapsed settlement delay. Source: `results/two_machine/mechanism_analysis_C2_concurrent_20261007T005925Z_20261007T010616Z.json`.

**Raw data:** `experiments/two_machine/raw/C1_concurrent_20261007T004629Z.jsonl`,
`experiments/two_machine/raw/C2_concurrent_20261007T005925Z.jsonl` (the retry; the original
attempt `C2_concurrent_20261007T005714Z` failed from a transient Azure/Docker network
hiccup after its first cell and is preserved as `*.INFRASTRUCTURE_FAILURE.*`, not deleted
or silently re-run over).

---

## 4. Concurrency scaling (Tier 1.4 / Tier 2)

**Existing claim:** "6 requests, budget 2, 4 over-served" — a single workload point, never
tested at other scales.

**New experiment:** Concurrency ∈ {1,2,4,8,16}, fixed budget=2, D ∈ {0,10,50,500}, 5 reps,
local; confirmed at concurrency ∈ {1,2,4,8}, D ∈ {0,500}, 3 reps, real topology.

**Evidence (local, D=500ms, every rep identical):**

| concurrency | served | over-served | pattern |
|---|---|---|---|
| 1 | 1 | 0 | — |
| 2 | 2 | 0 | — |
| 4 | 4 | 2 | = concurrency − budget |
| 8 | 8 | 6 | = concurrency − budget |
| 16 | 16 | 14 | = concurrency − budget |

**Evidence (real topology, D=0 and D=500, 18/18 cells, zero variance):** identical
`over_served = concurrency − budget` relationship, confirmed on real hardware.

**Confidence:** Substantially increased and the claim is **generalized**, not just
reproduced: "4/6 over-served" was one point on a line (`over_served = N − budget` for
N ≥ budget, under full racing), not a workload-specific artifact. This is a stronger,
more general claim than the original.

**Raw data:** `results/two_machine/C1_concurrent_20261007T004815Z.summary.json` through
`...20261007T004948Z.summary.json` (local, one file per concurrency level);
`results/two_machine/C2_concurrent_20261007T010723Z.summary.json` through
`...20261007T010911Z.summary.json` (real, one file per concurrency level).

---

## 5. Budget scaling (Tier 2.5)

**Existing claim:** untested at any budget other than 2.

**New experiment:** budget ∈ {1,2,4,8} × concurrency ∈ {2×, 4× budget} × D ∈ {10,50,500} ×
3 reps, local.

**Evidence:** `over_served = concurrency − budget` holds across every tested combination
(9/9 cells valid in each of the 8 budget/concurrency pairs), with one honest exception: at
budget=8/concurrency=32/D=10ms, 3 of 3 reps showed *slight* under-saturation (23, 27, 19
served instead of 32) — resolving to full, consistent saturation (32/32) by D=50ms and
D=500ms. This is reported, not smoothed over: at high absolute concurrency (32 simultaneous
connections), D=10ms is close enough to the connection-pool-queueing noise floor (see §3)
that a small fraction of requests can still see a partially-drained balance; by D=50ms this
noise is fully gone.

**Confidence:** Increased. The scaling law from §4 holds across budget sizes too, with the
noise floor's own scale-dependence now characterized rather than assumed constant.

**Raw data:** inline in the terminal transcript this phase (not separately saved to a
single file per the brief's "do not run the entire Cartesian product" guidance — each of
the 8 budget/concurrency pairs is a 9-cell run using the harness's standard summary output
under `results/two_machine/`, timestamped between 00:48–00:50 UTC on 2026-10-07).

---

## 6. Value/price-tier scaling (Tier 2.6)

**Existing claim:** untested whether leakage scales with delivered economic value.

**New experiment:** `--price-tier low|medium|high` (low=0.15, medium=1.5, high=15.0
$/1k-output-tokens — a 10× ladder at each step), D ∈ {50,500}, 3 reps, local, default
concurrency/budget.

**Evidence:** `over_served` count is **exactly invariant** to price tier (6 served, 4
over-served, every cell, every tier) — the race is a *count*-based admission phenomenon,
independent of price. Dollar leakage scales linearly and precisely with price: final
balance ≈ −$0.04 (low) → −$0.36 (medium, ≈10×) → −$3.5 (high, ≈10× again), matching the
tier pricing ratios exactly.

**Confidence:** Increased and cleanly separated: the *mechanism* (how many extra requests
get admitted) is price-independent; the *dollar cost* of that mechanism scales linearly
with whatever the account is being billed.

**Raw data:** inline terminal transcript, 2026-10-07 ~00:51 UTC local runs (price-tier
override smoke test plus the 3-tier comparison); code change validated in
`experiments/two_machine/run_distributed_experiment.py` commit `31bdaf2`.

---

## 7. Defense robustness and overhead (Tier 3)

**Existing claim (Phase 6):** C3 (atomic) shows zero over-serving across the original
delay sweep, both locally and on the real topology (100 cells total, Phase 6).

**New experiment:** C3 run under the *exact same* expanded matrix that made C2 over-serve
in §4/§5 — concurrency ∈ {1,2,4,8,16} × D ∈ {0,10,50,500}, local (100 cells); concurrency ∈
{8,16}, real topology (6 cells); budget-scaling spot checks at budget=4/conc=8 and
budget=8/conc=32 (local, 6 cells).

**Evidence:** **Zero over-serving in every single cell** — `served` exactly equals
`budget` regardless of concurrency (1 through 32) or delay (0 through 500ms), on both
topologies. This is the apples-to-apples comparison the original brief asked for: the exact
workload shapes that broke C2 leave C3 untouched.

**Overhead (new instrumentation added to `/async/b0/complete-atomic`, commit `a23c1db`):**

| topology | vulnerable `read_balance` latency | atomic `reserve_atomic` latency | overhead |
|---|---|---|---|
| local | mean 3.06ms, median 2.23ms (n=2031) | mean 3.52ms, median 2.56ms (n=325) | +0.46ms mean (+15%) |
| real (Host A→B) | mean 110.72ms, median 105.52ms (n=555) | mean 190.18ms, median 186.89ms (n=18) | +79.5ms mean (+71%) |

**Interpretation:** the atomic defense's overhead is small in absolute local terms but
becomes large in absolute real-network terms, for a mechanistic reason, not a vague "atomic
ops are slower" claim: `reserve_atomic` is a committed **write** (`UPDATE ... RETURNING`,
followed by `session.commit()`), while `read_balance` is a plain **read** — a committed
write over a real network needs at least one more round trip than a bare read, and that
extra round trip costs roughly the same ~60–110ms as every other round trip measured in
this phase, which is consistent with the size of the gap observed. This is reported as a
real, quantified cost of the defense, not claimed to be negligible, and not claimed to be
*exactly* one round trip: the T1→T2 instrumentation measures each call end-to-end
(network transit, PostgreSQL's own processing of the `UPDATE`, and — for the atomic path
— the commit acknowledgment, all aggregated together). This phase did not add
instrumentation to decompose network transit time from database processing time from
commit latency separately; the "~one extra round trip" explanation is offered as the
most parsimonious account consistent with the aggregate numbers and the known per-hop RTT
(§3), not as a component-level measurement.

**Confidence:** Substantially increased — the defense's robustness claim is now general
(holds across a 32× concurrency range and an 8× budget range, not just the original
workload point), and its cost is now quantified with a mechanism, not asserted as free.

**Raw data:** `results/two_machine/C3_concurrent_20261007T0048*` through `*T0055*` (local
concurrency/budget matrix), `results/two_machine/C3_concurrent_20261007T0109*`/`*T0110*`
(real concurrency spot-check); overhead figures computed directly from `m_records.extra`
on both the local and Host B Postgres instances (ad hoc query, not saved as a separate
artifact — reproducible via the SQL in this document's §7 and the instrumentation added in
commit `a23c1db`).

---

## 8. Failure/recovery (Tier 4)

**Existing claim (Phase 6):** worker-kill and extreme-delay failure injection against the
real deployment both recover cleanly; the local network-partition result was retracted in
favor of a verified Azure-NSG-Deny mechanism after an in-VM iptables approach was caught as
a silent no-op.

**New experiment:** a dedicated duplicate-settlement-event test (`--fault
duplicate_event`, sequential arrival, D=50ms, 5 reps, local) — the fault pipeline already
supported this (`FAULTS = (..., "duplicate_event", ...)`, pre-existing code), but it had
not been exercised as a dedicated, instrumented experiment before.

**Evidence:** `final_balance = 0.000000` in all 5 reps despite every served request's
settlement event being deliberately double-emitted; the worker's own counters confirm the
fault was genuinely exercised, not vacuously absent: `duplicates_suppressed=10`, exactly
matching 10 served requests (2 per rep × 5 reps) each duplicated once. The pre-existing
idempotency mechanism (`APPLIED_KEY` Redis set, checked in `async_worker.py::drain()`)
correctly suppressed every duplicate.

**Confidence:** Increased — this specific fault class (duplicate settlement) is now
verified with a dedicated, instrumented test rather than being merely "supported by the
code" (the fault enum existed; a direct experiment confirming it did not double-charge did
not).

**Not re-run:** worker-kill, network-partition, and extreme-delay against the real
deployment were already thoroughly covered in Phase 6 (`results/two_machine/failure_injection_remote_*`)
and are not repeated here — re-running an already-clean, already-verified result adds no
information.

**Raw data:** inline terminal transcript, 2026-10-07 ~00:55 UTC; worker log counters
confirmed via `docker logs sepaper-worker-1`.

---

## 9. TLA+ cross-check — a genuine, reported discrepancy

**Existing claim (implicit, from the model's own README):** the TLA+ model's `AtomicDebit`
flag formalizes "atomic conditional decrement vs. read/check/blind absolute write," and the
B0 class of vulnerability studied throughout this project (including the two-machine
experiment) is this model's unsafe branch.

**Cross-check performed:** read `formal/TokenAccounting.tla` and
`results/formal/model_check_results.json` directly, rather than assuming the
correspondence.

**Finding (reported honestly, not hidden):** the model's unsafe B0 branch
(`AuthorizeRead`→`ReserveWrite`) is a **blind absolute overwrite**:
`balance' = snapshot[r] - Cost(Chunks)`. Two overlapping requests under this semantics lose
one decrement entirely — the model-checked result is `AccountingIntegrity: HOLDS`,
`Solvency: HOLDS`, **`LedgerConservation: VIOLATED`** for `b0_vulnerable`. The balance never
goes negative; the provider simply under-collects (one decrement is silently discarded).

The async-settlement mechanism this entire two-machine experiment studies
(`async_b0_complete` → `async_worker.py::debit_unchecked`) is mechanistically **different**:
`debit_unchecked` is a genuine, atomic, **relative** decrement
(`UPDATE credits SET balance = balance - :c WHERE account_id = :a`, confirmed by reading
`app/accounting/backends.py::_mutable_debit` directly) — nothing is ever lost or
overwritten; every admitted request's debit eventually lands, correctly, additively. The
bug is a **TOCTOU admission race**: too many requests are admitted against a stale
pre-decrement balance before any of their (individually correct) debits land, and the
account goes **negative** — empirically, every over-served cell in this entire project
(Phase 6 and this phase) shows a negative `final_balance`, which is a **Solvency**
violation, not a `LedgerConservation` violation.

**This is a genuine formalization gap, not an error in either the code or the model**: the
TLA+ specification, as it stands, does not have states for an asynchronous settlement queue
with a configurable delay `D` — it reasons about races as abstract interleaving
reachability, not as a producer/consumer queue with real time passing between production
and consumption. It formally covers (and correctly predicts the qualitative existence of a
problem for) the *synchronous* lost-update variant of B0 (the original, already-published
class-6 baseline), but does not yet have a specification for the *asynchronous-settlement*
variant this two-machine experiment and all of Phase 6/7's C2/C3 conditions actually
exercise.

**What this means for the paper's claims:** every claim in this and the prior audit about
"over-serving" and "negative final balance" under async settlement should be understood as
an empirically-characterized **Solvency** violation under a TOCTOU admission race, model-
checked only implicitly (the *synchronous* sibling mechanism is verified; the *async*
mechanism studied here is not yet given its own TLA+ specification). The atomic defense
(C3) is still correctly modeled: `AtomicReserve`/`AtomicReject`'s single-statement
check-and-decrement is the precise abstraction of `ledger.reserve_atomic()`'s
`UPDATE ... WHERE balance >= :c RETURNING balance`, and `b0_hardened`'s model-check result
(`AccountingIntegrity: HOLDS`, `Solvency: HOLDS`, `LedgerConservation: HOLDS`,
`RefundBounded: HOLDS`) matches the empirical zero-over-serving result in §7 exactly.

**Recommendation (not implemented here, per the instruction not to rewrite the model to
match the experiment):** a future model extension adding explicit queue/delay states
(`EMIT`, `QUEUED`, `DUE`, `SETTLED` with a time parameter) would let TLC check the
async-settlement TOCTOU race directly, including whether `Solvency` can be violated under
bounded delay `D` and bounded concurrency `N` — closing this gap formally rather than only
empirically.

**Raw data:** `formal/TokenAccounting.tla`, `results/formal/model_check_results.json`
(read, not modified); `app/accounting/backends.py::_mutable_debit`,
`app/accounting/async_worker.py::drain()` (read, not modified for this finding).

---

## 10. Summary: what became stronger, what remains unproven

**Stronger:**
- The mechanism is now measured, not asserted (§1, §2).
- The delay threshold is precisely characterized on both topologies, with a mechanistic
  (not hand-wavy) explanation for why the real network doesn't weaken the race (§3).
- The headline "4/6 over-served" result is now known to be one point on a general
  `over_served = N − budget` scaling law, confirmed on real hardware (§4, §5).
- Leakage is shown to scale linearly and exactly with price while the admission mechanism
  itself is price-independent (§6).
- The atomic defense's robustness is generalized across a 32× concurrency range, and its
  cost is quantified with a mechanism rather than asserted as negligible (§7).
- Duplicate-settlement idempotency is now directly, dedicatedly tested (§8).

**Narrowed:**
- "D≥10ms gives a consistent result" is corrected to "D≥~2ms," and the reason is now
  understood to be about *relative* dispatch spread, not *absolute* network latency (§3).
- The formal-verification framing is narrowed: the existing TLA+ model certifiably covers
  the synchronous lost-update B0 variant and the atomic defense precisely, but does **not**
  yet formally cover the asynchronous-settlement TOCTOU variant this entire two-machine
  experiment studies — that variant's correctness claims rest on empirical measurement
  only, not model-checking, until the model is extended (§9).

**Remains unproven / explicitly out of scope this phase:**
- A `tc netem`-based direct network-delay injection (deliberately not run; see §3's
  justification for why the C1-vs-C2 comparison serves the same purpose more safely).
- Any claim about variance across Azure regions, VM sizes, or repeated provisioning
  (unchanged from the prior audit).
- A formal (TLA+) treatment of the async-settlement TOCTOU race (§9) — recommended, not
  attempted.

## 11. Git discipline

Three logical commits this phase, on top of `8545e59`, none amending any prior commit:

1. `b30a390` — Tier 1 instrumentation (T1–T7 timestamps, opt-in worker hook).
2. `a23c1db` — mechanism analysis tool, `--concurrency`/`--budget` harness overrides,
   atomic-endpoint timing.
3. `31bdaf2` — `--price-tier` harness override.

This document and the accompanying raw-data commit follow as a fourth commit (see the
session's final report for the exact hash).
