# Submission metadata — Computers & Security

## Title
Token-Accounting Integrity in LLM Metering: A Systematic Study of Client-Side
Under-Payment

## Author
Hardik

*The manuscript carries a single name. Elsevier's Editorial Manager takes given name and
family name as separate fields, and so does Zenodo. This must be resolved before
submission — it is tracked as item 7 in `paper/SUBMISSION_BLOCKERS.md`, and a family name
was deliberately not inferred from the email address.*

## Affiliation
Department of Computer Science and Data Analytics, Indian Institute of Technology
Patna, India

*Note: this affiliation and email were supplied directly by the author for this
submission. The author's resume also lists an institutional email
(`hardik24a12res263@iitp.ac.in`); either address can serve as the corresponding-author
contact, but institutional addresses are conventional for academic corresponding
authors and may be preferred by the journal. Decide and update
`\ead{}` in `paper/main_cose.tex` before submitting if you want the institutional
address instead.*

## Corresponding author
Hardik — hardikahlawat13@gmail.com (see note above)

## Article type
Full-length research article.

## Keywords (9)
usage metering; token accounting; billing integrity; quota enforcement; API security;
economic security; streaming inference; accounting reconciliation; model checking

## Manuscript metrics (measured by `scripts/count_cose_metrics.py`)

| metric | value | requirement |
|---|---|---|
| Abstract word count | 248 | <= 250 |
| Total word count (body + references) | 10,064 | <= 12,000 |
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

## Required declarations (all present in the manuscript)

| declaration | page |
|---|---|
| Acknowledgements | 23 |
| CRediT authorship contribution statement | 23 |
| Declaration of competing interest | 24 |
| Funding | 24 |
| Generative AI disclosure | 24 |
| Data availability | 24 |

## Repository and release
GitHub: https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING
Release tag reported in the paper: `v1.0.1`
Earlier tag `v1.0.0` is preserved unchanged as the historical snapshot.

## Zenodo / archival DOI
**No DOI exists.** The deposition package is built and waiting in `release/zenodo/`
(archive, SHA-256 checksum, file list, and every form field in `metadata.md`). Publishing
it requires the author's Zenodo account. See `paper/SUBMISSION_BLOCKERS.md` item 1.

## Files to upload

| file | role |
|---|---|
| `paper/main_cose.pdf` | manuscript |
| `paper/main_cose.tex` | LaTeX source (elsarticle) |
| `paper/highlights_upload.txt` | highlights — 5 bullets, nothing else |
| `paper/figures_cose/Figure_1.pdf` | Figure 1, vector (preferred) |
| `paper/figures_cose/Figure_1.png` | Figure 1, 600 dpi raster fallback |
| `paper/figures_cose/Figure_2.png` .. `Figure_6.png` | Figures 2-6, 600 dpi |
| `paper/cover_letter.md` | cover letter (paste as text) |
| `paper/author_bio.txt` | author biography — **PENDING, not yet written** |
| `paper/AUTHOR_PHOTO_REQUIRED.md` | photograph — **PENDING, not supplied** |

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
