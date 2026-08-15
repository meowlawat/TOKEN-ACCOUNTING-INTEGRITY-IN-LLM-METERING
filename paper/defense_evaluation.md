# Defense Evaluation

Each mechanism's vulnerable architecture is paired with a server-side enforcement
primitive, implemented behind the same interface and measured on the same rig.

| mechanism | vulnerable architecture(s) | defense (recommended) | residual leak | invariant | overhead |
|---|---|---|---|---|---|
| B0 | non-atomic check+decrement | atomic `UPDATE … WHERE balance>=cost RETURNING` | $0 at all concurrency | holds | none (no extra round trip) |
| M1 | `post_completion`, `reserve_refund_on_abort` | `reserve_reconcile` (settle to delivered in a cancellation-shielded path) | $0 at all abort points | holds | +9.8 ms mean (~few %) |
| M2 | `client`, `client_logged`, `client_total` | `server_recount` (independent tokenizer recount) | $0 for all 8 manipulations | holds | +0.1 ms mean (mock; tokenizer cost not captured) |

## Enforcement primitives

1. **Atomic compare-and-decrement (B0).** One serialized, row-locked statement; the
   check and the debit cannot be split. Affected-row count is the success signal.
2. **Reserve-then-reconcile (M1).** Atomically reserve the estimate *before*
   streaming; settle to tokens actually delivered on completion **or** disconnect,
   refunding only the unused remainder. Settlement is cancellation-shielded so it runs
   even when the client aborts. (Contrast the `reserve_refund_on_abort` anti-pattern,
   which refunds the *whole* reserve on abort — equivalent to no charge.)
3. **Server-authoritative recount (M2).** The server tokenizes the real input/output
   and bills that, ignoring the client-declared usage. `hybrid_reconcile` accepts the
   declared usage but recounts and corrects at request time, adding an explicit
   detection signal (D3) at negligible extra cost in the testbed.

## Safety property, verified per trial

For every served/completed request the summarizers and the control suites assert

```
NetDebit(r) ≥ AuthoritativeCost(r)      and      Σ NetDebit == initial − final.
```

Under every defense, invariant-violation rate = 0 and leakage efficiency = 0 across
the full attack catalogue (M1: 7 abort points × 3 tiers; M2: 8 manipulations × 3
tiers; B0: 7 concurrency levels). Under the vulnerable architectures the violations
are quantified, not hidden.

## Detection as a defense dimension

Defenses are not only leak/no-leak. The M2 spectrum shows that even when live billing
is client-authoritative, *logging a server recount* moves detection from D0 (invisible)
to D1 (reconcilable), and *reconciling at request time* reaches D3 (prevented). An
operator who cannot yet re-architect billing can still gain reconciliation-time
detection cheaply — a practical, deployable intermediate step.

## Cost realism caveat

The most important defense (M2 server recount) is nearly free in the testbed because
the mock tokenizer is trivial. In production the recount is a real tokenizer pass; its
cost is model/tokenizer-dependent and must be measured against a real tokenizer before
claiming production overhead. This is stated as a primary threat to validity.
