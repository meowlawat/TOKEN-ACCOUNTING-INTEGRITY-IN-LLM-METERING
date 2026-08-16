# Defense Sufficiency Conditions

For each mechanism we state conditions that are **sufficient**, *within the accounting
model of `accounting_state_model.md`*, to guarantee the integrity property

```
ValueDelivered(r) ≤ NetCommittedDebit(r)                      (INTEGRITY)
```

**Scope disclaimer, stated once and meant throughout.** These are sufficiency arguments
*within the model*, not a machine-checked proof and not a universal theorem about
deployed systems. The model abstracts away: partial failures of the datastore, clock
skew, operator error, and any adversary outside the threat model of §2 of the paper.
Where a condition depends on a property our implementation supplies but the model does
not force, we label it **implementation-specific**. Our experiments *test* these
conditions; they do not prove them.

---

## 0. Notation

For a request `r`:

| symbol | meaning |
|---|---|
| `V(r)` | value delivered to the client (cost of tokens actually received) |
| `Res(r)` | amount reserved before execution (0 if none) |
| `D(r)` | sum of committed debits attributable to `r` |
| `F(r)` | sum of refunds attributable to `r` |
| `N(r) = D(r) − F(r)` | net committed debit |
| `U_true(r)`, `U_bill(r)` | true and billed usage vectors |
| `P(·)` | pricing function, monotone non-decreasing in each usage category |

A terminal state is any state from which the request performs no further accounting
action (`COMPLETED`, `ABORTED`, `RECONCILED`, `REFUNDED`, or an error terminal).

---

## 1. M1 — commitment timing

### Sufficient conditions

> **(M1-a) Terminal-path totality.** Every terminal path of the request lifecycle
> reaches a state in which an accounting event for `r` has been *committed and is
> durable*, including paths entered by client disconnect, server exception, or stream
> truncation.
>
> **(M1-b) Refund boundedness.** Every refund satisfies
> `F(r) ≤ Res(r) − V(r)`; i.e. a refund may release only the *unconsumed* portion of a
> reservation and never the value already delivered.

### Argument (within the model)

Let `r` reach terminal state `s`. By (M1-a) an accounting event is committed at `s`, so
`D(r)` is well defined and durable. Two cases:

- **Reservation taken.** Then `D(r) = Res(r)` and, by (M1-b),
  `N(r) = Res(r) − F(r) ≥ Res(r) − (Res(r) − V(r)) = V(r)`. INTEGRITY holds.
- **No reservation.** Then (M1-a) requires the terminal event itself to commit a debit;
  our settlement commits `D(r) = P(U_delivered(r)) = V(r)` and `F(r) = 0`, so
  `N(r) = V(r)`. INTEGRITY holds with equality.

### Why each condition is necessary, empirically

Dropping either condition produces a measured violation, which is what the ablation
tests:

| architecture | (M1-a) | (M1-b) | measured outcome |
|---|---|---|---|
| `reserve_reconcile` | holds | holds | leak 0.0000 at every abort point |
| `no_reserve_settle` | holds | vacuous (no reservation) | leak 0.0000 (integrity holds) |
| `post_completion` | **violated** (abort path commits nothing) | — | leak up to 0.0960/req |
| `reserve_refund_on_abort` | holds | **violated** (`F = Res` while `V > 0`) | leak up to 0.0960/req |

### Not implied by INTEGRITY: solvency

INTEGRITY constrains what the client is *charged*, not what the provider can *afford to
serve*. Solvency is the separate property

```
served(r) ⇒ the system held sufficient committed or reserved capacity for r    (SOLVENCY)
```

> **(M1-c) Reservation sufficiency.** If a reservation is taken atomically before
> execution and the request is refused when the reservation fails, then no request is
> served without capacity, giving SOLVENCY.

`no_reserve_settle` satisfies (M1-a)/(M1-b) but **not** (M1-c): measured, it preserved
integrity (leak 0.0000) while driving the balance to −0.32 on a two-request budget.
**Therefore (M1-a)+(M1-b) and (M1-c) are independent, and both are required for a correct
design.** This is the formal counterpart of the empirical orthogonality result.

### Implementation-specific
- *Durability of the terminal accounting event under client disconnect.* The model says
  "committed"; our implementation achieves it by running settlement in a
  cancellation-shielded task with its own database session. A framework that cancels the
  settlement coroutine along with the request would violate (M1-a) despite identical
  architecture on paper.
- *Exactly-once settlement.* We rely on a settled-flag guard so a terminal path cannot
  settle twice. Double settlement would not break INTEGRITY (it over-charges) but would
  break conservation.

---

## 2. M2 — usage authority

### Sufficient conditions

> **(M2-a) Authority.** The usage value used for billing is derived from state the
> attacker cannot control: `U_bill(r) = U_true(r)`, where `U_true` is computed by the
> server (or supplied by a party trusted under the threat model) from the actual request
> and actual generated output.
>
> **(M2-b) Pricing monotonicity.** `P` is non-decreasing in each usage category, and the
> billed cost is `P(U_bill(r))`.

### Argument (within the model)

If (M2-a) holds then `U_bill = U_true`, so the charge is `P(U_true) = C(r)`. For a
completed request `V(r) = C(r)`, hence `N(r) = V(r)` and INTEGRITY holds with equality.
(M2-b) rules out a pathological pricing function under which reporting *more* usage could
reduce the bill, which would let an attacker profit even under server-side counting.

### The insufficiency result (this is the point)

Computing `U_true` is **not** sufficient. Let `A` be an architecture that computes
`U_true` correctly, records it, and bills `P(U_decl)` where `U_decl` is client-supplied.
`A` satisfies "the server recounts" but violates (M2-a), and

```
Leak(r) = P(U_true) − P(T(U_true)) > 0   whenever the attacker's transformation T
                                          lowers a category the pricing basis reads.
```

Measured: `client_logged` computes and stores a correct recount and still leaks
**0.583** (main sweep) / **0.595** (ablation, different prompt) — statistically
indistinguishable from `client`, which never recounts. The distinguishing property is
*authority*, not *computation*.

### Corollary (basis dependence)

Because leakage is `P(U_true) − P(T(U_true))`, the exploitable set of transformations is
determined by which components of `U` the pricing basis reads. Under category pricing a
transformation that alters only the declared *total* is inert; under flat-total pricing
it is maximal (measured 0.000 vs 0.741). This is a property of `P`, not of the attacker.

### Implementation-specific
- *What "the server computes it" means.* Our server recomputes usage from the prompt it
  received and the output it generated. A deployment that recomputes from a
  client-supplied echo of the prompt would satisfy the letter of (M2-a) and violate its
  intent.
- *Trusted upstream.* The `upstream` architecture satisfies (M2-a) **only because the
  provider is honest by assumption**. Under a dishonest-provider model (CoIn, Token
  Inflation) it would not, and that is explicitly out of scope.

---

## 3. B0 — synchronization (known baseline)

### Sufficient condition

> **(B0-a) Atomic authorize-and-decrement.** The check `balance ≥ cost` and the
> decrement `balance ← balance − cost` occur as one operation that is atomic with
> respect to competing transactions on the same account.

### Argument (within the model)

If (B0-a) holds, the authorize/decrement pairs on an account are totally ordered. By
induction over that order, each successful authorization observes the balance left by all
previously committed decrements, so no two requests can be authorized against the same
funds and `Σ N(rᵢ) = Σ V(rᵢ)`. Violating (B0-a) permits two transactions to read the same
pre-decrement balance and both commit, losing one decrement — the classic lost update.

**Necessity of ≥2 concurrency.** With a single in-flight transaction per account the
operations are trivially ordered, so (B0-a) is satisfied vacuously. This is why B0 leaks
nothing at concurrency 1 and leakage grows linearly thereafter (measured slope 0.099 per
additional concurrent request, R² = 1.0000) — and why B0, unlike M1/M2, is a
*concurrency-created* defect.

### Implementation-specific
- *How atomicity is obtained.* The mutable backend uses a conditional
  `UPDATE ... WHERE balance >= :cost`; the append-only backend serializes on an anchor
  row before appending. Both satisfy (B0-a); neither is required by the model. This is
  precisely what the second-backend experiment tests.
- *Isolation level.* Our results are under PostgreSQL `READ COMMITTED`. (B0-a) is a
  statement about the *operation*, not the isolation level; a system could also obtain it
  with `SERIALIZABLE` plus retry.

---

## 4. What the experiments can and cannot establish

| claim | status |
|---|---|
| The stated conditions are sufficient **within the model** | argued above, deductively |
| Removing a condition produces a violation **in our implementation** | measured (ablation) |
| The conditions hold across process/node topologies | measured (topology experiments) |
| The conditions are independent of balance-storage architecture | measured (backend experiments) |
| The conditions are sufficient in **any** deployed system | **not established** — out of scope |
| No other sufficient condition set exists | **not claimed** |

The honest summary: the sufficiency arguments are model-level and deductive; the
*necessity* evidence is empirical and specific to the evaluated architectures. We claim
no universal theorem.
