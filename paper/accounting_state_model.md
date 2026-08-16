# Accounting State Model and Formal Model

Purpose: demonstrate that B0, M1 and M2 are **architectural** properties of where
synchronization, economic commitment, and usage authority sit in the request
lifecycle — not a collection of unrelated implementation bugs. Each mechanism is
localized to a specific state transition.

---

## 1. Request lifecycle states

A metered inference request `r` moves through:

| state | meaning | value delivered? | economically committed? |
|---|---|---|---|
| `CREATED` | request accepted, nothing done | no | no |
| `AUTHORIZED` | balance/entitlement checked (read of accounting state) | no | no |
| `RESERVED` | an estimated amount is atomically held | no | **yes (provisional)** |
| `EXECUTING` | inference started (prefill) | no | depends |
| `STREAMING` | tokens are being delivered to the client | **yes, incrementally** | depends |
| `ABORTED` | client disconnected mid-stream | **partially** | depends |
| `COMPLETED` | generation finished, full response delivered | **yes, fully** | depends |
| `ACCOUNTED` | a usage record has been formed | yes | not yet final |
| `RECONCILED` | usage compared against an authority; debit adjusted | yes | **yes (final)** |
| `REFUNDED` | a reservation is released back to the balance | yes | **released** |

Two properties matter and are otherwise easy to conflate:

* **Value exposure** begins at the *first delivered token* — i.e. on entry to
  `STREAMING`, not at `COMPLETED`.
* **Economic commitment** is only final at `RECONCILED` (or at a `RESERVED` that is
  never refunded).

The gap between those two points is the **exposure window**, and it is exactly what
M1 exploits.

## 2. Permitted transitions

```
CREATED ──▶ AUTHORIZED ──┬─▶ RESERVED ──▶ EXECUTING ──▶ STREAMING ─┬─▶ COMPLETED ──▶ ACCOUNTED ──▶ RECONCILED
                         │                                          └─▶ ABORTED ────▶ ACCOUNTED ──▶ RECONCILED
                         └─▶ EXECUTING ──▶ STREAMING ─┬─▶ COMPLETED ──▶ ACCOUNTED ──▶ RECONCILED
                                                       └─▶ ABORTED ─────▶ (⚠ may terminate here)
RESERVED ──▶ REFUNDED            (release of a provisional hold)
ACCOUNTED ──▶ REFUNDED           (⚠ refund after value delivery)
```

The upper branch (`AUTHORIZED → RESERVED → …`) is *commit-before-inference*; the lower
branch (`AUTHORIZED → EXECUTING → …`) is *commit-after-delivery*.

## 3. Where each mechanism lives

### B0 — synchronization / state consistency
**Transition:** `AUTHORIZED → RESERVED` (or the equivalent decrement).

**Defect:** the read that produces `AUTHORIZED` and the write that produces
`RESERVED` are **not atomic**. Two concurrent requests both observe the same
pre-decrement balance and both transition to `RESERVED` on the same funds.

Formally, with balance `B`, cost `c`, and concurrent requests `r₁, r₂`:

```
read(r₁) = read(r₂) = B          (stale authorization state)
B ≥ c holds for both             (both authorize)
write(r₁): B := B − c
write(r₂): B := B − c            (from the SAME stale B → one decrement is lost)
⇒ Σ committed_debits = c   while   Σ value_delivered = 2c
```

**Requires ≥2 concurrent transactions.** At concurrency 1 the transition is trivially
serialized and no violation is possible — which is exactly what the B0 control
experiment shows.

### M1 — commitment timing
**Transition:** `STREAMING → ABORTED` and the (missing or reversed) subsequent
`ABORTED → ACCOUNTED → RECONCILED`.

**Defect:** value is delivered during `STREAMING`, but the architecture places final
commitment only on the `COMPLETED` path. A client that forces `ABORTED` therefore
exits the lifecycle with value delivered and no surviving debit. Two variants:

* `post_completion`: `ABORTED` has **no** transition to `ACCOUNTED` — nothing is billed.
* `reserve_refund_on_abort`: `ABORTED → REFUNDED` releases the *entire* reservation —
  economically identical to never billing.

```
delivered(r) = k tokens (k ≥ 1)            during STREAMING
NetCommittedDebit(r) = 0                   after ABORTED
⇒ Leak(r) = value(k) > 0
```

**Independent of concurrency**, because the defect is in the per-request transition
graph, not in a shared resource. This is why the M1 concurrency sweep is flat.

### M2 — usage authority
**Transition:** `ACCOUNTED → RECONCILED`.

**Defect:** the usage vector `U` used to compute the debit originates from (or can be
influenced by) the client, and no authoritative recount contradicts it. The state
machine is *correct*; the **data** flowing through the `ACCOUNTED` state is not
authoritative.

```
U_true = server-observed usage
U_decl = client-declared usage,  U_decl = T(U_true) for attacker transformation T
billed = P(U_decl)   instead of   P(U_true)
⇒ Leak(r) = P(U_true) − P(T(U_true))     whenever P∘T < P
```

Again **independent of concurrency**: authority is a per-request data-provenance
property.

## 4. The structural distinction (the paper's key architectural claim)

| mechanism | defective element | needs concurrency? | fixed by |
|---|---|---|---|
| B0 | *transition atomicity* (`AUTHORIZED→RESERVED`) | **yes** (≥2) | atomic compare-and-decrement |
| M1 | *transition graph* (abort path lacks final commit) | no | commit before/independently of client-controlled exit |
| M2 | *data authority* at `ACCOUNTED` | no | server-authoritative recount |

This is why the empirical result — B0 leakage scales with concurrency while M1/M2
per-request leakage is concurrency-invariant — is not an accident of our
implementation: it follows from *which* element of the state machine is defective.

---

## 5. Formal accounting model (Phase F)

### 5.1 Definitions

For a request `r`:

| symbol | definition |
|---|---|
| `U_true(r)` | the true usage vector actually produced (input, output, cached, reasoning tokens) |
| `U_bill(r)` | the usage vector the system bills on |
| `P(·)` | the pricing function, `P: usage → money` (exact decimal) |
| `C(r) = P(U_true(r))` | **true inference cost** |
| `V(r)` | **delivered value** — the cost of what the client actually received; `V(r) = P(U_delivered(r))` |
| `Res(r)` | reservation amount held before execution (0 if none) |
| `D(r)` | **committed debit** — the sum of balance decrements attributable to `r` |
| `F(r)` | **refund** applied to `r` |
| `N(r) = D(r) − F(r)` | **net committed debit** |
| `A(r) ∈ {client, upstream, server}` | **usage authority** — who determines `U_bill` |

### 5.2 Leak and integrity

```
Leak(r)      =  V(r) − N(r)
Integrity(r) :  V(r) ≤ N(r)                      ⟺  Leak(r) ≤ 0
```

Because legitimate reconciliation exists (a client that consumes less than the
reservation must be refunded the difference), the invariant is stated as an
inequality on **net** debit, not as an equality on gross debit. A refund is
*legitimate* iff it releases only the unconsumed portion:

```
legitimate_refund(r)  ⟺  F(r) ≤ Res(r) − V(r)
```

`reserve_refund_on_abort` violates exactly this side condition: it applies
`F(r) = Res(r)` while `V(r) > 0`.

### 5.3 System-level conservation (the integrity gate)

For a trial `T` (a set of requests against one account):

```
Σ_{r∈T} N(r)  =  B_initial − B_final
```

This is verified independently of the application's own bookkeeping in every
summarizer (gate G3); any divergence indicates the measurement itself is untrustworthy
and fails the build.

### 5.4 Mechanism-specific property violations

**B0 (stale authorization state → inconsistent debit state).**
```
∃ r₁ ≠ r₂ :  read_state(r₁) = read_state(r₂) = B  ∧  both authorize
⇒ Σ N(rᵢ) < Σ V(rᵢ)
```
Precondition: `|concurrent(r)| ≥ 2`. Defense: make `authorize ∧ decrement` a single
serialized transition (`UPDATE … WHERE balance ≥ cost`), so
`read_state(r₁) ≠ read_state(r₂)`.

**M1 (delivery before final commitment).**
```
∃ state s ∈ {STREAMING, ABORTED} :  V(r) > 0  ∧  final_commit(r) has not occurred
∧ the transition out of s does not lead to RECONCILED with N(r) ≥ V(r)
⇒ Leak(r) = V(r) > 0
```
Defense: either commit before entering `EXECUTING` (`pre_debit`), or guarantee that
**every** exit path — including `ABORTED` — reaches `RECONCILED` with
`N(r) ≥ V(r)` (`reserve_reconcile`, implemented with a cancellation-shielded
settlement so client disconnect cannot prevent the transition).

**M2 (non-authoritative usage state).**
```
A(r) = client  ∧  ∃ T attacker-controlled :  U_bill(r) = T(U_true(r))  ∧  P(T(U)) < P(U)
⇒ Leak(r) = P(U_true) − P(T(U_true)) > 0
```
Defense: set `A(r) = server` — recompute `U_bill` from server-observed state and bill
`P(U_true)` regardless of what the client declared.

### 5.5 Sufficiency (what the ablation tests)

The claim we test empirically in the ablation is not "the defenses work" but:

```
B0:  atomicity of (authorize ∧ decrement)            is sufficient
M1:  reservation ∧ abort-inclusive finalization      are BOTH required
M2:  server-side recount ∧ using it as billing basis are BOTH required
```

For M1 and M2 the conjunctions are the interesting part: a reservation *without*
abort-inclusive finalization, or a recount *without* using it for billing, should
still leak. `experiments/run_ablation.py` removes one primitive at a time and
measures which conjunct actually closes the violation.
