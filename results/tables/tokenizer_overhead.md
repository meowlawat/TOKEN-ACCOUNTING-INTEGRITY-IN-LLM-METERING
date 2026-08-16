# Tokenizer recount overhead (standalone microbenchmark)

- Generated: `20260815T115624Z`
- **Scope:** Standalone tokenizer-call cost only. NOT a gateway throughput result; see benchmarks/gateway_recount_overhead.py.
- Host: Windows-11-10.0.26200-SP0, 16 logical CPUs, Python 3.13.5
- Reps: adaptive: reps = clamp(budget/probe_time, REP_MIN, REP_MAX); actual reps recorded per cell; warm-up 5 runs

## Engines / revisions

| engine | library | version | revision | vocab |
|---|---|---|---|---|
| `tiktoken/cl100k_base` | tiktoken | 0.13.0 | `tiktoken==0.13.0` | 100277 |
| `tiktoken/o200k_base` | tiktoken | 0.13.0 | `tiktoken==0.13.0` | 200019 |
| `hf-fast/auto` | transformers | 5.15.0 | `d02ad6cb9dd2c229` | 32000 |
| `hf-fast/llama` | tokenizers | 0.22.2 | `d02ad6cb9dd2c229` | 32000 |
| `sentencepiece/llama` | sentencepiece | 0.2.2 | `d02ad6cb9dd2c229` | 32000 |

## p50 latency (ms) — workload: natural

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.18 | 0.73 | 2.89 | 11.68 | 23.46 |
| `tiktoken/o200k_base` | 0.16 | 0.62 | 2.54 | 10.05 | 20.30 |
| `hf-fast/auto` | 0.43 | 1.68 | 7.48 | 38.21 | 77.47 |
| `hf-fast/llama` | 0.33 | 1.50 | 6.54 | 34.24 | 88.21 |
| `sentencepiece/llama` | 0.57 | 2.37 | 10.32 | 41.89 | 85.77 |

## p50 latency (ms) — workload: code

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.18 | 0.70 | 2.86 | 11.42 | 23.06 |
| `tiktoken/o200k_base` | 0.16 | 0.63 | 2.46 | 9.98 | 19.25 |
| `hf-fast/auto` | 0.30 | 1.02 | 4.07 | 17.95 | 39.04 |
| `hf-fast/llama` | 0.21 | 0.81 | 3.46 | 16.02 | 36.50 |
| `sentencepiece/llama` | 0.38 | 1.53 | 6.30 | 25.60 | 52.32 |

## p50 latency (ms) — workload: high_entropy

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.09 | 0.33 | 1.42 | 5.72 | 11.62 |
| `tiktoken/o200k_base` | 0.09 | 0.36 | 1.51 | 6.05 | 12.26 |
| `hf-fast/auto` | 0.22 | 0.71 | 2.80 | 10.83 | 23.66 |
| `hf-fast/llama` | 0.12 | 0.50 | 2.06 | 8.11 | 18.31 |
| `sentencepiece/llama` | 0.29 | 1.18 | 5.11 | 19.78 | 40.24 |

## Throughput (tokens/sec at p50, natural)

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 1,384,532 | 1,406,014 | 1,415,146 | 1,402,428 | 1,397,034 |
| `tiktoken/o200k_base` | 1,606,023 | 1,653,480 | 1,613,996 | 1,630,346 | 1,614,426 |
| `hf-fast/auto` | 597,433 | 610,469 | 547,337 | 428,777 | 423,000 |
| `hf-fast/llama` | 766,008 | 684,950 | 625,869 | 478,526 | 371,469 |
| `sentencepiece/llama` | 451,818 | 432,122 | 396,726 | 391,109 | 382,061 |

**Memory note:** `tracemalloc_peak_python_heap_kib` is Python-heap allocation ONLY; native Rust/C tokenizer buffers are not visible to it. Process RSS deltas are reported separately and are noisy.
