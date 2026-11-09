# TAISAP migration changelog

Source: `paper/main_fgcs.tex` at commit `7665a3e` (SHA-256 `6efcc64bd66a55afc74b796d0ce159d35f7618771da3c4f50585000c751a3ea7`),
18-page FGCS manuscript. Produced on branch `taisap-migration`. The FGCS source,
PDF, and submission records are untouched by this work.

## Template and build

| Item | FGCS | TAISAP |
|---|---|---|
| Document class | `elsarticle[final,5p,times,twocolumn,number]` | `acmart[manuscript,review]` |
| Columns | two | one (review-manuscript format; TAISAP's final typeset format is two-column but that is assigned post-acceptance, not authored) |
| Bibliography | manual `\begin{thebibliography}` (81 `\bibitem`s, elsarticle-num style) | `references_taisap.bib` (81 `@misc` entries) + `\bibliographystyle{ACM-Reference-Format}` |
| Citation style | numeric, citation order | numeric, author-order (ACM-Reference-Format's convention) — reference *numbers* in the rendered PDF therefore differ from the FGCS version; reference *content* does not |
| Float syntax | `table*`/`figure*` (two-column spanning) | `table`/`figure` (single column has no spanning variant) — 7 environments converted, verified via diff to be the only change in that part of the file |

## Bibliography conversion (Section 7 of the task)

All 81 `\bibitem` entries were parsed programmatically (not retyped) from the FGCS
source into `references_taisap.bib`. Author lists were reformatted from the paper's
own prose style (`Last, F., Last2, G., et~al.`) into BibTeX's required
`Last, F. and Last2, G. and others` form — this was the one real bug hit during the
conversion (BibTeX initially mis-parsed 4+ author entries as a single malformed name;
fixed by writing a proper comma-pair splitter, verified against all 81 entries with
zero parse failures and zero odd-token-count edge cases). Every other field (title,
venue, DOI/URL) was carried through unchanged.

**What this conversion did NOT do, stated plainly:** it did not re-verify any of the
81 citations' metadata against Crossref, DOI resolution, or the publishers themselves.
The metadata carried over is whatever was already in the FGCS manuscript (itself
built up and audited across several earlier venue passes in this repository, per
`paper/FGCS_AUDIT.md` etc.), not freshly re-derived or independently re-checked here.
If live re-verification of all 81 external sources is wanted, that is a separate,
sizeable task.

## Framing changes (Section 5 of the task)

Everything in Threat Model, Related Work, Accounting State Model, Architectural
Taxonomy, Methodology, Formal Verification, Empirical Results, Defenses and
Sufficiency Conditions, Cross-Architecture and Asynchronous Validation, and Economic
and Pricing Analysis is **byte-identical** to the FGCS source except the 7
`table*`/`figure*` to `table`/`figure` syntax conversions (verified by diffing that
entire span of both files directly — 48 diff lines, all of them exactly those 14
`\begin`/`\end` pairs, nothing else).

Three places were edited for TAISAP's framing, each a small, targeted change over
content that was already largely aligned (the FGCS adaptation pass had already
reframed this paper around "distributed state management" and "security-critical
state" — TAISAP needs that connected explicitly to AI-system security, not
rebuilt from scratch):

1. **Abstract** — rewritten to open on the security boundary of deployed AI-serving
   infrastructure rather than LLM serving as a billing detail, and to close by
   stating plainly that the contribution is a security analysis of deployed
   infrastructure, not a new model-level attack. Every number in the original
   abstract (58.3%, 69.0%, ten configurations, four invariants, <0.1% overhead,
   V(r) ≤ N(r)) is preserved unchanged.
2. **Introduction, one clause added** (after "...now carry security-critical
   state"): "...making the usage-metering and settlement subsystem part of the
   AI-serving system's security boundary rather than a peripheral accounting
   concern external to it." Nothing removed, nothing else reworded in this section.
3. **Conclusion, opening sentence reworded**: "accounting integrity in metered
   computational services" → "accounting integrity in metered AI-serving
   infrastructure," framed explicitly as a security study. No claim changed.

**Title**: kept unchanged. The existing title already frames the paper around
"Metered LLM-Serving Infrastructure" with "Client-Side Under-Payment" signaling the
adversarial framing; a title change was considered and rejected as unnecessary
churn over something that already fits.

**CCS concepts**: intentionally left unfilled in the preamble rather than guessed.
ACM's CCS taxonomy codes must come from the official selector at
<https://dl.acm.org/ccs>; recommended selections based on the paper's actual content
(fill in via the tool, these are candidate paths, not verified codes):
- Security and privacy → Systems security → Distributed systems security
- Security and privacy → Economics of security and privacy
- Security and privacy → Formal methods and theory of security

## What was deliberately NOT done

- No experiment was rerun, no figure was regenerated from altered data, no TLA+
  specification was touched. Figures 1–6 are the identical files used by the FGCS
  manuscript (confirmed: `paper/figures_cose/Figure_1.png` through `Figure_6.png`,
  same `\graphicspath`).
- No author, affiliation, ORCID, or corresponding-author detail was changed.
- No rights-management metadata (DOI, ISBN, copyright year, article number) was
  added — ACM assigns this post-acceptance; inventing it would violate the
  non-negotiable rule against fabricated metadata.
- The `anonymous` acmart option was deliberately **not** used, correcting an
  assumption in the original migration brief: ACM journals (unlike many ACM
  conferences) are not run double-blind, confirmed by directly checking the current
  acmart class documentation before building the preamble.
