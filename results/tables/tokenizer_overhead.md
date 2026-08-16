# Tokenizer recount overhead (standalone microbenchmark)

- Generated: `20260816T123939Z`
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
| `tiktoken/cl100k_base` | 0.18 | 0.72 | 2.85 | 11.61 | 23.26 |
| `tiktoken/o200k_base` | 0.16 | 0.62 | 2.49 | 10.05 | 20.25 |
| `hf-fast/auto` | 0.44 | 1.65 | 7.17 | 36.07 | 76.18 |
| `hf-fast/llama` | 0.32 | 1.46 | 6.54 | 33.84 | 76.26 |
| `sentencepiece/llama` | 0.55 | 2.34 | 9.82 | 41.78 | 85.00 |

## p50 latency (ms) — workload: code

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.18 | 0.70 | 2.82 | 11.32 | 22.87 |
| `tiktoken/o200k_base` | 0.15 | 0.58 | 2.35 | 9.54 | 19.13 |
| `hf-fast/auto` | 0.30 | 1.00 | 3.98 | 17.95 | 38.78 |
| `hf-fast/llama` | 0.20 | 0.80 | 3.47 | 15.81 | 35.34 |
| `sentencepiece/llama` | 0.37 | 1.51 | 6.23 | 25.47 | 52.07 |

## p50 latency (ms) — workload: json

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.18 | 0.70 | 2.76 | 11.20 | 23.01 |
| `tiktoken/o200k_base` | 0.15 | 0.57 | 2.29 | 9.47 | 18.79 |
| `hf-fast/auto` | 0.25 | 0.84 | 3.21 | 14.42 | 31.56 |
| `hf-fast/llama` | 0.15 | 0.62 | 2.53 | 11.83 | 26.65 |
| `sentencepiece/llama` | 0.31 | 1.33 | 5.38 | 22.16 | 45.02 |

## p50 latency (ms) — workload: high_entropy

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.08 | 0.33 | 1.43 | 5.86 | 11.93 |
| `tiktoken/o200k_base` | 0.09 | 0.36 | 1.49 | 5.98 | 12.17 |
| `hf-fast/auto` | 0.22 | 0.69 | 2.63 | 10.56 | 23.46 |
| `hf-fast/llama` | 0.12 | 0.46 | 1.89 | 7.96 | 18.02 |
| `sentencepiece/llama` | 0.29 | 1.17 | 4.78 | 19.72 | 39.88 |

## Throughput (tokens/sec at p50, natural)

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 1,396,618 | 1,422,222 | 1,439,314 | 1,411,100 | 1,408,752 |
| `tiktoken/o200k_base` | 1,631,612 | 1,648,953 | 1,647,826 | 1,630,865 | 1,618,173 |
| `hf-fast/auto` | 588,100 | 620,230 | 570,927 | 454,195 | 430,135 |
| `hf-fast/llama` | 799,500 | 699,215 | 626,348 | 484,129 | 429,703 |
| `sentencepiece/llama` | 464,104 | 437,663 | 417,074 | 392,163 | 385,494 |

**Memory note:** `tracemalloc_peak_python_heap_kib` is Python-heap allocation ONLY; native Rust/C tokenizer buffers are not visible to it. Process RSS deltas are reported separately and are noisy.
