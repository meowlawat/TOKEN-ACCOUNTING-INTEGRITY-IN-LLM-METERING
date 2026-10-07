# Post-Integration Audit

Produced immediately after integrating the hardening/durability/formalization work into
`paper/main_fgcs.tex`, per `MANUSCRIPT_INTEGRATION_PLAN.md`. Base commit before this
pass's edits: `15def0a` (tree clean). This document covers the manuscript edit only; no
code, experiment, or raw data changed in this pass.

## 1. New claims added

1. The B0 asynchronous-settlement condition persists under a network-separated
   two-machine deployment (new `sec:netsep`, abstract, contributions item 4/5).
2. A settlement-confirmed "strict serialization" control shows zero over-serving across
   the same topology and delay range, distinct from (and a correction of the generality
   of) the sequential-arrivals-with-deferred-settlement result (`sec:netsep`).
3. The pre-fix architecture's queued settlement event was not durable against a hard
   queue-process failure, confirmed by direct test (SIGKILL, not simulated), and a
   PostgreSQL transactional outbox closes that specific gap (`sec:outboxdurability`,
   `tab:practical` Async row).
4. A second, separate, causal-ordering TLA+ specification
   (`AsyncSettlementTOCTOU.tla`) model-checks the asynchronous mechanism itself at two
   $(N,k)$ points, contrasted explicitly against the first specification's different
   invariant-violation signature (new `sec:asyncformal`).

## 2. Evidence supporting each

1. `results/two_machine/C2_sequential_20261007T123546Z.summary.json` — 35 cells, 7
   delays $\times$ 5 reps, real Azure two-machine topology, commit `f0a41ba`. Table
   values transcribed and spot-checked directly against the JSON (not audit prose) before
   writing: 0 over-served for $D \le 2000$ ms (25 cells), 3/2/2/2/2 at $D=5000$, 4/4/4/4/4
   at $D=10000$.
2. `results/two_machine/C2_strict-serial_20261007T125009Z.summary.json` — 12 cells
   (4 delays $\times$ 3 reps), over-served $=0$ and served $=$ budget in every cell,
   spot-checked directly. Corroborated by the 1-rep pilot
   `C1_strict-serial_20261007T123415Z.summary.json`.
3. `DURABILITY_HARDENING_AUDIT.md`'s failure-matrix and test-matrix rows (Redis SIGKILL
   test, worker-kill tests A/B/D/E/G/H/I/J), cross-checked against `app/accounting/
   ledger.py::claim_and_debit_outbox`, `app/accounting/worker_main.py::reconcile_outbox`,
   and `app/async_routes.py`'s commit-before-emit reordering, all read directly this
   session (not from the prior summary alone).
4. `FORMALIZATION_AUDIT.md` §Step 4/5 TLC output: `vulnerable_n6_k2` (29,820/7,869
   states, `Solvency` violated depth 13; `AccountingIntegrity`/`LedgerConservation`
   independently re-checked exhaustive, 91,921/22,521 states, no violation),
   `atomic_n6_k2` (517/247, all hold), `vulnerable_n4_k2` (1,750/598, `Solvency`
   violated), `atomic_n4_k2` (41/29, all hold).

## 3. Existing claims modified

- `sec:limits` "Distribution" paragraph: previously stated flatly that no second machine
  was used and a two-machine replication "was not performed here." This was true when
  written and is false now; reworded to report the replication and narrow the remaining
  limitation to the untested dimensions (VM/host restart, wide-area/multi-region,
  production deployment, network-behavior characterization beyond one cloud-region
  pair).
- `sec:limits` "Formal" paragraph: previously stated the formal model "assumes strongly
  consistent accounting state, so the asynchronous family... lies outside it." Reworded
  to say this of the *first* specification only, and to introduce the second,
  independently-limited specification.
- `tab:practical` Async row, Implementation pattern cell: previously named idempotency
  and at-least-once delivery only; now also names the transactional outbox as the
  mechanism providing the durable record the Model-level condition column already
  required. The Model-level condition, Failure mode, and Property-at-risk cells are
  unchanged — the fix satisfies a condition the table already stated correctly, it does
  not change what the table claims is required.
- Abstract and Contributions items 4-5: one clause each added, carrying the
  network-separation result forward; no existing sentence in either was deleted or
  reworded beyond the appended clause.
- `sec:async`, `sec:b0revised`, Discussion ("Engineering implications"): three short
  cross-reference/disambiguation clauses added (distinguishing the injected lost-event
  fault from the Redis-crash finding; defining "sequential" vs. "strict serialization"
  the first time both terms matter together; pointing the general durability sentence at
  the specific outbox fix). No measured number in any of these three locations changed.

## 4. Claims intentionally NOT added

- No claim that any commercial/production provider is vulnerable, implements this
  architecture, or exhibits this behavior at any prevalence. (Grep-verified: "production"
  appears 9 times, all as negations or explicit non-claims; "prevalen" appears once, as a
  non-claim.)
- No claim of "physical hardware separation" using that phrase, or of distributed-systems
  vulnerability in general — the two-machine result is scoped to the one tested
  cloud-region host pair throughout. (Grep-verified: zero hits for "physical separation"
  or "physically distributed" post-edit.)
- No claim of exactly-once delivery. (Grep-verified: the one "exactly-once" hit is the
  negation "at-least-once, not exactly-once.")
- No claim that the outbox fix is validated against a VM/host restart, arbitrary-scale
  distributed failure, or any topology beyond the one network-separated pair — stated as
  an explicit limitation in both `sec:outboxdurability` and the Implementation-specific
  caveats paragraph.
- No new figure, no new equation, no change to any number in `sec:results` or
  `sec:economics`, no change to `tab:asyncb0`, `tab:formalmatrix`, or any existing
  figure.
- No revenue-impact or large-scale load claim, no detectability claim (both pre-existing
  non-claims, left untouched).

## 5. New limitations added or sharpened

- Two-machine evidence is scoped to one cloud-region host pair; it establishes the
  condition is not a loopback artifact, not that it characterizes general networked
  deployments, VM/host restarts, wide-area topologies, or production systems
  (`sec:limits` Distribution, `sec:netsep` closing paragraph).
- The durability fix is validated only at the specific failure points tested (worker
  kill before/during/after consumption, hard queue-process termination, duplicate
  delivery); not against a host restart or arbitrary-scale distributed failure
  (`sec:outboxdurability`, Implementation-specific caveats).
- The second formal specification is an untimed, causal-ordering abstraction, checked
  exhaustively at exactly two finite $(N,k)$ points; it does not verify the
  implementation, timing, or network behavior, and does not generalize to arbitrary
  request counts (`sec:asyncformal`, `sec:limits` Formal).
- Delivery is at-least-once; only *application* of a settlement is idempotent/effectively
  exactly-once. This distinction is now stated explicitly where it previously was not
  stated at all (the mechanism did not exist in the manuscript before this pass).

## 6. Remaining reviewer vulnerabilities

- A reviewer could still ask why only one cloud region / host pair was tested, and
  whether results would hold under higher cross-region latency or packet loss — the
  manuscript now states this as an open limitation rather than answering it, which is
  honest but still a gap a reviewer may press on.
- The "clean transition" table (`tab:twomachine`) has only two delay points
  (5000, 10000 ms) showing partial/full over-serving; a reviewer could ask for finer
  delay granularity in that range. We did not run additional delays beyond the existing
  sweep to avoid fabricating or extrapolating a result not in hand — flagged here rather
  than silently left looking more resolved than it is.
- The formal model's shortest counterexample (3 staggered requests) and the empirical
  two-machine result were not cross-checked trace-for-trace (i.e., no claim that the
  formal counterexample's specific interleaving was reproduced live); the manuscript
  states both as independent evidence of the same mechanism, not as a verified
  correspondence beyond the existing "formally argued" / "empirically verified" labeling
  already used elsewhere in the paper.
- The outbox's "duplicate delivery does not result in duplicate debit" guarantee rests on
  one atomic database transaction; we did not force a live transaction rollback (stated
  explicitly as analytical-only), which a sufficiently hostile reviewer could still probe.

## 7. Compilation status

- `tectonic main_fgcs.tex`: succeeds, 20 pages (was 18 before this pass's net +161
  source lines), PDF written (`main_fgcs.pdf`, 2.06 MiB).
- Only warnings are pre-existing-pattern underfull/overfull hbox/vbox layout warnings
  (standard for this document class at this page count); none are new reference, label,
  or citation errors.
- Final converged pass's log (`main_fgcs.log`): zero "undefined reference," zero
  "undefined citation," zero "multiply defined" occurrences.
- All three new/modified labels (`sec:netsep`, `sec:outboxdurability`,
  `sec:asyncformal`, `tab:twomachine`) resolve correctly; no duplicate labels anywhere in
  the document (checked by counting all `\label{}` occurrences).
- Equation numbering unchanged: exactly the same three labeled equations
  (`eq:integrity`, `eq:refund`, `eq:m2`) as before this pass; no new numbered equation
  was added.
- Required greps, all passing: "sequential" (7 pre-existing occurrences, audited
  individually, all consistent; one new disambiguating sentence added, no existing
  occurrence changed), "exactly once" (1 hit, correct negation), "durable"/"durability"
  (audited individually; all new hits describe the outbox record as durable
  *independent of* the queue, never the queue itself), "physical separation"/"physically
  distributed" (0 hits), "production" (9 hits, all non-claims), "prevalence" (1 hit,
  non-claim), marketing language ("bulletproof," "production-ready," "definitive,"
  "robust," "solves distributed accounting": 0 hits).

## 8. Exact commit

Manuscript edits in this pass are not yet committed as of writing this document; they
will be committed together with this audit and the integration plan as one commit on
top of `15def0a`, with a message naming the integration and no AI attribution, per
standing project policy.
