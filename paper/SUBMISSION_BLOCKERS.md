# Submission blockers

Concrete, unresolved items that must be closed before `paper/main_cose.tex` is actually
submitted to Computers & Security. Nothing below was fabricated to make this list look
shorter than it is.

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

**Four problems with the record as deposited.**

**1a. It contains the manuscript, not the artifact. BLOCKING.**

The record holds `main_cose.tex` (77,041 bytes) and `main_cose.pdf` (2,376,354 bytes).
It does not hold `token-accounting-integrity-v1.0.1.zip` — the 334-file, 8.1 MB archive
with the raw data, processed results, tables, figures, TLA+ model, harnesses, defenses,
and audit code.

The paper's data-availability statement says all raw experimental data are released. That
is true of GitHub. It is not true of the Zenodo record, and a reviewer who follows the DOI
expecting data will find a PDF. Fix this before submitting.

Zenodo locks files after publication, so this needs **New version** rather than an edit:

1. Open https://zenodo.org/records/22085828 and choose *New version*.
2. Upload `release/zenodo/token-accounting-integrity-v1.0.1.zip`.
3. Decide whether the manuscript PDF stays (see 1b).
4. Publish. A new version DOI is minted; the concept DOI in the paper keeps working, so
   **no manuscript edit is needed**.

**1b. Resource type is "Journal article". Should be Dataset or Software.**

Two things are wrong with this. The deposition is an artifact archive, not an article. And
this paper is not published in any journal — a Zenodo record typed as "Journal article"
implies it is. Change it to **Dataset** (or Software) in *Edit* → *Resource type*;
metadata is editable without a new version.

Separately, be aware that depositing the full manuscript PDF makes it a **preprint**.
Elsevier permits preprints, but it is worth declaring at submission rather than leaving an
editor to discover it. If you did not intend to publish a preprint, remove the PDF when
you create the new version in 1a.

**1c. Licence says CC-BY-4.0; the repository is MIT.**

`LICENSE` in the repository is MIT, and the archive is mostly code. CC-BY is a
content licence and is a poor fit for software. Set the record to **MIT** to match, or if
you want CC-BY for the data specifically, say so explicitly in the description so the two
do not silently contradict each other. Editable without a new version.

**1d. Creator name renders as ". , . hardik .".**

The name fields were filled in a way that produces that citation string. For the mononym,
put `Hardik` in the family-name field and leave given-name empty. While you are there, add
the ORCID `0009-0001-1642-6669` and the affiliations. Editable without a new version.

**Status: BLOCKING for 1a.** 1b, 1c and 1d are metadata edits that take a few minutes and
should be done in the same sitting.

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

**Photograph: still open, and not closeable here.** `paper/AUTHOR_PHOTO_REQUIRED.md`
records the requirements. A portrait of a real person is not something to synthesise or
substitute.

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

Before submitting, add: the IIT Patna and VIPS affiliations, and the two accepted papers
(ETTIS 2026 / Springer, and ICDSCNC 2026 / IEEE Xplore). This takes about ten minutes at
https://orcid.org and is the highest-value-per-minute item on this list.

**Status: non-blocking, strongly recommended.**
