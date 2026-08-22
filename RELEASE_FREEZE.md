# Release freeze — v1.0.0

> ## RESEARCH FROZEN — NO SCIENTIFIC CHANGES AFTER THIS RELEASE
>
> Every experimental result, formal-checking outcome and reported number in this release is
> final. Later commits may correct documentation, packaging or typography. Any change that
> would alter a measured value, a claim, or an evidence label requires a new version and a
> new audit, not an amendment to this one.

---

## Exact state

| field | value |
|---|---|
| Branch | `master` |
| Freeze commit | recorded in `GITHUB_RELEASE_REPORT.md` at tag time |
| Release tag | `v1.0.0` |
| Freeze date | 2026-08-22 |
| Predecessor | `4027e23` — IEEE journal manuscript |

## Research status

Complete at the stated scope. Three architectural dimensions of one accounting boundary
studied, measured, formally checked and defended:

- **B0 — state synchronization.** Known baseline, not a contribution. Used to validate the
  measurement rig. Its conclusion was **revised** during the journal round: the condition is
  not about concurrency but about coupling. See below.
- **M1 — commitment timing.** Reservation and abort-safe finalization are **orthogonal**
  controls: reservation secures solvency, abort-safe finalization secures accounting
  integrity, and neither substitutes for the other. Established over all four combinations
  by exhaustive model checking, and measured on the diagonal.
- **M2 — usage authority.** Computing usage correctly is not the same as billing from it.
  An architecture that recounts accurately, stores the result and still bills the
  client-declared number leaks **58.3 %** of delivered value in the controlled setting and
  **69.0 %** against a real serving stack. Server-authoritative billing removed the observed
  leakage across all eight manipulations. The headline manipulation is **K0-feasible** —
  constructible from what the client itself can observe.

**M3 was killed at a decision gate and is not implemented.** Two of the original five
candidate attack classes were killed in the novelty audit.

### The B0 revision

The paper no longer claims B0 requires concurrency. Under asynchronous settlement with
**strictly sequential arrivals 20 ms apart**, over-serving appears once the reconciliation
delay reaches 100 ms and reaches four requests over a two-request budget at 500 ms, with
the balance driven negative. The sufficient condition is therefore stated as:

> The authorization decision must be atomically coupled to the economic commitment on the
> path that authorizes service.

Concurrency is one way to break that coupling; delayed settlement is another and requires
no concurrency at all. This is strictly more general than the original framing, which was
too weak rather than wrong.

## Manuscript status

| item | path | status |
|---|---|---|
| **IEEE journal manuscript (submit this)** | `paper/main_ieee.tex` | final |
| **IEEE PDF** | `paper/main_ieee.pdf` | final — 13 pages, 26 references, 0 overfull boxes, 0 undefined references or citations, 0 blank pages |
| Pre-IEEE manuscript | `paper/main.tex` / `paper/main.pdf` | superseded; retained for provenance. Its incorrect CVE citation was removed and it was recompiled, so no wrong citation stands anywhere in the repository. |

Author: **Hardik**, enrollment **03517713524**.

## Formal verification status

TLA+ specification `formal/TokenAccounting.tla`, checked with TLC 2.19.

| metric | value |
|---|---|
| Configurations × invariants | 10 × 4 = **40 exhaustive runs** |
| Distinct states | **27,526** (deterministic; `-workers 1`) |
| Disagreements with pre-declared expectations | **0** |

Expectations are declared in `formal/check.py` *before* the runs and the script exits
non-zero on any disagreement. The first specification was **wrong** — it treated a
reservation as a hold rather than a committed debit, and TLC rejected the *safe*
configurations until the settlement semantics were corrected. That failure is recorded in
`formal/README.md` and in the paper rather than erased.

**There is no mechanized refinement proof from the specification to the implementation.**
This is stated in the paper and remains the largest formal gap.

## Real-serving validation status

`llama.cpp` server running SmolLM2-135M-Instruct on CPU — third-party serving code, real
subword tokenization, real SSE streaming, server-produced usage records.

- 12 M1 cells + 48 M2 cells, **0 safety disagreements**.
- 5 of 48 M2 cells changed attack *effectiveness*; reported, not averaged away.
- The honest cost of a **byte-identical request varies 22–32 %** with prefix-cache state, so
  the provider's own authoritative number is not reproducible and a client cannot verify its
  own bill even in principle.

Local, controlled, one stack, one small model. **Not commercial-provider validation**, and
no claim about hosted APIs is made.

## Asynchronous validation status

Third accounting family: event queue plus a continuously running worker with a controlled
reconciliation delay.

- Honest pipeline is **delayed, not lossy**: exposure window tracks the delay
  (0/10/50/100/500 ms → 14.0/14.9/54.3/103.7/504.1 ms) and the leak reconciles to zero.
- Duplicates suppressed idempotently (25/25); a **lost event leaks permanently**.
- Produced the B0 revision above.

Measured but **not formally modelled** — the TLA+ specification assumes strongly consistent
accounting state.

## Independent audit status

All re-run at freeze, after every editorial change:

| check | result |
|---|---|
| `audit/recompute_all.py` (zero project imports) | **0 discrepancies** |
| `audit/m2_independent_check.py` (specification-derived truth) | **0 mismatches** |
| `formal/check.py` | 40/40, **0 disagreements** |
| `experiments/regression_class6.py` | **19/19** |
| `experiments/regression_m.py` | **16/16** |
| `experiments/metamorphic_checks.py` | **22/22** |
| `experiments/run_cross_validation.py` | all implementations agree |
| Claim-evidence matrix | 44 claims, **0 unsupported** |

An adversarial integrity audit raised six findings (F1–F6) and all six were closed: one by
**withdrawal** (detectability), two by **scope restatement**, one by **re-implementation**,
one by **disclosure**, one by **re-measurement**. The withdrawn detectability claim stays
withdrawn; D0–D3 appears nowhere in the IEEE manuscript as a claim.

## References

26 entries in the IEEE manuscript, 47 in-text citations, 0 undefined, 0 uncited, 0
duplicates. Every entry was retrieved from an authoritative source — arXiv, Crossref DOI,
MITRE CWE, the GitHub REST API, WHATWG, OWASP — before being cited.

**Two citation defects were found and corrected during this pass:**

1. `CVE-2026-31873` was cited as a Tyk API Gateway quota race. Both MITRE CVE Services and
   NVD show it belongs to an unrelated advisory. The citation is removed repository-wide;
   the origin of the error is recorded in `paper/phase1_sources.json` as a withdrawn source.
2. Kettle's 2023 PortSwigger research was cited under the wrong title and is corrected to
   *"Smashing the state machine: the true potential of web race conditions"*.

## Known limitations (complete)

1. No mechanized refinement proof from TLA+ specification to implementation.
2. Formal model is finite (2–3 requests, 2 value chunks, unit pricing) and safety-only; no
   liveness, no parameterized result.
3. The asynchronous accounting family is measured but **not** formally modelled.
4. Reconciliation delays are injected, not observed in production; the async result is
   conditional and stated as such.
5. B0's independence from the storage backend is **untested** — the frozen debit module
   never routes through the backend abstraction.
6. One physical host; no sharded or partitioned credit state; no consensus failures.
7. One local serving stack, one small model on CPU, one prompt family.
8. Cache-split nondeterminism is a property of this stack's prefix cache; no claim about
   hosted APIs.
9. Pricing tiers are synthetic; there is deliberately **no revenue-impact model**.
10. Detectability is withdrawn entirely; the artifact makes no claim in that dimension.
11. Attack effectiveness is generator-dependent (5 of 48 M2 cells flipped); only the
    architectural conclusion is claimed to transfer.
12. **No commercial provider was tested**, by explicit ethical constraint.

## What this release is not

Not accepted, not peer-reviewed, not "Q1-ready", and no DOI has been minted. The correct
description is **journal submission-ready**.
