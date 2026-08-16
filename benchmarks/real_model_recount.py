"""Local real-model external-validity experiment (Phase B).

PURPOSE: the rest of the study meters a *deterministic mock* generator. That makes
accounting reproducible but leaves one question open: how large is an authoritative
server-side recount **relative to real autoregressive inference**? This experiment
answers exactly that, and nothing else.

SCOPE (stated in every output):
  * "local real-model external-validity experiment"
  * A small open model runs locally on CPU. It is NOT a commercial provider, NOT a
    production serving stack, and NOT evidence about any vendor's billing.
  * Model quality is irrelevant here; only *timing* is measured.

Design: for each workload (short / medium / long context) and each accounting posture
(none / server_recount / hybrid_reconcile), run real token-by-token generation with a
controlled output length and measure the inference vs accounting split.

Headline metrics:
    recount_time / end_to_end_inference_time
    throughput_with_recount / throughput_without_recount

Local only:  python -m benchmarks.real_model_recount
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import statistics
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
SEED = 1337

# Prompt sizes in tokens (prefill), output length held constant across workloads.
WORKLOADS = {"short": 128, "medium": 1024, "long": 4096}
POSTURES = ["none", "server_recount", "hybrid_reconcile"]


def _rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:  # noqa: BLE001
        return None


def _cpu_time_s():
    try:
        import psutil
        t = psutil.Process().cpu_times()
        return t.user + t.system
    except Exception:  # noqa: BLE001
        return None


def build_prompt(tokenizer, n_tokens: int) -> str:
    """Build a prompt of EXACTLY n_tokens under this model's own tokenizer."""
    from benchmarks._workloads import build_exact_length_text
    return build_exact_length_text(
        "natural", n_tokens,
        lambda s: tokenizer.encode(s, add_special_tokens=False),
        lambda ids: tokenizer.decode(ids, skip_special_tokens=True),
        SEED,
    )


def run_one(model, tokenizer, torch, prompt: str, max_new_tokens: int, posture: str) -> dict:
    """One real generation with token-by-token streaming + the posture's accounting."""
    ids = tokenizer(prompt, return_tensors="pt")
    n_prompt = int(ids["input_ids"].shape[1])

    cpu0, rss0 = _cpu_time_s(), _rss_mb()
    t_start = time.perf_counter()

    past = None
    cur = ids["input_ids"]
    generated: list[int] = []
    ttft = None
    with torch.no_grad():
        for i in range(max_new_tokens):
            out = model(input_ids=cur, past_key_values=past, use_cache=True)
            past = out.past_key_values
            nxt = int(torch.argmax(out.logits[:, -1, :], dim=-1)[0])  # greedy => deterministic
            generated.append(nxt)
            if ttft is None:
                ttft = time.perf_counter() - t_start          # includes prefill
            cur = torch.tensor([[nxt]])
    t_gen_end = time.perf_counter()
    stream_duration = t_gen_end - t_start

    # ---- accounting posture -------------------------------------------------
    text_out = tokenizer.decode(generated, skip_special_tokens=True)
    t_acc0 = time.perf_counter()
    recount_s = 0.0
    reconciled = False
    if posture == "none":
        billed_prompt, billed_out = n_prompt, len(generated)   # declared, untrusted
    else:
        t_r0 = time.perf_counter()
        billed_prompt = len(tokenizer.encode(prompt, add_special_tokens=False))
        billed_out = len(tokenizer.encode(text_out, add_special_tokens=False))
        recount_s = time.perf_counter() - t_r0
        if posture == "hybrid_reconcile":
            reconciled = (billed_prompt != n_prompt) or (billed_out != len(generated))
    accounting_s = time.perf_counter() - t_acc0

    e2e = time.perf_counter() - t_start
    cpu1, rss1 = _cpu_time_s(), _rss_mb()

    return {
        "posture": posture, "prompt_tokens": n_prompt, "generated_tokens": len(generated),
        "billed_prompt_tokens": billed_prompt, "billed_output_tokens": billed_out,
        "reconciled_flag": reconciled,
        "ttft_s": ttft, "stream_duration_s": stream_duration,
        "recount_s": recount_s, "accounting_s": accounting_s, "e2e_s": e2e,
        "recount_frac_of_e2e": (recount_s / e2e) if e2e > 0 else None,
        "gen_tokens_per_s": (len(generated) / stream_duration) if stream_duration > 0 else None,
        "cpu_time_s": (cpu1 - cpu0) if (cpu0 is not None and cpu1 is not None) else None,
        "rss_before_mb": rss0, "rss_after_mb": rss1,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Local real-model external-validity experiment.")
    ap.add_argument("--model", default="HuggingFaceTB/SmolLM2-135M")
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--workloads", nargs="+", default=list(WORKLOADS))
    ap.add_argument("--postures", nargs="+", default=POSTURES)
    ap.add_argument("--threads", type=int, default=4, help="torch CPU threads (pinned for stability)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(args.threads)
    torch.manual_seed(SEED)

    try:
        from huggingface_hub import HfApi
        revision = HfApi().model_info(args.model).sha
    except Exception:  # noqa: BLE001
        revision = "unknown"

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model)
    model.eval()
    n_params = sum(p.numel() for p in model.parameters())
    print(f"model={args.model} rev={revision[:12]} params={n_params/1e6:.1f}M threads={args.threads}")

    prompts = {w: build_prompt(tokenizer, WORKLOADS[w]) for w in args.workloads}
    for w, p in prompts.items():
        got = len(tokenizer.encode(p, add_special_tokens=False))
        assert got == WORKLOADS[w], f"{w}: {got} != {WORKLOADS[w]}"
        print(f"  workload {w}: prompt exactly {got} tokens")

    # warm-up (weights paging, kernel autotune)
    run_one(model, tokenizer, torch, prompts[args.workloads[0]], 4, "none")

    rows: list[dict] = []
    for w in args.workloads:
        for posture in args.postures:
            for r in range(args.reps):
                gc.collect()
                rec = run_one(model, tokenizer, torch, prompts[w], args.max_new_tokens, posture)
                rec.update({"workload": w, "rep": r})
                rows.append(rec)
            sub = [x for x in rows if x["workload"] == w and x["posture"] == posture]
            print(f"[{w:<7} {posture:<18}] e2e_p50={statistics.median(x['e2e_s'] for x in sub):7.3f}s "
                  f"ttft={statistics.median(x['ttft_s'] for x in sub):6.3f}s "
                  f"recount={statistics.median(x['recount_s'] for x in sub)*1000:7.2f}ms "
                  f"recount/e2e={statistics.median(x['recount_frac_of_e2e'] for x in sub):.5%}")

    # Derived comparisons vs the no-recount posture, per workload.
    summary = []
    for w in args.workloads:
        base = [x for x in rows if x["workload"] == w and x["posture"] == "none"]
        base_e2e = statistics.median(x["e2e_s"] for x in base) if base else None
        for posture in args.postures:
            sub = [x for x in rows if x["workload"] == w and x["posture"] == posture]
            if not sub:
                continue
            e2e = sorted(x["e2e_s"] for x in sub)
            def pct(p):
                return e2e[min(len(e2e) - 1, max(0, int(round(p / 100 * (len(e2e) - 1)))))]
            med = statistics.median(x["e2e_s"] for x in sub)
            summary.append({
                "workload": w, "posture": posture, "n": len(sub),
                "e2e_mean_s": statistics.fmean(x["e2e_s"] for x in sub),
                "e2e_p50_s": pct(50), "e2e_p95_s": pct(95), "e2e_p99_s": pct(99),
                "e2e_std_s": statistics.stdev([x["e2e_s"] for x in sub]) if len(sub) > 1 else 0.0,
                "ttft_p50_s": statistics.median(x["ttft_s"] for x in sub),
                "stream_duration_p50_s": statistics.median(x["stream_duration_s"] for x in sub),
                "recount_p50_ms": statistics.median(x["recount_s"] for x in sub) * 1000,
                "accounting_p50_ms": statistics.median(x["accounting_s"] for x in sub) * 1000,
                "recount_frac_of_e2e_p50": statistics.median(x["recount_frac_of_e2e"] for x in sub),
                "gen_tokens_per_s_p50": statistics.median(x["gen_tokens_per_s"] for x in sub),
                "cpu_time_p50_s": statistics.median(x["cpu_time_s"] for x in sub if x["cpu_time_s"] is not None)
                    if any(x["cpu_time_s"] is not None for x in sub) else None,
                "rss_after_p50_mb": statistics.median(x["rss_after_mb"] for x in sub if x["rss_after_mb"])
                    if any(x["rss_after_mb"] for x in sub) else None,
                # throughput ratio = e2e_none / e2e_posture  (requests/sec ratio)
                "throughput_ratio_vs_none": (base_e2e / med) if (base_e2e and med) else None,
            })

    payload = {
        "benchmark": "real_model_recount",
        "label": "local real-model external-validity experiment",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "scope_warning": ("Small open model on local CPU. NOT a commercial provider, NOT a "
                          "production serving stack. Measures only the RELATIVE cost of "
                          "authoritative recount within an end-to-end inference pipeline. "
                          "Results do not generalize to commercial providers."),
        "model": {"repo": args.model, "revision": revision, "params": n_params,
                  "dtype": "float32", "device": "cpu", "decoding": "greedy (deterministic)",
                  "torch": torch.__version__, "torch_threads": args.threads},
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "cpu_count": os.cpu_count()},
        "parameters": {"workload_prompt_tokens": {w: WORKLOADS[w] for w in args.workloads},
                       "max_new_tokens": args.max_new_tokens, "reps": args.reps,
                       "postures": args.postures, "seed": SEED},
        "summary": summary, "runs": rows,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RAW / f"real_model_recount_{payload['generated_at']}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n{len(rows)} runs -> {out}")


if __name__ == "__main__":
    main()
