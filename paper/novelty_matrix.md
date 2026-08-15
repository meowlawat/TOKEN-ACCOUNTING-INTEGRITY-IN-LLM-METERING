# Novelty Matrix — Phase 1 Literature Audit

**Date:** 2026-08-15  |  **Posture:** adversarial (assume a skeptical *Computers & Security*
reviewer is trying to reject the novelty claim).

Machine-readable companion: [`novelty_matrix.csv`](./novelty_matrix.csv).
Sources (primary, opened): [`phase1_sources.json`](./phase1_sources.json).
Conclusion + gate: [`phase1_conclusion.md`](./phase1_conclusion.md).
False-positive sweep: [`false_positive_check.md`](./false_positive_check.md).

## How to read the novelty assessment codes

- **A** — completely novel mechanism (no prior demonstration).
- **B** — known/observed generic mechanism, but not systematically studied in LLM
  billing under the dishonest-client threat model with measurement + defense.
- **C** — existing *LLM-specific* mechanism already studied (for a different goal).
- **D** — rebranding of a known API/quota/accounting/authorization attack.
- **E** — too implementation-specific to justify a standalone research class.

**No class earns an A.** The whole recent LLM-billing-security literature runs the
*opposite* direction (dishonest **provider** overcharging an honest client), so our
direction (dishonest **client** underpaying) is under-studied — but the underlying
*mechanisms* we rely on are mostly known outside the LLM-billing framing. The
contribution therefore has to be **systematization + reproducible measurement +
defense evaluation**, not the discovery of new primitives.

---

## The two "covered" directions (verified)

| direction | representative work (opened) | attacker → victim |
|---|---|---|
| Provider inflates charges | CoIn (arXiv 2505.13778, 2025); Invisible Tokens, Visible Bills (arXiv 2505.18471, 2025); Token Inflation (arXiv 2605.30040, 2026) | provider → honest client |
| Attacker inflates victim's bill | Denial-of-Wallet (OWASP LLM10; DoW reviews); LLMjacking (Sysdig 2024, Auth0/CSA) | third party / credential thief → victim tenant |

All three provider-inflation papers, when opened, **explicitly do not** consider a
client under-paying or evading metering. LLMjacking is *credential theft* (dishonest
identity, victim pays) — a different threat model from a legitimate-but-dishonest
client evading its own meter. This is exactly the quadrant our project targets.

---

## Per-class verdicts

### Class 1 — Stream-abort accounting gap → **REFRAME / SURVIVES** (type B)
- **Prior art that hurts us:** `new-api` issue **#5235** (2026) is this attack in a
  *deployed* LLM gateway: streaming pre-consumes quota, and if the client disconnects
  before the final usage block arrives, the gateway records `quota=0` and **refunds
  the full pre-consumed amount** — the client keeps the tokens for free. The
  "Cancellation Tax" writeup (2026) documents the same abort/decode mechanism, and
  Token Inflation names "partial usage during cancellation" undercounting.
- **Why it can still survive:** those are one bug report + one ops writeup (framed as
  honest operator over-pay), not a systematic, adversarial, measured class across
  metering architectures. The reframe is mechanism-based: **accounting-after-completion
  (post-hoc usage commit) vs accounting-before-inference (pre-authorized reserve)** —
  the abort window exists iff the meter commits at stream end.
- **Reviewer will cite:** new-api #5235; the cancellation tax; Kettle (racing a
  finalization request).

### Class 2 — Client-declared token trust → **REFRAME / SURVIVES (borderline)** (type B)
- **Prior art that hurts us:** the generic principle is CWE-807 ("never trust client
  input in a security decision"), which predates LLMs by two decades. Token Inflation
  measured a **provider** over-reporting margin (50.85% under tokenization ambiguity).
- **Why it can still survive:** ours is the *mirror* — a dishonest **client**
  under-reporting the billed token count (or an app metering on a client-side
  tokenizer estimate / trusting an upstream `usage` field). The LLM-specific hook is
  that the billed unit is *tokens*, tokenization is nondeterministic across
  implementations, and a server-side recount is the defense — none of which is
  quantified for the client-underpay direction. Reframe: **server-authoritative
  recount vs client/upstream-authoritative usage.**
- **Reviewer will cite:** CWE-807; Token Inflation; token-count-discrepancy reports.

### Class 3 — Cache / recompute dodging → **REFRAME (weak) / SURVIVES (lowest confidence)** (type B/E)
- **Prior art that hurts us:** billing idempotency is a solved standard (Stripe;
  replay returns the stored response *without* re-billing — by design). Auditing
  Prompt Caching (ICML 2025) already studied LLM caching, but as a **privacy** timing
  side channel, not billing. Semantic-cache gateways state cache hits cost **zero**
  tokens/quota.
- **Why it might survive:** the LLM-specific angle is **inference-cache billing** —
  can a client farm inference-equivalent value via induced (exact/semantic) cache
  hits that bypass the meter, and is cache access gated by entitlement
  ("cache authorization vs cache correctness")? Testable, but it partially collapses
  into idempotency (solved) and authorization (class 5), so it is the weakest
  survivor and may be demoted or folded.
- **Reviewer will cite:** Stripe idempotency; arXiv 2502.07776.

### Class 4 — Adversarial retry on shared quota → **KILLED / MERGE into Class 6** (type D)
- **Fatal prior art:** **CVE-2026-31873 (Tyk Gateway, 2026, CVSS 7.5)** is precisely a
  non-atomic quota `GET`-then-`DECR` TOCTOU race that concurrency multiplies — i.e.
  the credit/quota-decrement race of Class 6. Kettle's single-packet attack is the
  generic technique. "Shared pool / thundering herd / priority inversion" is a
  deployment variant, not a distinct LLM-specific mechanism.
- **Verdict:** not a separate class. Fold into Class 6 as its "shared/multi-tenant
  quota" variant.

### Class 5 — Entitlement-metadata tampering → **KILLED** (type D)
- **Fatal prior art:** **OWASP API3:2023** (Broken Object Property Level Authorization
  / Mass Assignment — inject `tier:premium`, tamper `total_price`) and **OWASP
  API1:2023** (BOLA). Mature, generic, non-LLM. Reaching higher-tier *models* is just
  BFLA/BOLA applied to model routing.
- **Verdict:** remove. Cite OWASP API Security Top 10 as the reason; retain at most a
  one-line note that model-tier authorization is an *instance* of a solved class.

### Class 6 — Limit-overrun race on credit decrement → **BASELINE (known)**
- Doubly grounded: Kettle single-packet (2023) + CVE-2026-31873 (2026). Correctly
  treated as the known baseline that validates the measurement rig; never claimed as
  novel. (Already implemented and measured in Phase 0.)

---

## Summary table

| class | name | assessment | verdict |
|---|---|---|---|
| 1 | Stream-abort accounting gap | B | REFRAME → survives (commit-timing) |
| 2 | Client-declared token trust | B | REFRAME → survives, borderline (usage authority) |
| 3 | Cache / recompute dodging | B/E | REFRAME → survives, weakest (inference-cache billing) |
| 4 | Adversarial retry on shared quota | D | KILLED → merge into class 6 |
| 5 | Entitlement-metadata tampering | D | KILLED → remove (OWASP) |
| 6 | Limit-overrun race on credit decrement | — | BASELINE (known) |

**Uncertainty recorded:** the client-underpay *direction* being unstudied is a
bounded negative established by targeted searches that returned only provider-side
inflation, DoW, credential theft, and performance benchmarking — it is *not* proof
that no such work exists. Confidence that classes 4 and 5 are non-novel: high.
Confidence that classes 1 and 2 are defensible reframes: medium-high. Confidence that
class 3 is defensible: low.
