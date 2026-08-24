# Zenodo deposition metadata

Field-by-field values to enter in the Zenodo deposition form for the archival release of
the Token-Accounting Integrity artifact. Nothing here is a placeholder to be filled in
later except where explicitly marked **PENDING** — those are values Zenodo itself
generates, or values only the author can supply.

**No DOI exists yet.** It is minted by Zenodo at publication. Do not cite one, do not add
one to `CITATION.cff`, and do not write one into the manuscript before it has been issued.

---

## Upload type

```
Type:            Dataset
Publication date: <the date you press Publish>
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
MIT (code and data)
```

Matches `LICENSE` in the repository. Zenodo's Open Access setting applies.

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

Once Zenodo issues the DOI:

1. Add it to `CITATION.cff` (`doi:` field, currently a comment saying none is assigned).
2. Add it to the manuscript's data-availability statement, replacing the explicit
   placeholder — `paper/data_availability.md` marks the exact spot.
3. Add the Zenodo badge to `README.md`.
4. Re-run `python scripts/check_cose_submission.py`.

Do none of these before the DOI exists.
