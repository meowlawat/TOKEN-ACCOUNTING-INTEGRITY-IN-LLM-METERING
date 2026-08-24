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

## 2. Corresponding-author email choice

`paper/main_cose.tex` currently lists `hardikahlawat13@gmail.com` (personal address, as
supplied directly for this submission). The author's own resume lists an institutional
address, `hardik24a12res263@iitp.ac.in`. Academic corresponding-author addresses are
conventionally institutional. This is a judgment call for the author, not something this
conversion should decide unilaterally — flagged in `submission_metadata.md` as well.

**Status: non-blocking, but should be a deliberate choice before submission**, not an
oversight.

## 3. Author biography and photograph

Computers & Security's author guide requests a short biography and a passport-style
photograph per author. Neither exists and neither was invented. `paper/author_bio.txt`
holds the biography placeholder, with the verified affiliation already filled in and a
word-count target; `paper/AUTHOR_PHOTO_REQUIRED.md` holds the photograph requirements.
A portrait of a real person is not something to synthesise or substitute, so this one
cannot be closed from inside the repository at all.

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

## 7. Author name is a single word

`paper/main_cose.tex` prints `uthor{Hardik}`, and `CITATION.cff` carries
`family-names: Hardik` with `given-names` empty. Elsevier's Editorial Manager and Zenodo
both take given name and family name as separate fields, and anyone citing this paper
needs a family name to put in their reference list.

The corresponding-author address supplied for this submission hints at a surname, but a
family name that will appear on a publication and in other people's bibliographies is not
something to infer from an email address. The author must state it.

Once stated it must be changed in three places together, or the manuscript, the software
citation, and the dataset deposition will disagree about who wrote this:

```
paper/main_cose.tex          uthor{...}
CITATION.cff                 authors: family-names / given-names
release/zenodo/metadata.md   Authors section
```

**Status: BLOCKING.** This is not a formatting preference; a submission whose author
field cannot be parsed into given/family names is a submission that will come back.

## 8. CITATION.cff is behind the repository

`CITATION.cff` still says `version: 1.0.0`, carries `date-released: "2026-08-22"`, and
leaves `repository-code` commented out even though the GitHub remote now exists. It needs
`version: 1.0.1`, the release date of the actual v1.0.1 release, the repository URL, and
eventually the Zenodo DOI. Deliberately not updated here alongside the name fix, since
changing the author field is item 7's decision and the file should be corrected once,
completely, rather than twice.

**Status: non-blocking for the journal**, but it makes the artifact cite itself
incorrectly, so close it before announcing the release.
