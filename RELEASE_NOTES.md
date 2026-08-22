# Release notes — v1.0.0

**Token-Accounting Integrity in LLM Metering** — frozen journal-submission artifact.
Released 2026-08-22.

---

## What this is

A study of client-side under-payment in LLM metering under an honest-provider threat model,
with a reproducible testbed, an attack harness, three defense families, a machine-checked
formal model, and the complete measurement corpus.

The unifying property is one inequality over a request lifecycle:

> **V(r) ≤ N(r)** — delivered value must not exceed the net committed debit.

Three architectural dimensions can violate it, at three different points of the lifecycle:
**state synchronization (B0)**, **commitment timing (M1)**, and **usage authority (M2)**.

## Major contributions

1. **An accounting model** connecting execution, delivery, authorization, reservation,
   debit, reconciliation and refund, with an integrity property that admits legitimate
   refunds — `F(r) ≤ Res(r) − V(r)`.
2. **A taxonomy** of three experimentally distinguishable dimensions, with the known,
   systematized and defensive boundaries stated explicitly.
3. **A machine-checked formalization** in TLA+, checked exhaustively with TLC.
4. **A cross-architecture measurement study** over three execution topologies, three
   accounting families and two independent inference data planes.
5. **Defense sufficiency conditions** with their integrity and performance cost.

**No new attack primitive is claimed.** Each mechanism is individually known; the
contribution is their unification, formalization, measurement and defense analysis.

## Validated experiments

| experiment | scale | headline |
|---|---|---|
| B0 synchronization | 7 concurrency levels × 30 repetitions, 420 trials | Leakage grows linearly with concurrency (0.099/request, R² = 1.0000); hardened path leaks $0 |
| M1 commitment timing | 2,400 records | Leakage tracks abort position, collapses to zero at completion; reservation and abort-safe finalization are orthogonal |
| M2 usage authority | 4,800 records | A correct-but-unauthoritative recount leaks **58.3 %**; server-authoritative billing leaks **0.000** across all 8 manipulations |
| Topology sweep | 96 cells | 0 mismatches across single-worker, 4-worker and 2-container deployments |
| Backend comparison | 17 cells compared, **8 genuine** | Mutable balance row vs append-only derived ledger; 8 genuine cases agreed, none disagreed |
| Real serving stack | 60 cells | 0 safety disagreements; 5 cells changed attack effectiveness |
| Asynchronous accounting | 5 delays × 5 fault modes | Delayed, not lossy; a lost event leaks permanently |
| Tokenizer benchmarks | 100 exact-length cells | 2.9–3.6× spread across engines; cost linear in input length |
| Local real model | SmolLM2-135M, CPU | Recount is well under 0.1 % of end-to-end inference time |

## Formal verification

TLA+ / TLC 2.19. **10 configurations × 4 invariants = 40 exhaustive runs, 27,526 distinct
states, 0 disagreements** with expectations declared before the runs. Deterministic under
`-workers 1`.

The M1 orthogonality result is established over **all four** combinations of (reservation,
abort-safe finalization), not just the two the implementation ships.

The first specification was wrong and TLC caught it: it treated a reservation as a hold
rather than a committed debit, and rejected the *safe* configurations until the settlement
semantics were corrected. Recorded, not erased.

## Architecture validation

Three execution topologies, three accounting families (mutable row, append-only ledger,
asynchronous event pipeline), two inference data planes (deterministic generator and
third-party serving code).

## Real serving validation

`llama.cpp` serving SmolLM2-135M-Instruct on CPU. Same gateway, same architectures, same
accounting; only the token source changed. Every architectural conclusion held.

It also surfaced something the deterministic setting cannot show: prefix-cache reporting
makes the **honest** cost of a byte-identical request vary by **22–32 %**. The provider's
own number is not reproducible, a client cannot verify its own bill even in principle, and
an over-declared cached count carries genuine plausible deniability.

## Asynchronous accounting

The result that changed a conclusion. With **strictly sequential arrivals 20 ms apart** —
no concurrency at all — over-serving appears once the reconciliation delay reaches 100 ms
and reaches four requests over a two-request budget at 500 ms, with the balance negative.

An atomic guarded decrement, the entire B0 defense, provides nothing if it lands after the
next authorization has already read the balance. The condition is now:

> Authorization must be atomically coupled to economic commitment on the path that
> authorizes service.

## Withdrawn claims

- **Detectability (D0–D3) — withdrawn entirely.** Our own audit found the implementation
  *assigned* the level from static architecture metadata rather than measuring it. An
  evidence-only reclassification contradicted the published distinction: 2,200 records
  carrying the "invisible" label are reconcilable or prevented on the evidence, and no
  record qualifies as invisible at all. No weaker version is reported.
- **"17/17 backends identical" — restated as 8.** Only eight of seventeen cells genuinely
  exercised both backends; five agree analytically and four are B0 cells that never route
  through the backend abstraction.
- **M2 concurrency invariance as an empirical finding — reclassified as analytic.** It
  follows from the billing function being a pure per-request computation; the sweep confirms
  rather than discovers it.
- **M3 — killed at a decision gate.** Two further candidate classes were killed in the
  novelty audit.

## Citation corrections

- **`CVE-2026-31873` removed.** It was cited as a Tyk API Gateway quota race. Both MITRE
  CVE Services and NVD show the identifier belongs to an unrelated advisory. A third-party
  blog asserted the Tyk attribution; the registries were treated as authoritative. The
  origin of the error is preserved as a withdrawn source in `paper/phase1_sources.json`.
- **Kettle 2023 title corrected** to *"Smashing the state machine: the true potential of web
  race conditions"*.
- An unattributed "industry metering guidance" entry with no retrievable source was removed.

All 26 references in the manuscript were retrieved from an authoritative source before being
cited. None came from a search-result snippet.

## Known limitations

No mechanized refinement proof from specification to implementation. Finite formal model
(2–3 requests, unit pricing, safety only). The asynchronous family is measured but not
formally modelled. Reconciliation delays are injected, not observed. B0's storage
independence is untested. One physical host, one local serving stack, one small model. No
commercial-provider validation, by explicit ethical constraint. Pricing tiers are synthetic
and there is no revenue-impact model.

## Ethics

All experiments ran against the local testbed. No third-party, live or production system
was probed. No credentials, real user data or production billing APIs were used. Every
attack is paired with a defense.

## Status

**Journal submission-ready.** Not accepted, not peer-reviewed, no DOI minted.
