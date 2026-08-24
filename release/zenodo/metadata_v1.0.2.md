# Zenodo deposition — new version v1.0.2

Field-by-field values for the **New version** of the Zenodo record. This corrects the
v1.0.1 deposition, which was published holding only the manuscript rather than the
research artifact.

**The existing record is preserved, not replaced.** Zenodo versioning keeps
`10.5281/zenodo.22085828` resolvable forever as the historical v1.0.1 deposition. This is
a forward correction, not a deletion.

---

## Why the version numbers look mismatched

The Zenodo record version is **1.0.2**. The archive inside it is the artifact of GitHub
tag **v1.0.1**. That is intentional and not an error:

- `v1.0.1` is the *research artifact* — frozen, and not being changed. No measured value,
  script, or result differs.
- `1.0.2` is the *deposition* version — a second attempt at depositing that same artifact,
  because the first attempt uploaded the wrong files.

The description below states this explicitly so nobody reads 1.0.2 as a new scientific
release.

## Upload type

```
Resource type:   Dataset
```

**Not "Journal article."** The current record is typed that way, which is wrong twice
over: the deposit is an artifact archive rather than an article, and typing it as a
journal article implies a publication that does not exist. The manuscript is under
submission to *Computers & Security* and has not been accepted.

## Files

```
UPLOAD:      release/zenodo/token-accounting-integrity-v1.0.1.zip
             332 files, 8,090,152 bytes
             SHA-256 in release/zenodo/SHA256SUMS.txt
```

```
DO NOT UPLOAD:
    paper/submission_forms/           -- author photograph, signed declaration,
                                         cover letter, reviewer suggestions
    any personal submission paperwork
```

The archive builder excludes `paper/submission_forms/` by construction, so the zip cannot
contain them. Verified: the only submission-forms path inside the archive is
`scripts/prepare_author_photo.py`, a tool, carrying no image data.

**Decide about the manuscript PDF.** The v1.0.1 record contains `main_cose.pdf`, which
makes it a preprint. Elsevier permits preprints but expects them declared at submission.
If a preprint was not intended, do not carry the PDF into this version.

## Title

```
Token-Accounting Integrity in LLM Metering: reproducible testbed, measurement
corpus, and formal model (artifact v1.0.1)
```

## Creator

```
Family name:   Hardik
Given names:   (leave empty)
ORCID:         0009-0001-1642-6669
Affiliation:   Department of Computer Science and Data Analytics, Indian Institute
               of Technology Patna, India
```

Zenodo's creator form requires a family-name value and treats given names as optional.
Placing the mononym in the family-name field is how Zenodo and DataCite represent a single
name — the required field carries the whole name. It is **not** a fabricated surname, and
no surname is being introduced. Leave given names empty.

The current record's `. , . hardik .` citation string is what happens when those fields are
filled the other way round.

Zenodo accepts one affiliation per creator. Use IIT Patna, where the work sits; the
manuscript carries both affiliations, and the second is recorded in the description below.

## Description

> Research artifact accompanying the manuscript "Token-Accounting Integrity in LLM
> Metering: A Systematic Study of Client-Side Under-Payment". It corresponds to release
> v1.0.1 of the GitHub repository.
>
> The archive contains: a vulnerable-by-construction FastAPI/PostgreSQL/Redis metering
> testbed with paired vulnerable and hardened implementations of each architecture; attack
> harnesses and defense reference implementations for three dimensions of accounting
> failure — state synchronization (B0), commitment timing (M1), and usage authority (M2);
> the complete raw and processed experimental results together with the integrity checks
> that gate them; the generated figures and tables; a TLA+ specification of the request
> lifecycle with its TLC model-checking outputs; independent recomputation and
> metamorphic-testing harnesses; reproduction scripts; and the methodology documentation.
>
> This Zenodo record is version 1.0.2. The archive it contains is the artifact of GitHub
> tag v1.0.1, unchanged. The version numbers differ because the previous deposition
> (10.5281/zenodo.22085828) mistakenly contained only the manuscript rather than the
> artifact; no experimental data, script, or result has changed between them.
>
> All measurements were produced against the local testbed included here. No third-party,
> live, or production system was probed, scanned, or attacked, and no real user data or
> provider billing API was involved.
>
> The accompanying manuscript is under submission to Elsevier Computers & Security. It is
> not peer-reviewed and has not been accepted. Author affiliations: Department of Computer
> Science and Data Analytics, Indian Institute of Technology Patna, India; and Vivekananda
> School of Engineering and Technology, Vivekananda Institute of Professional Studies —
> Technical Campus, New Delhi, India.

## Version

```
1.0.2
```

## Language

```
English
```

## License

```
MIT
```

**This is a correction, not a change of licence semantics.** The repository's actual policy
is uniformly MIT: `LICENSE` is the MIT text, `README.md` states "MIT — see LICENSE", and
third-party components (TLC, llama.cpp, model weights, tokenizer artifacts) are downloaded
by documented commands rather than redistributed. The archive was audited: it contains
exactly one licence file, the repository's own MIT, and no vendored third-party code.

The current record says CC-BY-4.0. That is the deviation — nothing in the repository ever
declared CC-BY. Setting the deposit to MIT restores agreement between the archive and the
licence it actually ships under.

**One honest caveat, for the author to decide.** MIT is a software licence, and this
archive is part code and part research data. Some depositors prefer to dual-licence: MIT
for the code, CC-BY-4.0 for the data and documentation. That is a legitimate choice and
arguably more precise for a mixed deposit. It is *not* being made here, because it would
change what the repository declares, and that is the author's call rather than a packaging
decision. If you want it: say so explicitly in the Zenodo description — a mixed-licence
deposit must be documented, never implied — and update `LICENSE` and `README.md` in the
same pass so the repository and the deposit do not disagree.

## Keywords

```
usage metering
token accounting
billing integrity
quota enforcement
API security
economic security
streaming inference
accounting reconciliation
model checking
```

## Software metadata

```
Repository:            https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING
Programming language:  Python
Development status:    Active
```

## Related identifiers

```
is new version of     10.5281/zenodo.22085828
is supplement to      https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING
is identical to       Git tag v1.0.1
```

Do **not** add a journal DOI. The paper has not been accepted.

## Journal metadata

```
Journal title:    (leave blank)
Volume:           (leave blank)
Issue:            (leave blank)
Article number:   (leave blank)
Pages:            (leave blank)
ISSN:             (leave blank)
```

The manuscript is not a published article. Filling these in would assert otherwise.

---

## After publishing

Zenodo mints a new version DOI. **Read it off the published record.** Do not guess it, and
do not assume it is the previous number plus one — Zenodo does not allocate them that way.

Then run, from the repository root:

```
python scripts/set_zenodo_doi.py 10.5281/zenodo.<NEW>
```

That script installs the version-specific DOI into `paper/main_cose.tex`,
`paper/data_availability.md`, `paper/submission_metadata.md`, `CITATION.cff`, and
`README.md` in one pass, so they cannot drift apart. It refuses anything that is not a
well-formed Zenodo DOI, and refuses the two DOIs already known to be wrong for this
purpose.

Afterwards:

```
tectonic -X compile paper/main_cose.tex
python scripts/check_cose_submission.py
```
