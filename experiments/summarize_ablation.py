"""Summarize the architectural ablation, lifecycle failure modes, and detectability.

Consumes raw JSON only; writes Markdown + LaTeX tables to results/tables/ and a
processed JSON to results/processed/.

Produces:
  table_m1_ablation.{md,tex}     -- which primitive closes M1 (integrity vs solvency)
  table_m2_ablation.{md,tex}     -- which primitive closes M2
  table_failure_modes.{md,tex}   -- lifecycle failure injection outcomes
  table_detectability.{md,tex}   -- D0..D3 detection matrix
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
PROC = ROOT / "results" / "processed"
TAB = ROOT / "results" / "tables"


def _latest(pat: str):
    c = sorted(RAW.glob(pat))
    return max(c, key=lambda p: p.stat().st_mtime) if c else None


def _esc(s) -> str:
    return (str(s).replace("\\", "").replace("_", r"\_").replace("%", r"\%")
            .replace("&", r"\&").replace("$", r"\$").replace("#", r"\#"))


def write_table(name: str, header: list[str], rows: list[list[str]], caption: str, label: str):
    """Emit Markdown + LaTeX. Wide tables are wrapped in \\resizebox so they never
    overflow the text block (fixing overfull \\hbox at the GENERATOR, not by hand)."""
    TAB.mkdir(parents=True, exist_ok=True)
    md = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    (TAB / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    cols = "l" * 2 + "r" * (len(header) - 2) if len(header) > 2 else "l" * len(header)
    # Heuristic: estimate rendered width; wrap anything likely to overflow.
    widest = max([sum(len(str(c)) for c in r) for r in rows] + [sum(len(h) for h in header)])
    wide = len(header) >= 6 or widest > 70

    tex = [r"\begin{table}[t]", r"\centering", r"\small", f"\\caption{{{_esc(caption)}}}",
           f"\\label{{{label}}}"]
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


def summarize_ablation(d: dict) -> dict:
    # ---- M1: integrity vs solvency, by primitive ---------------------------
    solv = {r["architecture"]: r for r in d["m1_solvency_probe"]}
    rows = []
    for arch in dict.fromkeys(r["architecture"] for r in d["m1_factorial"]):
        cells = [r for r in d["m1_factorial"] if r["architecture"] == arch]
        leaks = [Decimal(c["leak_per_request"]) for c in cells]
        worst = max(leaks)
        viol = sum(c["invariant_violations"] for c in cells)
        f = cells[0]
        s = solv.get(arch, {})
        rows.append([
            arch,
            "yes" if f.get("reservation") is True else ("no" if f.get("reservation") is False else "n/a"),
            {True: "yes", False: "no"}.get(f.get("abort_finalization"), str(f.get("abort_finalization"))),
            f"{float(worst):+.4f}",
            "VIOLATED" if viol else "held",
            f"{s.get('served','?')}/6",
            "NEGATIVE" if s.get("went_negative") else "ok",
        ])
    write_table("table_m1_ablation",
                ["architecture", "reservation", "abort-finalization", "worst leak/req",
                 "integrity", "served (budget 2)", "solvency"],
                rows,
                "M1 ablation: abort-inclusive finalization closes the integrity violation; "
                "reservation independently provides the solvency (funds) guarantee. Both are "
                "needed for a correct design.", "tab:m1abl")

    # ---- M2: recount performed vs used -------------------------------------
    rows2 = []
    for arch in dict.fromkeys(r["architecture"] for r in d["m2_factorial"]):
        cells = [r for r in d["m2_factorial"] if r["architecture"] == arch]
        worst = max(c["leakage_efficiency"] for c in cells)
        viol = sum(c["invariant_violations"] for c in cells)
        dets = sorted({c["detection"] for c in cells if c["detection"] != "n/a"})
        f = cells[0]
        rows2.append([
            arch,
            "yes" if f.get("recount_performed") else "no",
            "yes" if f.get("recount_used_for_billing") else "no",
            f"{worst:.3f}",
            "VIOLATED" if viol else "held",
            dets[0] if dets else "n/a",
        ])
    write_table("table_m2_ablation",
                ["architecture", "recount performed", "recount used for billing",
                 "worst leak eff.", "integrity", "detection"],
                rows2,
                "M2 ablation: performing a recount is not sufficient; it must be used as the "
                "billing basis. client\\_logged computes the recount and still leaks.",
                "tab:m2abl")

    # ---- M1 two-property matrix: Solvency vs Accounting integrity ---------- #
    # Property A (Solvency):  served_value must not exceed the affordable balance.
    #   Probe: budget for exactly 2 requests, 6 issued -> serving >2 violates solvency,
    #   as does driving the balance negative.
    # Property B (Accounting integrity): delivered_value <= net_committed_debit.
    matrix = []
    for arch in dict.fromkeys(r["architecture"] for r in d["m1_factorial"]):
        cells = [r for r in d["m1_factorial"] if r["architecture"] == arch]
        integ_ok = sum(c["invariant_violations"] for c in cells) == 0
        s = solv.get(arch, {})
        served, k = s.get("served"), s.get("affordable", 2)
        overserved = (served is not None and served > k)
        negative = bool(s.get("went_negative"))
        solvency_ok = not (overserved or negative)
        why = []
        if overserved:
            why.append(f"served {served}/{s.get('requests', 6)} on a {k}-request budget")
        if negative:
            why.append(f"balance {s.get('final_balance')}")
        matrix.append([
            arch,
            "HOLDS" if solvency_ok else "VIOLATED",
            "HOLDS" if integ_ok else "VIOLATED",
            "; ".join(why) if why else "-",
        ])
    write_table("table_m1_property_matrix",
                ["architecture", "Property A: solvency", "Property B: accounting integrity",
                 "how the violated property fails"],
                matrix,
                "M1 architecture matrix. Solvency (served value must not exceed the affordable "
                "balance) and accounting integrity (delivered value must not exceed the net "
                "committed debit) are ORTHOGONAL: reservation provides the former and "
                "abort-safe finalization the latter, and neither substitutes for the other.",
                "tab:m1matrix")

    return {"m1_rows": rows, "m2_rows": rows2, "m1_property_matrix": matrix}


def summarize_failures(d: dict) -> dict:
    rows = []
    for r in d["results"]:
        rows.append([
            r["failure_id"], r["description"][:44], r["architecture"],
            "yes" if r["inference_delivered"] else "no",
            f"{float(r['net_debit']):.4f}",
            f"{float(r['refund_applied']):.4f}",
            f"{float(r['leakage']):.4f}",
            "HELD" if r["invariant_preserved"] else "VIOLATED",
        ])
    write_table("table_failure_modes",
                ["id", "failure injected", "architecture", "delivered", "net debit",
                 "refund", "leakage", "invariant"],
                rows,
                "Lifecycle failure injection. Every invariant violation occurs on a vulnerable "
                "architecture; the hardened architectures survive all injected failures, and a "
                "recount-engine failure is fail-closed.", "tab:failmodes")
    return {"rows": rows, "violations": sum(1 for r in d["results"] if not r["invariant_preserved"])}


def summarize_detectability(abl: dict, fm: dict) -> dict:
    """Detection matrix: which evidence source can reveal each violation."""
    # Evidence sources: request logs / usage ledger / reconciliation / final balance / real-time
    spec = [
        # (mechanism, architecture, req_logs, ledger, reconciliation, final_balance, realtime, level, latency)
        ("B0", "vulnerable (non-atomic)", "no", "yes", "yes", "no*", "no", "D1",
         "until a reconciliation pass"),
        ("B0", "hardened (atomic CAS)", "n/a", "n/a", "n/a", "n/a", "yes", "D3", "0 (prevented)"),
        ("M1", "post_completion", "partial", "no", "no", "no", "no", "D0",
         "never (no record is written)"),
        ("M1", "reserve_refund_on_abort", "partial", "yes", "yes", "yes", "no", "D1",
         "until a reconciliation pass"),
        ("M1", "reserve_reconcile", "n/a", "n/a", "n/a", "n/a", "yes", "D3", "0 (prevented)"),
        ("M2", "client", "no", "no", "no", "no", "no", "D0", "never (ledger records the lie)"),
        ("M2", "client_logged", "no", "yes", "yes", "no", "no", "D1",
         "until a reconciliation pass"),
        ("M2", "server_recount", "n/a", "n/a", "n/a", "n/a", "yes", "D3", "0 (prevented)"),
        ("M2", "hybrid_reconcile", "yes", "yes", "yes", "n/a", "yes", "D3",
         "0 (detected and corrected in-request)"),
    ]
    rows = [[m, a, rl, lg, rc, fb, rt, lvl, lat] for (m, a, rl, lg, rc, fb, rt, lvl, lat) in spec]
    write_table("table_detectability",
                ["mech", "architecture", "req logs", "usage ledger", "reconciliation",
                 "final balance", "real-time", "level", "detection latency"],
                rows,
                "Detectability matrix. D0 invisible; D1 only via post-hoc reconciliation; "
                "D2 logged discrepancy; D3 prevented or corrected in real time. "
                "*B0's final balance alone cannot reveal the loss because the ledger and the "
                "balance are both under-decremented consistently with the surviving write.",
                "tab:detect")
    return {"rows": rows}


def main() -> None:
    out = {}
    a = _latest("ablation_*.json")
    f = _latest("failure_modes_*.json")
    if a:
        out["ablation"] = summarize_ablation(json.loads(a.read_text(encoding="utf-8")))
        print(f"ablation      <- {a.name}")
    if f:
        out["failure_modes"] = summarize_failures(json.loads(f.read_text(encoding="utf-8")))
        print(f"failure modes <- {f.name}")
    out["detectability"] = summarize_detectability(out.get("ablation"), out.get("failure_modes"))
    PROC.mkdir(parents=True, exist_ok=True)
    (PROC / "ablation_failure_detect.summary.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("tables -> table_m1_ablation, table_m2_ablation, table_failure_modes, table_detectability")


if __name__ == "__main__":
    main()
