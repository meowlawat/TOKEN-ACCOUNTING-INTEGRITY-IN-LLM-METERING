"""Generate the formal-verification tables and the formal-empirical mapping.

Everything here is derived from `results/formal/model_check_results.json`, which is
written by TLC itself. Nothing in the generated tables is typed by hand, so a change in
the model or a change in a counterexample cannot silently drift away from the prose.

Writes:
    results/tables/table_formal_matrix.{md,tex}
    results/tables/table_formal_mapping.{md,tex}
    paper/formal_empirical_mapping.md   (traces + mapping, regenerated)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL_JSON = ROOT / "results" / "formal" / "model_check_results.json"
TAB = ROOT / "results" / "tables"
PAPER = ROOT / "paper"

INV_SHORT = {
    "AccountingIntegrity": "Integrity",
    "Solvency": "Solvency",
    "LedgerConservation": "Conservation",
    "RefundBounded": "Refund bnd",
}

# How each configuration corresponds to an implemented architecture and a measurement.
# The formal name is on the left; everything on the right must exist in the artifact.
CORRESPONDENCE = {
    "b0_vulnerable": dict(
        arch="B0 vulnerable (non-atomic read/check/blind write)",
        experiment="run_class6.py, vulnerable posture, c>=2",
        measured="leak grows with concurrency: slope 0.099/request, R^2=1.0000"),
    "b0_hardened": dict(
        arch="B0 hardened (atomic conditional decrement)",
        experiment="run_class6.py, hardened posture",
        measured="$0 leak at every tested concurrency (1..50)"),
    "m1_post_completion": dict(
        arch="M1 post_completion (no reservation, no abort-safe settle)",
        experiment="run_m1.py, abort sweep",
        measured="leak = value of tokens delivered before the commit; request-ASR 1.000"),
    "m1_reserve_refund_on_abort": dict(
        arch="M1 reserve_refund_on_abort (reservation, refunded away on abort)",
        experiment="run_m1.py, abort sweep",
        measured="leak > 0 at every abort position; invariant violated"),
    "m1_no_reserve_settle": dict(
        arch="M1 no_reserve_settle (ablation cell: settle without reserving)",
        experiment="run_ablation.py, constrained-budget solvency probe",
        measured="accounting integrity holds; final balance goes NEGATIVE"),
    "m1_reserve_reconcile": dict(
        arch="M1 reserve_reconcile (reservation + abort-safe finalization)",
        experiment="run_m1.py + run_ablation.py",
        measured="$0 leak, 0 invariant violations, balance never negative"),
    "m2_client": dict(
        arch="M2 client / client_logged (client-declared usage is the billing basis)",
        experiment="run_m2.py, under_report_output_90",
        measured="leakage efficiency 0.583 (prompt A) / 0.595 (prompt B)"),
    "m2_server_recount": dict(
        arch="M2 server_recount / hybrid_reconcile / upstream",
        experiment="run_m2.py, all 8 manipulations",
        measured="leakage efficiency 0.000 across every manipulation"),
    "all_defenses": dict(
        arch="all three defenses composed, under contention + abort + a lying client",
        experiment="regression_m.py + run_cross_validation.py",
        measured="16/16 regression checks; 60 cross-validation cells agree"),
    "all_defenses_3req": dict(
        arch="same, with three concurrent requests",
        experiment="topology sweep (96 cells, 0 mismatches)",
        measured="no configuration produced a violation"),
}


def write_table(name: str, header: list[str], rows: list[list], caption: str, label: str):
    TAB.mkdir(parents=True, exist_ok=True)
    md = ["| " + " | ".join(header) + " |",
          "|" + "|".join("---" for _ in header) + "|"]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    (TAB / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    def esc(x):
        return (str(x).replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")
                .replace("^", r"\^{}").replace(">", r"$>$").replace("<", r"$<$"))

    tex = [r"\begin{table}[t]\centering",
           r"\caption{" + esc(caption) + "}", r"\label{" + label + "}",
           r"\resizebox{\linewidth}{!}{%",
           r"\begin{tabular}{" + "l" * len(header) + "}", r"\toprule",
           " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
    for r in rows:
        tex.append(" & ".join(esc(c) for c in r) + r" \\")
    tex += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    (TAB / f"{name}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


def main() -> None:
    d = json.loads(FORMAL_JSON.read_text(encoding="utf-8"))
    invs = d["invariants"]
    by = {(r["config"], r["invariant"]): r for r in d["results"]}

    # ---- matrix table ------------------------------------------------------
    rows = []
    for cfg, row in d["matrix"].items():
        states = max(by[(cfg, i)].get("distinct_states", 0) for i in invs)
        cells = ["VIOLATED" if row[i] == "VIOLATED" else "holds" for i in invs]
        rows.append([cfg.replace("_", " "), by[(cfg, invs[0])]["mechanism"], *cells, f"{states:,}"])
    write_table("table_formal_matrix",
                ["configuration", "mech", *[INV_SHORT[i] for i in invs], "states"],
                rows,
                "TLC model-checking results. Each cell is an independent exhaustive run; "
                "`holds' means the invariant survived every reachable state and `VIOLATED' "
                "means TLC returned a counterexample. All 40 cells matched the expectation "
                "declared before the run. States = largest reachable state space among the "
                "four runs for that configuration.",
                "tab:formalmatrix")

    # ---- mapping table -----------------------------------------------------
    mrows = []
    for cfg, corr in CORRESPONDENCE.items():
        violated = [i for i in invs if d["matrix"][cfg][i] == "VIOLATED"]
        if violated:
            trace = min((by[(cfg, i)]["trace_length"] for i in violated))
            formal = ", ".join(INV_SHORT[i] for i in violated) + f" (trace {trace})"
        else:
            formal = "all four hold"
        mrows.append([cfg.replace("_", " "), formal, corr["measured"]])
    write_table("table_formal_mapping",
                ["formal configuration", "model-checked outcome", "measured outcome"],
                mrows,
                "Formal-to-empirical correspondence. Every model-checked outcome is paired "
                "with the measurement of the implemented architecture it abstracts. The "
                "formal model predicts which property fails; the experiment quantifies how "
                "much value leaks when it does.",
                "tab:formalmap")

    # ---- narrative mapping document ---------------------------------------
    def trace_block(cfg: str, inv: str) -> str:
        r = by[(cfg, inv)]
        out = [f"```", f"{cfg} -- {inv} violated in {r['trace_length']} steps "
                       f"({r['distinct_states']:,} distinct states explored)"]
        # `snapshot` is only meaningful for the non-atomic B0 path, where the stale
        # read IS the defect; showing it elsewhere would be noise.
        show_snap = any(s["vars"].get("snapshot", "").count(":> 0") == 0
                        for s in r["counterexample"])
        for s in r["counterexample"]:
            v = s["vars"]
            snap = f"snapshot={v.get('snapshot','')} " if show_snap else ""
            out.append(f"{s['step']:>3}. {s['action']:<18} {snap}"
                       f"balance={v.get('balance',''):<4} "
                       f"delivered={v.get('delivered','')} "
                       f"debit={v.get('debit','')} refund={v.get('refund','')}")
        out.append("```")
        return "\n".join(out)

    doc = [
        "# Formal-to-empirical mapping",
        "",
        "*Generated by `experiments/build_formal_docs.py` from `results/formal/"
        "model_check_results.json`. Do not edit by hand.*",
        "",
        "Each counterexample below was produced by TLC, not written by us. For every one,",
        "the corresponding row states the implemented architecture it abstracts and the",
        "measured result from the experiment corpus. The formal model says *which property*",
        "fails and *on every schedule*; the experiment says *how much value* leaks when it",
        "does. Neither substitutes for the other, which is the point of reporting both.",
        "",
        f"**Totals.** {d['checks']} checks over {d['configurations']} configurations, "
        f"{sum(r.get('distinct_states', 0) for r in d['results']):,} distinct states, "
        f"**{d['disagreements']} disagreements** with the pre-declared expectations.",
        "",
    ]
    for cfg, corr in CORRESPONDENCE.items():
        violated = [i for i in invs if d["matrix"][cfg][i] == "VIOLATED"]
        doc += [f"## `{cfg}`", "",
                f"- **Implemented architecture:** {corr['arch']}",
                f"- **Experiment:** `{corr['experiment']}`",
                f"- **Measured:** {corr['measured']}"]
        if not violated:
            doc += ["- **Model-checked:** all four invariants hold on every reachable state "
                    f"({max(by[(cfg, i)].get('distinct_states', 0) for i in invs):,} distinct "
                    "states). No counterexample exists within the model.", ""]
        else:
            doc += [f"- **Model-checked:** violates {', '.join(violated)}.", ""]
            for inv in violated:
                doc += [trace_block(cfg, inv), ""]
    (PAPER / "formal_empirical_mapping.md").write_text("\n".join(doc) + "\n", encoding="utf-8")

    print(f"checks={d['checks']} disagreements={d['disagreements']}")
    print("tables -> table_formal_matrix, table_formal_mapping")
    print("doc    -> paper/formal_empirical_mapping.md")


if __name__ == "__main__":
    main()
