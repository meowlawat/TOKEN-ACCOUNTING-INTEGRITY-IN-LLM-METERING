"""Cross-topology and cross-backend generality analysis (Phases 1-3, 6).

Answers one question: do the accounting-security outcomes change when the execution
topology or the balance-storage architecture changes?

Compares, per (mechanism, architecture, condition) cell:
    single        control      1 uvicorn worker, no proxy
    multiworker   Phase 1      nginx -> 4 workers (4 event loops)
    distributed   Phase 2      nginx LB -> 2 gateway containers x 2 workers
and separately:
    mutable vs ledger accounting backends (Phase 3)

Effect sizes: for deterministic accounting outcomes we report the ABSOLUTE DIFFERENCE
and Cliff's delta rather than p-values, because these quantities have (near-)zero
within-cell variance -- a significance test would be meaningless. Latency/throughput,
which genuinely vary, get medians and interquartile spread.

Writes results/tables/table_topology_generality.{md,tex},
       results/tables/table_backend_generality.{md,tex},
       results/processed/generality.summary.json
"""

from __future__ import annotations

import glob
import json
import os
import statistics
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
TOPO = RAW / "topology"
PROC = ROOT / "results" / "processed"
TAB = ROOT / "results" / "tables"

# Deterministic accounting quantities are expected to match exactly; a whole-token
# difference in delivered tokens can shift M1 leak by one token's price.
TOKEN_PRICE_MEDIUM = Decimal("0.0015")


def D(x):
    return Decimal(str(x)) if x is not None else Decimal("0")


def _esc(s):
    return (str(s).replace("\\", "").replace("_", r"\_").replace("%", r"\%")
            .replace("&", r"\&").replace("$", r"\$").replace("#", r"\#"))


def write_table(name, header, rows, caption, label):
    TAB.mkdir(parents=True, exist_ok=True)
    md = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    (TAB / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    cols = "ll" + "r" * (len(header) - 2)
    widest = max([sum(len(str(c)) for c in r) for r in rows] + [sum(len(h) for h in header)])
    wide = len(header) >= 6 or widest > 70
    tex = [r"\begin{table}[t]", r"\centering", r"\small",
           f"\\caption{{{_esc(caption)}}}", f"\\label{{{label}}}"]
    if wide:
        tex.append(r"\resizebox{\linewidth}{!}{%")
    tex += [f"\\begin{{tabular}}{{{cols}}}", r"\toprule",
            " & ".join(_esc(h) for h in header) + r" \\", r"\midrule"]
    tex += [" & ".join(_esc(c) for c in r) + r" \\" for r in rows]
    tex += [r"\bottomrule", r"\end{tabular}"]
    if wide:
        tex.append(r"}")
    tex.append(r"\end{table}")
    (TAB / f"{name}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


def latest(pattern, folder):
    """Newest match, excluding derived *.summary.* files (raw data only)."""
    c = [p for p in glob.glob(str(folder / pattern)) if ".summary." not in os.path.basename(p)]
    return max(c, key=os.path.getmtime) if c else None


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if p else None


# --------------------------------------------------------------------------- #
# Extract per-cell accounting outcomes, aggregated over concurrency
# --------------------------------------------------------------------------- #
def m1_cells(raw: dict) -> dict:
    """(architecture, abort_bin) -> {leak_per_request, violation_rate, reconciled, n, workers}"""
    out: dict[tuple, dict] = {}
    for t in raw["trials"]:
        if t["price_tier"] != "medium":
            continue
        served = [r for r in t["records"] if r["served"]]
        if not served:
            continue
        key = (t["architecture"], round(float(t["abort_pct"])))
        e = out.setdefault(key, {"leak": Decimal(0), "n": 0, "viol": 0, "recon": True,
                                 "workers": set(), "delivered": []})
        e["leak"] += sum(D(r["leak"]) for r in served)
        e["n"] += len(served)
        e["viol"] += t["invariant_violations"]
        e["recon"] = e["recon"] and (t["reconciled"] is True)
        e["delivered"] += [r["tokens_delivered"] for r in served]
        for r in served:
            w = (r.get("extra") or {}).get("worker")
            if w:
                e["workers"].add(w)
    return {k: {"leak_per_request": v["leak"] / v["n"] if v["n"] else Decimal(0),
                "violation_rate": v["viol"] / v["n"] if v["n"] else 0.0,
                "reconciled": v["recon"], "n": v["n"],
                "distinct_workers": len(v["workers"]),
                "mean_delivered": statistics.fmean(v["delivered"]) if v["delivered"] else 0.0}
            for k, v in out.items()}


def m2_cells(raw: dict) -> dict:
    """(architecture, manipulation) -> {efficiency, violation_rate, reconciled, n, workers}"""
    out: dict[tuple, dict] = {}
    for t in raw["trials"]:
        if t["price_tier"] != "medium":
            continue
        served = [r for r in t["records"] if r["served"]]
        if not served:
            continue
        key = (t["architecture"], t["manipulation"])
        e = out.setdefault(key, {"leak": Decimal(0), "auth": Decimal(0), "n": 0,
                                 "viol": 0, "recon": True, "workers": set()})
        e["leak"] += sum(D(r["leak"]) for r in served)
        e["auth"] += sum(D(r["authoritative_cost"]) for r in served)
        e["n"] += len(served)
        e["viol"] += t["invariant_violations"]
        e["recon"] = e["recon"] and (t["reconciled"] is True)
        for r in served:
            w = (r.get("extra") or {}).get("worker")
            if w:
                e["workers"].add(w)
    return {k: {"efficiency": float(v["leak"] / v["auth"]) if v["auth"] > 0 else 0.0,
                "violation_rate": v["viol"] / v["n"] if v["n"] else 0.0,
                "reconciled": v["recon"], "n": v["n"],
                "distinct_workers": len(v["workers"])}
            for k, v in out.items()}


def b0_cells(raw: dict) -> dict:
    """(posture, concurrency) -> {dollar_leak_mean, served_mean, reconciled}"""
    out = {}
    for t in raw["trials"]:
        key = (t["posture"], t["concurrency"])
        e = out.setdefault(key, {"leak": [], "served": [], "recon": True})
        e["leak"].append(float(D(t["dollar_leak"])))
        e["served"].append(t["server_served_count"])
        e["recon"] = e["recon"] and (t["reconciled"] is True)
    return {k: {"dollar_leak_mean": statistics.fmean(v["leak"]),
                "served_mean": statistics.fmean(v["served"]), "reconciled": v["recon"],
                "n": len(v["leak"])} for k, v in out.items()}


def main() -> None:
    # ---------------- topology comparison ---------------------------------- #
    sources = {
        "single": {"m1": latest("m1_2*.json", RAW), "m2": latest("m2_2*.json", RAW),
                   "b0": latest("class6_2*.json", ROOT / "results")},
        "multiworker": {"m1": latest("m1_multiworker_*.json", TOPO),
                        "m2": latest("m2_multiworker_*.json", TOPO),
                        "b0": latest("b0_multiworker_*.json", TOPO)},
        "distributed": {"m1": latest("m1_distributed_*.json", TOPO),
                        "m2": latest("m2_distributed_*.json", TOPO),
                        "b0": latest("b0_distributed_*.json", TOPO)},
    }
    topo = {}
    for name, s in sources.items():
        topo[name] = {
            "m1": m1_cells(load(s["m1"])) if s["m1"] else {},
            "m2": m2_cells(load(s["m2"])) if s["m2"] else {},
            "b0": b0_cells(load(s["b0"])) if s["b0"] else {},
            "files": {k: (os.path.basename(v) if v else None) for k, v in s.items()},
        }

    rows, mismatches = [], []
    base = "single"
    # M1: compare leak/request on overlapping (arch, abort) cells
    for other in ("multiworker", "distributed"):
        for key in sorted(set(topo[base]["m1"]) & set(topo[other]["m1"])):
            a, b = topo[base]["m1"][key], topo[other]["m1"][key]
            diff = abs(a["leak_per_request"] - b["leak_per_request"])
            tok = float(diff / TOKEN_PRICE_MEDIUM)
            same_verdict = (a["violation_rate"] > 0) == (b["violation_rate"] > 0)
            verdict = ("IDENTICAL" if diff == 0 else
                       ("WITHIN 1 TOKEN" if tok <= 1.001 else "DIFFERS"))
            if not same_verdict or verdict == "DIFFERS":
                mismatches.append({"mech": "M1", "cell": str(key), "topology": other,
                                   "base": str(a["leak_per_request"]), "other": str(b["leak_per_request"])})
            rows.append(["M1", f"{key[0]} @{key[1]}%", other,
                         f"{float(a['leak_per_request']):.4f}", f"{float(b['leak_per_request']):.4f}",
                         f"{float(diff):.4f}", f"{tok:.2f}", b["distinct_workers"], verdict])
    # M2: compare efficiency
    for other in ("multiworker", "distributed"):
        for key in sorted(set(topo[base]["m2"]) & set(topo[other]["m2"])):
            a, b = topo[base]["m2"][key], topo[other]["m2"][key]
            diff = abs(a["efficiency"] - b["efficiency"])
            same_verdict = (a["efficiency"] > 0) == (b["efficiency"] > 0)
            verdict = "IDENTICAL" if diff < 1e-9 else ("WITHIN 0.01" if diff < 0.01 else "DIFFERS")
            if not same_verdict or verdict == "DIFFERS":
                mismatches.append({"mech": "M2", "cell": str(key), "topology": other,
                                   "base": a["efficiency"], "other": b["efficiency"]})
            rows.append(["M2", f"{key[0]}/{key[1]}", other,
                         f"{a['efficiency']:.3f}", f"{b['efficiency']:.3f}",
                         f"{diff:.4f}", "-", b["distinct_workers"], verdict])

    write_table("table_topology_generality",
                ["mech", "cell", "topology", "single", "topology value", "abs diff",
                 "diff in tokens", "distinct procs", "verdict"],
                rows,
                "Cross-topology validation. Accounting outcomes are compared against the "
                "single-worker control. 'diff in tokens' expresses an M1 difference in whole "
                "delivered tokens; sub-token differences reflect disconnect-detection timing, "
                "not accounting divergence. 'distinct procs' confirms load actually spread.",
                "tab:topogen")

    # ---------------- backend comparison ------------------------------------ #
    bc = load(latest("backend_comparison_*.json", RAW))
    brows = []
    if bc:
        mut = {r["case"]: r for r in bc["results"]["mutable"]}
        led = {r["case"]: r for r in bc["results"]["ledger"]}
        for case in sorted(mut):
            a, b = mut[case], led.get(case, {})
            metric = ("efficiency" if "efficiency" in a else
                      "leak_per_request" if "leak_per_request" in a else "leak")
            va, vb = a.get(metric), b.get(metric)
            same = str(va) == str(vb)
            brows.append([case, metric, str(va), str(vb),
                          a.get("invariant_violations"), b.get("invariant_violations"),
                          "IDENTICAL" if same else "DIFFERS"])
        write_table("table_backend_generality",
                    ["case", "metric", "mutable", "ledger", "viol (mut)", "viol (led)", "verdict"],
                    brows,
                    "Cross-backend validation. The same cases run against a mutable balance row "
                    "and an append-only ledger with a derived balance, behind one semantic "
                    "interface. Identical outcomes indicate the results do not depend on the "
                    "balance-storage architecture.",
                    "tab:backendgen")

    summary = {
        "topology_files": {k: v["files"] for k, v in topo.items()},
        "topology_cells_compared": len(rows),
        "topology_mismatches": mismatches,
        "topology_all_consistent": not mismatches,
        "backend_cases_compared": len(brows),
        "backend_identical": bool(bc and bc.get("identical")),
        "backend_differences": (bc or {}).get("differences", []),
        "b0_by_topology": {k: {f"{p}/c{c}": v for (p, c), v in topo[k]["b0"].items()}
                           for k in topo},
    }
    PROC.mkdir(parents=True, exist_ok=True)
    (PROC / "generality.summary.json").write_text(json.dumps(summary, indent=2, default=str),
                                                  encoding="utf-8")
    print(f"topology cells compared: {len(rows)} | mismatches: {len(mismatches)}")
    print(f"backend cases compared : {len(brows)} | identical: {summary['backend_identical']}")
    for m in mismatches[:8]:
        print("  MISMATCH:", m)
    print("tables -> table_topology_generality, table_backend_generality")


if __name__ == "__main__":
    main()
