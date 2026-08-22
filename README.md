# Token-Accounting Integrity in LLM Metering

A reproducible testbed, attack harness, defense implementations and formal model for
**client-side under-payment** in LLM metering architectures.

Usage-based pricing makes metering a security boundary. Value reaches the client while
accounting is still open, and the amount charged depends on a multi-category usage record
that only exists once the request has run. Most security work on this boundary assumes the
client is honest: dishonest *providers* inflating hidden token counts, third parties
draining a *victim's* budget, intermediaries forging provenance. This project studies the
remaining direction — a legitimate, authenticated client that under-pays — and pairs every
attack with a defense.

**No new attack primitive is claimed.** Each enabling mechanism is individually known. The
contribution is their unification under one integrity property, a taxonomy that separates
them into experimentally distinguishable dimensions, exhaustive model checking of the
defense conditions, and a measurement study across three execution topologies, three
accounting families and two independent inference data planes.

> **Ethics (hard rule).** Everything here targets only the locally-built testbed. The
> harness defaults to `localhost` and contains no third-party endpoints. Never point it at
> any third-party, live or production system. No credentials, real user data or production
> billing APIs were used in this work.

**Status:** frozen at `v1.0.0` — see [`RELEASE_FREEZE.md`](./RELEASE_FREEZE.md).
**Paper:** [`paper/main_ieee.pdf`](./paper/main_ieee.pdf).

---

## Research question

Can a dishonest client obtain metered LLM inference while paying less than it owes, and
which server-side conditions actually prevent it?

Formally, for a request `r` with delivered value `V(r)`, committed debits `D(r)`, refunds
`F(r)` and net debit `N(r) = D(r) − F(r)`:

```
Leak(r)      = V(r) − N(r)
Integrity(r) : V(r) ≤ N(r)
```

The inequality is over the *net* debit so that legitimate reconciliation is admitted: a
client that consumes less than its reservation must be refunded the difference. A refund is
legitimate only when it releases the unconsumed portion, `F(r) ≤ Res(r) − V(r)`.

## The three dimensions

| | mechanism | failure | defense condition |
|---|---|---|---|
| **B0** | State synchronization *(known baseline, not a contribution)* | Authorization reads credit state that does not yet reflect prior commitments | Authorization atomically coupled to economic commitment **on the path that authorizes service** |
| **M1** | Commitment timing | A terminal path leaves the lifecycle without a committed debit, or refunds more than the unconsumed reservation | Terminal-path totality **and** refund boundedness; reservation, separately, for solvency |
| **M2** | Usage authority | Correct usage is computed and stored, but billing reads a client-influenced representation | Billing basis derived from state outside attacker control |

Two results are worth stating up front because they are counter-intuitive:

- **Reservation and abort-safe finalization are orthogonal.** Reservation alone secures
  solvency and loses integrity. Abort-safe finalization alone secures integrity and drives
  the balance negative. Only both together give both. Established over all four combinations
  by exhaustive model checking.
- **Computing usage correctly is not the same as billing from it.** An architecture that
  recounts accurately, stores the result, and still charges the client-declared number leaks
  **58.3 %** of delivered value in the controlled setting and **69.0 %** against a real
  serving stack.

**B0 is not about concurrency.** Under asynchronous settlement with *strictly sequential*
arrivals 20 ms apart, over-serving appears once the reconciliation delay reaches 100 ms. An
atomic guarded decrement provides nothing if it lands after the next authorization has
already read the balance.

## Threat model

Honest provider; dishonest client holding valid credentials. The client controls request
payloads including client-declared usage fields, permitted headers, request concurrency, the
connection lifecycle (it may abort at any moment), retries, and observation of its own
responses and balance. It cannot compromise TLS, reach the database or Redis, read the
gateway filesystem, compromise the inference backend, forge authenticated upstream metadata,
or modify server code.

Attacker knowledge is graded: **K0** client-observable only, **K1** provider-reported usage,
**K2** oracle access to true usage. The headline M2 result is K0-feasible.

## Architecture

```
client ──HTTP/SSE──▶ FastAPI gateway ──▶ inference (deterministic generator | llama.cpp)
                          │
                          ├── accounting backend A: mutable balance row
                          ├── accounting backend B: append-only ledger, derived balance
                          └── accounting backend C: event queue + async worker
                          │
                    PostgreSQL 16 (READ COMMITTED) + Redis 7
```

Five M1 architectures and six M2 architectures sit behind common interfaces, so experiments
compare *semantics* rather than unrelated code. Every mechanism has a vulnerable and a
hardened implementation.

## Repository layout

```
app/            testbed gateway: routes, architectures, accounting backends, LLM adapters
attacks/        one attack module per mechanism
defenses/       one defense module per mechanism
experiments/    runners (raw JSON only), summarizers, integrity gates, cross-validation
benchmarks/     real-tokenizer and gateway recount microbenchmarks
formal/         TLA+ specification, TLC configurations, checking driver
audit/          independent recomputation; imports nothing from the project
results/        raw data, processed summaries, generated tables and figures
paper/          IEEE manuscript, supporting analyses, audits
scripts/        reproduction entry points and release audits
deploy/         nginx configs for the multi-worker and distributed topologies
```

## Prerequisites

- Docker with Compose
- Python 3.11+ on the host, with `pip install -r requirements.txt`
- Optional, for the PDF: [`tectonic`](https://tectonic-typesetting.github.io)
- Optional, for formal checking: nothing — `jdk4py` ships a JDK as a wheel

## Quickstart

```bash
# 1. bring up the stack (gateway :8000, PostgreSQL :5432, Redis :6379)
docker compose up --build -d
curl -s http://localhost:8000/health

# 2. host-side client dependencies
pip install -r requirements.txt

# 3. controls and safety-invariant checks (must all pass)
python -m experiments.regression_class6      # 19/19
python -m experiments.regression_m           # 16/16
```

## Reproducing the study

Full pipeline, roughly one hour on a commodity host:

```bash
bash scripts/reproduce_all.sh          # Linux/macOS/Git-Bash
powershell -File scripts/reproduce_all.ps1   # Windows
```

Or step by step:

```bash
# B0 baseline
python -m experiments.run_class6 --affordable 10 --concurrency 1 2 5 10 20 30 50 --reps 30
python -m experiments.summarize_class6

# M1 commitment timing
python -m experiments.run_m1 --concurrency 1 5 20 50 100 --requests-per-cell 20
python -m experiments.summarize_m1

# M2 usage authority
python -m experiments.run_m2 --concurrency 1 5 20 50 100 --requests-per-cell 20
python -m experiments.summarize_m2

# ablation, lifecycle failure modes, cross-validation
python -m experiments.run_ablation --reps 10
python -m experiments.run_failure_modes --reps 5
python -m experiments.run_cross_validation --reps 5
python -m experiments.summarize_ablation

# economic sensitivity across three price tiers
python -m experiments.run_m2 --tiers low medium high --concurrency 1 \
    --requests-per-cell 20 --out results/raw/m2_tiers.json
python -m experiments.economic_analysis
```

### Formal verification

```bash
pip install jdk4py
curl -sSL -o formal/tools/tla2tools.jar \
  https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar

python formal/check.py            # all 10 configurations x 4 invariants
python formal/check.py m1_        # only M1
python experiments/build_formal_docs.py   # regenerate the formal tables
```

Expected: **40/40 matched, 27,526 distinct states, 0 disagreements.** The script exits
non-zero if TLC disagrees with the expectations declared in it before the run.

### Asynchronous accounting

```bash
python -m experiments.run_async_accounting --reps 5
python -m experiments.summarize_async
```

### Real-serving validation

Requires a local `llama.cpp` server. It is not vendored — download it and a small GGUF:

```bash
mkdir -p vendor/llama vendor/models
# binary (adjust for your platform; see https://github.com/ggml-org/llama.cpp/releases)
curl -sSL -o vendor/llama.zip \
  https://github.com/ggml-org/llama.cpp/releases/download/b10488/llama-b10488-bin-win-cpu-x64.zip
python -c "import zipfile;zipfile.ZipFile('vendor/llama.zip').extractall('vendor/llama')"
# weights
curl -L -o vendor/models/SmolLM2-135M-Instruct-Q8_0.gguf \
  https://huggingface.co/unsloth/SmolLM2-135M-Instruct-GGUF/resolve/main/SmolLM2-135M-Instruct-Q8_0.gguf

# serve
./vendor/llama/llama-server -m vendor/models/SmolLM2-135M-Instruct-Q8_0.gguf \
  --host 127.0.0.1 --port 8899 -c 2048 -t 4 --no-webui &

# the gateway reaches it at host.docker.internal:8899 (set in docker-compose.yml)
curl -s http://localhost:8000/admin/real-stack

python -m experiments.run_real_stack --reps 5
python -m experiments.cached_split_probe --repeats 4 --prompts 3
python -m experiments.summarize_real_stack
```

### Real-tokenizer benchmarks

The container performs no network access at request time, so tokenizer artifacts are
supplied through a mounted cache:

```bash
bash scripts/populate_tokenizer_cache.sh    # one-time, needs network
python -m benchmarks.tokenizer_overhead
python -m benchmarks.summarize_benchmarks
```

### Independent verification

Code under `audit/` imports nothing from the project and re-derives every reported quantity
from raw data:

```bash
python audit/recompute_all.py           # expect: 0 discrepancies
python audit/m2_independent_check.py    # expect: 0 mismatches
python -m experiments.metamorphic_checks   # expect: 22/22
python experiments/build_claim_matrix.py   # expect: 0 unsupported claims
```

### Regenerating tables, figures and the paper

```bash
python -m experiments.summarize_class6
python -m experiments.summarize_m1
python -m experiments.summarize_m2
python -m experiments.summarize_generality
python -m experiments.statistical_analysis
python scripts/make_ieee_tables.py

cd paper && tectonic -X compile main_ieee.tex
cd .. && python scripts/audit_references.py && python scripts/audit_ieee_format.py
```

Every table and figure in the paper is generated from raw data. None is hand-edited.

## The paper

**[`paper/main_ieee.pdf`](./paper/main_ieee.pdf)** — 13 pages, 26 references.

`paper/main.tex` and `main.pdf` are the superseded pre-IEEE version, retained for
provenance. Supporting analyses live alongside them: `formal_verification.md`,
`scope_of_formal_claims.md`, `defense_sufficiency.md`, `formal_empirical_mapping.md`,
`claim_evidence_matrix.csv`, and the reviewer simulations.

## Known limitations

No mechanized refinement proof from the TLA+ specification to the implementation. The formal
model is finite (2–3 requests, unit pricing) and checks safety only. The asynchronous
accounting family is measured but not formally modelled. Reconciliation delays are injected,
not observed in production. B0's independence from the storage backend is untested. One
physical host, one local serving stack, one small model. Pricing tiers are synthetic and
there is deliberately no revenue-impact model. **No commercial provider was tested.**

Detectability was claimed in an earlier version and is **withdrawn** — our own audit showed
the instrumentation restated experimenter-assigned labels rather than measuring evidence.
See `audit/confirmation_bias.md`.

## Citation

See [`CITATION.cff`](./CITATION.cff). The manuscript is prepared for journal submission; it
is not peer-reviewed and no DOI has been minted.

## License

MIT — see [`LICENSE`](./LICENSE). Third-party components (TLC, `llama.cpp`, model weights,
tokenizer artifacts) are downloaded by the commands above, not redistributed here.
