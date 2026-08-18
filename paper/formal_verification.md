# Formal verification

Every claim in this document carries one of three labels, and they are not
interchangeable:

| label | meaning |
|---|---|
| **MODEL-CHECKED** | TLC exhaustively explored the reachable state space of `formal/TokenAccounting.tla` under a stated configuration and found no violation (or found a counterexample, where that was the expectation). Machine-checked. |
| **FORMALLY ARGUED** | Stated over the accounting model and reasoned about by hand. *Not* machine-checked. Never described as "proved". |
| **EMPIRICALLY VERIFIED** | Measured on the implemented testbed and independently recomputed from raw data. |

A property may hold more than one label; where it does, that is the strongest form of
evidence this artifact offers, and it is stated explicitly.

**Summary of what was actually run:** 10 configurations × 4 invariants = **40 independent
TLC runs**, **28,363 distinct states**, ~36 s wall clock, **0 disagreements** with the
expectations declared in `formal/check.py` before the run.

---

## 1. State variables

| variable | domain | meaning |
|---|---|---|
| `pc[r]` | 12 lifecycle states | where request `r` is: `CREATED`, `AUTHORIZED`, `RESERVED`, `EXECUTING`, `STREAMING`, `ABORTED`, `COMPLETED`, `ACCOUNTED`, `RECONCILED`, `REFUNDED`, `REJECTED`, `DONE` |
| `snapshot[r]` | `0..InitialBalance` | the balance value `r` read — the stale read that makes the B0 race possible |
| `delivered[r]` | `0..Chunks` | inference value actually streamed to the client |
| `reserved[r]` | `0..Chunks` | funds held out of the balance for `r` |
| `debit[r]` | `0..Chunks` | committed charge |
| `refund[r]` | `0..Chunks` | amount returned to the client |
| `balance` | integer | the shared credit state (**integer**, not natural — solvency must be *able* to fail) |

Derived: `Net(r) = debit[r] − refund[r]`.

## 2. Architecture constants

The safe and unsafe architectures are the *same* state machine under different constants,
exactly as the testbed implements them behind one interface.

| constant | dimension | `TRUE` means |
|---|---|---|
| `AtomicDebit` | B0 | guard and decrement in one action |
| `Reserves` | M1 | hold funds before execution |
| `AbortSafe` | M1 | every terminal path reaches accounting finalization |
| `ServerAuthority` | M2 | the billing basis is server-computed usage |
| `ClientMayAbort` | *workload* | the client may disconnect mid-stream |

`ClientMayAbort` is a workload switch, not an architecture property. It is disabled in the
B0 configurations so that the synchronization counterexample is free of commitment-timing
noise — the same isolation the experiments enforce by holding the other two dimensions at
their safe setting.

## 3. Transitions

```
CREATED ──AuthorizeRead──▶ AUTHORIZED ──ReserveWrite──▶ RESERVED     (non-atomic path)
CREATED ──AtomicReserve─────────────────────────────────▶ RESERVED     (atomic path)
CREATED / AUTHORIZED ──AtomicReject / RejectStale──────▶ REJECTED
RESERVED ──Begin──▶ EXECUTING ──StartStream──▶ STREAMING
STREAMING ──Deliver──▶ STREAMING          (value leaves the provider, one chunk at a time)
STREAMING ──Abort──▶ ABORTED              (client disconnects, any time)
STREAMING ──Complete──▶ COMPLETED         (only when delivered = Chunks)
COMPLETED ──AccountComplete──▶ ACCOUNTED
ABORTED   ──AccountAbort──▶ ACCOUNTED     (only if AbortSafe)
ABORTED   ──AbortBypass──▶ REFUNDED       (only if ¬AbortSafe)
ACCOUNTED ──Reconcile──▶ RECONCILED ──Finish──▶ DONE
REFUNDED  ──Finish──▶ DONE
```

The essential asymmetry: `Deliver` moves value to the client while accounting is still
open. Every mechanism studied is a different way of failing to close that gap.

## 4. Invariants

| invariant | statement | empirical counterpart |
|---|---|---|
| `AccountingIntegrity` | `∀r` terminal: `delivered[r] ≤ Net(r)` | gate G1 (per-record leak recomputation) |
| `Solvency` | `balance ≥ 0` | the constrained-budget probe in the M1 ablation |
| `LedgerConservation` | all terminal ⇒ `InitialBalance − balance = Σ Net(r)` | gate G3 (ledger conservation) |
| `RefundBounded` | `refund[r] ≤ max(0, reserved[r] − delivered[r])` | the paper's legitimate-refund condition `F(r) ≤ Res(r) − V(r)` |

Solvency is checked **separately** from accounting integrity. Collapsing them would
destroy the very result the ablation exists to establish.

## 5. Results per mechanism

### B0 — state synchronization

**Unsafe counterexample (MODEL-CHECKED, 21 steps, 157 distinct states).** Both requests
read `snapshot = 2`; both blind-write `balance := 2 − 2 = 0`, so one decrement is lost;
both then deliver 2 units and are each charged 2. Final `balance = 0`, so
`InitialBalance − balance = 2` while `Σ Net = 4`. `LedgerConservation` fails by exactly
one request's cost.

Note *which* invariant fails. Accounting integrity and the refund bound both **hold**:
every individual record is internally consistent, and the charge matches what that request
received. What breaks is conservation of the shared balance. This is precisely the
empirical finding that the B0 lost update "collapses all concurrent debits to a single
surviving one" while each usage record still looks correct — and it is why a per-record
audit cannot detect B0 but a conservation check can.

**Defense (MODEL-CHECKED).** With `AtomicDebit = TRUE`, all four invariants hold on every
reachable state (37 distinct states; the guard collapses the race). Requests that cannot
afford the cost reach `REJECTED` without delivering value.

*Sufficient condition:* a single atomic guarded decrement of the shared credit state.
**MODEL-CHECKED** against the modelled concurrency (2 and 3 requests) and
**EMPIRICALLY VERIFIED** ($0 leak at every tested concurrency 1–50).

### M1 — commitment timing

This is the paper's orthogonality claim, and the model checks all four combinations of
(reserves, abort-safe) rather than the two the implementation happens to ship.

| configuration | reserves | abort-safe | Integrity | Solvency |
|---|---|---|---|---|
| `m1_post_completion` | ✗ | ✗ | **VIOLATED** | holds |
| `m1_reserve_refund_on_abort` | ✓ | ✗ | **VIOLATED** | holds |
| `m1_no_reserve_settle` | ✗ | ✓ | holds | **VIOLATED** |
| `m1_reserve_reconcile` | ✓ | ✓ | holds | holds |

**Counterexamples (MODEL-CHECKED).**

* `m1_post_completion` — 7 steps: deliver 1 chunk, abort, `AbortBypass`, terminate with
  `Net = 0` while `delivered = 1`.
* `m1_reserve_refund_on_abort` — 9 steps for integrity, 7 for the refund bound: the
  reservation is committed *and then fully refunded*, so `Net = 0` despite delivery, and
  `refund = 2 > reserved − delivered = 1`. This is the shape of the deployed `new-api`
  bug.
* `m1_no_reserve_settle` — 12 steps: two requests each settle honestly for what they
  delivered, but with no reservation the second settlement drives `balance` to **−1**.
  Accounting integrity holds throughout; the provider is simply owed money it never held.

**The orthogonality result (MODEL-CHECKED).** Reservation alone gives solvency and not
integrity; abort-safe finalization alone gives integrity and not solvency; only the
conjunction gives both. Neither primitive substitutes for the other, and this is now
established by exhaustive state-space exploration rather than by the two architectures we
happened to build. This is also **EMPIRICALLY VERIFIED** by the ablation.

*Sufficient condition:* terminal-path totality (every terminal state reaches accounting
finalization) **plus** a reservation. **MODEL-CHECKED** under the model.

### M2 — usage authority

**Unsafe counterexample (MODEL-CHECKED, 11 steps).** With `ServerAuthority = FALSE` and
`DeclaredUsage = 1 < Chunks = 2`: the request delivers 2 units and is charged 1.
`Net = 1 < delivered = 2`. `AccountingIntegrity` fails.

`RefundBounded` **also** fails (9 steps): with a reservation in place, under-billing
manifests as an over-refund — `refund = reserved − declared` exceeds
`reserved − delivered`. That the same defect surfaces in two independent invariants is a
consequence of the model, not something we set out to show, and it is reported because the
per-invariant checking regime made it visible.

**Defense (MODEL-CHECKED).** With `ServerAuthority = TRUE` all four invariants hold, *for
the same lying client* — `DeclaredUsage` is still 1. The declared value simply stops being
read.

*Sufficient condition:* the billing basis is a server-computed usage vector outside
attacker control. **MODEL-CHECKED for the modelled transformation family**
(under-declaration of the billed quantity) and **EMPIRICALLY VERIFIED** across all 8
implemented manipulations (leakage efficiency 0.000 on every server-authoritative
architecture).

**Note on scope.** The model checks one transformation shape: the declared quantity is
lower than the true one. The pricing-function analysis
(`paper/pricing_function_analysis.md`) covers *which* transformations pay off under which
pricing basis; that is an economic argument, **FORMALLY ARGUED** and
**EMPIRICALLY VERIFIED**, not model-checked. Encoding multi-category pricing in TLA+ would
enlarge the state space without strengthening the architectural condition, which is about
*authority*, not *arithmetic*.

### Composition

`all_defenses` (2 requests, contended budget, aborts enabled, a lying client) and
`all_defenses_3req` (3 requests, 4,807 distinct states) hold all four invariants on every
reachable state. **MODEL-CHECKED.** The three defenses compose; none re-opens another's
gap within the model.

## 6. The M2 concurrency claim, formally

The paper classifies M2's concurrency independence as **analytic, not empirical**. The
model makes the reason explicit: `BilledUsage(actual)` is a function of one request's own
fields and contains no reference to `balance` or to any other request's variables. No
interleaving can change it. The empirical sweep is a consistency check that the
implementation contains no unintended shared-state dependency — and it passes.

Status: **FORMALLY ARGUED** (from the structure of the specification and of
`app/m_routes.py`, where the billed cost is computed before any balance read) and
**EMPIRICALLY VERIFIED** (identical leakage efficiency at every concurrency level). It is
*not* claimed as MODEL-CHECKED: TLC verifies invariants over reachable states, not the
absence of a data dependency in a function definition.

## 7. What is proven and what is not

**Proven (within the model).** Under bounded request counts (2 and 3), unit pricing, a
single shared balance, strongly-consistent state, and the modelled transformation family:
the stated defense conditions are *sufficient* for all four invariants, and each unsafe
architecture violates a *specific, identified* invariant on **every** schedule — not
merely on the schedules our harness happened to produce. That last point is the real gain
over measurement alone: a passing experiment shows absence of failure on the paths taken,
while model checking shows absence of failure on all paths in the model.

**Not proven.** Nothing here establishes that a production implementation is safe. The
model abstracts away the database, the network, partial failure, retries at the transport
layer, asynchronous reconciliation, multi-category pricing, and tokenizer disagreement.
The full exclusion list is `paper/scope_of_formal_claims.md`.

**Implementation-specific, and deliberately left so.** The correspondence between a
constant here and a code path in `app/` is an argument, not a refinement proof. We do not
claim the implementation refines the specification; we claim they agree on the properties
checked, and `paper/formal_empirical_mapping.md` pairs each counterexample with the
measurement it predicts.

## 8. The expectation discipline

`formal/check.py` declares the expected outcome of every one of the 40 cells **before**
running TLC and exits non-zero on any disagreement. Without that, a formal model is just a
document that can be edited until it agrees with the paper.

It caught a real error immediately. The first version of the specification treated a
reservation as a *hold* and set `debit = charge` at settlement, so `Net = debit − refund`
fell below the delivered value and TLC rejected the **safe** configurations. The model was
wrong, not the paper: in a reserve-and-reconcile architecture the reservation *is* the
committed debit and the refund returns its unused part. Correcting the settlement
semantics (`committed == IF reserved > 0 THEN reserved ELSE charge`) made the safe
configurations verify. The failure is recorded here and in `formal/README.md` rather than
erased, for the same reason the withdrawn detectability claim is recorded rather than
deleted.
