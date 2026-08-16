"""Real-tokenizer microbenchmark (closes the "mock tokenizer is free" gap).

Measures the standalone cost of a server-side token recount across real tokenizer
engines, workloads, and input lengths.

SCOPE WARNING (repeated in the outputs): this measures the *tokenizer call in
isolation*. It is NOT a gateway throughput result. See
``benchmarks/gateway_recount_overhead.py`` for the end-to-end effect.

Engines (only those that actually resolve locally are benchmarked; the exact
artifact + revision is recorded):
  * tiktoken ``cl100k_base``
  * tiktoken ``o200k_base``
  * HuggingFace Llama-family tokenizer (fast/Rust backend)
  * SentencePiece, loaded from that Llama tokenizer's own ``tokenizer.model``

Every (engine, workload, length) cell constructs its OWN input and asserts
``len(encode(text)) == target``. Cells that cannot satisfy the invariant are
recorded as failures, never silently mis-labelled.

Metrics per cell: cold call (first call after construction, n=1), warm distribution
(mean/std/p50/p95/p99, ns resolution via ``time.perf_counter_ns``), tokens/sec, and
peak **Python-heap** allocation via ``tracemalloc`` (explicitly NOT total process
memory) plus process RSS deltas via ``psutil``.

Usage:
    python -m benchmarks.tokenizer_overhead
    python -m benchmarks.tokenizer_overhead --lengths 256 1024 --quick
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import statistics
import time
import tracemalloc
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

warnings.filterwarnings("ignore")

from benchmarks._workloads import ExactLengthError, build_exact_length_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"

DEFAULT_LENGTHS = [256, 1024, 4096, 16384, 32768]
WORKLOADS = ["natural", "code", "json", "high_entropy"]
SEED = 1337

# Adaptive repetition budget (documented in the methodology): we target a wall-clock
# budget per cell so short inputs get many reps and long inputs stay tractable, with
# hard floor/ceiling. The ACTUAL rep count is recorded per cell.
REP_MIN = 30
REP_MAX = 300
CELL_TIME_BUDGET_S = 1.5
WARMUP_RUNS = 5


@dataclass
class Engine:
    name: str
    family: str
    encode: Callable[[str], list]
    decode: Callable[[list], str]
    meta: dict = field(default_factory=dict)


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_engines(llama_repo: str) -> tuple[list[Engine], list[dict]]:
    """Instantiate every engine that resolves locally; record artifact + revision."""
    engines: list[Engine] = []
    unavailable: list[dict] = []

    # --- tiktoken ---------------------------------------------------------- #
    try:
        import tiktoken
        import importlib.metadata as md
        tv = md.version("tiktoken")
        for enc_name in ("cl100k_base", "o200k_base"):
            enc = tiktoken.get_encoding(enc_name)
            # Reproducible artifact fingerprint: hash the byte form of a fixed token
            # range (public API), so a changed vocabulary is detectable across runs.
            h = hashlib.sha256()
            for tid in range(0, min(2000, enc.n_vocab)):
                try:
                    h.update(enc.decode_single_token_bytes(tid))
                except Exception:  # noqa: BLE001
                    h.update(b"\x00")
            engines.append(Engine(
                name=f"tiktoken/{enc_name}", family="tiktoken",
                encode=enc.encode, decode=enc.decode,
                meta={"library": "tiktoken", "library_version": tv,
                      "encoding": enc_name, "n_vocab": enc.n_vocab,
                      "vocab_fingerprint_sha256_first2k": h.hexdigest(),
                      "revision": f"tiktoken=={tv}; encoding={enc_name}"},
            ))
    except Exception as e:  # noqa: BLE001
        unavailable.append({"engine": "tiktoken", "reason": f"{type(e).__name__}: {e}"})

    # --- HuggingFace Llama-family ------------------------------------------ #
    hf_sha = None
    try:
        import importlib.metadata as md
        from transformers import AutoTokenizer
        try:
            from huggingface_hub import HfApi
            hf_sha = HfApi().model_info(llama_repo).sha
        except Exception:  # noqa: BLE001
            hf_sha = None
        tk = AutoTokenizer.from_pretrained(llama_repo)
        engines.append(Engine(
            name=("hf-fast/auto" if getattr(tk, "is_fast", False) else "hf-slow/auto"),
            family="huggingface-auto",
            encode=lambda s, _tk=tk: _tk.encode(s, add_special_tokens=False),
            decode=lambda ids, _tk=tk: _tk.decode(ids, skip_special_tokens=True),
            meta={"library": "transformers", "library_version": md.version("transformers"),
                  "tokenizers_version": md.version("tokenizers"),
                  "repo": llama_repo, "revision": hf_sha or "unknown",
                  "tokenizer_class": type(tk).__name__,
                  "is_fast": bool(getattr(tk, "is_fast", False)),
                  "vocab_size": tk.vocab_size},
        ))
    except Exception as e:  # noqa: BLE001
        unavailable.append({"engine": "huggingface", "reason": f"{type(e).__name__}: {e}"})

    # --- HuggingFace FAST (Rust) backend, loaded straight from tokenizer.json #
    # This is what a production gateway actually runs; the AutoTokenizer above
    # resolves to the SLOW Python LlamaTokenizer for this repo, so we measure both.
    try:
        import importlib.metadata as md
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer as RsTokenizer
        tj = Path(hf_hub_download(llama_repo, "tokenizer.json"))
        rs = RsTokenizer.from_file(str(tj))
        engines.append(Engine(
            name="hf-fast/llama", family="huggingface-fast",
            encode=lambda s, _rs=rs: _rs.encode(s, add_special_tokens=False).ids,
            decode=lambda ids, _rs=rs: _rs.decode(ids, skip_special_tokens=True),
            meta={"library": "tokenizers", "library_version": md.version("tokenizers"),
                  "repo": llama_repo, "revision": hf_sha or "unknown",
                  "model_file": "tokenizer.json",
                  "model_sha256": _sha256_file(tj), "is_fast": True,
                  "vocab_size": rs.get_vocab_size()},
        ))
    except Exception as e:  # noqa: BLE001
        unavailable.append({"engine": "huggingface-fast", "reason": f"{type(e).__name__}: {e}"})

    # --- SentencePiece (from the same Llama repo's tokenizer.model) --------- #
    try:
        import importlib.metadata as md
        import sentencepiece as spm
        from huggingface_hub import hf_hub_download
        model_path = Path(hf_hub_download(llama_repo, "tokenizer.model"))
        sp = spm.SentencePieceProcessor(model_file=str(model_path))
        engines.append(Engine(
            name="sentencepiece/llama", family="sentencepiece",
            encode=lambda s, _sp=sp: _sp.encode(s, out_type=int),
            decode=lambda ids, _sp=sp: _sp.decode(ids),
            meta={"library": "sentencepiece", "library_version": md.version("sentencepiece"),
                  "repo": llama_repo, "revision": hf_sha or "unknown",
                  "model_file": "tokenizer.model",
                  "model_sha256": _sha256_file(model_path),
                  "vocab_size": sp.get_piece_size()},
        ))
    except Exception as e:  # noqa: BLE001
        unavailable.append({"engine": "sentencepiece", "reason": f"{type(e).__name__}: {e}"})

    return engines, unavailable


def _rss_mb() -> float | None:
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:  # noqa: BLE001
        return None


def measure_cell(engine: Engine, workload: str, target: int) -> dict:
    """Build an exact-length input and time the encode call."""
    try:
        text = build_exact_length_text(workload, target, engine.encode, engine.decode, SEED)
    except ExactLengthError as e:
        return {"engine": engine.name, "workload": workload, "target_tokens": target,
                "status": "exact_length_failed", "error": str(e)}

    verified = len(engine.encode(text))
    if verified != target:
        return {"engine": engine.name, "workload": workload, "target_tokens": target,
                "status": "verification_failed", "verified_tokens": verified}

    # --- cold call: first encode after a fresh GC (includes lazy caches) ----- #
    gc.collect()
    t0 = time.perf_counter_ns()
    engine.encode(text)
    cold_ns = time.perf_counter_ns() - t0

    # --- warm-up ------------------------------------------------------------ #
    for _ in range(WARMUP_RUNS):
        engine.encode(text)

    # --- calibrate rep count to the time budget ----------------------------- #
    t0 = time.perf_counter_ns()
    engine.encode(text)
    probe_ns = max(time.perf_counter_ns() - t0, 1)
    reps = int((CELL_TIME_BUDGET_S * 1e9) / probe_ns)
    reps = max(REP_MIN, min(REP_MAX, reps))

    # --- timed loop (Python-heap allocation tracked around the loop) -------- #
    rss_before = _rss_mb()
    gc.collect()
    tracemalloc.start()
    samples_ns: list[int] = []
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        engine.encode(text)
        samples_ns.append(time.perf_counter_ns() - t0)
    _cur, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = _rss_mb()

    s = sorted(samples_ns)
    def pct(p: float) -> float:
        idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
        return s[idx] / 1e6  # ms

    mean_ms = statistics.fmean(samples_ns) / 1e6
    std_ms = (statistics.stdev(samples_ns) / 1e6) if len(samples_ns) > 1 else 0.0
    p50 = pct(50)

    return {
        "engine": engine.name, "family": engine.family, "workload": workload,
        "target_tokens": target, "verified_tokens": verified, "status": "ok",
        "chars": len(text), "reps": reps, "warmup_runs": WARMUP_RUNS,
        "cold_ms": cold_ns / 1e6,
        "mean_ms": mean_ms, "std_ms": std_ms,
        "p50_ms": p50, "p95_ms": pct(95), "p99_ms": pct(99),
        "min_ms": s[0] / 1e6, "max_ms": s[-1] / 1e6,
        "tokens_per_sec_at_p50": (target / (p50 / 1000.0)) if p50 > 0 else None,
        "tokens_per_sec_at_mean": (target / (mean_ms / 1000.0)) if mean_ms > 0 else None,
        "us_per_token_at_p50": (p50 * 1000.0 / target) if target else None,
        # NOTE: tracemalloc measures PYTHON-HEAP allocations only. Rust/C tokenizer
        # buffers (tiktoken, HF fast, sentencepiece) are largely invisible to it.
        "tracemalloc_peak_python_heap_kib": peak_bytes / 1024.0,
        "process_rss_before_mb": rss_before, "process_rss_after_mb": rss_after,
        "process_rss_delta_mb": (None if (rss_before is None or rss_after is None)
                                 else rss_after - rss_before),
        "cold_warm_ratio": (cold_ns / 1e6) / p50 if p50 > 0 else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Real-tokenizer overhead microbenchmark.")
    ap.add_argument("--lengths", type=int, nargs="+", default=DEFAULT_LENGTHS)
    ap.add_argument("--workloads", nargs="+", default=WORKLOADS)
    ap.add_argument("--llama-repo", default="hf-internal-testing/llama-tokenizer",
                    help="Open (non-gated) Llama-family tokenizer repo.")
    ap.add_argument("--quick", action="store_true", help="smaller budget for a smoke run")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.quick:
        global CELL_TIME_BUDGET_S, REP_MIN
        CELL_TIME_BUDGET_S, REP_MIN = 0.3, 10

    engines, unavailable = build_engines(args.llama_repo)
    if not engines:
        raise SystemExit("no tokenizer engines available")

    print(f"engines: {[e.name for e in engines]}")
    for u in unavailable:
        print(f"  UNAVAILABLE {u['engine']}: {u['reason'][:100]}")

    rows: list[dict] = []
    for engine in engines:
        for workload in args.workloads:
            for target in args.lengths:
                r = measure_cell(engine, workload, target)
                rows.append(r)
                if r["status"] == "ok":
                    print(f"[{engine.name:<28} {workload:<13} {target:>6}] "
                          f"p50={r['p50_ms']:.3f}ms tok/s={r['tokens_per_sec_at_p50']:,.0f} "
                          f"reps={r['reps']}")
                else:
                    print(f"[{engine.name:<28} {workload:<13} {target:>6}] {r['status']}")

    payload = {
        "benchmark": "tokenizer_overhead",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "scope_warning": ("Standalone tokenizer-call cost only. NOT a gateway throughput "
                          "result; see benchmarks/gateway_recount_overhead.py."),
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "processor": platform.processor(), "machine": platform.machine(),
            "cpu_count": __import__("os").cpu_count(),
        },
        "engines": [{"name": e.name, "family": e.family, **e.meta} for e in engines],
        "unavailable_engines": unavailable,
        "parameters": {
            "lengths": args.lengths, "workloads": args.workloads, "seed": SEED,
            "warmup_runs": WARMUP_RUNS, "rep_min": REP_MIN, "rep_max": REP_MAX,
            "cell_time_budget_s": CELL_TIME_BUDGET_S,
            "rep_policy": ("adaptive: reps = clamp(budget/probe_time, REP_MIN, REP_MAX); "
                           "actual reps recorded per cell"),
            "memory_note": ("tracemalloc_peak_python_heap_kib is PYTHON-HEAP ONLY and "
                            "excludes native Rust/C tokenizer buffers; process RSS deltas "
                            "are reported separately and are noisy."),
        },
        "results": rows,
    }
    try:
        import psutil
        payload["environment"]["total_ram_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
    except Exception:  # noqa: BLE001
        pass

    RAW.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RAW / f"tokenizer_overhead_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    ok = sum(1 for r in rows if r["status"] == "ok")
    print(f"\n{ok}/{len(rows)} cells OK -> {out}")


if __name__ == "__main__":
    main()
