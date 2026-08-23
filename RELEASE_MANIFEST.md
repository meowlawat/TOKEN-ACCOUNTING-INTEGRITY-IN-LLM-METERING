# Release manifest — v1.0.0

What is in the release, and why each part is there. 312 tracked files.

---

## Root (13 files)

| path | why it is included |
|---|---|
| `README.md` | Entry point. An external researcher should be able to run everything from it without reading `CLAUDE.md`. |
| `ARTIFACT_README.md` | Artifact-evaluation view: what to run, expected runtime, expected outputs. |
| `RELEASE_FREEZE.md` | The frozen scientific state, with the exact limitations. |
| `RELEASE_MANIFEST.md` | This file. |
| `RELEASE_NOTES.md` | What v1.0.0 contains and what changed. |
| `FINAL_RESEARCH_REPORT.md` | Full research narrative and findings. |
| `AUDIT_REPORT.md` | Adversarial integrity audit (F1–F6) and the corrections it forced. |
| `JOURNAL_READINESS_REPORT.md` | Argued per-dimension ratings and per-venue assessment. |
| `CLAUDE.md` | Project working context. Retained because it records the taxonomy decisions, including the killed classes. |
| `LICENSE` | MIT. All shipped code is ours; third-party binaries are downloaded, never redistributed. |
| `CITATION.cff` | Citation metadata. No DOI is claimed because none has been minted. |
| `requirements.txt` | Pinned Python dependencies. |
| `.env.example` / `.gitignore` / `Dockerfile` / `docker-compose*.yml` | Environment and three deployment topologies. |

## `app/` (24 files) — the testbed

The vulnerable-by-construction gateway. FastAPI over PostgreSQL and Redis. Contains the B0
debit paths (`metering/`), the M1 and M2 architectures (`architectures/`), the three
accounting families (`accounting/`, including `async_worker.py`), the deterministic
generator and the real-serving adapter (`llm/`), and the request routes (`main.py`,
`m_routes.py`, `async_routes.py`).

Both a vulnerable and a hardened implementation exist behind each interface, so experiments
compare semantics rather than unrelated code.

## `attacks/` (4) and `defenses/` (5)

One module per mechanism. Every attack in the artifact is paired with a defense — that
pairing is an ethical requirement of the work, not a convention.

## `experiments/` (35) — runners, summarizers, gates

Runners write raw JSON only. Summarizers read raw JSON and emit CSV, Markdown, LaTeX and
figures, so every table and figure in the paper regenerates from data rather than by hand.
Includes the integrity gates, metamorphic checks, fault injection, cross-validation, the
claim-evidence matrix builder, and the provenance manifest builder.

## `formal/` (13) — TLA+ model

`TokenAccounting.tla` plus ten reviewer-runnable `.cfg` configurations and `check.py`,
which runs each invariant in its own TLC run and compares against expectations declared
before the run. `tools/tla2tools.jar` is **excluded** — it is a third-party binary with a
documented one-line download.

## `audit/` (11) — independent verification

Code that imports nothing from the project and re-derives every reported quantity from raw
data. Includes the specification-derived M2 model, the evidence-only detectability
classifier that led to that claim being withdrawn, the confirmation-bias review, and the
audit baselines.

## `benchmarks/` (7) and `deploy/` (2)

Real-tokenizer microbenchmarks and gateway recount benchmarks; nginx configurations for the
multi-worker and distributed topologies.

## `scripts/` (16)

Reproduction entry points (`reproduce_all.sh` / `.ps1`), the tokenizer-cache populator, the
reference verifier and the two release audits. The `_patch_*.py` files are one-shot,
idempotent edits kept for provenance: they show exactly how the manuscript was transformed.

## `results/` (132) — the scientific evidence

| path | count | contents |
|---|---|---|
| `results/raw/` | 34 | Per-request records from every experiment: B0, M1, M2, topology sweeps, backend comparison, real serving stack, asynchronous accounting, cached-split probe, cross-validation. **Superseded datasets are retained** where they support auditability. |
| `results/processed/` | 18 | Summaries produced by the summarizers, each gated. |
| `results/tables/` | 67 | Generated Markdown and LaTeX tables, including the `ieee/` variants. |
| `results/figures/` | 9 | Generated figures. |
| `results/formal/` | 1 | TLC model-checking results, including every counterexample trace. |
| `results/` (top) | 3 | Provenance manifest and environment record. |

**Nothing here was deleted to tidy the repository.** Historical records that carry a
withdrawn classification — the `detection_level` field in stored rows — are retained so
that historical runs stay byte-reproducible, and are marked as withdrawn in the code that
writes them and in the paper.

## `paper/` (43)

The IEEE manuscript and its PDF, the superseded pre-IEEE manuscript retained for
provenance, the generated state-machine figure, and the supporting analyses: formal
verification, scope of formal claims, defense sufficiency, formal-to-empirical mapping,
threat model, methodology, novelty audit, reviewer simulations, claim-evidence matrix, and
the two release audits.

---

## Deliberately excluded

| excluded | size | why, and how to get it back |
|---|---|---|
| `vendor/` | ~184 MB | `llama.cpp` binary and SmolLM2 GGUF weights. Third-party binaries; download commands are in the README. |
| `tokenizer_cache/` | ~268 MB | HuggingFace and tiktoken artifacts. Regenerate with `scripts/populate_tokenizer_cache.sh`. |
| `formal/tools/tla2tools.jar` | 2.2 MB | TLC. One-line download in `formal/README.md`. |
| `__pycache__/`, `.pytest_cache/` | — | Build artifacts. |
| LaTeX intermediates (`.aux`, `.log`, `.out`) | — | Regenerated on compile. Final PDFs are tracked. |
| `.env`, credentials, keys | — | Never committed. `.env.example` is the template and contains only localhost defaults. |
| Docker volumes and images | — | Recreated by `docker compose up --build`. |

The exclusions are all **downloadable or regenerable**, and every one has a documented
command. Excluding them keeps the repository at roughly 40 MB instead of 500 MB without
costing reproducibility.

## Not excluded, deliberately

Raw scientific data, generated figures and tables, formal specifications, the final PDFs
and every audit document are tracked. They are the evidence; a reader must be able to check
our arithmetic without re-running anything.
