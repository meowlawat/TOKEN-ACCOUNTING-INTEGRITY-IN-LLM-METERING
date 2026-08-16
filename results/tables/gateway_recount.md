# Gateway-level recount overhead (end-to-end)

- Generated: `20260816T111159Z`
- **Scope:** End-to-end gateway effect of a real server-side recount. Single uvicorn worker; tokenization is CPU-bound and blocks the event loop, which is the realistic single-worker case. Sizes are exact under cl100k_base; other engines see similar-but-different counts.
- Duration/cell: 5.0s; workload `natural`; sizes exact under `tiktoken/cl100k_base`

## Throughput ratio vs. no-recount (1.00 = free)


### 256 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 0.982 | 0.988 | 1.001 | 0.644 |
| `tiktoken/o200k_base` | 0.977 | 0.998 | 1.012 | 1.033 |
| `hf/llama` | 0.974 | 0.980 | 1.063 | 0.626 |
| `sentencepiece/llama` | 0.973 | 0.978 | 0.972 | 0.642 |

### 1024 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 0.984 | 0.985 | 0.871 | 0.768 |
| `tiktoken/o200k_base` | 0.979 | 0.988 | 0.864 | 0.580 |
| `hf/llama` | 0.955 | 0.875 | 0.989 | 0.894 |
| `sentencepiece/llama` | 0.957 | 0.883 | 1.035 | 0.768 |

### 4096 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 0.984 | 0.931 | 1.335 | 0.948 |
| `tiktoken/o200k_base` | 0.975 | 0.961 | 0.957 | 0.949 |
| `hf/llama` | 0.864 | 0.577 | 0.532 | 0.855 |
| `sentencepiece/llama` | 0.878 | 0.617 | 0.575 | 0.849 |

### 16384 tokens/request

| engine | c=1 | c=10 | c=50 | c=100 |
|---|---|---|---|---|
| `none` | 1.000 | 1.000 | 1.000 | 1.000 |
| `tiktoken/cl100k_base` | 0.761 | 0.309 | 0.527 | 0.382 |
| `tiktoken/o200k_base` | 0.793 | 0.427 | 0.648 | 0.415 |
| `hf/llama` | 0.205 | 0.048 | 0.094 | 0.097 |
| `sentencepiece/llama` | 0.241 | 0.060 | 0.105 | 0.113 |

## Server-measured tokenization component (mean ms)

| engine | 256 tok | 1024 tok | 4096 tok | 16384 tok |
|---|---|---|---|---|
| `none` | 0.00 | 0.00 | 0.00 | 0.00 |
| `tiktoken/cl100k_base` | 0.18 | 0.35 | 1.11 | 3.37 |
| `tiktoken/o200k_base` | 0.14 | 0.30 | 0.78 | 2.06 |
| `hf/llama` | 0.70 | 1.77 | 6.79 | 29.56 |
| `sentencepiece/llama` | 0.59 | 1.76 | 6.19 | 25.46 |