# Gateway-level recount overhead (end-to-end)

- Generated: `20260816T130335Z`
- **Scope:** End-to-end gateway effect of a real server-side recount. Single uvicorn worker; tokenization is CPU-bound and blocks the event loop, which is the realistic single-worker case. Sizes are exact under cl100k_base; other engines see similar-but-different counts.
- Duration/cell: 5.0s; workload `natural`; sizes exact under `tiktoken/cl100k_base`

## Throughput ratio vs. no-recount (1.00 = free)


### 256 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 0.983 | 0.987 | 0.894 | 0.925 |
| `tiktoken/o200k_base` | 0.990 | 0.993 | 0.870 | 1.037 |
| `hf/llama` | 0.975 | 0.974 | 0.894 | 0.995 |
| `sentencepiece/llama` | 0.980 | 0.972 | 0.884 | 1.012 |

### 1024 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 1.011 | 0.969 | 1.006 | 0.886 |
| `tiktoken/o200k_base` | 1.015 | 0.988 | 0.941 | 1.080 |
| `hf/llama` | 0.968 | 0.877 | 0.912 | 0.690 |
| `sentencepiece/llama` | 0.956 | 0.878 | 0.870 | 0.685 |

### 4096 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 0.962 | 0.920 | 0.997 | 0.927 |
| `tiktoken/o200k_base` | 0.964 | 0.957 | 1.156 | 0.916 |
| `hf/llama` | 0.860 | 0.663 | 0.627 | 0.765 |
| `sentencepiece/llama` | 0.850 | 0.588 | 0.547 | 0.778 |

### 16384 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 1.016 | 0.520 | 0.738 | 0.798 |
| `tiktoken/o200k_base` | 1.210 | 0.707 | 0.932 | 0.865 |
| `hf/llama` | 0.496 | 0.150 | 0.220 | 0.325 |
| `sentencepiece/llama` | 0.408 | 0.116 | 0.164 | 0.245 |

## Server-measured tokenization component (mean ms)

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok |
|---|---|---|---|---|
| `none` | 0.00 | 0.00 | 0.00 | 0.00 |
| `tiktoken/cl100k_base` | 0.17 | 0.34 | 1.19 | 3.48 |
| `tiktoken/o200k_base` | 0.14 | 0.24 | 0.80 | 2.13 |
| `hf/llama` | 0.57 | 1.45 | 4.88 | 18.34 |
| `sentencepiece/llama` | 0.52 | 1.78 | 6.06 | 25.20 |