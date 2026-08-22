# Post-Experiment Findings

Written **after** the benchmarks and concurrency sweeps, **before** any change to the
paper narrative. Purpose: state what the new evidence actually supports, including
where it contradicts earlier claims.

Evidence: `results/raw/tokenizer_overhead_*.json` (75 cells, all exact-length
verified), `results/raw/gateway_recount_*.json` (80 cells, median of 3 repeats),
`results/raw/m1_*.json` (120 cells), `results/raw/m2_*.json` (240 cells). All
summarizer integrity gates (G1 leak recomputation, G2 invariant consistency, G3
ledger conservation) **PASS**; B0 regression 19/19, M1/M2 regression 16/16.

---

## 1. Does a real tokenizer recount actually have meaningful overhead?

**It depends on input size — and the honest answer spans three orders of magnitude.**

Standalone `encode()` p50 (natural text):

| engine | 256 tok | 1 024 | 4 096 | 16 384 | 32 768 |
|---|---|---|---|---|---|
| tiktoken `cl100k_base` | 0.18 ms | 0.73 | 2.89 | 11.68 | 23.46 |
| tiktoken `o200k_base` | 0.16 ms | 0.62 | 2.54 | 10.05 | 20.30 |
| HF fast (Rust) Llama | 0.33 ms | 1.50 | 6.54 | 34.24 | 88.21 |
| SentencePiece Llama | 0.57 ms | 2.37 | 10.32 | 41.89 | 85.77 |

- At **short prompts (≤1 024 tokens) the recount is negligible** (0.16–2.4 ms) —
  consistent in *spirit* with the old "cheap" claim.
- At **long context (16 k–32 k) it is material**: 10–88 ms of pure CPU per request.
- **Engine choice is a 3.7–5× factor** at every size (tiktoken vs SentencePiece).
- The previously reported **"+0.1 ms" mock figure is refuted as a general claim.** It
  is only in the right ballpark for very short inputs with the fastest engine; it
  understates a 32 k-token SentencePiece recount by **~850×**.

## 2. Does the overhead depend strongly on token count?

**Yes — and it is essentially linear.** µs/token is near-constant per engine across a
128× range of input sizes (256 → 32 768):

| engine | µs/token (256 → 32 768) |
|---|---|
| tiktoken `cl100k_base` | 0.722 → 0.716 (flat) |
| tiktoken `o200k_base` | 0.623 → 0.619 (flat) |
| SentencePiece Llama | 2.213 → 2.617 (+18 %) |
| HF fast Llama | 1.305 → 2.692 (+106 %, mildly superlinear) |

So recount cost is predictable: **cost ≈ tokens × per-token constant**, letting an
operator budget it directly. Workload also matters, but less than size: at 4 096
tokens, `natural` is the *most* expensive and `high_entropy` the cheapest
(e.g. SentencePiece 10.32 ms vs 5.11 ms) — at a fixed token count, high-entropy text
carries fewer characters per token, so there is less input to scan.

Cold-vs-warm: the first call after GC is at most **2.3×** the warm p50, so lazy
initialization is real but modest; all headline numbers are warm.

## 3. Does concurrency materially change M1 leakage?

**No. This is a clean negative result.** With request volume held constant (20
requests/cell at every concurrency level), leak **per request** is invariant:

| architecture | c=1 | c=5 | c=20 | c=50 | c=100 |
|---|---|---|---|---|---|
| `post_completion` | 0.0528 | 0.0528 | 0.0529 | 0.0529 | 0.0528 |
| `reserve_refund_on_abort` | 0.0528 | 0.0528 | 0.0528 | 0.0528 | 0.0528 |
| `pre_debit` (safe) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `reserve_reconcile` (safe) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Request-ASR is exactly 1.000 (vulnerable) / 0.000 (safe) at **every** concurrency.
The honest-client control arm leaks 0.0000 at every concurrency and architecture,
confirming the leak requires attacker behaviour (mid-stream abort), not load.

**Interpretation: M1 is a per-request accounting-design defect, not a race.** A single
client at concurrency 1 extracts the full per-request leak; concurrency only
multiplies *volume*. This sharply distinguishes M1 from B0, whose leakage is
*created* by concurrency (B0 leaks nothing at concurrency 1 and requires ≥2
concurrent transactions).

Secondary observation: the cancellation→accounting-commit interval grows with load
(0 ms at c≤5 to ~8–38 ms at c=20–100), i.e. the exposure window widens under load,
but this does **not** change the outcome because the settlement is
cancellation-shielded and eventually commits.

## 4. Does concurrency materially change M2 leakage?

**No — identically invariant.** Leakage efficiency by architecture (attacker arm):

| architecture | c=1 | c=5 | c=20 | c=50 | c=100 |
|---|---|---|---|---|---|
| `client` | 0.228 | 0.228 | 0.228 | 0.228 | 0.228 |
| `client_logged` | 0.228 | 0.228 | 0.228 | 0.228 | 0.228 |
| `client_total` | 0.257 | 0.257 | 0.257 | 0.257 | 0.257 |
| `upstream` / `server_recount` / `hybrid_reconcile` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

M2 is a pure authority defect: whoever is trusted to count is trusted at any load.

## 5. Does concurrency materially change defense overhead?

**No, in the testbed.** M2 p95 latency rises with load for *every* architecture
(≈55 ms at c=1 → ≈100 ms at c=100), but the **safe architectures track the vulnerable
ones within noise** at every level (e.g. at c=100: `client` 102.3 ms vs
`server_recount` 97.7 ms vs `hybrid_reconcile` 95.8 ms). The rise is queueing, not
defense cost. Zero errors and zero timeouts across all 240 M2 cells.

**But this is the mock-recount result.** The *real* recount cost is the separate
gateway benchmark, and there concurrency does interact with size:

throughput ratio vs. no-recount (median of 3 repeats; 1.00 = free):

| size | engine | c=1 | c=10 |
|---|---|---|---|
| 256 | tiktoken / HF / SP | 0.98 / 0.97 / 0.97 | 0.99 / 0.98 / 0.98 |
| 1 024 | tiktoken / HF / SP | 0.98 / 0.96 / 0.96 | 0.99 / 0.88 / 0.88 |
| 4 096 | tiktoken / HF / SP | 0.98 / 0.86 / 0.88 | 0.93 / 0.58 / 0.62 |
| 16 384 | tiktoken / HF / SP | 0.76 / 0.21 / 0.24 | 0.31 / 0.048 / 0.060 |

At long context the recount can cost **an order of magnitude of throughput**
(HF/SentencePiece at 16 k: 0.05–0.24×), while tiktoken stays far cheaper. Under a
single uvicorn worker, tokenization is CPU-bound and blocks the event loop, so the
effect compounds with concurrency — this is an **upper bound**; a multi-worker or
thread-pool deployment would amortize it.

## 6. Which findings survive normalization?

- **Survive (unchanged):** M1 leak-per-request and request-ASR; M2 leakage efficiency
  and request-ASR; the architecture safe/unsafe partition; the billing-basis result
  (`client_total` is exploitable by `total_mismatch` while category pricing is not);
  the M1 abort-timing curve shape; B0's concurrency dependence.
- **Survive but must be re-labelled:** absolute leakage totals. They scale with
  request volume by construction and are meaningless across cells with different
  volume; we now hold volume constant and report `leak_per_request` as the headline.
- **Do not survive as stated:** "server-side recount adds ~0.1 ms / is essentially
  free." Replaced by a size- and engine-dependent statement.

## 7. Which original claims are no longer supported?

1. **"M2 server-recount defense costs +0.1 ms (negligible)."** REFUTED as a general
   claim. True only for short inputs with a fast BPE engine; at 16 k–32 k tokens the
   standalone recount is 10–88 ms and can cost 76–95 % of gateway throughput.
2. **Any implication that M1/M2 are concurrency-sensitive.** They are not. Earlier
   framing left this open ("M1/M2 not evaluated under concurrency" was listed as a
   limitation); it is now closed with a negative result.
3. **The unverified "2025 *Computers & Security* race-condition methodology"
   citation** — removed from `attacks/class6_credit_race.py`, replaced with the two
   verified sources (Kettle 2023; *(CVE citation withdrawn — the identifier belongs to an unrelated advisory)*).

## 8. What claims should be weakened (or sharpened)?

- **Weaken:** "the M2 defense is practically free." → *"The M2 defense is
  inexpensive for short prompts (≤1 k tokens: ≤2.4 ms, ≥0.96× throughput) but is a
  first-order cost at long context (16 k: 10–42 ms; 0.05–0.76× throughput), and the
  tokenizer implementation matters by 3.7–5×."*
- **Sharpen:** the taxonomy now has an evidence-backed axis — **B0 is a
  concurrency-created race; M1 and M2 are concurrency-invariant per-request
  accounting-design defects.** That is a stronger, testable structural claim than
  "three mechanisms that all violate one invariant".
- **Weaken:** high-concurrency gateway ratios (c=50, c=100). Repeat spread reaches
  173 % of the median in some small-payload cells and the `none` baseline is itself
  non-monotonic, indicating client-side and event-loop saturation. The **c=1 and
  c=10 columns are the defensible ones**; higher-concurrency numbers should be
  reported as capacity observations with the confound stated.
- **Keep, with scope:** "no served inference without a committed, non-refunded,
  server-authoritative debit" — every defense still drives leakage and invariant
  violations to exactly zero across all 360 M1/M2 cells.

## Net effect on the contribution

The core systematization and the defense results **hold and are now better
supported** (real tokenizers, real concurrency, tighter integrity gates). One
convenience claim (cheap recount) is replaced by a nuanced, measured cost model, and
one previously-open limitation (no concurrency evaluation) is closed with a clean
negative result that actually *strengthens* the taxonomy by separating race-created
from design-created accounting failures.

**This does not make the paper Q1-ready.** It closes two identified empirical gaps.
Remaining gaps are listed in `threats_to_validity.md` (production model, multi-worker
deployment, multi-tenant contention, broader architecture coverage).
