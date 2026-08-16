"""Summarize the tokenizer and gateway-recount benchmarks into CSV/MD/figures.

Consumes ONLY raw JSON from results/raw/. Emits:
  results/processed/tokenizer_overhead.csv
  results/processed/gateway_recount.csv
  results/tables/tokenizer_overhead.md
  results/tables/gateway_recount.md
  results/figures/tokenizer_latency.png
  results/figures/tokenizer_throughput.png
  results/figures/gateway_recount_throughput.png
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
PROC = ROOT / "results" / "processed"
TAB = ROOT / "results" / "tables"
FIG = ROOT / "results" / "figures"

plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 140, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.autolayout": True})
PAL = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#8C8C8C"]


def _latest(pattern: str) -> Path | None:
    c = sorted(RAW.glob(pattern))
    return max(c, key=lambda p: p.stat().st_mtime) if c else None


# --------------------------------------------------------------------------- #
# Tokenizer benchmark
# --------------------------------------------------------------------------- #
_TOK_COLS = ["engine", "family", "workload", "target_tokens", "verified_tokens", "reps",
             "cold_ms", "mean_ms", "std_ms", "p50_ms", "p95_ms", "p99_ms",
             "tokens_per_sec_at_p50", "us_per_token_at_p50",
             "tracemalloc_peak_python_heap_kib", "process_rss_delta_mb", "cold_warm_ratio"]


def tokenizer_outputs(raw: dict) -> None:
    rows = [r for r in raw["results"] if r["status"] == "ok"]
    PROC.mkdir(parents=True, exist_ok=True)
    with (PROC / "tokenizer_overhead.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_TOK_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v)
                        for k, v in r.items() if k in _TOK_COLS})

    engines = [e["name"] for e in raw["engines"]]
    lens = raw["parameters"]["lengths"]
    workloads = raw["parameters"]["workloads"]

    # --- Markdown table ---
    lines = ["# Tokenizer recount overhead (standalone microbenchmark)\n",
             f"- Generated: `{raw['generated_at']}`",
             f"- **Scope:** {raw['scope_warning']}",
             f"- Host: {raw['environment'].get('platform')}, "
             f"{raw['environment'].get('cpu_count')} logical CPUs, "
             f"Python {raw['environment'].get('python')}",
             f"- Reps: {raw['parameters']['rep_policy']}; warm-up {raw['parameters']['warmup_runs']} runs",
             "\n## Engines / revisions\n",
             "| engine | library | version | revision | vocab |", "|---|---|---|---|---|"]
    for e in raw["engines"]:
        lines.append(f"| `{e['name']}` | {e.get('library','')} | {e.get('library_version','')} "
                     f"| `{str(e.get('revision',''))[:16]}` | {e.get('n_vocab') or e.get('vocab_size','')} |")
    for wl in workloads:
        lines += [f"\n## p50 latency (ms) — workload: {wl}\n",
                  "| engine | " + " | ".join(f"{L} tok" for L in lens) + " |",
                  "|---" * (len(lens) + 1) + "|"]
        for en in engines:
            cells = []
            for L in lens:
                m = [r for r in rows if r["engine"] == en and r["workload"] == wl and r["target_tokens"] == L]
                cells.append(f"{m[0]['p50_ms']:.2f}" if m else "—")
            lines.append(f"| `{en}` | " + " | ".join(cells) + " |")
    lines += ["\n## Throughput (tokens/sec at p50, natural)\n",
              "| engine | " + " | ".join(f"{L} tok" for L in lens) + " |",
              "|---" * (len(lens) + 1) + "|"]
    for en in engines:
        cells = []
        for L in lens:
            m = [r for r in rows if r["engine"] == en and r["workload"] == "natural" and r["target_tokens"] == L]
            cells.append(f"{m[0]['tokens_per_sec_at_p50']:,.0f}" if m else "—")
        lines.append(f"| `{en}` | " + " | ".join(cells) + " |")
    lines.append("\n**Memory note:** `tracemalloc_peak_python_heap_kib` is Python-heap "
                 "allocation ONLY; native Rust/C tokenizer buffers are not visible to it. "
                 "Process RSS deltas are reported separately and are noisy.\n")
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / "tokenizer_overhead.md").write_text("\n".join(lines), encoding="utf-8")

    # --- Figures ---
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(workloads), figsize=(4.2 * len(workloads), 3.6), sharey=True)
    axes = [axes] if len(workloads) == 1 else list(axes)
    for ax, wl in zip(axes, workloads):
        for i, en in enumerate(engines):
            pts = sorted([(r["target_tokens"], r["p50_ms"]) for r in rows
                          if r["engine"] == en and r["workload"] == wl])
            if pts:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=3.5,
                        lw=1.6, color=PAL[i % len(PAL)], label=en)
        ax.set_xscale("log", base=2); ax.set_yscale("log")
        ax.set_title(wl); ax.set_xlabel("input length (tokens)")
    axes[0].set_ylabel("p50 encode latency (ms)")
    axes[-1].legend(fontsize=6.5, frameon=False)
    fig.suptitle("Standalone tokenizer recount latency (NOT gateway throughput)", fontsize=10)
    fig.savefig(FIG / "tokenizer_latency.png"); plt.close(fig)

    fig, axes = plt.subplots(1, len(workloads), figsize=(4.2 * len(workloads), 3.6), sharey=True)
    axes = [axes] if len(workloads) == 1 else list(axes)
    for ax, wl in zip(axes, workloads):
        for i, en in enumerate(engines):
            pts = sorted([(r["target_tokens"], r["tokens_per_sec_at_p50"]) for r in rows
                          if r["engine"] == en and r["workload"] == wl])
            if pts:
                ax.plot([p[0] for p in pts], [p[1] / 1e6 for p in pts], marker="o", ms=3.5,
                        lw=1.6, color=PAL[i % len(PAL)], label=en)
        ax.set_xscale("log", base=2); ax.set_title(wl); ax.set_xlabel("input length (tokens)")
    axes[0].set_ylabel("throughput (M tokens/sec)")
    axes[-1].legend(fontsize=6.5, frameon=False)
    fig.suptitle("Tokenizer throughput by engine and workload", fontsize=10)
    fig.savefig(FIG / "tokenizer_throughput.png"); plt.close(fig)


# --------------------------------------------------------------------------- #
# Gateway recount benchmark
# --------------------------------------------------------------------------- #
_GW_COLS = ["engine", "size_tokens_cl100k", "concurrency", "requests_ok", "throughput_rps",
            "throughput_ratio_vs_none", "latency_p50", "latency_p95", "latency_p99",
            "latency_p50_delta_ms", "latency_p99_delta_ms", "tokenize_ms_mean",
            "server_total_ms_mean", "error_rate"]


def gateway_outputs(raw: dict) -> None:
    cells = raw["cells"]
    PROC.mkdir(parents=True, exist_ok=True)
    with (PROC / "gateway_recount.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_GW_COLS)
        w.writeheader()
        for c in cells:
            w.writerow({
                "engine": c["engine"], "size_tokens_cl100k": c["size_tokens_cl100k"],
                "concurrency": c["concurrency"], "requests_ok": c["requests_ok"],
                "throughput_rps": round(c["throughput_rps"], 3),
                "throughput_ratio_vs_none": round(c.get("throughput_ratio_vs_none", float("nan")), 4)
                    if c.get("throughput_ratio_vs_none") is not None else "",
                "latency_p50": round(c["latency_ms"]["p50"], 3),
                "latency_p95": round(c["latency_ms"]["p95"], 3),
                "latency_p99": round(c["latency_ms"]["p99"], 3),
                "latency_p50_delta_ms": round(c.get("latency_p50_delta_ms", 0.0), 3)
                    if c.get("latency_p50_delta_ms") is not None else "",
                "latency_p99_delta_ms": round(c.get("latency_p99_delta_ms", 0.0), 3)
                    if c.get("latency_p99_delta_ms") is not None else "",
                "tokenize_ms_mean": round(c["tokenize_ms_mean"], 3),
                "server_total_ms_mean": round(c["server_total_ms_mean"], 3),
                "error_rate": round(c["error_rate"], 4)})

    sizes = raw["parameters"]["sizes"]
    concs = raw["parameters"]["concurrency"]
    engines = [e for e in raw["parameters"]["engines"] if any(c["engine"] == e for c in cells)]

    lines = ["# Gateway-level recount overhead (end-to-end)\n",
             f"- Generated: `{raw['generated_at']}`",
             f"- **Scope:** {raw['scope_note']}",
             f"- Duration/cell: {raw['parameters']['duration_s']}s; workload "
             f"`{raw['parameters']['workload']}`; sizes exact under "
             f"`{raw['parameters']['reference_tokenizer']}`\n",
             "## Throughput ratio vs. no-recount (1.00 = free)\n"]
    for size in sizes:
        lines += [f"\n### {size} tokens/request\n",
                  "| engine | " + " | ".join(f"c={c}" for c in concs) + " |",
                  "|---" * (len(concs) + 1) + "|"]
        for en in engines:
            cells_row = []
            for c in concs:
                m = [x for x in cells if x["engine"] == en and x["size_tokens_cl100k"] == size
                     and x["concurrency"] == c]
                if m and m[0].get("throughput_ratio_vs_none") is not None:
                    cells_row.append(f"{m[0]['throughput_ratio_vs_none']:.3f}")
                elif m:
                    cells_row.append("1.000" if en == "none" else "—")
                else:
                    cells_row.append("—")
            lines.append(f"| `{en}` | " + " | ".join(cells_row) + " |")
    lines += ["\n## Server-measured tokenization component (mean ms)\n",
              "| engine | " + " | ".join(f"{s} tok" for s in sizes) + " |",
              "|---" * (len(sizes) + 1) + "|"]
    for en in engines:
        row = []
        for s in sizes:
            m = [x for x in cells if x["engine"] == en and x["size_tokens_cl100k"] == s
                 and x["concurrency"] == 1]
            row.append(f"{m[0]['tokenize_ms_mean']:.2f}" if m else "—")
        lines.append(f"| `{en}` | " + " | ".join(row) + " |")
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / "gateway_recount.md").write_text("\n".join(lines), encoding="utf-8")

    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, len(sizes), figsize=(3.6 * len(sizes), 3.4), sharey=True)
    axes = [axes] if len(sizes) == 1 else list(axes)
    for ax, size in zip(axes, sizes):
        for i, en in enumerate(engines):
            pts = sorted([(x["concurrency"], x.get("throughput_ratio_vs_none"))
                          for x in cells if x["engine"] == en and x["size_tokens_cl100k"] == size
                          and x.get("throughput_ratio_vs_none") is not None])
            if pts:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=4, lw=1.6,
                        color=PAL[i % len(PAL)], label=en)
        ax.axhline(1.0, color="black", lw=0.8, ls=":")
        ax.set_xscale("log"); ax.set_title(f"{size} tokens"); ax.set_xlabel("concurrency")
    axes[0].set_ylabel("throughput ratio vs. no recount")
    axes[-1].legend(fontsize=6.5, frameon=False)
    fig.suptitle("Gateway throughput cost of server-side recount (1.0 = free)\n"
                 "median of 3 repeats; c>=50 is host-saturated and excluded from "
                 "headline performance claims", fontsize=9)
    fig.savefig(FIG / "gateway_recount_throughput.png"); plt.close(fig)


def main() -> None:
    tok = _latest("tokenizer_overhead_*.json")
    gw = _latest("gateway_recount_*.json")
    if tok:
        tokenizer_outputs(json.loads(tok.read_text(encoding="utf-8")))
        print(f"tokenizer  <- {tok.name}")
    if gw:
        gateway_outputs(json.loads(gw.read_text(encoding="utf-8")))
        print(f"gateway    <- {gw.name}")
    print("wrote processed CSV, tables, figures")


if __name__ == "__main__":
    main()
