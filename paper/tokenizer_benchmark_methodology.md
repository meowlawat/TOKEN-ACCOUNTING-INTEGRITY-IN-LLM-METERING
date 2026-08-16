# Tokenizer & Recount Benchmark Methodology

This document backs the claims about what a **server-side token recount** actually
costs. It exists because the earlier mock-model figure (+0.1 ms) was not a real
tokenizer measurement and must not be cited as one.

Two separate benchmarks, deliberately kept distinct:

| benchmark | question | file | raw output |
|---|---|---|---|
| Tokenizer microbenchmark | What does one `encode()` call cost, in isolation? | `benchmarks/tokenizer_overhead.py` | `results/raw/tokenizer_overhead_*.json` |
| Gateway recount benchmark | What does enabling recount cost the *gateway* end-to-end? | `benchmarks/gateway_recount_overhead.py` | `results/raw/gateway_recount_*.json` |

> **Standalone tokenizer cost ≠ gateway throughput cost.** The microbenchmark measures
> a CPU-bound function call with no I/O, no HTTP, no database. The gateway benchmark
> measures the same work inside the real metered request path. Neither may be
> substituted for the other, and neither is a production-model result.

---

## 1. Environment

Recorded automatically into every raw JSON (`environment` block):

- **OS:** Windows 11 (build 26200), Docker Desktop with a Linux VM backend
- **CPU:** Intel i5-13450HX, **16 logical CPUs**
- **RAM:** 16 GB (host); container limit reported by Docker as ~10.4 GiB
- **Host Python:** 3.13.5 (benchmark driver)
- **Container Python:** 3.11-slim (gateway)
- **PostgreSQL:** 16 (`READ COMMITTED`), **Redis:** 7

## 2. Tokenizer engines and exact revisions

Recorded in the `engines` block of the raw JSON. No model weights are downloaded —
only tokenizer artifacts — and nothing is fetched silently at benchmark time (the
container runs fully offline from a pre-populated, read-only mounted cache).

| engine | library | version | artifact / revision | vocab |
|---|---|---|---|---|
| `tiktoken/cl100k_base` | tiktoken | 0.13.0 | encoding `cl100k_base` (pinned by library version) | 100 277 |
| `tiktoken/o200k_base` | tiktoken | 0.13.0 | encoding `o200k_base` | 200 019 |
| `hf-fast/auto` | transformers | 5.15.0 | `hf-internal-testing/llama-tokenizer` @ `d02ad6cb9dd2c2296a6332199fa2fdca5938fef0` | 32 000 |
| `hf-fast/llama` | tokenizers | 0.22.2 | same repo/revision, loaded directly from `tokenizer.json` (SHA-256 recorded) | 32 000 |
| `sentencepiece/llama` | sentencepiece | 0.2.2 | same repo/revision, `tokenizer.model` (SHA-256 recorded) | 32 000 |

**Why an open Llama-family tokenizer?** `meta-llama/*` repos are gated and would
require credentials; `hf-internal-testing/llama-tokenizer` is the open,
non-gated Llama tokenizer used for exactly this purpose. Its `tokenizer.model` is
the SentencePiece artifact, so the HF and SentencePiece rows are the *same*
tokenizer via two different runtimes — an intentional apples-to-apples comparison of
implementation cost, not of vocabulary.

**Fast vs slow matters.** In `transformers` 5.15 the Llama `AutoTokenizer` resolves
to a **fast (Rust)** tokenizer; we additionally load the Rust backend directly and
the pure SentencePiece runtime, so the table separates *algorithm* from *runtime*.

## 3. Token-length construction (the critical invariant)

Target lengths: **256, 1024, 4096, 16384, 32768**.

The same text does **not** produce the same token count under different tokenizers.
Therefore every `(engine, workload, length)` cell constructs **its own** input and
enforces:

```
len(encode(text)) == target_length        # exact, asserted, per cell
```

Construction (`benchmarks/_workloads.py`): generate an over-long seeded corpus →
truncate in *token* space → decode → re-encode → iteratively repair (decode/encode
round-trips are not stable under byte-fallback/merge boundaries) → fine-tune by
appending/trimming single characters. Cells that cannot reach the exact target are
recorded with `status != "ok"` and excluded — never silently mis-labelled.
**In the reported run all 75 cells reached their exact target.**

## 4. Workloads

Three seeded families (`seed = 1337`), chosen to bracket BPE behaviour:

1. **natural** — English prose from a fixed word bank (~4 chars/token).
2. **code** — Python/SQL/JSON-like structured text (punctuation-dense).
3. **high_entropy** — random alphanumerics (worst case: approaches 1 token/char,
   exercises byte fallback).

## 5. Timing and repetitions

- Clock: `time.perf_counter_ns()` (monotonic, nanosecond resolution).
- **Warm-up:** 5 untimed calls per cell before measurement.
- **Cold vs warm:** the *first* call after a `gc.collect()` is recorded separately as
  `cold_ms` (n = 1, includes lazy internal caches); `cold_warm_ratio` reports how much
  the first call over-states steady state. All headline numbers are **warm**.
- **Repetition count is adaptive, not a copied constant.** After warm-up a single
  probe call is timed, then
  `reps = clamp(1.5 s / probe_time, 30, 300)`.
  Short inputs therefore get 300 reps and 32 768-token inputs get ~30; the **actual**
  rep count is stored per cell (`reps`) and appears in the CSV. Rationale: the
  measured per-cell dispersion is small relative to the between-engine differences we
  are resolving (which span 3–5×), so a 1.5 s budget is ample; spending equal reps on
  every cell would waste ~20 minutes to sharpen an already-unambiguous ordering.
- Reported statistics: mean, std, p50, p95, p99, min, max, plus `tokens_per_sec` and
  `us_per_token` derived at p50.

## 6. Memory measurement (and what it does NOT mean)

- `tracemalloc_peak_python_heap_kib` is the **Python-heap** allocation peak measured
  around the timed loop. It is **not** total process memory. tiktoken, HF-fast and
  SentencePiece do most allocation in **native Rust/C** buffers that `tracemalloc`
  cannot see, so this number under-states true memory traffic and is reported only as
  a Python-side allocation-pressure signal.
- Process **RSS** before/after each cell (`psutil`) is reported separately. RSS is
  noisy (allocator retention, GC timing, OS accounting) and deltas near zero should
  not be read as "no memory used".
- No claim is made about peak native tokenizer memory; measuring that would require
  an allocator-level profiler and is out of scope.

## 7. Gateway benchmark methodology

- **Postures:** (A) `recount_engine="none"` — the gateway trusts a client-declared
  count; (B) a real engine — the gateway performs a server-authoritative
  `encode()` on the request text. Both run the identical accounting path
  (auth → [recount] → atomic debit → respond), so the difference isolates the recount.
- **Controlled concurrency:** a fixed pool of `c` worker tasks pulls from a shared
  queue for a fixed wall-clock duration (default 5 s/cell). Each worker starts its
  next request only when its previous one completes, so in-flight load is a sustained
  `c` — *not* a one-shot `gather` of `c` tasks with uncontrolled start timing.
- **Sizes:** 256/1024/4096/16384 tokens, constructed **exact under `cl100k_base`**
  (the reference tokenizer). Other engines see a similar-but-different count for the
  same text; this is stated in the raw JSON rather than assumed equal.
- **Metrics:** requests/sec, successful requests/sec, p50/p95/p99 latency, error rate,
  server-measured tokenization component (`tokenize_ms`, timed inside the handler),
  total server handler time, and best-effort container CPU/memory via `docker stats`.
- **Headline derived quantity:** `throughput_ratio_vs_none` =
  `throughput_with_recount / throughput_without_recount` at the same (size, concurrency),
  plus p50/p99 latency deltas.
- **Single uvicorn worker.** Tokenization is CPU-bound and blocks the event loop.
  This is the realistic single-worker case and makes the measured impact an
  **upper bound** for a multi-worker deployment; a production gateway would run
  multiple workers or offload to a thread pool.

## 8. Known confounds and limitations

1. **Environment latency floor.** On Docker Desktop for Windows, a trivial
   `/bench/complete` round trip costs ~48 ms p50 (VM loopback + Postgres round trip).
   Small recounts (≤1024 tokens, ~0.2–2 ms) are therefore *invisible* against this
   floor: the measured throughput ratio is conservative — it **understates** the
   relative cost of recount that a low-latency production gateway would see. Absolute
   tokenization cost is reported separately (`tokenize_ms`) precisely so this confound
   does not contaminate the tokenizer conclusion.
2. **Standalone ≠ gateway.** Stated above; the two benchmarks are never merged.
3. **Mock model ≠ production model.** The gateway still uses the deterministic mock
   LLM for *generation*; only the *recount* is real. Real generation would add GPU
   time that dwarfs tokenization, which would make recount look relatively cheaper.
4. **Local concurrency ≠ internet-scale behaviour.** Single host, loopback, no real
   network jitter, no multi-tenant contention, no load balancer.
5. **Single-worker gateway** (see §7) — an upper bound, not a tuned deployment.
6. **Sizes are cl100k-exact**, so cross-engine gateway rows differ slightly in true
   token count for the same payload.
7. **Windows/Docker Desktop scheduling.** Host CPU is shared with the benchmark
   driver; cells were run sequentially, never concurrently with other benchmarks, but
   background OS activity is not controlled.
8. **No claim about which tokenizer a given commercial provider uses.** The engines
   are representative implementations, not attributions.

## 9. Reproducing

```bash
# one-time: populate the offline tokenizer cache used by the container
bash scripts/populate_tokenizer_cache.sh

docker compose up --build -d
python -m benchmarks.tokenizer_overhead          # ~13 min, 75 cells
python -m benchmarks.gateway_recount_overhead    # ~15 min
python -m benchmarks.summarize_benchmarks        # CSV + tables + figures
```
