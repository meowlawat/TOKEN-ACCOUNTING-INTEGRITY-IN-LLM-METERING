# M3 Decision Gate — Inference-Cache Billing

**Decision: KILLED after the experimental/literature audit.** M3 is *not* implemented
as a contribution. This is a deliberate scientific outcome, not an omission.

## The gate (§11 of the execution plan)

| question | finding | verdict |
|---|---|---|
| 1. Genuinely about LLM inference economics? | Semantic/prompt caching is LLM-specific (embedding similarity, prefix reuse). | partial yes |
| 2. Does the attacker obtain **inference** without a corresponding charge? | A cache hit means **no new inference happens**. The client receives a stored response; there is no fresh metered computation to evade. The "value" is a repeated answer, not new inference. | **NO** |
| 3. Survives proper cache authorization? | Vendor gateways offer per-tenant/per-user cache isolation. With it, no cross-user leak. Without it, the issue is a cache-authorization misconfiguration. | reduces to authz |
| 4. Distinguishable from HTTP replay / idempotency? | Idempotency-key replay returning a stored response **without** re-billing is the intended Stripe/IETF semantics for safe retries. Not a novel attack. | **NO** |
| 5. Does an architecture-level defense differ from ordinary cache correctness/authorization? | The "defense" is (a) authorize cache access and (b) decide a billing policy for hits — ordinary cache authorization plus a pricing choice, not a novel LLM-specific enforcement primitive. | **NO** |

M3 fails questions 2, 4, and 5. It collapses into three already-solved or already-killed
areas:

1. **Billing idempotency** — a solved standard (Stripe, IETF idempotency-key draft):
   replay returns the stored response without re-charge *by design*.
2. **Cache authorization** — generic access control; overlaps the already-killed
   Class 5 (OWASP API1/API3). "Cache keyed on content not entitlement" is an
   authorization bug, not an inference-accounting bug.
3. **Billing policy** — whether to charge for a cache hit (semantic-cache gateways
   bill hits at zero by design; that is a legitimate cost-saving feature, not evasion).

There is no residual LLM-specific *accounting-integrity violation* in M3 that is not
already covered by M2 (who authoritatively sets the billed quantity) or by generic
idempotency/authorization. Per the execution principle, it is scientifically
preferable to ship **M1 + M2 + B0** than to pad the taxonomy with a weak third class.

## Consequence

- `attacks/m3_cache.py` and `defenses/m3_cache.py` are intentionally **not created**.
- The paper reports M3 as *killed at the decision gate*, with this document as the
  evidence trail.
- If a future reviewer or experiment surfaces a crisp, testable, LLM-specific
  inference-accounting violation in caching that is distinct from idempotency and
  authorization, M3 can be revived; we found none.
