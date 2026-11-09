# Final Hardening Baseline

Produced before any code or manuscript changes in this pass, per instruction. Establishes
ground truth from the actual repository state, not from prior summaries.

## 1. Exact current commit

```
HEAD: 0a0753d68e79565ad0d2eeed8876bc2fbcb21537
      "formalize actual async-settlement TOCTOU mechanism"
```

Working tree is clean (no uncommitted changes) as of the start of this pass.

Commit chain this entire two-machine/formalization effort sits on (newest first), none
amended, verified via `git log --oneline`:

```
0a0753d formalize actual async-settlement TOCTOU mechanism
1aeb97e Experimental strengthening: mechanism, robustness, defense, and TLA+ cross-check
31bdaf2 Add --price-tier override to the harness for Tier 2 value-scaling experiments
a23c1db Tier 1/2/3 harness: mechanism analysis tool, concurrency/budget overrides, atomic-endpoint timing
b30a390 Tier 1 instrumentation: per-request T1-T7 timestamps for the B0 async race
8545e59 Complete real two-machine experiment: C2 reproduces over Azure, C3 holds
2549200 Complete two-machine asynchronous settlement experiment: final local validation
```

## 2. Experiments actually completed (verified against raw artifacts, not plans)

- **Local, single-host, in-process worker (C0)** and **local, separate-process sibling
  container worker (C1)**: both topologies' B0-async delay sweeps exist as raw JSONL under
  `experiments/two_machine/raw/`, both concurrent and sequential arrival.
- **Real two-machine, Azure Central India (C2)**: raw JSONL + manifests exist for sequential
  and concurrent arrival, delays 0/1/2/5/10/20/50/100/250/500/1000ms, confirmed reachable
  via SSH and the gateway's own `/admin/db-info` at the time of this baseline check (VM
  running — see §9 for the cost implication).
- **Atomic defense (C3)**, same topologies, same delay/concurrency/budget matrices.
- **TLA+**: one model (`TokenAccounting.tla`, pre-existing, unmodified) covering the
  synchronous lost-update B0 baseline, and one new model
  (`AsyncSettlementTOCTOU.tla`) covering the actual async-settlement TOCTOU mechanism,
  both TLC-checked with results in this session's transcript and
  `FORMALIZATION_AUDIT.md`.
- **Failure injection**: worker-kill, network-partition (NSG-verified mechanism),
  extreme-delay, duplicate-settlement-event — all against the real deployment, documented
  in `FINAL_EXPERIMENT_AUDIT.md` and `EXPERIMENTAL_STRENGTHENING_AUDIT.md`.

## 3. Experiments NOT completed / not integrated

- **None of the above (two-machine, strengthening, or formalization work) is written into
  the manuscript (`paper/main_fgcs.tex`) in any form.** Confirmed by direct grep: the only
  mention of a two-machine experiment is the Threats-to-Validity "Distribution" paragraph,
  which still says it **was not performed** (see §6).
- No `tc netem` direct network-delay injection (deliberately scoped out in the prior
  phase, documented reasoning in `EXPERIMENTAL_STRENGTHENING_AUDIT.md` §3).
- No transactional-outbox durability redesign — not yet assessed against the current
  architecture (this pass's P0 item).
- No fresh-clone reproducibility test has been run in this session.

## 4. Current architecture (as read directly from code, this session)

- Gateway (`app/async_routes.py::async_b0_complete`): authorization is a plain, read-only
  `SELECT` (`ledger.read_balance` → `backends.py::_mutable_read`); it never writes
  `balance`. On admission, an event is created (`aw.new_event`, wall-clock
  `created_ns`/`deliver_after_ns`) and pushed to Redis (`aw.emit`); an `MRecord` row is
  written (audit trail) **after** the event is already queued — a pre-existing ordering,
  not introduced by this session, noted as a source of a benign instrumentation race in
  `EXPERIMENTAL_STRENGTHENING_AUDIT.md` §1.
- Settlement worker (`app/accounting/async_worker.py::drain`, run via
  `app/accounting/worker_main.py` as a standalone process, or `_worker_loop` in-process):
  polls Redis, and for each due event applies `ledger.debit_unchecked` →
  `backends.py::_mutable_debit`: a single, atomic, **relative** decrement
  (`UPDATE credits SET balance = balance - :c ... RETURNING balance`). Idempotency via a
  Redis `APPLIED_KEY` set, checked before applying.
- Atomic defense (`app/async_routes.py::async_b0_complete_atomic`):
  `ledger.reserve_atomic` → `backends.py::_mutable_reserve`: check-and-decrement as one
  atomic SQL statement, no event queued, nothing left to settle later.
- Two-machine deployment: Machine A (`docker-compose.machineA.yml`, gateway only) and
  Machine B (`docker-compose.machineB.yml`, Postgres + Redis + standalone worker), real
  Azure VM for Machine B, confirmed via the account-visibility proof in
  `FINAL_EXPERIMENT_AUDIT.md`.

## 5. Current formal model status

- `formal/TokenAccounting.tla` (pre-existing, untouched): models the **synchronous**
  blind-overwrite lost-update B0 race. `b0_vulnerable`: `AccountingIntegrity` HOLDS,
  `Solvency` HOLDS, `LedgerConservation` VIOLATED. This is the original Class-6 baseline,
  not the async-settlement mechanism.
- `formal/AsyncSettlementTOCTOU.tla` (new this phase): models the actual async-settlement
  TOCTOU mechanism. Vulnerable config (`N=6,k=2` and `N=4,k=2`): `Solvency` **VIOLATED**,
  `AccountingIntegrity`/`LedgerConservation` HOLD exhaustively. Atomic config: all three
  HOLD. TLC results, counterexample trace, and the full implementation-to-model mapping
  are in `FORMALIZATION_AUDIT.md`.
- Neither model is claimed, anywhere in the committed documentation, to verify the
  implementation directly — both rest on a cited, file-and-line correspondence argument,
  not a mechanized refinement proof. This limitation is stated explicitly in
  `FORMALIZATION_AUDIT.md` §9.

## 6. Current empirical claims (manuscript, `paper/main_fgcs.tex`, as currently published/submitted)

- §"Mechanism localization", B0 paragraph (lines 495-508): **already** distinguishes the
  "baseline trigger" (concurrent overlap) from the "general security condition"
  (authorization not atomically coupled to commitment), and states deferred settlement
  creates the same condition "under strictly sequential arrivals, with no overlap at all."
  This is precise, careful language that predates this session's two-machine work.
- §"B0 revisited" (lines 1184-1227, Table 3 `tab:asyncb0`): reports a **single-host**,
  **sequential**, 20ms-apart, 6-request/2-budget sweep at delays 0/10/50/100/500ms, with
  over-served = 0,0,0,1,4. This is the manuscript's one quantitative async-B0 sequential
  result.
- Threats to Validity, "Distribution" paragraph (lines 1394-1410): states physical
  separation was **not tested** ("we did not run the accounting store or the settlement
  worker on a second machine... A two-machine replication... was not performed here").
  **This paragraph is now stale** — the two-machine experiment exists — but has not been
  updated, because none of this session's work has touched the manuscript yet.

## 7. Unresolved limitations (as of this baseline, before this pass's work)

- Two-machine/strengthening/formalization results are not in the manuscript (§3).
- The Threats-to-Validity "Distribution" paragraph is factually stale (§6).
- See §8 for a newly-discovered inconsistency that is more serious than staleness.

## 8. Inconsistencies discovered during this baseline check (the most important section)

### 8.1 — The real two-machine "sequential never races" result is confounded by network RTT, not a clean negative control

This was found by direct experimentation during this baseline check, specifically because
the task asked to audit sequential-vs-concurrent terminology and verify two-host status
against raw artifacts rather than prior summaries.

**The chain of evidence:**

1. Re-ran `experiments/run_async_accounting.py` (the original, unmodified, published
   single-host harness) against the current codebase, unmodified. It reproduced the
   manuscript's Table 3 numbers **exactly**: over-served = 0,0,0,1,4 at D=0,10,50,100,500ms.
   This confirms the implementation has not regressed relative to the published result.

2. Ran the two-machine harness's (`run_distributed_experiment.py`) sequential-arrival logic
   against the same local server, same moment, condition `C0` (in-process worker, matching
   the original topology exactly): reproduced 0,0,0,1,4 **exactly**.

3. Ran the identical test with condition `C1` (separate-process sibling-container worker):
   **also** reproduced 0,0,0,1,4. The harness's own sequential-firing logic is correct and
   matches the original protocol faithfully, regardless of in-process vs. separate-process
   worker topology, locally.

4. This directly contradicts the **already-committed, Phase-6** real-two-machine sequential
   sweep (`results/two_machine/C2_sequential_20261006T233416Z.summary.json`,
   `experiments/two_machine/raw/C2_sequential_20261006T233416Z.jsonl`), which shows
   over-served = 0 at **every** delay including 500ms, across **all 50 reps** (10 reps ×
   5 delays), with no exceptions.

5. **Root cause, found by measuring actual elapsed wall-clock time between consecutive
   sequential requests directly from the raw JSONL's own `sent_at_utc` timestamps** (not
   inferred): for the real Azure topology at D=500ms, rep=0, the measured gaps between
   consecutive request sends are **513, 857, 513, 545, 482ms** — not the nominal 20ms. The
   harness's sequential loop `await`s each request's full round trip (dominated by real
   network RTT to Host B, measured at 40-108ms per hop, doubled because both `read_balance`
   and the Redis `emit` are separate round trips) before sleeping the additional 20ms. Over
   a real network, this makes the **actual** inter-arrival time 500-900ms, not 20ms.

**What this means, stated precisely:** the real-topology "sequential never races, even at
D=500ms" result is **genuine, correctly measured data** — it is not a bug, and it is not
fabricated. But the **interpretation** given to it in
`EXPERIMENTAL_STRENGTHENING_AUDIT.md` §3 ("Sequential arrival shows zero over-serving at
every delay... it is not a null result, it is the designed-in negative control") is
**misleading and must be corrected**: the result does not demonstrate that sequential
arrival is structurally immune to the async-settlement race under physical separation. It
demonstrates that the specific fixed 20ms inter-arrival constant, designed for a
near-zero-latency single-host topology, is **overwhelmed by real network RTT** once the
requests are issued over a real network, because the harness's request-pacing is
round-trip-coupled rather than wall-clock-scheduled. The real network's RTT (500-900ms
effective spacing) already exceeds every tested D by the time later requests fire, which
is **why** it never races — not because physical separation defeats the mechanism.

**This does NOT affect the concurrent-arrival result** (the primary claimed finding,
"C2 reproduces over-serving over a real network"): concurrent arrival fires all N requests
via `asyncio.gather` simultaneously, independent of per-request RTT, and that result
stands on its own evidence.

**This has not yet caused any false claim in a submitted manuscript**, because the
manuscript does not yet describe the two-machine sequential result at all (§6). It is
flagged now, before any manuscript integration, so the "negative control" is not written
up as clean when it is confounded.

**Not yet decided: how to proceed.** Per the task's own stop conditions ("a result
contradicts a published manuscript result" is not quite this — nothing published
contradicts anything; the issue is a prior-phase *interpretation*, now known to be
unsound, of an unpublished internal result), and because the correct remediation is a
judgment call (see Final Report below), this baseline stops here rather than silently
picking a fix.

## 9. Azure resource status (cost-relevant, checked this session)

VM `vm-llm-metering-hostb` (resource group `rg-llm-metering-two-machine`) is **currently
running**, confirmed via `az vm get-instance-view`. This has been running since
provisioning across multiple prior sessions. Flagging per the task's own stop condition
("Azure would incur substantial cost") — no action taken on it without instruction.
