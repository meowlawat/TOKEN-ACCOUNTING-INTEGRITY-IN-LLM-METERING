# Submission blockers

> **The Computers & Security submission is closed.** The manuscript was submitted on
> August 25, 2026, assigned COSE-D-26-05174, and desk-rejected the same day on journal
> scope (AI/ML moratorium) by the Editor-in-Chief. No peer review, no reviewer reports.
> See `paper/FINAL_SUBMISSION_STATUS.md`.
>
> Items below are therefore no longer blockers *for C&S*. They are retained because most
> of them carry forward to any future venue, and because they record what the state
> actually was. Item 10 is new and specific to the published Zenodo archive.

Concrete, unresolved items. Nothing below was fabricated to make this list look shorter
than it is.

## 1. Zenodo record is incomplete and mis-typed

**The DOI exists.**

```
Concept DOI (cited in the manuscript):  10.5281/zenodo.22085827
Version DOI (v1.0.1):                   10.5281/zenodo.22085828
Record:                                 https://zenodo.org/records/22085828
```

The manuscript, `CITATION.cff`, and `paper/data_availability.md` all now carry the concept
DOI, which always resolves to the latest version of the record. That choice matters here:
the record has to change, and a concept DOI survives that.

**Four problems with the record as deposited**, and the fix for all of them is a single
Zenodo **New version** publish, prepared in `release/zenodo/metadata_v1.0.2.md`.

| | problem | why it matters |
|---|---|---|
| 1a | holds `main_cose.tex` and `main_cose.pdf`, not the artifact | the paper promises raw data at this DOI; a reviewer who follows it finds a PDF |
| 1b | resource type "Journal article" | wrong for an artifact archive, and it implies a publication that does not exist |
| 1c | licence CC-BY-4.0 | the repository is uniformly MIT; nothing in it ever declared CC-BY |
| 1d | creator renders `. , . hardik .` | the mononym goes in the family-name field with given names empty |

### What to do

Everything below is prepared. Nothing needs deciding except the preprint question in
step 3.

1. Open https://zenodo.org/records/22085828 and choose **New version**. This preserves the
   existing record — `10.5281/zenodo.22085828` stays resolvable forever as the historical
   v1.0.1 deposition. Do not delete or overwrite it.
2. Upload `release/zenodo/token-accounting-integrity-v1.0.1.zip` (333 files, ~8.1 MB;
   exact size and checksum in `release/zenodo/SHA256SUMS.txt`).
3. Decide whether `main_cose.pdf` stays. Keeping it makes the record a **preprint**, which
   Elsevier permits but expects declared at submission. If a preprint was not intended,
   drop it.
4. Set every field from `release/zenodo/metadata_v1.0.2.md` — resource type **Dataset**,
   version **1.0.2**, licence **MIT**, creator **Hardik** with ORCID
   `0009-0001-1642-6669`, the artifact description, the nine keywords, the related
   identifiers, and the journal fields left blank.
5. Publish. Read the new version DOI **off the record** — do not guess it.
6. Run `python scripts/set_zenodo_doi.py 10.5281/zenodo.<NEW>`. It installs that DOI into
   the manuscript, `CITATION.cff`, `README.md`, `data_availability.md`, and
   `submission_metadata.md` in one pass, and refuses a malformed DOI, the concept DOI, or
   the superseded one.
7. `tectonic -X compile paper/main_cose.tex` then `python scripts/check_cose_submission.py`.

### On the version numbers

The Zenodo record becomes version **1.0.2** while the archive inside is the artifact of
GitHub tag **v1.0.1**. That is deliberate. The artifact is frozen and unchanged; 1.0.2 is
the second *deposition* of it, because the first deposited the wrong files. The Zenodo
description states this so nobody reads 1.0.2 as a new scientific release.

### On the licence

Set **MIT**, matching the repository. This is a correction, not a change of semantics:
`LICENSE` is MIT, `README.md` says MIT, and an audit of the archive found exactly one
licence file — the repository's own — with no vendored third-party code. CC-BY-4.0 on the
current record is the deviation.

`release/zenodo/metadata_v1.0.2.md` records one caveat honestly: MIT is a software licence
and this archive is part code and part data, so a dual MIT/CC-BY-4.0 deposit is a
defensible alternative. That choice was **not** made unilaterally, because it would change
what the repository declares. If you want it, document it explicitly in the Zenodo
description and update `LICENSE` and `README.md` in the same pass.

**Status: BLOCKING.** This cannot be done from inside the repository — it needs the
author's Zenodo account. Everything that could be prepared has been.

## 2. Corresponding-author email choice — RESOLVED

**Status: RESOLVED.** The author chose to list both, institutional first:
`hardik24a12res263@iitp.ac.in` then `hardikahlawat13@gmail.com`. The institutional address
carries the conventional academic signal; the personal one survives graduation in 2027,
which matters for a paper that may be in review or cited long afterwards. Both print in
the corresponding-author footnote on page 1.

## 3. Author biography and photograph

**Biography: DRAFTED, needs the author's review.** `paper/author_bio.txt` now carries an
85-word biography built from the author's own resume, GitHub profile, and ORCID record,
with every claim traced to its source and a list of what was deliberately left out and
why. Read it and correct it — it is a biography of a real person and should not go out
unread.

**Photograph: SUPPLIED.** `paper/submission_forms/author_photo.jpg` — 1200x1600 px at
300 dpi, JPEG, white background, passport framing. Prepared by
`scripts/prepare_author_photo.py` from the author's own photograph: framing and format
only, no retouching. Details and provenance in `paper/AUTHOR_PHOTO_REQUIRED.md`.

The source had been through Gemini for background removal. The author confirmed it is a
real photograph of them rather than a synthetic likeness before it was packaged; an
AI-generated portrait presented as an author photograph would be a fabricated record and
would not have been used.

**Status: BLOCKING** if the journal's current submission system enforces this field;
check the live author guide, since requirements can change.

## 4. Graphical abstract

Optional per Elsevier's own guidance and left unmade here, since assembling one would
require new artwork beyond what exists in the repository (see
`submission_metadata.md`). Not a blocker, but worth deciding deliberately.

## 5. Residual B0 framing inconsistency in the IEEE manuscript — RESOLVED at v1.0.1

**Status: RESOLVED.** `paper/accounting_state_model_ieee.tex` (included by
`main_ieee.tex` via `\input`) previously stated unconditionally that B0 "needs
concurrency: yes" and that B0 leakage is "created by concurrency," contradicting the
corrected condition stated everywhere else in the same manuscript. It was corrected at
v1.0.1, together with two related fixes giving M1's and M2's concurrency independence
their correct epistemic status (measured for M1, analytic for M2).

No raw data, measured value, or experimental result changed. The Elsevier manuscript was
already correct and is byte-identical across the fix. v1.0.1 supersedes v1.0.0 for
submission use; v1.0.0 is preserved immutable for historical reproducibility.

## 6. Manuscript still needs a human read-through

This conversion preserved every scientific claim, statistic, and citation from the
frozen IEEE source, adapted section numbering and citation style for Elsevier, and fixed
the one internal contradiction described in item 5 (COSE version only). It has not been
read by a human co-author or a native-English copyeditor. Recommended before submission,
not because errors are known to exist, but because no automated pass substitutes for a
human final read.

## 7. Author name — RESOLVED

**Status: RESOLVED.** The author publishes under the mononym **Hardik**, by their own
decision. This is consistent across the manuscript, `CITATION.cff` (using the CFF
schema's `name:` field, which exists precisely for unsplittable single names), and
`release/zenodo/metadata.md`.

Practical note for the submission systems: in Editorial Manager, enter the name in the
last-name field and leave the first-name field empty. Zenodo takes the same convention.
Both systems accept mononyms; they just default to expecting a split.

## 8. CITATION.cff is behind the repository

**Status: RESOLVED**, except for the DOI. `CITATION.cff` now carries `version: 1.0.1`,
`date-released: "2026-08-24"`, the repository URL, the author's ORCID, the affiliation,
and the mononym expressed with the CFF `name:` field. It parses as valid YAML.

The `doi:` field is still commented out and must stay that way until Zenodo mints one.

## 9. ORCID record is near-empty

The author's ORCID is `0009-0001-1642-6669`, verified as theirs from the link published on
`github.com/meowlawat`. It is now recorded in `CITATION.cff`, `release/zenodo/metadata.md`,
and `paper/submission_metadata.md`, and should be entered in Editorial Manager.

The record itself, however, contains only the given name "hardik" — no family name, no
employment, no education, no works. An ORCID that resolves to a blank page is a weaker
signal to an editor than no ORCID at all.

Add: the IIT Patna and VIPS affiliations, and the two accepted papers (ETTIS 2026 /
Springer, and ICDSCNC 2026 / IEEE Xplore). This takes about ten minutes at
https://orcid.org and is the highest-value-per-minute item on this list.

**Status: non-blocking, strongly recommended before any future submission.**

## 10. Published Zenodo archive contains the withdrawn AI disclosure

The archive published at **DOI 10.5281/zenodo.22086254** (record version 1.0.2) was
deposited before the generative-AI declaration was removed from the manuscript. It
therefore still contains that declaration, in six files inside
`token-accounting-integrity-v1.0.1.zip`:

```
paper/main_cose.tex                      source
paper/main_cose.pdf                      compiled, 25 pp
paper/COSE_SUBMISSION_READINESS.md
paper/FINAL_SUBMISSION_MANIFEST.md
paper/submission_metadata.md
scripts/check_cose_submission.py
```

**The published record is not to be deleted, altered, or hidden.** It is an accurate
snapshot of what existed on the day it was deposited, and rewriting it to remove a record
of tool use would be a provenance problem, not a tidiness fix.

The correct mechanism, if a corrected archive is wanted, is a **new Zenodo version** that
supersedes it while leaving 10.5281/zenodo.22086254 permanently resolvable. The concept
DOI `10.5281/zenodo.22085827` already resolves to whatever the latest version is, so the
manuscript's own citation would not need to change.

**Status: author's decision. Not actioned.**
