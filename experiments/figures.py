"""Generate publication figures from processed summaries. No hand-drawn charts.

Reads the latest processed M1/M2 summaries and the B0 class-6 summary, writing PNGs
to results/figures/. Run after the summarizers.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "results" / "processed"
FIG = ROOT / "results" / "figures"

plt.rcParams.update({
    "figure.dpi": 140, "savefig.dpi": 140, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "figure.autolayout": True,
})
# colour-blind-safe categorical palette
PAL = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860", "#DA8BC3", "#8C8C8C"]


def _latest(pattern: str, folder: Path) -> Path | None:
    c = sorted(folder.glob(pattern))
    return max(c, key=lambda p: p.stat().st_mtime) if c else None


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _min_conc(cells: list[dict]) -> int:
    vals = [c.get("concurrency", 1) for c in cells]
    return min(vals) if vals else 1


def fig_m1_abort_curve(m1: dict) -> None:
    """Leak vs abort timing at the LOWEST concurrency (isolates the timing effect)."""
    base_c = _min_conc(m1["cells"])
    cells = [c for c in m1["cells"]
             if c["price_tier"] == "medium" and c.get("concurrency", 1) == base_c]
    archs = sorted({c["architecture"] for c in cells})
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for i, arch in enumerate(archs):
        cs = sorted((c for c in cells if c["architecture"] == arch), key=lambda c: c["abort_bin"])
        xs = [c["abort_bin"] for c in cs]
        ys = [c["leak"]["mean"] for c in cs]
        errs = [c["leak"]["std"] for c in cs]
        ls = "--" if arch in ("pre_debit", "reserve_reconcile") else "-"
        ax.errorbar(xs, ys, yerr=errs, marker="o", ms=4, lw=1.8, ls=ls, color=PAL[i % len(PAL)], label=arch)
    ax.set_xlabel("abort point (% of stream delivered before disconnect)")
    ax.set_ylabel("mean leak per request ($, medium tier)")
    ax.set_title(f"M1: leakage vs. abort timing (concurrency={base_c})")
    ax.legend(fontsize=8, frameon=False)
    fig.savefig(FIG / "fig_m1_abort_curve.png")
    plt.close(fig)


def fig_m1_concurrency(m1: dict) -> None:
    """NORMALIZED leak per request vs concurrency: does per-request vulnerability scale?"""
    cells = [c for c in m1["cells"] if c["price_tier"] == "medium"]
    concs = sorted({c.get("concurrency", 1) for c in cells})
    if len(concs) < 2:
        return
    archs = sorted({c["architecture"] for c in cells})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.0))
    for i, arch in enumerate(archs):
        xs, ys, zs = [], [], []
        for cc in concs:
            grp = [c for c in cells if c["architecture"] == arch and c.get("concurrency", 1) == cc
                   and c["client_type"] == "attacker"]
            if not grp:
                continue
            n = sum(g["n_records"] for g in grp)
            xs.append(cc)
            ys.append(sum(g["leak_per_request"] * g["n_records"] for g in grp) / n if n else 0.0)
            zs.append(sum(g["request_asr"]["p"] * g["n_records"] for g in grp) / n if n else 0.0)
        if xs:
            ax1.plot(xs, ys, marker="o", ms=5, lw=1.8, color=PAL[i % len(PAL)], label=arch)
            ax2.plot(xs, zs, marker="o", ms=5, lw=1.8, color=PAL[i % len(PAL)], label=arch)
    for ax, lab, ttl in ((ax1, "leak per request ($)", "Normalized leakage vs concurrency"),
                         (ax2, "request ASR", "Per-request attack success vs concurrency")):
        ax.set_xscale("log"); ax.set_xlabel("concurrency"); ax.set_ylabel(lab); ax.set_title(ttl)
    ax2.set_ylim(-0.05, 1.05)
    ax1.legend(fontsize=7, frameon=False)
    fig.suptitle("M1: does concurrency change PER-REQUEST vulnerability? (volume held constant)",
                 fontsize=10)
    fig.savefig(FIG / "fig_m1_concurrency.png")
    plt.close(fig)


def fig_m2_concurrency(m2: dict) -> None:
    """M2 leakage efficiency and defense latency vs concurrency."""
    cells = [c for c in m2["cells"] if c["price_tier"] == "medium"]
    concs = sorted({c.get("concurrency", 1) for c in cells})
    if len(concs) < 2:
        return
    archs = sorted({c["architecture"] for c in cells})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.0))
    for i, arch in enumerate(archs):
        xs, ys, ls_ = [], [], []
        for cc in concs:
            grp = [c for c in cells if c["architecture"] == arch and c.get("concurrency", 1) == cc
                   and c["client_type"] == "attacker"]
            if not grp:
                continue
            n = sum(g["n_records"] for g in grp)
            xs.append(cc)
            ys.append(sum(g["leakage_efficiency"]["mean"] * g["n_records"] for g in grp) / n if n else 0.0)
            lat = [g["latency_p95_ms"] for g in grp if g.get("latency_p95_ms")]
            ls_.append(sum(lat) / len(lat) if lat else 0.0)
        if xs:
            ax1.plot(xs, ys, marker="o", ms=5, lw=1.8, color=PAL[i % len(PAL)], label=arch)
            ax2.plot(xs, ls_, marker="o", ms=5, lw=1.8, color=PAL[i % len(PAL)], label=arch)
    ax1.set_ylabel("leakage efficiency"); ax1.set_title("Accounting failure vs concurrency")
    ax2.set_ylabel("p95 latency (ms)"); ax2.set_title("Defense cost vs concurrency (secondary)")
    for ax in (ax1, ax2):
        ax.set_xscale("log"); ax.set_xlabel("concurrency")
    ax1.set_ylim(-0.05, 1.05)
    ax1.legend(fontsize=7, frameon=False)
    fig.suptitle("M2: concurrency vs accounting integrity and defense overhead", fontsize=10)
    fig.savefig(FIG / "fig_m2_concurrency.png")
    plt.close(fig)


def fig_m2_efficiency_heatmap(m2: dict) -> None:
    base_c = _min_conc(m2["cells"])
    cells = [c for c in m2["cells"]
             if c["price_tier"] == "medium" and c.get("concurrency", 1) == base_c]
    archs = m2["parameters"]["architectures"]
    manips = m2["parameters"]["manipulations"]
    M = np.zeros((len(archs), len(manips)))
    for c in cells:
        i = archs.index(c["architecture"])
        j = manips.index(c["manipulation"])
        M[i, j] = c["leakage_efficiency"]["mean"]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    im = ax.imshow(M, cmap="magma_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(manips)))
    ax.set_xticklabels(manips, rotation=40, ha="right", fontsize=7)
    ax.set_yticks(range(len(archs)))
    ax.set_yticklabels(archs, fontsize=8)
    for i in range(len(archs)):
        for j in range(len(manips)):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    color="white" if M[i, j] > 0.5 else "black", fontsize=6.5)
    ax.set_title("M2: leakage efficiency (fraction of value evaded) — medium tier")
    fig.colorbar(im, ax=ax, shrink=0.8, label="leakage efficiency")
    fig.savefig(FIG / "fig_m2_efficiency_heatmap.png")
    plt.close(fig)


def fig_b0_concurrency(b0: dict) -> None:
    cells = b0["cells"]
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    for i, posture in enumerate(["vulnerable", "hardened"]):
        cs = sorted((c for c in cells if c["posture"] == posture), key=lambda c: c["concurrency"])
        xs = [c["concurrency"] for c in cs]
        ys = [c["dollar_leak"]["mean"] for c in cs]
        ax.plot(xs, ys, marker="o", ms=5, lw=1.8, color=PAL[i], label=posture)
    ax.set_xlabel("concurrency (simultaneous requests)")
    ax.set_ylabel("mean $-leak per trial (medium-equiv.)")
    ax.set_title("B0 baseline: credit-decrement race leakage vs. concurrency")
    ax.legend(frameon=False)
    fig.savefig(FIG / "fig_b0_concurrency.png")
    plt.close(fig)


def fig_defense_summary(m1: dict, m2: dict) -> None:
    """Max leakage efficiency per architecture (0 = safe), across all attacks/tiers."""
    rows = []
    for c in m1["cells"]:
        eff = c["leak"]["mean"]  # dollar; convert to efficiency proxy not available -> use ASR
        rows.append(("M1:" + c["architecture"], c["request_asr"]["p"]))
    for c in m2["cells"]:
        rows.append(("M2:" + c["architecture"], c["request_asr"]["p"]))
    agg: dict[str, float] = {}
    for name, v in rows:
        agg[name] = max(agg.get(name, 0.0), v)
    names = list(agg.keys())
    vals = [agg[n] for n in names]
    order = np.argsort(vals)
    names = [names[i] for i in order]
    vals = [vals[i] for i in order]
    colors = ["#55A868" if v == 0 else "#C44E52" for v in vals]
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    ax.barh(names, vals, color=colors)
    ax.set_xlabel("max request-ASR across attacks (0 = safe)")
    ax.set_title("Architecture safety: which designs leak")
    fig.savefig(FIG / "fig_architecture_safety.png")
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    m1p = _latest("m1_*.summary.json", PROC)
    m2p = _latest("m2_*.summary.json", PROC)
    b0p = _latest("class6_*.summary.json", ROOT / "results")
    made = []
    if m1p:
        m1 = _load(m1p)
        fig_m1_abort_curve(m1); made.append("fig_m1_abort_curve.png")
        fig_m1_concurrency(m1); made.append("fig_m1_concurrency.png (if multi-concurrency)")
    if m2p:
        m2 = _load(m2p)
        fig_m2_efficiency_heatmap(m2); made.append("fig_m2_efficiency_heatmap.png")
        fig_m2_concurrency(m2); made.append("fig_m2_concurrency.png (if multi-concurrency)")
    if b0p:
        b0 = _load(b0p); fig_b0_concurrency(b0); made.append("fig_b0_concurrency.png")
    if m1p and m2p:
        fig_defense_summary(_load(m1p), _load(m2p)); made.append("fig_architecture_safety.png")
    print("figures written to", FIG)
    for m in made:
        print("  -", m)


if __name__ == "__main__":
    main()
