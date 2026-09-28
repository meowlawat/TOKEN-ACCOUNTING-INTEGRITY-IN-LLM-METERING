# FGCS Resubmission Audit — Repository Map

Generated during the pre-resubmission forensic audit for FGCS-D-26-05286 resubmission
(post ORCID-verification fix). This is the Part 1 repository map required before any
edits were made. See the chat-delivered final report for verdicts and fixes applied.

## Authoritative manuscript source

- **`paper/main_fgcs.tex`** — the authoritative FGCS source. Compiles standalone with
  `tectonic`. `elsarticle` class, `[final,5p,times,twocolumn,number]` options (was
  `authoryear`, changed during this audit — see final report).
- **`paper/main_fgcs.pdf`** — rebuilt from `main_fgcs.tex` during this audit via
  `tectonic -X compile main_fgcs.tex` (default multi-pass). 18 pages, matches source.
- **`paper/main_fgcs.log`** — stale (dated before the last source edit); gitignored,
  not part of the submission, safe to ignore/regenerate at will.

## Competing/historical manuscript sources (NOT for FGCS submission)

These are prior-venue variants, preserved unmodified per their own history, and must
never be uploaded to FGCS's Editorial Manager:

| File | Venue | Status |
|---|---|---|
| `paper/main.tex` / `main.pdf` | original/earliest draft | historical |
| `paper/main_cose.tex/.pdf` | Computers & Security | desk-rejected (COSE-D-26-05174) |
| `paper/main_jisa.tex/.pdf` | JISA | prepared/submitted, no longer under consideration |
| `paper/main_jss.tex/.pdf` | Journal of Systems and Software | submitted as JSSOFTWARE-S-26-03217 |
| `paper/main_cn.tex/.pdf` | Computer Networks | prepared, not submitted |
| `paper/main_ieee.tex/.pdf` | IEEE-format variant | historical/artifact release copy |

`main_fgcs.tex` is derived from `main_jss.tex`. No measured value, table, figure, or
equation differs across these files per the (now-removed) header note — the FGCS
version is a venue/framing adaptation only.

## Bibliography workflow

- **Manual `\begin{thebibliography}{81}`** with `\bibitem[Author(Year)]{key}` entries —
  not BibTeX/Biber-generated, no `.bib` file exists for this manuscript.
- Citation commands: `\citep{}` (93 uses) and `\citet{}` (10 uses), via `natbib`
  (loaded internally by `elsarticle.cls` per its `\@biboptions` class-option switch).
- `\bibliographystyle{...}` is present but **inert** for this manuscript: BibTeX is
  never invoked (no `\bibliography{}` command exists), so the named style has no
  effect on the rendered bibliography. It is set for source-hygiene/consistency only.

## Title page / submission-forms files

- `paper/submission_forms/title_page_fgcs.tex` — standalone `elsarticle` doc with the
  same title/author/affiliation/`\ead`/`\cortext` block as `main_fgcs.tex`. Verified to
  compile standalone. Not imported by `main_fgcs.tex`. **KEEP** (see final report).
- `paper/submission_forms/cover_letter_fgcs.txt` — FGCS cover letter, no old-venue text.
- `paper/submission_forms/declaration_of_interests_fgcs.docx` — clean, correct
  authors/affiliations, "no competing interests" checked, `[SUBMISSION DATE]`
  placeholder still needs a real date at upload time.
- `paper/highlights.txt` — 5 bullets, all ≤85 characters.
- `paper/author_bio.txt` — **flagged in final report**: contains unverified claims.
- `paper/submission_forms/author_photo.jpg` — present.
- Sibling `submission_forms/cover_letter.txt`, `cover_letter_cn.txt`,
  `cover_letter_jisa.txt`, `cover_letter_jss.txt`, `declaration_of_interests.docx`,
  `declaration_of_interests_jss.docx`, `CN_SCOPE_NOTES.md` — all belong to the other
  venue variants above and must **not** be uploaded to FGCS's EM.

## Build system

No Makefile/build script exists specifically for `main_fgcs.tex`. It is compiled
directly with `tectonic -X compile main_fgcs.tex` from `paper/`. `scripts/` contains
build helpers for other variants (`render_cose_figures.py`, `make_ieee_tables.py`,
`audit_ieee_format.py`, etc.) — none are FGCS-specific except general figure/table
generation already reflected in the tracked `.tex`/`.png` outputs.

## Figures and tables in main_fgcs.tex

6 figures (Figure 1 is inline `tikzpicture`, not `\includegraphics`; Figures 2–6 are
`\includegraphics{Figure_N.png}` from `paper/figures_cose/`), 8 tables. All present, all
labeled, all referenced — see final report's Figure/Table audit.

## Duplicate/stale-file risk

The repository holds 6 parallel `main_*.tex`/`.pdf` pairs (fgcs, cose, jisa, jss, cn,
ieee, plus the unsuffixed `main.tex`). This is a real "wrong manuscript uploaded"
risk purely from file-count — mitigated only by careful manual selection at EM upload
time. No automated safeguard prevents picking the wrong file.
