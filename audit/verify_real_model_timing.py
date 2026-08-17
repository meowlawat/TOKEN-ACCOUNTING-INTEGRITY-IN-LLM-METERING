"""Independent re-measurement of the real-model recount ratio (audit fix F6).

The first audit pass did NOT re-measure the 0.014-0.019% claim, so it could not be
called independently verified. This script re-measures it with newly written timing code
that imports nothing from `benchmarks/`.

Deliberately reduced: enough repetitions to verify the ORDER OF MAGNITUDE and range, not
a full re-run. Uses the same documented configuration (SmolLM2-135M, CPU, greedy,
exact-length prompts) so the comparison is like-for-like.

Reports, per workload:  recount_time / end_to_end_time
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

AUDIT = Path(__file__).parent
MODEL = "HuggingFaceTB/SmolLM2-135M"
SEED = 1337
WORD = ("the model streams a token then another under test with deterministic timing "
        "for reproducible billing and metering research on commodity hardware").split()


def build_exact_prompt(tok, n_tokens: int) -> str:
    """Build a prompt of exactly n_tokens under this model's own tokenizer.

    Independent implementation: grow then trim, verifying after every change.
    """
    text = " ".join(WORD[i % len(WORD)] for i in range(max(4, n_tokens)))
    ids = tok.encode(text, add_special_tokens=False)
    while len(ids) < n_tokens:
        text += " " + WORD[len(ids) % len(WORD)]
        ids = tok.encode(text, add_special_tokens=False)
    # trim down to exactly n_tokens by decoding a truncated id sequence, then repair
    text = tok.decode(ids[:n_tokens], skip_special_tokens=True)
    guard = 0
    while len(tok.encode(text, add_special_tokens=False)) != n_tokens and guard < 200:
        cur = len(tok.encode(text, add_special_tokens=False))
        if cur > n_tokens:
            text = text[:-1]
        else:
            text += " a"
        guard += 1
    got = len(tok.encode(text, add_special_tokens=False))
    assert got == n_tokens, f"could not build exact prompt: {got} != {n_tokens}"
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workloads", type=int, nargs="+", default=[128, 1024])
    ap.add_argument("--max-new-tokens", type=int, default=32)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(args.threads)
    torch.manual_seed(SEED)

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL)
    model.eval()
    print(f"model={MODEL} params={sum(p.numel() for p in model.parameters())/1e6:.1f}M "
          f"threads={args.threads} max_new={args.max_new_tokens} reps={args.reps}")

    rows = []
    for n_prompt in args.workloads:
        prompt = build_exact_prompt(tok, n_prompt)
        print(f"\nworkload {n_prompt}: prompt is exactly "
              f"{len(tok.encode(prompt, add_special_tokens=False))} tokens")
        # warm-up (excluded)
        with torch.no_grad():
            model(input_ids=tok(prompt, return_tensors='pt')['input_ids'][:, :16])

        for rep in range(args.reps):
            ids = tok(prompt, return_tensors="pt")
            t0 = time.perf_counter()
            past, cur, gen = None, ids["input_ids"], []
            with torch.no_grad():
                for _ in range(args.max_new_tokens):
                    o = model(input_ids=cur, past_key_values=past, use_cache=True)
                    past = o.past_key_values
                    nxt = int(torch.argmax(o.logits[:, -1, :], dim=-1)[0])
                    gen.append(nxt)
                    cur = torch.tensor([[nxt]])
            gen_end = time.perf_counter()

            # the accounting recount, timed independently
            text_out = tok.decode(gen, skip_special_tokens=True)
            r0 = time.perf_counter()
            _ = len(tok.encode(prompt, add_special_tokens=False))
            _ = len(tok.encode(text_out, add_special_tokens=False))
            recount = time.perf_counter() - r0
            e2e = time.perf_counter() - t0

            rows.append({"prompt_tokens": n_prompt, "rep": rep,
                         "generation_s": gen_end - t0, "recount_s": recount, "e2e_s": e2e,
                         "ratio_pct": 100.0 * recount / e2e})
            print(f"  rep {rep}: e2e={e2e:6.2f}s recount={recount*1000:6.2f}ms "
                  f"ratio={100.0*recount/e2e:.5f}%")

    print("\n" + "=" * 70)
    print("INDEPENDENT re-measurement of recount / end-to-end")
    print("=" * 70)
    summary = {}
    for n in args.workloads:
        rs = [r["ratio_pct"] for r in rows if r["prompt_tokens"] == n]
        summary[str(n)] = {"median_pct": statistics.median(rs), "min_pct": min(rs), "max_pct": max(rs),
                           "n": len(rs)}
        print(f"  prompt={n:<6} median={statistics.median(rs):.5f}%  "
              f"range=[{min(rs):.5f}%, {max(rs):.5f}%]  n={len(rs)}")
    allr = [r["ratio_pct"] for r in rows]
    print(f"\n  OVERALL range: {min(allr):.4f}% - {max(allr):.4f}%")
    print("  Previously reported in the artifact: 0.014% - 0.019%")
    within = all(0.005 <= r <= 0.10 for r in allr)
    print(f"  Same order of magnitude as the artifact claim: {within}")

    (AUDIT / "real_model_timing_recheck.json").write_text(
        json.dumps({"model": MODEL, "max_new_tokens": args.max_new_tokens,
                    "threads": args.threads, "rows": rows, "summary": summary,
                    "artifact_claim_pct": [0.014, 0.019],
                    "same_order_of_magnitude": within}, indent=2), encoding="utf-8")
    print(f"-> audit/real_model_timing_recheck.json")


if __name__ == "__main__":
    main()
