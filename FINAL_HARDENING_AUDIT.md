# Final Hardening Audit

Follows `FINAL_HARDENING_BASELINE.md`. Produced as a hostile FGCS reviewer/editor pass
over the actual repository state, after fixing the one confound found during baseline
establishment (sequential-arrival pacing) and directly testing one previously-untested
durability question (Redis crash). No manuscript text has been changed in this pass except
the two retractions documented in §6/§11 — this document is the audit, not the rewrite.

---

## 1. Current baseline

See `FINAL_HARDENING_BASELINE.md` in full. Summary: HEAD at the start of this pass was
`0a0753d`; as of this document, `5deca0b` (two harness-fix/data commits + one
manuscript-adjacent correction on top). Working tree clean before each commit, verified by
`git status`/`git diff --check` every time, per the stated discipline.

## 2. Completed experiments (this pass, verified against raw artifacts)

- Reproduced the original single-host `experiments/run_async_accounting.py` unmodified:
  exact match to the manuscript's Table 3 (0,0,0,1,4) — confirms no implementation
  regression.
- Reproduced the same result via the two-machine harness's own sequential logic, both
  in-process (C0) and separate-process-sibling-container (C1) worker topologies, locally —
  confirms the harness's request-firing logic itself was never the bug.
- Found, via direct timestamp measurement (not inference), that the real two-machine
  topology's achieved sequential inter-arrival gap is 513–857ms, not the nominal 20ms.
- Fixed the harness (`experiments/two_machine/run_distributed_experiment.py`, commit
  `f0a41ba`): `sequential` now records the achieved gap per request;  new `strict-serial`
  mode added, which waits for each request's settlement to be independently confirmed
  (balance-based, not queue-depth-based — see the in-code note on why queue-depth was
  tried first and found to have a real, confirmed race) before dispatching the next.
- Reran the real two-machine topology with the fix: a corrected sequential sweep
  (0/200/500/1000/2000/5000/10000ms, 5 reps) showing a clean transition from
  zero-over-serving to fully-saturated over-serving as delay crosses the real achieved
  gap; a `strict-serial` sweep (0/500/2000/10000ms, 3 reps) confirming zero over-serving
  at every tested delay — a genuine, structurally-guaranteed negative control.
- Directly tested Redis crash-durability (not simulated): queued an event with a 30s
  delay, confirmed it in the queue, hard-killed (`SIGKILL`) the Redis container, restarted
  it, and confirmed the event was **permanently lost** (queue empty, balance never
  debited) — Redis's default config (`appendonly no`, coarse `save` thresholds) does not
  guarantee per-write durability.
- Corrected two passages in `FINAL_EXPERIMENT_AUDIT.md` that had mischaracterized the
  (pre-fix) sequential result as a clean, topology-independent negative control — retracted
  inline, not deleted, with the corrected explanation and pointers to the real data.

## 3. Uncompleted (explicitly, not silently)

- No fresh-clone reproducibility test was run this pass (§10). Current-environment
  versions are recorded instead.
- No transactional-outbox redesign was attempted (§5) — recognized as a
  fundamentally-new-architecture change and intentionally not undertaken without
  asking first; the fallback (targeted crash experiment + precise guarantee
  statement) was used instead, per the task's own explicit fallback instruction.
- Reordering (of settlement application order) is addressed **analytically**, not
  empirically (§7) — justified below, not glossed over.
- Two-machine/strengthening/formalization work remains **not integrated into the
  manuscript** (unchanged from the baseline; integration was explicitly deferred to
  "only after the scientific audit is complete" per this task's own structure).

## 4. Architecture audit

Confirmed directly from code (re-verified this pass, not assumed from memory):

- `async_b0_complete`: authorization is a read-only `SELECT`
  (`backends.py::_mutable_read`), never writes `balance`.
- `async_worker.py::drain`: settlement is a single, atomic, **relative** decrement
  (`backends.py::_mutable_debit`, `UPDATE ... SET balance = balance - :c`).
  Idempotent via a Redis `APPLIED_KEY` set.
- `async_b0_complete_atomic`: check-and-decrement as one atomic SQL statement
  (`backends.py::_mutable_reserve`).
- Event ordering in the gateway: Redis `emit()` happens **before** the `MRecord` audit
  row is written (confirmed in code, both this pass and the prior phase) — a pre-existing
  property, not introduced here, and not itself a correctness bug (the debit is correct
  regardless of when the audit row lands), but worth naming precisely for anyone adding
  future instrumentation on this path (see `EXPERIMENTAL_STRENGTHENING_AUDIT.md` §1).

## 5. Durability audit

**The question:** does the architecture survive (1) worker cancellation, (2) worker
process crash, (3) container kill, (4) machine restart, (5) event lost before durable
enqueue, (6) duplicate delivery, (7) worker restart after partial processing?

| scenario | tested how | result | guarantee |
|---|---|---|---|
| (1)/(2)/(3) worker killed mid-delay | Phase 6 failure injection, real deployment, `worker_kill` scenario, server-audit-verified | queue (Redis) survives, worker restart drains backlog correctly, no lost events, no double counting | **Guaranteed**, because Redis itself was never touched — only the worker process died |
| (4) machine restart | **not tested** | — | **Not established.** A full Azure VM reboot was not performed (would touch all of Postgres/Redis/worker simultaneously and was judged out of proportion for this pass; flagged as a gap, not papered over) |
| (5) event lost before durable enqueue | **this pass**, direct Redis `SIGKILL` + restart | queued, not-yet-due event **permanently lost** — queue emptied, balance never debited | **Not guaranteed.** Redis's default persistence (`appendonly no`, `save 3600 1 300 100 60 10000`) does not snapshot on every write; a hard crash between snapshots loses anything queued since the last one |
| (6) duplicate delivery | Phase 6 (`fault=duplicate_event`) + a dedicated Tier-4 test this phase, worker counters directly confirm suppression | idempotency (`APPLIED_KEY`) correctly suppresses every duplicate, `duplicates_suppressed` count matches exactly | **Guaranteed**, by the idempotency set — contingent on (5) not having already lost the event first |
| (7) worker restart after partial processing | Phase 6 `worker_kill`, server-audit-verified | reconciles correctly, no partial-application artifacts observed | **Guaranteed**, same caveat as (1)-(3) |

**The precise, honest statement this audit supports:** the architecture provides
**at-least-once settlement, contingent on the event surviving in Redis long enough to be
drained** — it is **not** durable against a hard crash of the Redis process itself between
enqueue and settlement. Cancellation-shielding (used elsewhere, in M1's settlement task)
is a different mechanism protecting against a different failure (the *gateway's own*
task being cancelled), already correctly scoped in the manuscript (`main_fgcs.tex`
line 993-995: *"a framework that cancelled that task would satisfy the architecture on
paper while violating (M1-a)"*) — this audit found no manuscript claim that extends
"committed and durable" to the B0-async Redis queue's survival of a Redis process crash,
so **no retraction is needed there**; this is new, additional precision, not a correction
of an existing overclaim.

**Why no transactional outbox was implemented:** doing so properly (writing the
accounting event in the same Postgres transaction that establishes the economic
decision, before any Redis involvement at all) would change which transaction the TOCTOU
window sits around — exactly the mechanism the entire two-machine experiment and the new
TLA+ model (`AsyncSettlementTOCTOU.tla`) measured and formalized. Changing it now would
invalidate the already-collected empirical and formal evidence rather than harden it. Per
the task's own stop condition ("a proposed fix requires a fundamentally new
architecture"), this was treated as a stop-and-ask matter, not implemented unilaterally.
The fallback explicitly offered in the same instructions — "perform targeted crash/restart
experiments and clearly define what the current architecture guarantees and what it does
not" — is what this section does instead.

## 6. Failure-injection audit

Re-examined `FINAL_EXPERIMENT_AUDIT.md` §8 directly (not re-run, since re-running an
already-clean, already-honestly-caveated result adds no information):

| scenario | intended | actually occurred? | independently verified? | recovery |
|---|---|---|---|---|
| `worker_kill` (real deployment) | kill settlement worker mid-delay | yes, confirmed via container logs | yes, server audit (`record_count`/`served_count` match) | clean |
| `network_partition_remote` (first attempt, in-VM iptables) | block Host A↔B traffic | **no — silent no-op**, 0 packets matched, caught *before* being reported as a result | yes, verified by direct measurement after the fact | n/a — never used |
| `network_partition_remote` (Azure NSG Deny, used) | block Host A↔B traffic | yes, verified by a direct `socket.connect` timeout test with the rule active, before trusting it for the real run | yes | clean, but see next row |
| — reachability probe during that partition | gateway `/admin/async/state` during the block | reported "still reachable" | **this was investigated and correctly NOT reported as "partition failed"** — explained as pooled-connection resilience to a *new-connection* block (NSGs are stateful, don't tear down existing flows), explicitly distinguished from new-connection reachability in the existing writeup | — |
| `extreme_delay` | D=10s | yes | yes (balance/queue state checked immediately after response) | n/a (demonstrative) |
| `duplicate_event` | double-deliver a settlement event | yes, confirmed via worker's own `duplicates_suppressed` counter | yes | suppressed correctly |
| Redis hard crash (new, this pass) | lose a queued event | yes | yes, balance/queue checked directly | **event permanently lost — reported as such, not as a recovery** |

No injection in the existing record was found to be a silent no-op that was *reported as
successful* — the one genuine no-op (the first iptables attempt) was caught and excluded
before being used for any claim, which is exactly the discipline this audit was checking
for.

## 7. Formal-model audit

- `formal/TokenAccounting.tla` (unmodified): synchronous blind-overwrite B0, M1, M2.
  Model-checked, 40 configuration×invariant runs, matches `results/formal/model_check_results.json`.
- `formal/AsyncSettlementTOCTOU.tla` (new, `FORMALIZATION_AUDIT.md`): the actual
  async-settlement TOCTOU mechanism, built directly from a file-and-line-cited T1-T7
  mapping, **causal-ordering based, not millisecond-based** — exactly the P1 instruction's
  requirement (`Authorize(A), Authorize(B), Settle(A), Settle(B)` is a reachable
  interleaving TLC explores structurally, not a timed simulation). Vulnerable config:
  `Solvency` violated (shortest counterexample: 3 staggered requests, no simultaneity
  required); `AccountingIntegrity`/`LedgerConservation` hold exhaustively. Atomic config:
  all three hold. Checked at two `(N,k)` points.
- **Neither model is claimed to verify the implementation.** Both rest on a cited,
  file-and-line correspondence argument (Step 1 of `FORMALIZATION_AUDIT.md`), explicitly
  not a mechanized refinement proof — stated in `FORMALIZATION_AUDIT.md` §9, consistent
  with the pre-existing `scope_of_formal_claims.md`'s own discipline for the old model.
- The manuscript's own "TLA+ verifies the abstract model, not the implementation" framing
  (already present, see `main_fgcs.tex` §"Implementation-specific caveats") remains
  accurate and requires no change for either model.

## 8. Mathematical audit

`FORMALIZATION_AUDIT.md` Step 3: `over_served ≤ max(0, N−k)`, equality under five stated
assumptions (equal value, fixed initial balance, no unrelated failures, the fully-raced
interleaving specifically, relative-decrement semantics). The project's own safe-execution
data (2 of 6 served) is cited as the direct counterexample to unconditional equality. No
instance of an unconditional `O = N − k` claim was found in any committed document after
this pass's correction; checked by direct grep across `*.md` this session.

## 9. Statistical audit

Repetition counts used this pass were chosen for the phenomenon's determinism, not
mechanically fixed at 30: the delay-threshold transition (clearly bimodal: 0 or fully
saturated, with a narrow noisy band) used 5 reps per cell locally/initially and 3-5 reps
for the real-topology confirmations, sufficient to characterize a transition that is
either fully consistent (D far from threshold) or visibly noisy (D near threshold) within
a handful of trials — adding more reps would not change the qualitative picture already
visible at n=3-5, and the task's own instruction ("do not mechanically use 30... justify
the repetition count") is satisfied by this reasoning rather than a fixed convention.

## 10. Reproducibility audit

Current environment, recorded directly (not a fresh-clone test — see §3 for why that was
not attempted this pass):

| component | version |
|---|---|
| Host OS | Windows 11 (build 10.0.26300) |
| Container base image | `python:3.11-slim` |
| Docker Engine | 29.8.0 |
| PostgreSQL | 16.15 (`postgres:16-alpine`) |
| Redis | 7.x (`redis:7-alpine`; `redis-cli` reports 7.4.11) |
| TLC | 2.19 (08 August 2024) |
| Java (running TLC) | OpenJDK Temurin 25.0.2, via `jdk4py` |
| harness Python | 3.13.5 (host, for the experiment client) |

Secrets/auth requirements for full reproduction: an Azure subscription (for the real
two-machine legs only; local C0/C1 topologies need none), SSH keypair for Host B — neither
is published, per standing rule. Cloud requirement: one small Azure VM
(`Standard_B2ls_v2` or equivalent), already documented in
`experiments/two_machine/REPRODUCIBILITY.md`.

## 11. Claim-to-evidence matrix

| Claim | Evidence source | Raw artifact | Config | Formal support? | Independent validation? | Remaining qualification |
|---|---|---|---|---|---|---|
| B0 (sync, lost-update) leaks under concurrency, baseline | `main_fgcs.tex` Table 1/2 region, pre-existing | `results/raw/*class6*` | concurrency sweep | `TokenAccounting.tla`, `b0_vulnerable` | yes, original + this-session regression-free | none new |
| B0-async over-serves under concurrent arrival, single host | `main_fgcs.tex` §b0revised | `results/raw/async_accounting_*.json` | 6 req/budget 2, D sweep | **no** (model didn't exist until this phase; see below) | reproduced fresh this pass, exact match | correctly scoped already |
| B0-async over-serves under **sequential** arrival once D exceeds inter-arrival time | `main_fgcs.tex` Table 3 | same as above | D=0..500, single run (no reps in original) | no | reproduced fresh this pass (0,0,0,1,4, exact) | original had **no repetitions**; this pass's local reruns (5 reps) confirm determinism locally |
| B0-async reproduces under **real physical separation**, concurrent arrival | not yet in manuscript | `results/two_machine/C2_concurrent_*.summary.json` | 10 reps × 5 delays | no | yes, multiple independent sweeps across two phases | unaffected by the sequential confound |
| B0-async reproduces under **real physical separation**, sequential arrival | not yet in manuscript | `results/two_machine/C2_sequential_20261007T123546Z.summary.json` | corrected D range, 5 reps | no | yes, this pass | races once D exceeds the *achieved*, not nominal, gap |
| Strict-serial is a true negative control | not yet in manuscript | `results/two_machine/C2_strict-serial_20261007T125009Z.summary.json` | D up to 10000ms, 3 reps | no | yes, this pass, both topologies | none |
| Atomic defense (C3) eliminates over-serving | not yet in manuscript (local/historical atomic result is) | `results/two_machine/C3_*.summary.json` | full concurrency/budget/delay matrix, both topologies | yes, `AsyncSettlementTOCTOU.tla` atomic config | yes | overhead quantified, not claimed free |
| Async-settlement mechanism is a Solvency violation via TOCTOU, not a LedgerConservation lost-update | not yet in manuscript | `FORMALIZATION_AUDIT.md` | TLC, two (N,k) points | **yes**, this phase | yes (empirical `balance_seen` signal + TLC) | derivation checked at 2 of infinitely many (N,k) points |
| Redis queue is durable against process crash | **not claimed anywhere** (correctly) | n/a | n/a | n/a | this pass found it is **not**, for a hard Redis crash specifically | now precisely characterized, §5 |
| M2 leakage efficiency independent of settlement delay | `main_fgcs.tex` §b0revised | `results/raw/async_accounting_*.json` | 3 delays | no | reproduced fresh this pass (0.5823 at every delay) | none |
| Pricing monotonicity is a sufficient condition, not an empirical claim about all commercial pricing | `main_fgcs.tex` M2 conditions paragraph | n/a (definitional) | n/a | n/a | already correctly scoped before this pass | none |
| No detectability claim | `main_fgcs.tex` §"Limits of detectability measurement" | `audit/confirmation_bias.md` (prior phase) | n/a | n/a | already correctly scoped before this pass | none |
| No prevalence/commercial-vulnerability claim | `main_fgcs.tex` "Scope of empirical claims" paragraph | n/a | n/a | n/a | already correctly scoped before this pass | none |

No major claim in this matrix is left at "evidence: inferred" — every row has either a
raw artifact, a formal result, or an explicit "not claimed" entry.

## 12. Remaining limitations (consolidated, not new)

- Machine-restart durability (full VM reboot) untested.
- Reordering tested analytically (commutativity of relative decrement), not empirically —
  justified: the only invariants that matter (`Solvency`, `LedgerConservation`,
  `AccountingIntegrity`) are defined over the *final* state after all settlements apply,
  and addition is commutative/associative regardless of the order `debit_unchecked` calls
  arrive in; an empirical reordering test would measure the same arithmetic fact already
  established by inspection of `_mutable_debit`'s single-statement, no-ordering-dependency
  implementation, not reveal new information.
- No fresh-clone reproducibility run.
- Two-machine/strengthening/formalization work is still not in the manuscript.
- No refinement proof, no liveness proof, no parameterized proof (both models).

## 13. Reviewer attack matrix

### Reviewer 1 — Distributed systems: "Is the distributed/asynchronous architecture actually demonstrated?"

| # | Objection | Severity | Evidence | Fix | Fixed? | New experiment? | Manuscript change needed? |
|---|---|---|---|---|---|---|---|
| 1.1 | "Your 'sequential, physically separated' negative control was never a valid test — you never exceeded the real network's own latency." | **P0** | Confirmed directly from raw timestamps (§2) | Harness fix + rerun with a correct D range | **Yes** | Yes (performed, bounded) | Yes, when integrated — must use corrected framing, not the retracted one |
| 1.2 | "You never crashed the actual distributed data plane (Redis), only the worker." | **P0** | Confirmed: worker-kill ≠ Redis-kill | Direct Redis SIGKILL test, this pass | **Yes, characterized** (not "fixed" — the gap is real) | Yes (performed) | Yes — any "durable" claim about the async queue must say "at-least-once given Redis survives," not "durable" |
| 1.3 | "One VM, one region, one provisioning — this is one data point." | P1 | Stated in Threats to Validity already | None attempted (would require more Azure spend) | N/A | Not performed (out of scope this pass) | Already disclosed |

### Reviewer 2 — Security: "Is there a realistic integrity failure and is the defense actually sufficient?"

| # | Objection | Severity | Evidence | Fix | Fixed? | New experiment? | Manuscript change needed? |
|---|---|---|---|---|---|---|---|
| 2.1 | "Is over-serving really a Solvency problem, or did you just relabel a lost-update bug?" | **P0** | `FORMALIZATION_AUDIT.md` §8: direct code citation shows relative decrement, no lost updates, TLC confirms `LedgerConservation` HOLDS while `Solvency` VIOLATED | Formalized and distinguished explicitly from the old model | Yes | No (TLC, not a large experiment) | Yes, when integrated |
| 2.2 | "Does the atomic defense actually cost nothing, or are you hiding the price?" | P1 | Quantified: +15% local, +71% real, mechanistically explained, decomposition explicitly stated as not performed | Wording already hedged; this pass added the decomposition disclaimer | Yes | No | Minor, if quoted verbatim |

### Reviewer 3 — Formal methods: "Does the formal model actually correspond to the claimed mechanism?"

| # | Objection | Severity | Evidence | Fix | Fixed? | New experiment? | Manuscript change needed? |
|---|---|---|---|---|---|---|---|
| 3.1 | "Your old TLA+ model doesn't even model what you're claiming — it's a different race." | **P0** | Found and formalized precisely, `FORMALIZATION_AUDIT.md` | New, separate model built; old model's actual scope stated precisely, not silently relabeled | Yes | No (TLC) | Yes, when integrated: must not attribute the old model's guarantees to the async mechanism |
| 3.2 | "No refinement proof — the model could be anything." | P1 (conceded, not fixable this pass) | File-and-line correspondence table, not mechanized | None — stated as a limitation, matching the pre-existing standard for the old model | N/A (documented, not "fixed") | No | Already the project's standing position |

### Reviewer 4 — Experimental methodology: "Could the results be an artifact of the harness, timing, stale state, or infrastructure?"

| # | Objection | Severity | Evidence | Fix | Fixed? | New experiment? | Manuscript change needed? |
|---|---|---|---|---|---|---|---|
| 4.1 | "Your sequential negative control was literally a harness artifact (round-trip-coupled pacing)." | **P0** | This entire pass's central finding | Fixed, rerun, retracted old claim inline | **Yes** | Yes | Yes |
| 4.2 | "Your first network-partition attempt was a silent no-op — were there others you didn't catch?" | P1 | Re-audited (§6): no other silent no-ops found in the existing record | N/A, already correctly handled before this pass | Already fixed (prior phase) | No | No |
| 4.3 | "One repetition count fits all? Did you justify it or just pick 30/5/3?" | P2 | §9: justified by the phenomenon's determinism/transition shape, not a fixed convention | Documented | Yes | No | No |

### Reviewer 5 — FGCS editor: "Is this a distributed-systems/infrastructure contribution, not merely an LLM-security application paper?"

| # | Objection | Severity | Evidence | Fix | Fixed? | New experiment? | Manuscript change needed? |
|---|---|---|---|---|---|---|---|
| 5.1 | "LLM is incidental — this is a generic accounting-race paper with an LLM example." | P1, not closeable by more experiments | Already conceded explicitly in the manuscript's own novelty framing (`journal_reviewer_attack_v2.md` Reviewer A) | N/A — contribution framing is systematization + measurement + sufficiency conditions, stated as such throughout | N/A | No | None (framing already correct; do not inflate) |
| 5.2 | "A two-machine Azure experiment and a new TLA+ model exist but aren't in the paper — why should I believe they're real?" | **P0 for THIS submission's credibility** | Everything in this and the prior two phases is committed, raw-data-backed, and this document is the trail | Integrate into the manuscript (next step, explicitly deferred per task structure) | **Not yet done** | No | **Yes — this is the single largest remaining action item** |

## 14. Final recommendation

The empirical and formal evidence base is now internally consistent, precisely scoped, and
free of the one confound and the one durability overclaim-risk this pass found. **The
manuscript itself, as currently published/submitted, was already careful on nearly every
dimension this audit checked** (sequential-vs-concurrent distinction, pricing
monotonicity as a sufficient condition, no detectability claim, no prevalence claim, TLA+
scope discipline) — the real gaps were in *this session's own prior-phase interpretation*
of the (unpublished, not-yet-integrated) two-machine work, now corrected.

**The project is not yet ready to claim the two-machine/formalization work is part of the
paper**, because it is not in the paper. It is ready to be integrated, and this document
is the evidence trail that integration should draw from.
