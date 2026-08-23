# Journal readiness report

*Regenerated after the journal-upgrade round (formal verification, real serving stack,
asynchronous accounting). Ratings are argued from artifact evidence, not asserted. Where a
dimension is weak, the rating says so — a report that scored everything highly would be
worth nothing.*

**Baseline for this round:** `audit/journal_upgrade_baseline.md` (commit `a66ade9`).

**Final consistency pass (this update).** An adversarial read of `paper/main_ieee.tex`
looking specifically for a B0/concurrency contradiction — the abstract's "B0 is not about
concurrency" against the results section's "leaks only when at least two requests
overlap." The manuscript was already internally consistent: the results section states the
baseline's empirical trigger, the figure caption and Section~X.F ("B0 revisited") state the
general condition, and the sufficiency section, discussion and conclusion all agree with
each other. No wording changed there. What did change: the index terms carried "LLM
security" as the first keyword, which reads as model-security scope rather than
infrastructure-security scope; it was replaced (see the venue note below). Independent
recomputation, the M2 spec-derived checker, TLC, the regression suites and cross-validation
were all re-run and remain at zero unexplained discrepancies; the claim matrix is unchanged
at 44 claims, 0 unsupported.

---

## 1. What changed in this round

| addition | evidence |
|---|---|
| **Machine-checked formal model** | `formal/TokenAccounting.tla` + TLC: 10 configurations × 4 invariants = 40 runs, **27,526 distinct states**, deterministic, **0 disagreements** with pre-declared expectations |
| **Real third-party serving stack** | `llama.cpp llama-server` + SmolLM2-135M-Instruct: 12 M1 + 48 M2 cells, **0 safety disagreements**; 5 generator-dependent cells reported |
| **Asynchronous accounting family** | event queue + continuously running worker, delays 0–500 ms, 5 injected pipeline faults |
| **Cache-split nondeterminism** | honest cost of a byte-identical request varies **22–32%** with server cache state (3/3 prompts) |
| **Claim matrix upgrade** | `MODEL-CHECKED` class added; **44 claims, 0 UNSUPPORTED** |

Two conclusions changed as a result, both from adversarial pressure rather than from
polishing:

1. **B0's sufficiency condition was too weak.** Under asynchronous settlement, over-serving
   appears with *strictly sequential* arrivals 20 ms apart once the reconciliation delay
   reaches 100 ms — 4 requests over a 2-request budget at 500 ms, balance negative. An
   atomic guarded decrement provides nothing if it lands after the next authorization. The
   condition now requires atomicity **on the path that authorizes**.
2. **M1 orthogonality is now exhaustive rather than exemplary.** All four combinations of
   (reservation, abort-safe finalization) are model-checked; each single control leaves one
   of solvency/integrity broken.

---

## 2. Ratings

### Research problem — **8/10**
A real security boundary with a clean threat model (honest provider, dishonest client) that
prior work genuinely does not occupy: provider over-charge, victim bill inflation, and
intermediary provenance are all cited and all distinct. Loses points because the problem is
a *quadrant completion* rather than a new class of threat, and because its practical
severity depends on deployment choices we cannot observe in the wild.

### Conceptual contribution — **8/10**
Two crisp architectural distinctions that survive scrutiny and are not in the prior art:
**reservation ≠ accounting finality** and **usage computation ≠ usage authority**. Both are
actionable design rules, both are model-checked, and the second contradicts the obvious
advice ("just recount server-side") with a 58.3% leak from an architecture that recounts
correctly. Not a 9 because the underlying mechanisms are known and the framing is
systematization.

### Formal rigor — **6/10**
Real model checking, not prose: 40 exhaustive runs, expectations declared in advance, and a
model that was *wrong first* and rejected by TLC until corrected. Counterexamples map
step-for-step onto measured failures. But: no refinement proof to the implementation, a
finite model (2–3 requests, unit pricing), safety only, no liveness, no parameterized
result, and the asynchronous family lies outside the model. Honest ceiling for a
security-venue paper rather than a formal-methods one.

### Empirical rigor — **9/10**
7,200+ per-request records with three fail-closed integrity gates, gates themselves
validated by fault injection (12/12) and metamorphic checks (22/22), independent
recomputation with **zero** project imports (0 discrepancies), a specification-derived
independent M2 model (0 mismatches), and cross-validation across 60 cells. Statistical
treatment separates empirical, analytic, and confirmatory results. The withdrawn
detectability claim demonstrates the process removes claims as well as adding them.

### Architectural generality — **8/10**
Three execution topologies (96 cells, 0 mismatches), three accounting families
(mutable row, append-only ledger, asynchronous event pipeline), and a third-party serving
stack. The backend-parity claim is stated at its defensible strength (8 genuine cells, not
17). Held back by: one host, no sharded credit state, B0's storage independence untested,
and injected rather than observed reconciliation delays.

### Economic analysis — **7/10**
Leakage efficiency is price-invariant under uniform scaling and the effect of *structural*
repricing is characterized: which manipulation pays off is a property of the billing
function (0.000 under category pricing vs 0.741 under flat-total for the same attack).
Attacker knowledge is graded K0/K1/K2 with the headline attack shown K0-feasible. The
cache-split result is a genuinely new economic observation about LLM metering. No
revenue-impact model — deliberately, since any such number would require an invented
attacker population.

### External validity — **7/10**
Substantially improved this round: a serving stack we did not write, with real tokenization,
real streaming, and real usage records, over 60 cells with 0 safety disagreements. The paper
also reports where effectiveness *does* move (5 cells) rather than only where it does not.
Ceiling is set by what is ethically and practically off-limits: no commercial provider, no
production billing API, one small model on CPU.

### Reproducibility — **9/10**
Everything regenerates from raw data; figures and tables are generated, never hand-edited;
provenance manifest with 108 artifact hashes plus the PDF hash; the formal checker is
deterministic by construction (`-workers 1`, chosen after observing state-count drift under
parallel workers). Docker Compose plus a pip-installable JDK means no manual toolchain
setup. Not a 10 because a full clean-room reproduction of the *new* material has not yet
been run end-to-end from wiped volumes.

### Artifact quality — **9/10**
Testbed, attack harness, three defense families, formal model, independent audit code, and
a reviewer-runnable TLA+ configuration set. Failures are documented in place (the wrong
first TLA+ model, the manual-drain harness that measured its own sleep, the classifier that
used outcome value instead of code path). A reader can find every retraction.

### Novelty as primitive — **3/10**
Low, and stated as such throughout. No new attack primitive; each mechanism is individually
known; two candidate classes were killed in the novelty audit and a third at a decision
gate. The paper makes no priority claim.

### Novelty as systematization — **8/10**
The unifying invariant, the three-dimensional decomposition, the two orthogonality results,
the pricing-function characterization, and the cache-split observation together constitute a
contribution that is not assembled anywhere in the cited literature.

---

## 3. Venue assessment

Acceptance is not assumed anywhere below. Each entry states what that venue would attack.

### Computers & Security — **strong candidate**
Fits the venue's profile precisely: systematization plus measurement plus defense
evaluation, with a reproducible artifact.
**What they will attack:** novelty as primitive (Reviewer A above), and whether a
single-host testbed with a 135M model supports conclusions about production metering. Both
are answerable from the artifact — the topology/backend/serving-stack matrix exists — but
expect a revision request asking for sharper separation between what was measured and what
is argued. The three-label evidence discipline was built for exactly that question.

**Scope positioning, stated explicitly because it matters for desk review.** Some security
venues currently exclude papers whose principal subject is the security *of* AI/ML models
themselves (adversarial robustness, model privacy, prompt injection). This paper is not
that. The LLM is the workload that makes the metering boundary interesting; the object of
study throughout is accounting infrastructure — authorization, reservation, debit,
reconciliation, billing authority. Nothing in the contribution touches model behavior,
robustness, or output safety. The index terms and abstract were checked against this
distinction during the final consistency pass, and the one keyword ("LLM security") that
could have read as model-security scope was replaced with terms naming the actual subject
(usage metering, quota enforcement, accounting reconciliation).

### ACM TOPS (Transactions on Privacy and Security) — **plausible, higher novelty/formal risk**
TOPS publishes rigorous systems-security work and would engage seriously with the formal
verification and the cross-architecture measurement. **What they will attack:** the same
primitive-novelty objection as everywhere else, likely pressed harder than at Computers &
Security, and the same formal gap as TDSC — no refinement proof, a finite model. TOPS
reviewers tend to expect either stronger novelty or stronger formal guarantees than this
paper claims; it is a plausible target, not a comfortable one, and the honest expectation is
a harder review than Computers & Security with a similar or lower acceptance probability.

### IEEE TDSC — **submittable, likely major revision**
The formal work raises this from "not ready" to "arguable".
**What they will attack:** the absence of a refinement proof, the finite model, and
safety-only checking. A TDSC reviewer may reasonably ask for a parameterized argument or a
mechanized link between specification and implementation. Neither exists, and the paper says
so rather than obscuring it. Realistic outcome: major revision with a demand for stronger
formal ties, or rejection on formal depth.

### ETTIS / comparable Springer conference — **ready**
Comfortably above bar on empirical rigor and artifact quality.
**What they will attack:** relatively little; the more likely risk is that the contribution
reads as too incremental for a novelty-seeking PC member.

### INDICON — **ready**
Well above the typical bar for empirical depth and reproducibility.
**What they will attack:** scope framing; the paper may read as narrow for a broad-audience
venue, and the formal section will be skimmed.

### Top-tier security conference (S&P / USENIX / CCS / NDSS) — **not recommended**
**What they will attack:** primitive novelty, decisively. These venues reward new attack
classes or new defenses with strong guarantees. This paper has neither and does not pretend
to. A submission would likely be rejected on "known mechanisms, systematized" regardless of
execution quality.

---

## 4. Remaining limitations (complete list)

1. No refinement proof from the TLA+ specification to the implementation.
2. Formal model is finite (2–3 requests, 2 chunks, unit pricing) and safety-only.
3. Asynchronous accounting is measured but **not** formally modelled.
4. Reconciliation delays are injected, not observed in production.
5. B0's independence from the storage backend remains untested (the frozen debit module
   never routes through the abstraction).
6. One host; no sharded or partitioned credit state; no consensus failures.
7. One real serving stack, one small model, one prompt family.
8. The cache-split nondeterminism is a property of this stack's prefix cache; no claim is
   made about hosted APIs.
9. Pricing tiers are synthetic; no revenue-impact model.
10. Detectability is withdrawn entirely — the artifact makes no claim in that dimension.
11. Attack effectiveness is generator-dependent (5 of 48 M2 cells flipped); only the
    architectural conclusion is claimed to transfer.
12. No commercial provider was tested, by explicit ethical constraint.

---

## 5. Verdict

> ## JOURNAL-CANDIDATE

Not *journal-ready* in the unqualified sense, and the gap is specific and nameable rather
than vague: **there is no mechanized link between the specification and the implementation**,
and the asynchronous family — which produced the round's sharpest finding — sits outside the
formal model. A reviewer at a formal-methods-leaning venue can press on exactly that.

Everything else that a Q1 reviewer would normally reject a paper for has been closed with
evidence rather than argument. The methodology is not shallow (formal + empirical +
independent recomputation), not circular (the one circular claim was found by our own audit
and withdrawn), not single-architecture (three topologies, three accounting families, two
generators), and not weakly formalized (40 exhaustive model-checking runs against
expectations fixed in advance).

For *Computers & Security* the paper is a strong candidate now. For TDSC it is submittable
with a foreseeable demand for deeper formal ties. The honest summary is that this round
converted the largest reviewer objection — "single-architecture, synchronous, your own
generator" — into three concrete pieces of evidence, and in the process changed two of the
paper's own conclusions.
