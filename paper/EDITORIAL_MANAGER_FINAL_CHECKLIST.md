# Editorial Manager — final submission checklist

Everything below is prepared. What remains is the portal work, which only you can do.

**The paper has not been submitted.** Nothing in this repository submits it.

---

## 1. Submission fields

| field | value |
|---|---|
| Journal | Elsevier *Computers & Security* |
| Article type | **Full Length Article** |
| Title | Token-Accounting Integrity in LLM Metering: A Systematic Study of Client-Side Under-Payment |
| Author | **Hardik** |
| ORCID | `0009-0001-1642-6669` |
| Affiliation (a) | Department of Computer Science and Data Analytics, Indian Institute of Technology Patna, India |
| Affiliation (b) | Vivekananda School of Engineering and Technology, Vivekananda Institute of Professional Studies — Technical Campus, New Delhi, India |
| Corresponding email | `hardik24a12res263@iitp.ac.in` (primary), `hardikahlawat13@gmail.com` |

**Entering the name.** Put `Hardik` in the **last name** field and leave **first name
empty**. Editorial Manager expects a given/family split; a mononym goes in the family
field, which is the same convention Zenodo uses. Do not add a surname.

## 2. Files to upload

| # | file | role |
|---|---|---|
| 1 | `paper/main_cose.pdf` | manuscript — 25 pages |
| 2 | `paper/main_cose.tex` | LaTeX source (elsarticle, self-contained) |
| 3 | `paper/highlights_upload.txt` | highlights — 5 bullets, nothing else |
| 4 | `paper/submission_forms/cover_letter.txt` | cover letter — paste as text |
| 5 | `paper/submission_forms/declaration_of_interests.docx` | competing interests, completed and dated |
| 6 | `paper/submission_forms/author_photo.jpg` | author photograph, 1200×1600 @ 300 dpi |
| 7 | `paper/author_bio.txt` | author biography — copy the BIOGRAPHY block only |
| 8 | `paper/figures_cose/Figure_1.pdf` | Figure 1, vector (preferred) |
| 9 | `paper/figures_cose/Figure_1.png` | Figure 1, 600 dpi raster fallback |
| 10 | `paper/figures_cose/Figure_2.png` … `Figure_6.png` | Figures 2–6, 600 dpi |

**Do not upload** `paper/highlights.txt` — it carries working annotations. Upload
`highlights_upload.txt`.

**Do not upload** the internal working files: `submission_metadata.md`,
`SUBMISSION_BLOCKERS.md`, `FINAL_SUBMISSION_STATUS.md`,
`FINAL_SUBMISSION_MANIFEST.md`, `data_availability.md`, this checklist. The journal asks
for none of them.

## 3. Declarations — already inside the manuscript

| declaration | page | status |
|---|---|---|
| Acknowledgements | 23 | none apply, stated rather than omitted |
| CRediT authorship contribution statement | 23 | single author, 11 roles |
| Declaration of competing interest | 24 | none declared |
| Funding | 24 | no specific grant |
| Declaration of generative AI and AI-assisted technologies | 24 | Elsevier template wording, tool named, responsibility accepted |
| Data availability | 24 | GitHub + Zenodo DOI |

If the portal asks these as separate form fields as well, the text to paste is in the
manuscript at the pages above.

## 4. Data repository

```
Version DOI (cited in the paper):  10.5281/zenodo.22086254   (v1.0.2, complete artifact)
Concept DOI (resolves to latest):  10.5281/zenodo.22085827
Repository:                        https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING
```

The deposited archive was verified byte-for-byte against the local build: 8,092,411 bytes,
MD5 `c872a3904d5414c69ce8ff0d27b0aee2`, matching `release/zenodo/SHA256SUMS.txt`. A
reviewer who downloads it gets exactly what this repository produced.

The superseded v1.0.1 deposition (`10.5281/zenodo.22085828`) held only the manuscript. It
is not cited anywhere in the paper, and a gate check now fails if it reappears.

## 5. Suggested reviewers

`paper/submission_forms/suggested_reviewers.md` — five candidates from the manuscript's own
reference list, with the conflict statement (none).

**Verify manually before entering.** Contact details are deliberately blank: names and
affiliations change, and a suggestion with a guessed email is worse than no suggestion.
Take each person's current address from the cited paper or their institutional page.

## 6. Optional / not applicable

| item | status |
|---|---|
| Graphical abstract | **optional — not submitted.** Would require new artwork beyond the artifact. |
| Supplementary material | none, unless the portal requires it. The artifact is the Zenodo deposit. |
| Preprint declaration | not applicable — the v1.0.2 Zenodo record contains the artifact only, no manuscript PDF. |

## 7. Before you press submit

- [ ] Author name entered as a mononym (last-name field only)
- [ ] ORCID entered — and the ORCID record itself populated (see below)
- [ ] Both affiliations entered
- [ ] Article type set to **Full Length Article**
- [ ] Reviewer contact details looked up and verified
- [ ] Biography copied from the BIOGRAPHY block of `author_bio.txt` — **read it first**
- [ ] Zenodo record's licence and creator name corrected (see below)

## 8. Two things worth fixing first — neither blocks submission

**The ORCID record is near-empty.** `0009-0001-1642-6669` resolves to a page with a given
name and nothing else — no affiliations, no works. An ORCID that resolves to a blank page
is a weaker signal to an editor than no ORCID. Add IIT Patna, VIPS, and the two accepted
papers (ETTIS 2026 / Springer; ICDSCNC 2026 / IEEE Xplore). Ten minutes.

**The Zenodo record still has two metadata problems.** Both are editable without creating a
new version — use *Edit* on the record, not *New version*:

1. **Licence reads `cc-by-4.0`, but the archive ships an MIT `LICENSE` file.** The record
   contradicts its own contents. The repository is uniformly MIT (`LICENSE`, `README`), and
   an audit found no third-party code redistributed. Set it to MIT — or, if you want
   CC-BY for the data specifically, say so explicitly in the description and update
   `LICENSE` and `README.md` to match. Either is defensible; the current mismatch is not.
2. **Creator name is stored as `., hardik`**, so the record cites as `. , . hardik .`. Put
   `Hardik` in the family-name field and leave given names empty.

Neither affects the manuscript, the DOI, or the deposited data. They affect how the dataset
cites itself.

---

## Verified state of the package

```
submission checker    36/36 PASS
abstract              248 words        (limit 250)
article               10,061 words     (limit 12,000)
keywords              9                (range 5-10)
figures               6/6 cited
tables                6/6 cited
pages                 25, 0 blank
undefined references  0
undefined citations   0
duplicate labels      0
fatal LaTeX errors    0
overfull boxes        2  (2.6 pt, 6.8 pt — cosmetic)
```
