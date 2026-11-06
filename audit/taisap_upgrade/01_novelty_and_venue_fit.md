# Adversarial novelty and venue-fit review

Observed 2026-11-06. Primary literature is indexed in `prior_work_matrix.csv`. Existing
manuscript citations and earlier audits were treated as search leads, not conclusions.

## Finding

No defensible primitive-level novelty claim survives. Non-atomic check/decrement,
reservation, terminal-path settlement, server-side measurement, escrow, and authoritative
state are established ideas. Three public gateway issues directly precede the M1 failure
shape, and the new-api report is particularly close. Recent LLM-billing papers now make
the economic-integrity neighborhood crowded: CoIn, Invisible Tokens, Token Inflation,
Auditing Pay-Per-Token, and the September 2026 PTIA paper all study whether token charges
can be trusted. They mostly reverse the adversary direction, but they remove any credible
claim that LLM billing integrity itself is a new research problem.

What remains potentially publishable is narrower: one falsifiable lifecycle model ties
three placements to different invariant signatures; the M1 two-by-two ablation separates
solvency from per-request accounting integrity; M2 demonstrates that a correct recount is
not a defense unless it is the billing authority; and two bounded models plus controlled
experiments expose exactly where these statements hold. This is a systems-security
evaluation and sufficiency-conditions paper, not a new-attack paper.

The September 2026 PTIA preprint is the most important newly found neighbor. It evaluates
provider-side manipulation across live APIs and therefore has stronger external breadth,
although it assumes a dishonest provider and changes generated output rather than letting
a client corrupt accounting state. The present manuscript must cite and contrast it before
submission. GRIEF and GIFT independently support the claim that serving infrastructure is
a security boundary, but neither studies accounting. Gateway-path provenance is closer to
M2's authority question; it protects against a dishonest intermediary with attestation,
whereas this manuscript assumes an honest provider and tests client-controlled inputs.

## Three reviewer perspectives

### Hostile-editor abstract 1 — primitive novelty

The paper combines known lost-update, escrow, and trusted-input principles in an LLM
testbed. Public gateway issues already document missing usage on disconnect. The formal
models are bounded and do not verify the implementation. Unless the authors lead with the
ablation and invariant separation rather than “new attacks,” the work is incremental.

### Hostile-editor abstract 2 — systems evidence

The testbed is unusually transparent and includes raw data, real tokenization, one external
serving stack, a second host, and failure injection. Yet it uses one small CPU model, one
prompt family, and one physical host pair; only eight backend-sensitive cells genuinely
compare both accounting stores. The evidence establishes realizability, not prevalence or
production generality.

### Hostile-editor abstract 3 — formal methods

TLC checks small finite configurations under simplified pricing and consistency
assumptions. The primary and asynchronous specifications encode different races and no
refinement mapping connects either model to FastAPI/PostgreSQL/Redis. The formal result is
useful as bounded exhaustive ablation evidence, but any wording that says the lifecycle is
“verified” without the bound nearby invites rejection.

## Four likely desk-rejection sentences

1. “The mechanisms are established distributed-systems and input-authority failures, and
   the manuscript does not show enough scientific gain from applying them to LLM billing.”
2. “The external-validity evidence is too narrow for claims about deployed AI-serving
   infrastructure.”
3. “Bounded model checking is presented too prominently relative to the missing
   implementation-refinement argument.”
4. “The paper sits between AI security and accounting systems, without a single primary
   contribution that matches this journal's readership.”

## Required scientific response

The paper should state one identity: **an evidence-backed systems-security study of the
conditions required for accounting integrity and solvency in token-metered streaming
inference**. B0 must stay a calibration baseline. M1/M2 must be framed as controlled
architectural ablations with precedents, not attacks discovered here. “Verified” must
always mean bounded TLC checking at named configurations. A decisive extension should
stress a structural prediction rather than add another venue-facing paragraph.

