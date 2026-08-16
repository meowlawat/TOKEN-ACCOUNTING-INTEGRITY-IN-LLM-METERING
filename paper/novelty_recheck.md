# Novelty Recheck (post-implementation)

> **Note:** this is the *first* of two post-hoc novelty audits, run immediately after
> M1/M2 were implemented. The **final** audit — run after all experiments and used to
> set the paper's related-work framing — is
> [`novelty_reattack.md`](./novelty_reattack.md), which supersedes this document where
> they differ and adds a fourth adversary axis (dishonest intermediary). Both are kept
> as a record of what was known at each point.


**Date:** 2026-08-15 (same session as the Phase 1 audit; performed after implementing
M1/M2 to catch anything the first pass missed on the strongest survivors).

## Queries run (targeted at the surviving mechanisms)

- "metering commit timing streaming inference billing abort client evasion measurement"
- "LLM usage record authority server-side token recount under-reporting billing integrity attack"
- (plus the Phase 1 corpus: client-side LLM billing evasion, streaming billing race,
  usage finalization after disconnect, quota concurrency bypass, etc.)

## Findings

1. **No systematic study** of client-side metering-commit-timing evasion or
   usage-record-authority under-reporting under the dishonest-client model was found.
   The provider-overcharge line grew (Predictive Auditing of Hidden Tokens, arXiv
   2508.00912; a 2606 lifecycle survey) but remains the *opposite* direction. The gap
   holds.

2. **New in-the-wild instance for M2 (increases reality, slightly reduces novelty):**
   `lightninglabs/aperture` **PR #247** (L402 metered token draw-down) mitigates
   *compression-based client evasion* — it strips the client `Accept-Encoding` header
   "so the upstream response comes back plaintext, ensuring the usage tail is always
   parseable," and treats a non-identity encoding as an error "rather than a silent
   zero-debit." This is a concrete engineering instance of a client manipulating the
   response so the usage record cannot be formed → a silent zero-debit. It is a real
   *mitigation against client-side usage evasion*, confirming M2 describes a live
   concern. It is not a systematic measurement study, so it does not scoop the
   contribution, but it MUST be cited so a reviewer does not treat M2 as hypothetical.

3. **M1** remains grounded in `new-api` #5235 (refund-on-missing-final-usage) and the
   Cancellation Tax; no new systematic study appeared.

## Effect on claims

- Reconfirms the framing: **systematization + measurement + defense**, not discovery.
- Adds one prior-evidence citation (aperture #247) to M2's related work; strengthens
  the "this is real, not hypothetical" argument while keeping novelty bounded.
- No class needs to be killed or added beyond the Phase 1 result (M1/M2 survive as
  reframes; M3 killed at its decision gate; M4/M5 killed in Phase 1).

## Source to append to `phase1_sources.json`

```json
{
  "id": "aperture-pr-247",
  "title": "aperture #247: metered draw-down of prepaid L402 tokens; strip Accept-Encoding to prevent silent zero-debit",
  "authors": ["lightninglabs/aperture contributors"],
  "year": 2026, "venue": "GitHub PR (lightninglabs/aperture)",
  "doi_url": "https://github.com/lightninglabs/aperture/pull/247",
  "source_type": "in-the-wild-mitigation", "access_level": "search-summary",
  "relevance": "Engineering mitigation against client-side usage evasion (encoding-induced silent zero-debit) in a metered-token proxy; prior evidence that M2 is a live concern.",
  "classes_affected": ["M2"]
}
```
