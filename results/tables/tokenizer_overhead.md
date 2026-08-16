# Tokenizer recount overhead (standalone microbenchmark)

- Generated: `20260816T120624Z`
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
| `tiktoken/cl100k_base` | 0.19 | 0.73 | 2.92 | 11.84 | 23.34 |
| `tiktoken/o200k_base` | 0.16 | 0.62 | 2.53 | 10.21 | 20.65 |
| `hf-fast/auto` | 0.43 | 1.68 | 7.05 | 35.41 | 77.33 |
| `hf-fast/llama` | 0.33 | 1.49 | 6.52 | 33.70 | 73.91 |
| `sentencepiece/llama` | 0.56 | 2.37 | 9.86 | 41.37 | 85.23 |

## p50 latency (ms) — workload: code

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.21 | 0.71 | 2.88 | 11.53 | 22.96 |
| `tiktoken/o200k_base` | 0.16 | 0.61 | 2.47 | 9.77 | 19.76 |
| `hf-fast/auto` | 0.30 | 1.02 | 4.06 | 17.86 | 39.12 |
| `hf-fast/llama` | 0.20 | 0.81 | 3.40 | 15.68 | 35.26 |
| `sentencepiece/llama` | 0.37 | 1.52 | 6.26 | 25.58 | 52.00 |

## p50 latency (ms) — workload: json

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.18 | 0.70 | 2.75 | 11.21 | 23.17 |
| `tiktoken/o200k_base` | 0.15 | 0.59 | 2.33 | 9.42 | 18.97 |
| `hf-fast/auto` | 0.25 | 0.85 | 3.26 | 14.52 | 31.45 |
| `hf-fast/llama` | 0.15 | 0.63 | 2.55 | 11.89 | 26.85 |
| `sentencepiece/llama` | 0.31 | 1.33 | 5.43 | 22.18 | 44.97 |

## p50 latency (ms) — workload: high_entropy

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 0.09 | 0.33 | 1.41 | 5.90 | 11.75 |
| `tiktoken/o200k_base` | 0.09 | 0.36 | 1.49 | 6.55 | 13.08 |
| `hf-fast/auto` | 0.22 | 0.71 | 2.67 | 10.86 | 23.55 |
| `hf-fast/llama` | 0.12 | 0.47 | 1.92 | 7.93 | 18.07 |
| `sentencepiece/llama` | 0.30 | 1.21 | 5.08 | 19.38 | 40.19 |

## Throughput (tokens/sec at p50, natural)

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok | 32768 tok |
|---|---|---|---|---|---|
| `tiktoken/cl100k_base` | 1,373,391 | 1,394,715 | 1,401,780 | 1,383,620 | 1,404,164 |
| `tiktoken/o200k_base` | 1,626,429 | 1,646,302 | 1,618,141 | 1,604,638 | 1,586,598 |
| `hf-fast/auto` | 599,532 | 610,541 | 581,018 | 462,726 | 423,730 |
| `hf-fast/llama` | 778,116 | 686,373 | 628,327 | 486,149 | 443,363 |
| `sentencepiece/llama` | 454,303 | 432,853 | 415,597 | 396,005 | 384,445 |

**Memory note:** `tracemalloc_peak_python_heap_kib` is Python-heap allocation ONLY; native Rust/C tokenizer buffers are not visible to it. Process RSS deltas are reported separately and are noisy.
