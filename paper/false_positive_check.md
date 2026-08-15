# False-Positive Check — Does It Already Exist Under Another Name?

**Date:** 2026-08-15. Purpose: a reviewer will search these exact concepts even
though our terminology differs. For each, we record whether the mechanism already
exists, under what name, in which (opened) source, and the consequence for our
novelty. Verdicts: **EXISTS** (documented, hurts novelty), **PARTIAL** (adjacent /
different goal), **NOT FOUND** (targeted search surfaced nothing).

| # | Concept a reviewer will search | Status | Where it already lives | Consequence |
|---|---|---|---|---|
| 1 | Streaming billing race | **EXISTS** | new-api #5235; Cancellation Tax; Kettle "race the finalization request" | Class 1 mechanism is documented in the wild → contribution must be systematization + measurement + defense, not discovery |
| 2 | Usage-record finalization after disconnect | **EXISTS** | new-api #5235 (refund on missing final-usage block); Token Inflation ("partial usage during cancellation") | Same as #1 — directly names Class 1 |
| 3 | Client-controlled token count | **PARTIAL** | CWE-807/602 (generic); Token Inflation measures the *provider* over-report side | The client-underpay mirror is unstudied, but the primitive is generic → Class 2 is a reframe, not new |
| 4 | Token-count mismatch exploitation | **PARTIAL** | Token-count discrepancy reports (AWS/Google/OpenAI/litellm) are all *honest* mismatches; Token Inflation exploits ambiguity for provider over-charge | No client-side exploitation study found; tokenization ambiguity as an *evasion* margin is open |
| 5 | Replaying inference requests without new billing | **EXISTS (as a feature)** | Idempotency keys (Stripe/IETF); semantic-cache gateways return cached response, 0 tokens | This is *intended* behavior; framing it as an attack requires the entitlement/authorization angle → weak (Class 3) |
| 6 | Cache hit without quota charge | **EXISTS (as a feature)** | Semantic caching writeups: "no LLM call is made and no tokens are burned"; Auditing Prompt Caching (privacy) | Cache-hit-bills-zero is a known gateway property; billing-evasion framing unstudied but thin → Class 3 |
| 7 | Retry without duplicate billing | **EXISTS (solved)** | Idempotency-key standard (Stripe, IETF draft) | Solved problem; not a research gap |
| 8 | Quota exhaustion bypass through concurrency | **EXISTS** | CVE-2026-31873 (Tyk, non-atomic GET+DECR); Kettle single-packet | This is Class 6 / (killed) Class 4 — a real recent CVE. Strong prior art |
| 9 | Plan / entitlement tampering | **EXISTS** | OWASP API3:2023 (BOPLA / mass assignment); OWASP API1:2023 (BOLA) | This is Class 5 — textbook API auth. Killed |
| 10 | Inference credit rollback / reconciliation bug | **EXISTS** | new-api #5235 (refund-all on missing usage); Medusa refund-success-on-partial-failure; "double-dip" cashback (arXiv 2604.16427); Claude Code July-17 billing incident | The refund/reconciliation failure is the *same* mechanism as Class 1's stream-abort; generic refund-abuse is well known |

## Key takeaways for the framing

1. **Class 1 is the most exposed to a "this already exists" rejection** — new-api #5235
   is a near-perfect instance. But it is a single, unmeasured bug report; nobody has
   (a) modelled it as an adversarial client class, (b) measured `$-leak` vs abort
   timing across metering architectures, or (c) evaluated the defense (pre-authorize /
   commit-before-inference) with overhead numbers. That gap is our contribution.
2. **Classes 4 and 5 are fully covered** by, respectively, the quota-decrement race
   (Tyk CVE / Kettle / our own Class 6) and OWASP API1/API3. They must be killed;
   keeping them invites an easy desk-reject.
3. **Class 3 is a feature, not obviously an attack.** Caching and idempotency are
   deliberately built to return value without recompute/recharge. The only defensible
   research angle is *authorization of cache access* and *inference-vs-billing
   idempotency*, which overlaps Class 5 and the idempotency literature — hence low
   confidence.
4. **Class 2's mirror is genuinely open** — the provider over-report margin under
   tokenization ambiguity is measured (50.85%, Token Inflation), but the symmetric
   *client under-report* margin, and whether a server-side recount fully closes it, is
   not. This is the cleanest measurable LLM-specific hook among the survivors.
5. A reviewer searching all ten terms will find prior art for **8 of 10**. Our defense
   is not "these are unknown" but "these are scattered across bug trackers, one ICML
   privacy paper, generic CWEs, and payment-idempotency folklore, and have never been
   unified into a client-side LLM-billing-evasion taxonomy with a reproducible testbed,
   `$-leak`/ASR measurement, and server-side defense evaluation." That bounded claim
   must appear verbatim in the paper's related-work section.
