"""Generate LaTeX (booktabs) and Markdown tables from processed summaries.

No experimental number is entered by hand. Writes to results/tables/.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "results" / "processed"
TAB = ROOT / "results" / "tables"


def _latest(pattern: str, folder: Path) -> Path | None:
    c = sorted(folder.glob(pattern))
    return max(c, key=lambda p: p.stat().st_mtime) if c else None


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _write(name: str, header: list[str], rows: list[list[str]], caption: str, label: str) -> None:
    # markdown
    md = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    (TAB / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    # latex
    cols = "l" + "r" * (len(header) - 1)
    def esc(s):
        return (str(s).replace("\\", "").replace("_", r"\_").replace("%", r"\%")
                .replace("&", r"\&").replace("$", r"\$").replace("#", r"\#"))
    # Wrap wide tables in \resizebox so they cannot overflow the text block.
    widest = max([sum(len(str(c)) for c in r) for r in rows] + [sum(len(h) for h in header)]) if rows else 0
    wide = len(header) >= 6 or widest > 70
    tex = [r"\begin{table}[t]", r"\centering", r"\small",
           f"\\caption{{{esc(caption)}}}", f"\\label{{{label}}}"]
    if wide:
        tex.append(r"\resizebox{\linewidth}{!}{%")
    tex += [f"\\begin{{tabular}}{{{cols}}}", r"\toprule",
            " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
    for r in rows:
        tex.append(" & ".join(esc(x) for x in r) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular}"]
    if wide:
        tex.append(r"}")
    tex.append(r"\end{table}")
    (TAB / f"{name}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


def table_b0(b0: dict) -> None:
    rows = []
    for c in sorted(b0["cells"], key=lambda c: (c["posture"], c["concurrency"])):
        rows.append([c["posture"], str(c["concurrency"]), f"{c['served']['mean']:.1f}",
                     f"{c['dollar_leak']['mean']:.4f}", f"{c['trial_asr']['p']:.2f}",
                     f"{c['request_asr']['p']:.3f}", c["detection_status"]])
    _write("table_b0_baseline",
           ["posture", "conc", "served", "$-leak", "trial ASR", "req ASR", "detect"],
           rows, "B0 baseline: credit-decrement race (30 reps/cell).", "tab:b0")


def _min_conc(cells):
    v = [c.get("concurrency", 1) for c in cells]
    return min(v) if v else 1


def table_m1(m1: dict) -> None:
    base = _min_conc(m1["cells"])
    rows = []
    for c in [c for c in m1["cells"]
              if c["price_tier"] == "medium" and c.get("concurrency", 1) == base]:
        rows.append([c["architecture"], f"{c['abort_bin']:.0f}", f"{c['tokens_delivered']['mean']:.0f}",
                     f"{c['leak_per_request']:.4f}", f"{c['request_asr']['p']:.2f}",
                     f"{c['invariant_violation_rate']:.2f}", c["detection"]])
    _write("table_m1_results",
           ["architecture", "abort%", "delivered", "leak/req", "req ASR", "inv.viol", "detect"],
           rows, f"M1 metering-commit timing: leak vs. abort (medium tier, concurrency={base}).",
           "tab:m1")


def table_m1_concurrency(m1: dict) -> None:
    """Normalized per-request vulnerability across concurrency (workload held constant)."""
    concs = sorted({c.get("concurrency", 1) for c in m1["cells"]})
    if len(concs) < 2:
        return
    archs = sorted({c["architecture"] for c in m1["cells"]})
    rows = []
    for arch in archs:
        row = [arch]
        for cc in concs:
            grp = [c for c in m1["cells"] if c["architecture"] == arch
                   and c.get("concurrency", 1) == cc and c["client_type"] == "attacker"
                   and c["price_tier"] == "medium"]
            n = sum(g["n_records"] for g in grp)
            val = sum(g["leak_per_request"] * g["n_records"] for g in grp) / n if n else 0.0
            row.append(f"{val:.4f}")
        rows.append(row)
    _write("table_m1_concurrency", ["architecture"] + [f"c={c}" for c in concs], rows,
           "M1: leak PER REQUEST vs concurrency (request volume held constant, attacker arm).",
           "tab:m1conc")


def table_m2(m2: dict) -> None:
    base = _min_conc(m2["cells"])
    rows = []
    for c in [c for c in m2["cells"]
              if c["price_tier"] == "medium" and c.get("concurrency", 1) == base]:
        rows.append([c["architecture"], c["manipulation"], f"{c['leakage_efficiency']['mean']:.2f}",
                     f"{c['request_asr']['p']:.2f}", f"{c['invariant_violation_rate']:.2f}", c["detection"]])
    _write("table_m2_results",
           ["architecture", "manipulation", "leak eff.", "req ASR", "inv.viol", "detect"],
           rows, f"M2 usage-record authority: leakage efficiency by manipulation (medium tier, concurrency={base}).",
           "tab:m2")


def table_m2_concurrency(m2: dict) -> None:
    concs = sorted({c.get("concurrency", 1) for c in m2["cells"]})
    if len(concs) < 2:
        return
    archs = sorted({c["architecture"] for c in m2["cells"]})
    rows = []
    for arch in archs:
        row = [arch]
        for cc in concs:
            grp = [c for c in m2["cells"] if c["architecture"] == arch
                   and c.get("concurrency", 1) == cc and c["client_type"] == "attacker"
                   and c["price_tier"] == "medium"]
            n = sum(g["n_records"] for g in grp)
            eff = sum(g["leakage_efficiency"]["mean"] * g["n_records"] for g in grp) / n if n else 0.0
            row.append(f"{eff:.3f}")
        rows.append(row)
    _write("table_m2_concurrency", ["architecture"] + [f"c={c}" for c in concs], rows,
           "M2: leakage efficiency vs concurrency (attacker arm; volume held constant).",
           "tab:m2conc")


def table_defense(m1: dict, m2: dict) -> None:
    rows = []
    for mech, s in (("M1", m1), ("M2", m2)):
        for arch in dict.fromkeys(c["architecture"] for c in s["cells"]):
            cs = [c for c in s["cells"] if c["architecture"] == arch]
            max_asr = max(c["request_asr"]["p"] for c in cs)
            det = "D3" if max_asr == 0 else min((c["detection"] for c in cs if c["detection"] != "n/a"),
                                                default="n/a")
            rows.append([mech, arch, "safe" if max_asr == 0 else "LEAKS",
                         f"{max_asr:.2f}", det])
    _write("table_defense_summary",
           ["mech", "architecture", "verdict", "max req ASR", "best detect"],
           rows, "Architecture safety summary across all attacks and tiers.", "tab:defense")


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    b0 = _latest("class6_*.summary.json", ROOT / "results")
    m1 = _latest("m1_*.summary.json", PROC)
    m2 = _latest("m2_*.summary.json", PROC)
    if b0:
        table_b0(_load(b0))
    if m1:
        _m1 = _load(m1)
        table_m1(_m1)
        table_m1_concurrency(_m1)
    if m2:
        _m2 = _load(m2)
        table_m2(_m2)
        table_m2_concurrency(_m2)
    if m1 and m2:
        table_defense(_load(m1), _load(m2))
    print("tables written to", TAB)
    for f in sorted(TAB.glob("*.tex")):
        print("  -", f.name)


if __name__ == "__main__":
    main()
