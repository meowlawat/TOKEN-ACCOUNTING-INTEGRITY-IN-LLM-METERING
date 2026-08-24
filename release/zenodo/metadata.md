# Zenodo deposition metadata

Field-by-field values to enter in the Zenodo deposition form for the archival release of
the Token-Accounting Integrity artifact. Nothing here is a placeholder to be filled in
later except where explicitly marked **PENDING** — those are values Zenodo itself
generates, or values only the author can supply.

**The DOI now exists**, and this file is kept as the record of what the deposition should
contain — because the record as first published does not match it.

```
Concept DOI (cited in the manuscript):  10.5281/zenodo.22085827
Version DOI (v1.0.1):                   10.5281/zenodo.22085828
Record:                                 https://zenodo.org/records/22085828
```

**Deposited so far:** `main_cose.tex` and `main_cose.pdf` only.
**Not deposited:** `token-accounting-integrity-v1.0.1.zip`, which is the actual artifact.

The fields below are the ones to enter. Where the live record disagrees with them, the
live record is wrong. `paper/SUBMISSION_BLOCKERS.md` item 1 lists the four fixes and which
of them need a *New version* rather than a metadata edit.

---

## Upload type

```
Type:            Dataset          <- live record says "Journal article"; change it
Publication date: 2026-08-24
```

Zenodo also offers "Software". This deposition is chosen as **Dataset** because its
primary archival value is the measurement corpus and model-checking output; the code that
produced it is included and is also on GitHub, which is where its version history lives.

## Title

```
Token-Accounting Integrity in LLM Metering: reproducible testbed, measurement
corpus, and formal model (v1.0.1)
```

## Authors

```
Name:         Hardik
Affiliation:  Department of Computer Science and Data Analytics,
              Indian Institute of Technology Patna, India
ORCID:        0009-0001-1642-6669
```

The author publishes under the mononym "Hardik", by their own decision; this matches the
manuscript and `CITATION.cff`. Zenodo's name field accepts a single name — enter it in the
family-name box and leave the given-name box empty, which is how Zenodo renders mononyms.

The ORCID is verified as the author's: it is the link published on `github.com/meowlawat`,
the account that owns this repository. Note that the ORCID record itself is currently
near-empty; filling in affiliations and works before depositing makes it worth citing.

## Description

> Usage-based pricing makes metering a security boundary for LLM inference: value reaches
> the client while accounting is still open, and the charge depends on a usage record
> produced by the same pipeline that serves the request. This artifact accompanies a study
> of client-side under-payment in LLM metering under an honest-provider, dishonest-client
> threat model.
>
> It contains a vulnerable-by-construction FastAPI/PostgreSQL/Redis testbed with paired
> vulnerable and hardened implementations of each metering architecture; attack harnesses
> and defense reference implementations for three dimensions of failure — state
> synchronization (B0, a known baseline used to validate the rig), commitment timing (M1),
> and usage authority (M2); the complete raw and processed measurement corpus with the
> integrity checks that gate it; a TLA+ specification checked exhaustively with TLC
> (10 configurations x 4 invariants, 27,526 distinct states); independent recomputation
> and metamorphic-testing harnesses; and the scripts that regenerate every figure and
> table in the paper from the raw data.
>
> All measurements were produced against the local testbed included here. No third-party,
> live, or production system was probed, scanned, or attacked, and no real user data or
> provider billing API was involved.
>
> The accompanying manuscript is under submission and is not peer-reviewed. No claim in
> the artifact should be read as a validated finding about any named commercial provider.

## Version

```
v1.0.1
```

`v1.0.1` supersedes `v1.0.0` for citation. `v1.0.0` is preserved unchanged as the
historical record of what was frozen at that point; the difference is a scientific
*consistency* correction to how the B0 condition is stated, not a change to any measured
value. See `RELEASE_NOTES.md`.

## License

```
MIT (code and data)               <- live record says CC-BY-4.0; change it
```

Matches `LICENSE` in the repository, which is what the archive mostly contains. CC-BY is a
content licence and fits software poorly. Zenodo's Open Access setting applies.

## Keywords

```
LLM security
usage metering
token accounting
billing integrity
economic security
API security
streaming inference
quota enforcement
model checking
TLA+
```

These match `CITATION.cff`. The manuscript's own keyword list is shorter and differently
ordered because Elsevier caps it; that is expected, not an inconsistency.

## Related identifiers

```
is supplement to      https://github.com/meowlawat/TOKEN-ACCOUNTING-INTEGRITY-IN-LLM-METERING
is identical to       Git tag v1.0.1
is supplement to      <journal DOI>  -- PENDING: add only after acceptance
```

Note: the record is currently typed as a journal article, which implies a publication that
does not exist. The paper is under submission and has not been accepted.

## Files

```
token-accounting-integrity-v1.0.1.zip
```

Checksum in `SHA256SUMS.txt`; complete file list in `ARCHIVE_CONTENTS.md`. The archive is
built from the tracked tree at the tagged commit by `scripts/build_zenodo_archive.py` and
rebuilds byte-identically, so the published checksum stays verifiable.

## What is not in the archive, and why

Everything excluded is regenerable, and each has a documented command:

| excluded | regenerate with |
|---|---|
| `tokenizer_cache/` | `scripts/populate_tokenizer_cache.sh` |
| llama.cpp binary, `*.gguf` weights | download commands in `README.md` |
| `formal/tools/tla2tools.jar` | download command in `formal/README.md` |
| LaTeX intermediates | `tectonic -X compile paper/main_cose.tex` |

Secrets, key material, Docker volumes, editor/OS metadata, and experiment scratch were
never tracked and are therefore absent by construction rather than by filtering.

---

## After publishing

Done already, now that the DOI exists:

1. `CITATION.cff` carries `doi: 10.5281/zenodo.22085827`.
2. The manuscript's data-availability statement cites the concept DOI and names the
   version DOI; the placeholder is gone, and the gate fails if it ever returns.
3. `README.md` carries the Zenodo badge.
4. `scripts/check_cose_submission.py` passes 34/34, including two new checks: no
   unminted-DOI placeholder, and the concept DOI present.

Still to do, on Zenodo rather than here: the four fixes in `paper/SUBMISSION_BLOCKERS.md`
item 1. Because the manuscript cites the **concept** DOI, publishing a new version does
not invalidate anything already printed — that is why the concept DOI was chosen.
