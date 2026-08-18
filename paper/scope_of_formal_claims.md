# Scope of formal claims

This document exists so that the formal model cannot be read as claiming more than it
does. It states, explicitly, what `formal/TokenAccounting.tla` does **not** cover.

A reviewer should be able to use this list to check that no claim in the paper depends on
anything below. If one does, that is a defect in the paper, not a matter of
interpretation.

---

## What the model *does* establish

Within a finite configuration — 2 or 3 concurrent requests, unit pricing, a single shared
balance, strongly-consistent state, and a declared-usage transformation that lowers the
billed quantity — TLC exhaustively verified that:

* the stated defense conditions are **sufficient** for accounting integrity, solvency,
  ledger conservation, and the refund bound;
* each unsafe architecture violates a **specific, identified** invariant on **every**
  schedule, not merely on the schedules the harness happened to produce;
* reservation and abort-safe finalization are **orthogonal** — each alone leaves one of
  the two properties broken;
* a correct server-side recount that is **not** the billing basis does not restore
  integrity.

## What the model does **not** cover

### Systems and infrastructure

1. **Any commercial provider implementation.** No claim is made about OpenAI, Anthropic,
   Google, AWS Bedrock, Azure OpenAI, or any hosted gateway. Nothing here was tested
   against a production billing API, by explicit ethical constraint.
2. **Real database semantics.** `balance` is a single variable. PostgreSQL isolation
   levels, MVCC, lock escalation, deadlock retry, and connection-pool behaviour are
   outside the model. The B0 mechanism was *separately* verified against live PostgreSQL
   READ COMMITTED in the empirical work; the model abstracts that to a stale read.
3. **Database corruption, disk failure, or data loss.** State is assumed durable and
   correct once written.
4. **Distributed consensus failures** — partitions, split brain, clock skew, leader
   election, quorum loss. The model has one shared balance and no replication.
5. **Network-layer behaviour** — TCP resets, HTTP/2 stream cancellation semantics,
   proxy buffering, retries generated below the application layer, or the single-packet
   attack technique that makes B0 practically exploitable.
6. **Kernel, hypervisor, or container escape.**
7. **TLS compromise or credential theft.** The client is dishonest but authenticated.
8. **Malicious provider.** The provider is honest throughout. Provider over-charge is a
   different threat model (CoIn, Invisible Tokens, Token Inflation) and is out of scope.
9. **Compromised inference engine.** The model that produces the tokens is assumed to
   report its own output truthfully to the gateway.
10. **Malicious intermediary.** Gateway-path provenance and misrouting (AEX,
    gateway-path provenance) are a third threat model, also out of scope.

### Accounting semantics

11. **Eventual consistency and asynchronous reconciliation anomalies beyond those
    modelled.** The specification assumes accounting state is strongly consistent. The
    asynchronous-accounting architecture studied empirically is *not* covered by the
    formal model, and its results are labelled EMPIRICALLY VERIFIED only.
12. **Multi-category pricing.** The model uses unit pricing (`Cost(u) = u`). The
    input/output/cached/reasoning category structure, and which transformations pay off
    under which pricing basis, are handled analytically in
    `paper/pricing_function_analysis.md` — **FORMALLY ARGUED**, not model-checked.
13. **Tokenizer disagreement.** The model has no notion of tokenization. Real engines
    disagree on token counts by 2.9–3.6×, which is measured empirically and is a source
    of *legitimate* discrepancy the formal model cannot express.
14. **Semantic caching policy** beyond the tested architectures. M3 was killed at the
    decision gate and is not implemented or modelled.
15. **Idempotency and retry accounting.** Duplicate request suppression, idempotency
    keys, and at-least-once delivery of usage events are outside the specification.
16. **Account-level, contractual, or legal billing policy** — credit expiry, minimum
    commitments, negotiated rates, chargebacks, disputes, refund policy as a business
    decision rather than an accounting operation.
17. **Currency, rounding, and floating-point representation.** The model uses integers.
    The implementation uses exact `Decimal` arithmetic on `NUMERIC(18,6)`; the model does
    not check that this is done correctly.

### Method

18. **The implementation is not proven to refine the specification.** There is no
    refinement mapping and no attempt at one. The correspondence between a TLA+ constant
    and a code path in `app/` is an *argument*, documented in
    `paper/formal_empirical_mapping.md`, supported by the fact that the formal and
    empirical outcomes agree case by case. It is not a proof, and the paper does not call
    it one.
19. **The model is finite and small.** 2 and 3 concurrent requests; 2 value chunks per
    request. Exhaustive checking at these sizes does not establish a result for arbitrary
    `n`. No induction or parameterized proof was attempted.
20. **Liveness is not checked.** All four properties are safety invariants. The model
    includes weak fairness so that `Spec` is well-formed, but no temporal property (e.g.
    "every reservation is eventually settled") is verified.
21. **The transformation family is narrow.** M2 is checked against under-declaration of
    the billed quantity. Category-shifting (`inflate_cached`) and hidden-field dropping
    (`drop_reasoning`) are measured empirically and analysed economically, but not
    model-checked — and both require attacker knowledge above K0 in any case.

---

## Consequence for the paper's claims

Every claim in the claim-evidence matrix carries an evidence class. **MODEL-CHECKED**
appears only for properties in the "does establish" list above. Anything touching the
exclusions is labelled **FORMALLY ARGUED**, **EMPIRICALLY VERIFIED**, or
**ANALYTICALLY DERIVED** — never "proved".

If a reviewer finds a claim in the paper that depends on an item in the exclusion list and
is not labelled accordingly, it is an error and should be reported as one.
