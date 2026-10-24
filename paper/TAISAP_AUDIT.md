# TAISAP scope-fit and scientific-integrity audit

Written after the TAISAP migration, on branch `taisap-migration`, commit base
`7665a3e`. Companion to `CHANGELOG_TAISAP.md`, which has the file-level diff detail.

## Scope-fit memo

**Verified TAISAP scope** (checked live against ACM's own pages, not assumed):
TAISAP covers "all aspects of AI security and privacy," explicitly including
*models, systems, and environments*, welcomes both theoretical and applied
contributions, and its "Just Accepted" queue as of this writing already includes
LLM-infrastructure-adjacent security work (backdoors in RAG pipelines, LLM-agent
vulnerabilities, DNN side-channels) — confirming the venue is actively handling this
category of paper, not merely claiming to in its charter.

1. **Strongest defensible fit**: the "systems" clause. This paper is about the
   security of the usage-metering and billing-settlement boundary around a deployed
   AI-serving system — an architectural/infrastructure security problem, which is
   explicitly in scope, not a stretch reading of it.
2. **Closest scope objection a reviewer could raise**: "this is a generic billing
   race condition with an LLM label on it, not an AI-specific threat." The honest
   answer, already stated throughout the paper and not weakened for this venue: B0
   is explicitly a known, generic race presented as a baseline, not a contribution.
   M1 and M2 are systematization and measurement over individually-documented
   mechanisms, not new primitives. What TAISAP should find relevant is the
   *combination* specific to AI-serving infrastructure (streamed, runtime-produced,
   multi-category usage settled asynchronously) and the formal+empirical treatment
   of it, not a claim of a novel attack class.
3. **What makes it relevant to AI security specifically**: the integrity property
   studied here is a property of the AI-serving system's own security boundary —
   whether the system can enforce the resource/economic constraints it claims to
   enforce on a client it has already authenticated.
4. **Limitation that must stay explicit**: the "distributed" claim is about
   processes/containers on one host over loopback (plus one genuinely
   network-separated two-machine experiment), not a wide-area production
   deployment. This is already stated in its own limitations subsection and is
   unchanged by this migration.

## Numerical and scientific-claim integrity — pass/fail table

Every value below was directly grep-verified present, unchanged, in both
`main_fgcs.tex` and `main_taisap.tex` (not eyeballed) after the migration:

| Claim | Value | Status |
|---|---|---|
| Integrity property | $V(r) \le N(r)$ | PASS — unchanged |
| TLA+ configurations / invariants | 10 configurations, 4 invariants | PASS — unchanged |
| B0 leakage slope | \$0.099/request, $R^2=1.0000$, $p=1.9\times10^{-50}$ | PASS — unchanged |
| B0 leakage at concurrency 2/30/50 | \$0.099 / \$2.871 / \$4.851 | PASS — unchanged |
| M2 client-declared leakage (controlled) | 58.3% | PASS — unchanged |
| M2 client-declared leakage (real stack) | 69.0% | PASS — unchanged |
| M2 flat-total strongest-attack leakage | 0.741 | PASS — unchanged |
| M2 leakage efficiency, async-delay invariance | 0.5823 at every delay | PASS — unchanged |
| Async formal model state counts | 91,921 generated / 22,521 distinct | PASS — unchanged |
| Primary TLA+ state count | 27,526 distinct states | PASS — unchanged |
| OpenGateLLM public-report instance | 254,347 completion tokens | PASS — unchanged |
| Strongest M2 defense overhead | under 0.1% of end-to-end time | PASS — unchanged (appears in abstract and body) |
| Figure 1–6 content and data | unchanged files | PASS — same `figures_cose/*.png`, byte-identical |
| Author/affiliation/ORCID/email | unchanged | PASS — verified via direct grep of `\email{}` lines against source |

No value was changed in this migration. No authorized correction was needed or made.

## Qualifications and distinctions — verified still explicit

Directly checked present, unreworded, in `main_taisap.tex`:
- Model-checking vs. implementation proof: "We do not provide a mechanized
  refinement proof from the abstract specification to the implementation" (bold in
  source) — present, unchanged.
- Finite model scope: "two to three concurrent requests, two value chunks, unit
  pricing" — present, unchanged.
- At-least-once + idempotent ≠ exactly-once: "Delivery remains at-least-once, not
  exactly-once" — present, unchanged (Durability subsection).
- Local/loopback vs. physically distributed: the Distribution limitation paragraph
  and the two-machine network-separation caveat are both present, unchanged.
- Detectability claim stays withdrawn: "we make no detectability claim" — present,
  unchanged.
- No commercial-provider testing claim: present, unchanged, in Threats to Validity.

## Citation integrity — what was and wasn't verified

**Was done**: mechanical, auditable conversion of all 81 references from the FGCS
manuscript's own prose-style bibliography into BibTeX, with zero data loss verified
by reconstructing each entry's text from the generated `.bib` file and diffing
against the original (77/81 byte-identical automatically; the other 4 were
confirmed identical by hand — the mismatch was a cosmetic artifact in the audit
script's own string formatting, not a content difference).

**Was NOT done**: live re-verification of each of the 81 citations' title/author/
venue/DOI against Crossref, the publisher, or any other external source. This
migration carried the existing, already-audited FGCS bibliography through
unchanged — it did not re-derive or re-check it. State this honestly in any
cover-letter or submission note rather than implying a fresh verification pass
happened here.

No citation was added, removed, or reattached to a different claim.

## Template and build

- Document class: `\documentclass[manuscript,review]{acmart}` — verified live
  against the current acmart class documentation before use, not assumed; `review`
  adds line numbers for reviewer convenience, `anonymous` deliberately omitted
  (ACM journals are not double-blind).
- Build: `tectonic main_taisap.tex --keep-logs`, including a full BibTeX pass via
  `ACM-Reference-Format.bst`.
- Result: 31 pages (single-column manuscript format naturally runs much longer
  than FGCS's tightly-typeset two-column 18 pages; TAISAP is a continuously-published
  journal without FGCS's fixed-page-budget submission constraint, so this is not a
  compliance problem the way it was for FGCS).
- Citations/references: 0 undefined, 0 duplicate labels (verified: scanned the
  full rendered PDF text for `[?]`/`(?)` broken-reference markers — zero found
  across 109,609 extracted characters).
- BibTeX: 0 errors, 0 warnings on the final run (the author-list bug from the
  first attempt was fixed before this).
- Visual inspection: title page, a related-work page, a results page, the
  practical-defense table (Table 6), Figure 6's page, and the final references
  page were each rendered and read directly — not just compiled — before writing
  this report. All read correctly; Figure 6 confirmed still in its repaired 2×2
  layout with unchanged data.

## Submission checklist

| Item | Status |
|---|---|
| Manuscript compiles cleanly | DONE |
| Bibliography converted, verified lossless | DONE |
| Scope-fit memo | DONE (above) |
| Framing edits (abstract/intro/conclusion) | DONE |
| Numerical integrity re-check | DONE (above) |
| CCS concepts | **NOT DONE** — must be generated at <https://dl.acm.org/ccs>; candidates listed in `CHANGELOG_TAISAP.md` |
| Live citation re-verification (Crossref/DOI) | **NOT DONE** — not attempted, flagged honestly above |
| Cover letter | DONE — `paper/submission_forms/cover_letter_taisap.txt` |
| ORCID record populated | carries forward from the FGCS checklist — still worth doing, not specific to this migration |
| Actual TAISAP submission | **NOT DONE — not authorized by this task, and not performed** |

## Next-action recommendation

**NOT READY TO SUBMIT** — two concrete, bounded gaps remain (CCS concept codes from
the official tool; a decision on whether to run the live citation-reverification
pass), neither of which requires rewriting anything, both of which are the
author's call, not something to guess through. Everything else — content fidelity,
template correctness, build cleanliness, framing — is READY FOR MANUAL FINAL
REVIEW.
