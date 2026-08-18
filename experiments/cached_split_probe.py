"""Probe: is the authoritative cost of an identical request stable on a real stack?

The mock generator makes usage a pure function of `(prompt, seed)`, so the honest cost of
a request is fixed. Real serving stacks report a *prefix-cache split* --
`prompt_tokens_details.cached_tokens` -- that depends on what the server has recently
seen. Under any pricing scheme where cached input is discounted (ours prices it 10x
cheaper than uncached input), that makes the honest cost of a byte-identical request a
function of server state rather than of the request.

This matters for the paper's threat model in three ways, so it is measured rather than
asserted:

  1. the provider's own authoritative number is not reproducible across calls;
  2. a client therefore cannot verify its own bill, even in principle;
  3. a client that over-declares cached tokens has genuine plausible deniability, because
     the true value legitimately varies.

Run against a live `llama-server` (see app/llm/real_server.py for the deployment used).

Usage:
    python -m experiments.cached_split_probe --repeats 4 --prompts 3
"""

from __future__ import annotations

import argparse
import json
import statistics
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
URL = "http://127.0.0.1:8899/v1/chat/completions"

# Medium tier, matching the experiment corpus: cached input is 10x cheaper than
# uncached input, which is what turns a cache-split change into a price change.
PRICE_INPUT_PER_1K = Decimal("0.5")
PRICE_CACHED_PER_1K = Decimal("0.05")
PRICE_OUTPUT_PER_1K = Decimal("1.5")


def cost(prompt_tokens: int, cached: int, completion: int) -> Decimal:
    uncached = max(0, prompt_tokens - cached)
    return (Decimal(uncached) / 1000 * PRICE_INPUT_PER_1K
            + Decimal(cached) / 1000 * PRICE_CACHED_PER_1K
            + Decimal(completion) / 1000 * PRICE_OUTPUT_PER_1K).quantize(Decimal("0.000001"))


def call(prompt: str, seed: int, max_tokens: int) -> dict:
    body = {"model": "probe", "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0, "seed": seed}
    u = httpx.post(URL, json=body, timeout=120).json()["usage"]
    pt = int(u.get("prompt_tokens", 0))
    ct = int(u.get("completion_tokens", 0))
    cached = int((u.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
    return {"prompt_tokens": pt, "completion_tokens": ct, "cached_tokens": cached,
            "authoritative_cost": str(cost(pt, cached, ct))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--prompts", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=16)
    args = ap.parse_args()

    # Each prompt must be unseen, or the first call is already warm.
    nonce = uuid.uuid4().hex[:8]
    prompts = [f"Unseen probe {nonce}-{i}: state two short facts about the number {i}."
               for i in range(args.prompts)]

    results = []
    print("=" * 78)
    print("CACHED-SPLIT PROBE -- identical request, repeated")
    print("=" * 78)
    for p in prompts:
        calls = [call(p, 1337, args.max_tokens) for _ in range(args.repeats)]
        cached = [c["cached_tokens"] for c in calls]
        costs = [Decimal(c["authoritative_cost"]) for c in calls]
        row = {
            "prompt": p, "calls": calls,
            "cached_distinct": sorted(set(cached)),
            "cached_varies": len(set(cached)) > 1,
            "cost_distinct": sorted({str(c) for c in costs}),
            "cost_varies": len(set(costs)) > 1,
            "cost_spread_pct": (float((max(costs) - min(costs)) / max(costs) * 100)
                                if max(costs) > 0 else 0.0),
        }
        results.append(row)
        print(f"\nprompt: {p[:56]}...")
        for i, c in enumerate(calls):
            print(f"  call {i}: prompt={c['prompt_tokens']:<4} cached={c['cached_tokens']:<4} "
                  f"completion={c['completion_tokens']:<4} cost={c['authoritative_cost']}")
        print(f"  cached tokens varied: {row['cached_varies']} {row['cached_distinct']}")
        print(f"  honest cost varied  : {row['cost_varies']} "
              f"(spread {row['cost_spread_pct']:.2f}% of the larger cost)")

    any_varies = any(r["cost_varies"] for r in results)
    spreads = [r["cost_spread_pct"] for r in results if r["cost_varies"]]
    summary = {
        "prompts_tested": len(results),
        "repeats_per_prompt": args.repeats,
        "any_cost_varies": any_varies,
        "prompts_with_varying_cost": sum(1 for r in results if r["cost_varies"]),
        "mean_cost_spread_pct": round(statistics.fmean(spreads), 3) if spreads else 0.0,
        "max_cost_spread_pct": round(max(spreads), 3) if spreads else 0.0,
    }
    print("\n" + "-" * 78)
    print(f"prompts whose honest cost changed between identical calls: "
          f"{summary['prompts_with_varying_cost']}/{summary['prompts_tested']}")
    if any_varies:
        print(f"mean spread {summary['mean_cost_spread_pct']:.2f}%, "
              f"max {summary['max_cost_spread_pct']:.2f}%")
        print("=> On this stack the authoritative cost of a byte-identical request is a")
        print("   function of SERVER CACHE STATE, not of the request. The provider's own")
        print("   number is not reproducible, so the client cannot verify its bill and an")
        print("   over-declared cached count has genuine plausible deniability.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"cached_split_probe_{stamp}.json"
    out.write_text(json.dumps({
        "experiment": "cached_split_probe",
        "generated_at": stamp,
        "upstream": URL,
        "prices": {"input_per_1k": str(PRICE_INPUT_PER_1K),
                   "cached_input_per_1k": str(PRICE_CACHED_PER_1K),
                   "output_per_1k": str(PRICE_OUTPUT_PER_1K)},
        "summary": summary, "results": results}, indent=2), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
