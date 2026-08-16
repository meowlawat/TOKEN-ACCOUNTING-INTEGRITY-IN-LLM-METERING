"""Gateway-level recount overhead: does server-side recount cost real throughput?

A tokenizer microbenchmark is NOT a gateway result. This measures the end-to-end
effect of enabling a real server-side recount on the metered request path:

    A. recount disabled  (client-declared count trusted)
    B. recount enabled   (server-authoritative recount), per tokenizer engine

Sweeps concurrency {1,10,50,100} x request size {256,1024,4096,16384} tokens and
reports requests/sec, success rate, latency percentiles, error rate, and the
server-measured tokenization component, plus the headline ratio

    throughput_with_recount / throughput_without_recount.

Concurrency is *controlled*: a fixed pool of `c` worker tasks pulls from a shared
queue for a fixed duration, so offered load is genuinely `c` in-flight requests
rather than a thundering-herd of gathered tasks.

Local testbed only.  Usage:  python -m benchmarks.gateway_recount_overhead
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from benchmarks._workloads import build_exact_length_text

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
SEED = 1337


def _pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[i]


async def _worker(client, api_key, payload, stop_at, lat, errs, server_ms, tok_ms):
    while time.perf_counter() < stop_at:
        t0 = time.perf_counter()
        try:
            r = await client.post("/bench/complete", headers={"X-API-Key": api_key}, json=payload)
            dt = (time.perf_counter() - t0) * 1000.0
            if r.status_code == 200:
                lat.append(dt)
                b = r.json()
                server_ms.append(b["total_server_ms"])
                tok_ms.append(b["tokenize_ms"])
            else:
                errs.append(r.status_code)
        except Exception:  # noqa: BLE001
            errs.append(-1)


async def run_cell(client, api_key, text, declared, engine, concurrency, duration_s) -> dict:
    payload = {"text": text, "declared_tokens": declared, "recount_engine": engine}
    lat: list[float] = []
    errs: list[int] = []
    server_ms: list[float] = []
    tok_ms: list[float] = []

    # warm-up (also forces lazy tokenizer construction in the server process)
    for _ in range(3):
        await client.post("/bench/complete", headers={"X-API-Key": api_key}, json=payload)

    t_start = time.perf_counter()
    stop_at = t_start + duration_s
    workers = [asyncio.create_task(
        _worker(client, api_key, payload, stop_at, lat, errs, server_ms, tok_ms)
    ) for _ in range(concurrency)]
    await asyncio.gather(*workers)
    elapsed = time.perf_counter() - t_start

    s = sorted(lat)
    n_ok = len(lat)
    return {
        "engine": engine, "concurrency": concurrency, "duration_s": elapsed,
        "requests_ok": n_ok, "errors": len(errs), "error_rate": len(errs) / max(1, n_ok + len(errs)),
        "throughput_rps": n_ok / elapsed if elapsed > 0 else 0.0,
        "latency_ms": {
            "mean": statistics.fmean(s) if s else 0.0,
            "std": statistics.stdev(s) if len(s) > 1 else 0.0,
            "p50": _pct(s, 50), "p95": _pct(s, 95), "p99": _pct(s, 99),
            "min": s[0] if s else 0.0, "max": s[-1] if s else 0.0,
        },
        "server_total_ms_mean": statistics.fmean(server_ms) if server_ms else 0.0,
        "tokenize_ms_mean": statistics.fmean(tok_ms) if tok_ms else 0.0,
        "tokenize_ms_p95": _pct(sorted(tok_ms), 95) if tok_ms else 0.0,
    }


async def container_stats() -> dict | None:
    """Best-effort container CPU/RSS snapshot via `docker stats` (may be unavailable)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "stats", "--no-stream", "--format", "{{.Name}},{{.CPUPerc}},{{.MemUsage}}",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
        rows = {}
        for line in out.decode().strip().splitlines():
            parts = line.split(",")
            if len(parts) >= 3 and "app" in parts[0]:
                rows["app_cpu_pct"] = parts[1]
                rows["app_mem"] = parts[2]
        return rows or None
    except Exception:  # noqa: BLE001
        return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--concurrency", type=int, nargs="+", default=[1, 10, 50, 100])
    ap.add_argument("--sizes", type=int, nargs="+", default=[256, 1024, 4096, 16384])
    ap.add_argument("--engines", nargs="+",
                    default=["none", "tiktoken/cl100k_base", "tiktoken/o200k_base",
                             "hf/llama", "sentencepiece/llama"])
    ap.add_argument("--duration", type=float, default=5.0, help="seconds per cell")
    ap.add_argument("--repeats", type=int, default=1,
                    help="independent repeats per cell; the MEDIAN throughput is used "
                         "(single 5s runs proved noisy enough to yield impossible >1.0 ratios)")
    ap.add_argument("--workload", default="natural")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # Build request texts with EXACT token lengths under a reference tokenizer
    # (cl100k). Sizes are therefore "cl100k-exact"; other engines see a similar but
    # not identical count -- recorded explicitly rather than assumed equal.
    import tiktoken
    ref = tiktoken.get_encoding("cl100k_base")
    texts: dict[int, str] = {}
    for n in args.sizes:
        texts[n] = build_exact_length_text(args.workload, n, ref.encode, ref.decode, SEED)
        assert len(ref.encode(texts[n])) == n

    limits = httpx.Limits(max_connections=max(args.concurrency) + 20,
                          max_keepalive_connections=max(args.concurrency) + 20)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0, limits=limits) as client:
        (await client.get("/health")).raise_for_status()
        engines_avail = (await client.get("/bench/engines")).json()
        # NUMERIC(18,6) allows at most 12 integer digits; 1e9 is ample headroom.
        acct = (await client.post("/admin/accounts",
                                  json={"name": "bench-recount", "balance": 1e9})).json()
        api_key = acct["api_key"]

        cells = []
        for size in args.sizes:
            for engine in args.engines:
                if engine != "none" and not engines_avail.get(engine, {}).get("available"):
                    print(f"  skip {engine} (unavailable in container)")
                    continue
                for c in args.concurrency:
                    reps = [await run_cell(client, api_key, texts[size], size, engine, c,
                                           args.duration) for _ in range(max(1, args.repeats))]
                    # Median-throughput repeat is the representative one; keep all.
                    reps_sorted = sorted(reps, key=lambda x: x["throughput_rps"])
                    r = dict(reps_sorted[len(reps_sorted) // 2])
                    r["repeats"] = len(reps)
                    r["throughput_rps_all"] = [x["throughput_rps"] for x in reps]
                    r["throughput_rps_spread"] = (max(x["throughput_rps"] for x in reps)
                                                  - min(x["throughput_rps"] for x in reps))
                    r["size_tokens_cl100k"] = size
                    r["workload"] = args.workload
                    r["container"] = await container_stats()
                    cells.append(r)
                    print(f"[{size:>5}tok {engine:<22} c={c:>3}] "
                          f"rps={r['throughput_rps']:8.1f} p50={r['latency_ms']['p50']:7.2f}ms "
                          f"p99={r['latency_ms']['p99']:8.2f}ms tok={r['tokenize_ms_mean']:6.2f}ms "
                          f"err={r['error_rate']:.1%}")

    # Derived ratios vs the no-recount baseline at the same (size, concurrency).
    base = {(c["size_tokens_cl100k"], c["concurrency"]): c
            for c in cells if c["engine"] == "none"}
    for c in cells:
        b = base.get((c["size_tokens_cl100k"], c["concurrency"]))
        if b and b["throughput_rps"] > 0:
            c["throughput_ratio_vs_none"] = c["throughput_rps"] / b["throughput_rps"]
            c["latency_p50_delta_ms"] = c["latency_ms"]["p50"] - b["latency_ms"]["p50"]
            c["latency_p99_delta_ms"] = c["latency_ms"]["p99"] - b["latency_ms"]["p99"]

    payload = {
        "benchmark": "gateway_recount_overhead", "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "scope_note": ("End-to-end gateway effect of a real server-side recount. Single "
                       "uvicorn worker; tokenization is CPU-bound and blocks the event "
                       "loop, which is the realistic single-worker case. Sizes are exact "
                       "under cl100k_base; other engines see similar-but-different counts."),
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "cpu_count": __import__("os").cpu_count()},
        "engines_available_in_container": engines_avail,
        "parameters": {"concurrency": args.concurrency, "sizes": args.sizes,
                       "engines": args.engines, "duration_s": args.duration,
                       "workload": args.workload, "seed": SEED,
                       "reference_tokenizer": "tiktoken/cl100k_base"},
        "cells": cells,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RAW / f"gateway_recount_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n{len(cells)} cells -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
