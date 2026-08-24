# Submission blockers

Concrete, unresolved items that must be closed before `paper/main_cose.tex` is actually
submitted to Computers & Security. Nothing below was fabricated to make this list look
shorter than it is.

## 1. Zenodo DOI still required before submission

`paper/main_cose.tex`'s Data Availability section currently references the GitHub
release directly and states that an archival Zenodo snapshot is intended. Elsevier and
most funders now expect a persistent dataset DOI, not just a GitHub URL. Action:

The deposition is prepared and waiting. `release/zenodo/` contains the archive
(`token-accounting-integrity-v1.0.1.zip`, built from the tagged commit), its SHA-256
checksum, its complete file list, and `metadata.md` with every Zenodo form field already
filled in. What remains is the part only a human with the account can do:

1. Connect the GitHub repository to Zenodo (https://zenodo.org/account/settings/github/),
   or upload the prepared archive manually.
2. Create a GitHub release for tag `v1.0.1` — Zenodo archives on release creation, not on
   existing tags, so a fresh release is needed even though the tag already exists.
3. Enter the fields from `release/zenodo/metadata.md`. Note that the Authors field needs
   the name question in item 7 resolved first.
4. Zenodo mints the DOI. Insert it in place of `[ZENODO DOI TO BE INSERTED]` in
   `paper/main_cose.tex` and `paper/data_availability.md`, add it to `CITATION.cff`, then
   re-run `python scripts/check_cose_submission.py`.

**Status: BLOCKING.** Do not submit with a placeholder DOI string in the manuscript.

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
