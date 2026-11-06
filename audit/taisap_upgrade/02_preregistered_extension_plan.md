# Preregistered decisive extension plan

Frozen before new scientific execution on 2026-11-06. Existing results do not count as
execution of these protocols. Analysis code may reject malformed input, but the hypotheses,
metrics, cell definitions, exclusions, and success criteria below must not be changed after
seeing new outcomes without a dated amendment.

## E1 — Bounded asynchronous-condition falsifier

This is **designed to falsify the central claim** that authorization is safe only when it
is atomically coupled to the economic commitment on the authorizing path.

Hypothesis: In the causal async model, vulnerable configurations admit more than budget
whenever at least `k+1` requests can be admitted before settlement; atomic admission never
exceeds budget for all preregistered `(N,k)` points.

Null/falsifying outcome: Any atomic configuration violates solvency, or any vulnerable
configuration with `N>k` has no reachable over-serving trace despite a schedule permitting
`k+1` pre-settlement admissions.

Controls: Existing `(6,2)` and `(4,2)` configurations; identical state machine and
invariants; only `N`, `k`, and `AtomicAdmission` vary.

Sample size: Exhaustive TLC checks at `(N,k) = (3,1), (4,1), (4,2), (5,2), (6,2), (6,3)`
for vulnerable and atomic modes, each invariant checked independently.

Exclusions: TLC parse/semantic errors, state-space exhaustion, or tool termination are
failures, never safe results; no configuration may be removed after execution.

Locked metrics: Exit code, generated/distinct states, invariant outcome, shortest
counterexample length, and exact configuration/spec hashes.

Positive interpretation: The bounded causal model supports the generalized coupling
condition at the six points only; it is not an implementation or unbounded proof.

Null interpretation: Withdraw or narrow the generalized B0 condition before any venue
submission and investigate the counterexample without relabeling it.

Resources: Local CPU, bundled `tla2tools.jar`, single TLC worker; expected under 20 minutes.

Execution status: PROPOSED_ONLY

## E2 — M2 independent repricing and authority audit

Hypothesis: For every stored request record, changing the pricing function changes the
profitable manipulation set exactly through fields read by that function, while every
server-authoritative billing architecture retains non-positive leakage under all catalogued
transformations.

Null/falsifying outcome: An independent raw-data auditor finds positive leakage for a
server-authoritative architecture, or finds a profitable manipulation that changes no
field consumed by the locked pricing function.

Controls: Honest declarations; original category-additive and flat-total pricing; original
raw records retained byte-for-byte; client-authoritative architectures as positive controls.

Sample size: All M2 raw records in the frozen controlled and real-stack datasets; eight
manipulations, six architectures, and three locked pricing bases (category-additive,
flat-total, and a preregistered mixed vector `1:0.1:5:2`).

Exclusions: Duplicate request IDs, missing true/declaration vectors, non-finite prices, or
failed conservation checks invalidate the dataset and halt analysis rather than dropping
rows.

Locked metrics: Per-record true cost, billed cost, leakage, leakage efficiency, sign,
architecture, manipulation, and pricing-field dependency; cell counts must reconcile to
raw input counts.

Positive interpretation: Supports M2's computation-versus-authority and pricing-basis
claims for the two frozen datasets and three pricing functions only.

Null interpretation: Downgrade M2 sufficiency, locate whether the defect is data,
implementation, or theory, and report the failed cell.

Resources: Local Python only; no service, model inference, or network access; expected
under 10 minutes.

Execution status: PROPOSED_ONLY

## E3 — Terminal-path totality fault matrix

Hypothesis: Reserve-and-reconcile with durable idempotent finalization preserves
accounting integrity at every preregistered cancellation/worker/queue cutpoint; the two
vulnerable M1 controls fail at their predicted cutpoints.

Null/falsifying outcome: Any hardened cell ends after the reconciliation horizon with
`V(r)>N(r)`, a duplicate debit, an unbounded refund, or an unsettled due outbox record.

Controls: Honest completion; post-completion debit and refund-all-on-abort positive
controls; no-reserve-settle solvency negative control; duplicate-delivery control.

Sample size: 12 cutpoints (before admission commit; after admission commit; before first,
middle, and final chunk; before and after outbox enqueue; worker before claim, after claim,
and after debit; queue termination; duplicate delivery), 20 repetitions per architecture
for five architectures, fixed seed list `0..19` (1,200 trials).

Exclusions: Infrastructure startup failure before the first request is a named failed run;
application exceptions after admission remain outcomes; no timing outlier is removed.

Locked metrics: Delivered value, reservation, debit, refund, net committed amount, final
balance, outbox state, application count, duplicate count, and reconciliation latency.

Positive interpretation: Supports terminal-path totality only for the implemented local
stack and injected cutpoints, not arbitrary distributed failures.

Null interpretation: The hardened implementation does not realize the stated M1
sufficiency condition; manuscript and formal-to-empirical mapping must be corrected.

Resources: Local Docker/PostgreSQL/Redis and existing testbed; no third-party endpoint;
estimated 30–60 minutes.

Execution status: PROPOSED_ONLY

## E4 — Independent physical two-machine replication

Hypothesis: With achieved inter-arrival gaps measured at the gateway, over-serving begins
when deferred settlement crosses the authorization cadence, while settlement-confirmed
strict serialization serves exactly the budget.

Null/falsifying outcome: The vulnerable condition shows no delay-linked transition across
the locked range, or strict serialization over-serves at any delay.

Controls: Same-host external-worker control, zero-delay control, strict serialization, and
clock-sync/network-baseline capture.

Sample size: Delays `0, 500, 2000, 5000, 10000` ms, five repetitions, six requests against
budget two for vulnerable sequential arrivals; three repetitions for strict serialization
(40 total cells).

Exclusions: Runs with manifest/hash mismatch, missing request records, failed clock check,
or unreachable host are infrastructure failures and are retained as such, not analyzed as
zero leakage.

Locked metrics: Achieved inter-arrival gap, authorization and settlement timestamps,
served/settled counts, over-served count, balance, ledger conservation, and host manifests.

Positive interpretation: One independent host pair reproduces the mechanism; this still
does not establish production prevalence or multi-region behavior.

Null interpretation: Withdraw the physical-distribution generalization and retain only
the local causal result if independently reproduced.

Resources: Requires an independently provisioned authorized second host and may incur
cloud cost; no host will be created or contacted without explicit user authorization.

Execution status: HUMAN_APPROVAL_REQUIRED

