# Submission metadata — Computers & Security

> **Submission closed.** Submitted August 25, 2026 as **COSE-D-26-05174**; desk-rejected
> the same day by the Editor-in-Chief on journal scope (AI/ML moratorium). Not peer
> reviewed. This file records the metadata as submitted and remains the reference for a
> future venue. See `paper/FINAL_SUBMISSION_STATUS.md`.

## Title
Token-Accounting Integrity in LLM Metering: A Systematic Study of Client-Side
Under-Payment

## Author
Hardik

*A mononym, by the author's decision. In Editorial Manager, enter it in the last-name
field and leave the first-name field empty; the same convention applies in Zenodo.*

## ORCID
`0009-0001-1642-6669`

*Verified as the author's — it is the link published on `github.com/meowlawat`, the
account that owns this repository. The record is near-empty as of writing; populate the
affiliations and accepted works before any future submission.*

## Affiliations
a. Department of Computer Science and Data Analytics, Indian Institute of Technology
   Patna, India
b. Vivekananda School of Engineering and Technology, Vivekananda Institute of
   Professional Studies — Technical Campus, New Delhi, India

*The author is dual-enrolled (IIT Patna, B.Sc. Hons, 2024–2027; VIPS, B.Tech CSE
Cybersecurity, 2024–2028), so both are listed.*

## Corresponding author
Hardik — `hardik24a12res263@iitp.ac.in` (institutional, primary) and
`hardikahlawat13@gmail.com` (personal, durable after graduation). Both are printed in the
manuscript's corresponding-author footnote, institutional first.

## Article type
Full-length research article.

## Keywords (9)
usage metering; token accounting; billing integrity; quota enforcement; API security;
economic security; streaming inference; accounting reconciliation; model checking

## Manuscript metrics (measured by `scripts/count_cose_metrics.py`)

| metric | value | requirement |
|---|---|---|
| Abstract word count | 248 | <= 250 |
| Total word count (body + references) | 10,025 | <= 12,000 |
| Numbered sections | 15 | --- |
| Unnumbered (declaration) sections | 6 | --- |
| Figures | 6 (1 vector TikZ diagram + 5 raster at 600 dpi) | --- |
| Tables | 6 | --- |
| Reference count | 26 | --- |
| Distinct cited keys | 26 (all bibliography entries cited) | --- |
| Total in-text citations | 49 | --- |
| Uncited figures or tables | 0 | every float must be cited |
| Compiled length | 25 pages, 0 blank | --- |

Figure and table counts are of floats that are both present *and* referred to in the
text; `scripts/check_cose_submission.py` fails if any float is never cited.

## Required declarations

| declaration | page |
|---|---|
| Acknowledgements | 23 |
| CRediT authorship contribution statement | 23 |
| Declaration of competing interest | 24 |
| Funding | 24 |
| Data availability | 24 |

No generative AI declaration is present in the manuscript, by author decision.

## Repository and release
GitHub: https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING
Release tag reported in the paper: `v1.0.1`
Earlier tag `v1.0.0` is preserved unchanged as the historical snapshot.

## Zenodo / archival DOI

```
Version DOI (cited in the manuscript):  10.5281/zenodo.22086254   (v1.0.2, complete artifact)
Concept DOI (resolves to latest):       10.5281/zenodo.22085827
Superseded deposition (v1.0.1):         10.5281/zenodo.22085828
```

**The record still needs work before submission** — it currently holds only the
manuscript, its resource type says "Journal article", its licence says CC-BY-4.0 where the
repository is MIT, and the creator name renders as ". , . hardik .". See
`paper/SUBMISSION_BLOCKERS.md` item 1.

## Files to upload

| file | role |
|---|---|
| `paper/main_cose.pdf` | manuscript |
| `paper/main_cose.tex` | LaTeX source (elsarticle) |
| `paper/highlights_upload.txt` | highlights — 5 bullets, nothing else |
| `paper/figures_cose/Figure_1.pdf` | Figure 1, vector (preferred) |
| `paper/figures_cose/Figure_1.png` | Figure 1, 600 dpi raster fallback |
| `paper/figures_cose/Figure_2.png` .. `Figure_6.png` | Figures 2-6, 600 dpi |
| `paper/submission_forms/cover_letter.txt` | cover letter, paste-ready plain text |
| `paper/submission_forms/declaration_of_interests.docx` | Elsevier declaration-of-interests form, completed |
| `paper/submission_forms/suggested_reviewers.md` | reviewer suggestions (enter in Editorial Manager) |
| `paper/author_bio.txt` | author biography — 85 words, **needs author review** |
| `paper/submission_forms/author_photo.jpg` | author photograph, 1200x1600 @ 300 dpi |

Do not upload `paper/highlights.txt`; it carries working annotations. The paste-ready
version is `paper/highlights_upload.txt`.

## Not for upload — internal working files
`paper/submission_metadata.md` (this file), `paper/SUBMISSION_BLOCKERS.md`,
`paper/COSE_SUBMISSION_READINESS.md`, `paper/FINAL_SUBMISSION_MANIFEST.md`,
`paper/FINAL_SUBMISSION_STATUS.md`, `paper/data_availability.md`. These document the
submission for the author; the journal asks for none of them.

## Graphical abstract
Not created. The repository contains the request-lifecycle TikZ diagram
(Figure 1 in the manuscript body) but assembling a separate graphical-abstract image
summarizing streaming inference -> accounting boundary -> B0/M1/M2 -> $V(r)\le N(r)$ ->
defenses would require new artwork beyond what exists in the artifact. Per instruction,
this is left optional rather than fabricated. Status: **optional / not submitted.**
