# GitHub release report — v1.0.0

---

## Repository URL

**NOT CONFIGURED.** `git remote -v` returns nothing, and the GitHub CLI (`gh`) is not
installed on this machine. No remote was invented, and nothing was pushed.

The release is complete and tagged **locally**. To publish it, configure a remote you own
and push — nothing else about the release needs to change:

```bash
cd "E:\se paper"
git remote add origin https://github.com/<your-account>/<repo>.git
git push -u origin master
git push origin v1.0.0
```

If you would rather keep it private, create the repository as private first; the push
command is identical. After pushing, verify with:

```bash
git ls-remote --tags origin        # expect refs/tags/v1.0.0
git rev-parse HEAD                 # must match the remote head
```

## Branch

`master`

## Commit

Whatever `v1.0.0` points at — resolve it with `git rev-list -n1 v1.0.0`.

`8775e26` is the freeze commit itself. The commits after it add this report and
correct hand-typed inventory counts; no experimental result, formal outcome or
claim changed in any of them. The hash is deliberately not written out here: a
document that names the commit recording it can never be accurate, because
writing the hash changes the hash.

## Tag

`v1.0.0` — annotated: *"Frozen journal-submission artifact for Token-Accounting
Integrity"*

## Release

**BLOCKED.** A GitHub release cannot be created without a remote and an authenticated
`gh`. Once the remote exists and `gh auth login` has been run:

```bash
gh release create v1.0.0 \
  --title "Token-Accounting Integrity v1.0.0 — Journal Submission Artifact" \
  --notes-file RELEASE_NOTES.md
```

`RELEASE_NOTES.md` is written and ready to be used as the release body. The paper does not
need to be attached separately — `paper/main_ieee.pdf` is tracked in the repository.

## Files intentionally excluded

| excluded | size | how to restore |
|---|---|---|
| `vendor/` (llama.cpp binary, SmolLM2 GGUF weights) | 184 MB | download commands in `README.md` |
| `tokenizer_cache/` (HF + tiktoken artifacts) | 268 MB | `bash scripts/populate_tokenizer_cache.sh` |
| `formal/tools/tla2tools.jar` | 2.2 MB | one-line `curl` in `formal/README.md` |
| `__pycache__/`, `.pytest_cache/`, build scratch | — | regenerated on run |
| LaTeX intermediates (`.aux`, `.log`, `.out`, `.synctex.gz`) | — | regenerated on compile |
| `.env`, credentials, private keys | — | never existed in this repository |
| Docker images, volumes, build cache | — | `docker compose up --build` |

Every exclusion is downloadable or regenerable and has a documented command. None of it is
scientific evidence.

## Scientific artifacts preserved

**All of it.** 312 tracked files.

| kind | detail |
|---|---|
| Raw data | 34 files in `results/raw/` covering B0, M1, M2, the topology sweeps, backend comparison, real serving stack, asynchronous accounting, the cached-split probe and cross-validation |
| Processed summaries | 18 files, each produced through a fail-closed integrity gate |
| Tables | 67 generated Markdown/LaTeX files including the IEEE variants |
| Figures | 9 generated figures |
| Formal outputs | `results/formal/model_check_results.json` with every counterexample trace |
| Audit outputs | `audit/` — independent recomputation, spec-derived M2 model, confirmation-bias review |
| Papers | `paper/main_ieee.{tex,pdf}` (final) and `paper/main.{tex,pdf}` (superseded, retained for provenance) |
| Provenance | `results/reproduction_manifest.json` (132 artifact hashes + PDF hash), `results/environment.json` |

Superseded datasets were **not** deleted. Records carrying the withdrawn `detection_level`
classification were **not** rewritten — they are retained so historical runs stay
byte-reproducible, and are marked withdrawn in the code that writes them and in the paper.

## Secret scan

**PASS — 0 secrets found.**

Scanned tracked files for `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AWS_ACCESS_KEY`,
`AWS_SECRET`, `GITHUB_TOKEN`, `PASSWORD=`, `SECRET=`, `BEGIN … PRIVATE KEY`, `ghp_`,
`sk-…`, and for `.env`, `credentials*`, `*.pem`, `*.key`, `*.p12`, `*.crt`, `id_rsa`.

The only credential-shaped string is `postgres:postgres` in the Docker Compose files — the
throwaway local database login for a testbed that binds to localhost. `.env.example` is
tracked deliberately and contains only localhost defaults and mock pricing constants.

Staged content was re-scanned before committing. No machine-specific absolute paths
(`E:\se paper`, `C:\Users\…`) appear in any tracked file.

## Regression

**PASS**

| suite | result |
|---|---|
| `regression_class6` | 19/19 |
| `regression_m` | 16/16 |
| `metamorphic_checks` | 22/22 |
| `run_cross_validation` | all implementations agree |

## Independent verification

**PASS**

| check | result |
|---|---|
| `audit/recompute_all.py` (zero project imports) | 0 discrepancies |
| `audit/m2_independent_check.py` (specification-derived) | 0 mismatches |
| Claim-evidence matrix | 44 claims, 0 unsupported |
| Reference audit | 26 entries, 0 undefined, 0 uncited, 0 duplicates |

## TLA+

**PASS** — 40/40 checks matched pre-declared expectations, 27,526 distinct states, 0
disagreements, deterministic under `-workers 1`.

## PDF

**PASS** — `paper/main_ieee.pdf`: valid, 13 pages, no blank pages, title and author
(Hardik, enrollment 03517713524) correct, abstract present, index terms present, 5 embedded
figures, references render last, 0 overfull boxes, 0 undefined references or citations.

## Working tree

**CLEAN** — `git status --porcelain` returns nothing. `git fsck` reports only dangling
objects from earlier amended work, which is normal and harmless.

## Disk reclaimed during freeze

| item | reclaimed |
|---|---|
| Docker build cache | 7.48 GB |
| Docker images | 5.69 GB |
| Docker volumes | 207 MB |
| Docker containers | 66 MB |
| `tokenizer_cache/` | 268 MB |
| `vendor/` | 184 MB |
| `__pycache__` and build scratch | small |
| **Total** | **≈ 13.9 GB** |

Project directory: **508 MB → 58 MB**, of which 17 MB is `.git` and 37 MB is scientific
data. Nothing deleted was scientific evidence, and every deleted item has a documented
command to restore it.

> **One caveat, stated plainly.** The instruction was to clean up *after* pushing to
> GitHub. The push did not happen, because there is no remote. The cleanup was therefore
> limited to items that are regenerable or downloadable, and the repository — which holds
> the only copy of the research — was left completely intact. Do not delete `E:\se paper`
> until `git push` has succeeded.
