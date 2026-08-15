"""Defense-overhead micro-benchmark (RQ4).

Measures client-observed per-request latency for the safe vs vulnerable architecture
of each mechanism under a fixed workload, so the latency cost of the enforcement
primitive can be reported. Writes raw JSON + prints a summary.

Caveat (recorded in threats-to-validity): the mock model makes the *server recount*
in M2 nearly free; a production tokenizer pass is the real cost and is not captured
here. What IS captured is the database-operation overhead (extra atomic reserve /
reconcile writes) and the end-to-end latency shape.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np

from attacks.m1_stream_abort import stream_and_abort
from attacks.m2_usage_authority import send
from experiments import _mcommon as C

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
PROMPT = "benchmark the defense overhead across architectures please now"
SEED = 1337


def _stats(lat):
    a = np.asarray(lat) * 1000.0
    return {"n": len(lat), "mean": float(a.mean()), "p50": float(np.percentile(a, 50)),
            "p95": float(np.percentile(a, 95)), "p99": float(np.percentile(a, 99)),
            "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--m2-n", type=int, default=200)
    ap.add_argument("--m1-n", type=int, default=40)
    args = ap.parse_args()

    out = {"experiment": "defense_overhead", "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
           "environment": C.env_meta(), "m2": {}, "m1": {}}

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0) as client:
        (await client.get("/health")).raise_for_status()
        aid, key = await C.create_account(client, "overhead")

        # ---- M2 overhead: client (vuln) vs server_recount vs hybrid (safe) ----
        for arch in ["client", "server_recount", "hybrid_reconcile"]:
            tid = (await C.create_m_trial(client, aid, "m2", arch, "medium", PROMPT, SEED))["trial_id"]
            lat = []
            for _ in range(args.m2_n):
                t0 = time.perf_counter()
                await send(client, key, PROMPT, SEED, tid, "honest")
                lat.append(time.perf_counter() - t0)
            out["m2"][arch] = _stats(lat)
            print(f"M2 {arch:<16} mean={out['m2'][arch]['mean']:.2f}ms p95={out['m2'][arch]['p95']:.2f}ms")

        # ---- M1 overhead: post_completion (vuln) vs reserve_reconcile (safe) ----
        # full completion (no abort) so streaming time is identical; measures reserve cost.
        for arch in ["post_completion", "reserve_reconcile"]:
            tid = (await C.create_m_trial(client, aid, "m1", arch, "medium", PROMPT, SEED))["trial_id"]
            lat = []
            for _ in range(args.m1_n):
                t0 = time.perf_counter()
                await stream_and_abort(client, key, PROMPT, SEED, tid, None)
                lat.append(time.perf_counter() - t0)
            out["m1"][arch] = _stats(lat)
            print(f"M1 {arch:<16} mean={out['m1'][arch]['mean']:.2f}ms p95={out['m1'][arch]['p95']:.2f}ms")

    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / f"overhead_{out['generated_at']}.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    # deltas
    if "client" in out["m2"] and "server_recount" in out["m2"]:
        d = out["m2"]["server_recount"]["mean"] - out["m2"]["client"]["mean"]
        print(f"\nM2 recount overhead vs client: {d:+.3f} ms mean")
    if "post_completion" in out["m1"] and "reserve_reconcile" in out["m1"]:
        d = out["m1"]["reserve_reconcile"]["mean"] - out["m1"]["post_completion"]["mean"]
        print(f"M1 reserve_reconcile overhead vs post_completion: {d:+.3f} ms mean")
    print(f"raw -> {p}")


if __name__ == "__main__":
    asyncio.run(main())
