"""Build the claim-to-evidence matrix (Phase R).

Every major paper claim is declared here with its evidence pointer, and the script
VERIFIES that the cited artifact exists (and, where the value is machine-readable,
that the cited number still matches the data). Claims that cannot be verified are
emitted as UNSUPPORTED so they can be deleted from the paper.

Writes paper/claim_evidence_matrix.csv and .md
"""

from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
RESULTS = ROOT / "results"

# kind: DIRECTLY MEASURED | INFERRED | LITERATURE-SUPPORTED | HYPOTHESIS | UNSUPPORTED

DEFAULT_CONFIDENCE = {
    "DIRECTLY MEASURED": "high",
    "INFERRED": "medium",
    "LITERATURE-SUPPORTED": "medium (bounded negative)",
    "HYPOTHESIS": "n/a (scope statement)",
    "UNSUPPORTED": "none",
}
DEFAULT_LIMITATION = {
    "DIRECTLY MEASURED": "single-host testbed; mock generator unless stated",
    "INFERRED": "derived from measurements, not directly observed",
    "LITERATURE-SUPPORTED": "targeted search; does not establish non-existence",
    "HYPOTHESIS": "explicitly not claimed as a result",
    "UNSUPPORTED": "must be deleted",
}
CLAIMS = [
    # ---- taxonomy / model -------------------------------------------------
    dict(id="C01", section="Taxonomy",
         claim="Client-side under-payment spans three architectural dimensions: state "
               "synchronization (B0), commitment timing (M1), usage authority (M2).",
         kind="INFERRED", metric="structural argument + per-mechanism measurements",
         source="paper/accounting_state_model.md",
         result_file="paper/accounting_state_model.md"),
    dict(id="C02", section="Taxonomy",
         claim="Each mechanism localizes to a distinct state transition (AUTHORIZED->RESERVED; "
               "STREAMING->ABORTED; ACCOUNTED->RECONCILED).",
         kind="INFERRED", metric="state-machine derivation",
         source="paper/accounting_state_model.md", result_file="paper/accounting_state_model.tex"),
    # ---- B0 ---------------------------------------------------------------
    dict(id="C03", section="Results/B0",
         claim="B0 leakage is created by concurrency: zero at c=1, linear thereafter "
               "(slope 0.099/request, R^2=1.0000, p=1.9e-50).",
         kind="DIRECTLY MEASURED", metric="mean $-leak vs concurrency, OLS",
         source="experiments/statistical_analysis.py", result_file="results/tables/stats_output.txt",
         verify=("stats", "slope=0.099000/request")),
    dict(id="C04", section="Results/B0",
         claim="Hardened atomic compare-and-decrement leaks $0 at every tested concurrency.",
         kind="DIRECTLY MEASURED", metric="mean $-leak, hardened posture",
         source="experiments/run_class6.py", result_file="results/tables/stats_output.txt"),
    # ---- M1 ---------------------------------------------------------------
    dict(id="C05", section="Results/M1",
         claim="M1 leakage rises monotonically with abort position and collapses to zero at "
               "completion.",
         kind="DIRECTLY MEASURED", metric="mean leak per request vs abort_bin",
         source="experiments/run_m1.py", result_file="results/tables/table_m1_results.md"),
    dict(id="C06", section="Results/M1",
         claim="M1 per-request leakage is invariant to concurrency (identical to 4 dp across "
               "c=1..100 with request volume held constant).",
         kind="DIRECTLY MEASURED", metric="leak_per_request by concurrency",
         source="experiments/run_m1.py", result_file="results/tables/table_m1_concurrency.md"),
    dict(id="C07", section="Results/M1",
         claim="Honest clients (no abort) leak zero on every architecture.",
         kind="DIRECTLY MEASURED", metric="leak_per_request, client_type=honest",
         source="experiments/run_m1.py", result_file="results/processed"),
    # ---- M2 ---------------------------------------------------------------
    dict(id="C08", section="Results/M2",
         claim="Client-authoritative billing leaks; server-authoritative billing leaks zero "
               "for every manipulation tested.",
         kind="DIRECTLY MEASURED", metric="leakage efficiency by architecture",
         source="experiments/run_m2.py", result_file="results/tables/table_m2_results.md"),
    dict(id="C09", section="Results/M2",
         claim="Which manipulation succeeds depends on the pricing basis: total/subtotal "
               "mismatch is inert under category pricing (0.000) but the strongest attack "
               "under flat-total pricing (0.741).",
         kind="DIRECTLY MEASURED", metric="leakage efficiency by (basis, manipulation)",
         source="experiments/economic_analysis.py", result_file="results/tables/table_m2_formal.md",
         verify=("file_contains", ("results/tables/table_m2_formal.md", "0.741"))),
    dict(id="C10", section="Results/M2",
         claim="M2 leakage efficiency is invariant to concurrency.",
         kind="DIRECTLY MEASURED", metric="leakage efficiency by concurrency",
         source="experiments/run_m2.py", result_file="results/tables/table_m2_concurrency.md"),
    # ---- ablation ---------------------------------------------------------
    dict(id="C11", section="Ablation",
         claim="Abort-inclusive finalization closes M1's integrity violation with or without a "
               "reservation.",
         kind="DIRECTLY MEASURED", metric="worst leak/req by (reservation, finalization)",
         source="experiments/run_ablation.py", result_file="results/tables/table_m1_ablation.md"),
    dict(id="C12", section="Ablation",
         claim="Reservation independently provides solvency: without it the balance goes "
               "negative under a constrained budget.",
         kind="DIRECTLY MEASURED", metric="final_balance in the solvency probe",
         source="experiments/run_ablation.py", result_file="results/tables/table_m1_ablation.md",
         verify=("file_contains", ("results/tables/table_m1_ablation.md", "NEGATIVE"))),
    dict(id="C13", section="Ablation",
         claim="Performing a recount is insufficient: client_logged computes an authoritative "
               "recount and still leaks (efficiency 0.595) because billing ignores it.",
         kind="DIRECTLY MEASURED", metric="leakage efficiency, client_logged",
         source="experiments/run_ablation.py", result_file="results/tables/table_m2_ablation.md",
         verify=("file_contains", ("results/tables/table_m2_ablation.md", "0.595"))),
    # ---- tokenizer / gateway / real model ---------------------------------
    dict(id="C14", section="Cost/RQ4",
         claim="Tokenizer recount cost is linear in input length (log-log slope 0.999-1.14, "
               "R^2>=0.998).",
         kind="DIRECTLY MEASURED", metric="log-log regression of p50 latency vs tokens",
         source="experiments/statistical_analysis.py", result_file="results/tables/stats_output.txt"),
    dict(id="C15", section="Cost/RQ4",
         claim="Tokenizer engine choice changes recount cost by ~2.9-3.6x at 16384 tokens.",
         kind="DIRECTLY MEASURED", metric="p50 latency ratio vs tiktoken/cl100k_base",
         source="benchmarks/tokenizer_overhead.py", result_file="results/tables/tokenizer_overhead.md"),
    dict(id="C16", section="Cost/RQ4",
         claim="With a mock (zero-cost) generator, gateway recount costs up to 95% of throughput "
               "at 16384 tokens; tokenization time explains it (Spearman rho=-0.868, p=1.3e-5).",
         kind="DIRECTLY MEASURED", metric="throughput ratio vs no-recount; Spearman",
         source="benchmarks/gateway_recount_overhead.py", result_file="results/tables/stats_output.txt"),
    dict(id="C17", section="Cost/RQ4",
         claim="With real local inference, the recount is 0.012-0.016% of end-to-end time at "
               "every context size.",
         kind="DIRECTLY MEASURED", metric="recount_frac_of_e2e with bootstrap CI",
         source="benchmarks/real_model_recount.py", result_file="results/tables/stats_output.txt"),
    dict(id="C18", section="Cost/RQ4",
         claim="The apparent expense of recount under the mock gateway is an artifact of the "
               "generator costing nothing.",
         kind="INFERRED", metric="comparison of mock-gateway vs real-model ratios",
         source="paper/post_experiment_findings.md", result_file="results/tables/stats_output.txt"),
    # ---- integrity / validation -------------------------------------------
    dict(id="C19", section="Methodology",
         claim="Integrity gates fail closed: six corruption types are each detected for both M1 "
               "and M2 (12/12).",
         kind="DIRECTLY MEASURED", metric="fault-injection detection rate",
         source="experiments/metamorphic_checks.py",
         result_file="results/processed/metamorphic_report.json"),
    dict(id="C20", section="Methodology",
         claim="An independently coded checker agrees with the gateway on all cross-validated "
               "cells (42 M2, 16 M1, 2 B0).",
         kind="DIRECTLY MEASURED", metric="verdict agreement",
         source="experiments/run_cross_validation.py",
         result_file="results/raw", verify=("cross_val", None)),
    dict(id="C21", section="Methodology",
         claim="Hardened architectures survive nine injected lifecycle failures; recount-engine "
               "failure is fail-closed.",
         kind="DIRECTLY MEASURED", metric="invariant_preserved per failure mode",
         source="experiments/run_failure_modes.py", result_file="results/tables/table_failure_modes.md"),
    # ---- economics --------------------------------------------------------
    dict(id="C22", section="Economics",
         claim="Leakage efficiency is invariant under uniform price scaling (low->medium x10) "
               "and shifts by at most ~0.012 under a price-structure change.",
         kind="DIRECTLY MEASURED", metric="efficiency by price tier",
         source="experiments/economic_analysis.py",
         result_file="results/tables/table_economic_sensitivity.md"),
    dict(id="C23", section="Economics",
         claim="Flat-total pricing systematically overcharges honest clients (negative leak).",
         kind="DIRECTLY MEASURED", metric="signed leak, client_total + honest",
         source="experiments/economic_analysis.py",
         result_file="results/tables/table_economic_sensitivity.md"),
    # ---- detectability ----------------------------------------------------
    dict(id="C24", section="Detectability",
         claim="Logging a server recount moves an M2 leak from D0 (invisible) to D1 "
               "(reconcilable) without preventing it.",
         kind="DIRECTLY MEASURED", metric="detection level by architecture",
         source="experiments/run_m2.py", result_file="results/tables/table_detectability.md"),
    # ---- literature -------------------------------------------------------
    dict(id="C25", section="Related work",
         claim="Prior LLM-billing security work covers provider over-charge, victim bill "
               "inflation, and intermediary provenance; not client under-payment.",
         kind="LITERATURE-SUPPORTED", metric="targeted corpus review (bounded negative)",
         source="paper/novelty_reattack.md", result_file="paper/phase1_sources.json"),
    dict(id="C26", section="Related work",
         claim="M1 and M2 are type-B systematization contributions, not novel primitives; "
               "B0 is a known baseline.",
         kind="LITERATURE-SUPPORTED", metric="novelty assessment",
         source="paper/novelty_matrix.md", result_file="paper/novelty_matrix.csv"),
    # ---- cross-architecture generality (Phases 1-3) ------------------------
    dict(id="C28", section="Results/generality",
         claim="Accounting outcomes match the single-worker control across a 4-worker and a "
               "2-instance topology: 96 cells compared, 0 mismatches.",
         kind="DIRECTLY MEASURED", metric="per-cell leak/efficiency vs control",
         source="experiments/run_topology.py + summarize_generality.py",
         result_file="results/tables/table_topology_generality.md",
         verify=("generality", "topology")),
    dict(id="C29", section="Results/generality",
         claim="Load demonstrably spread across workers/instances (per-request serving-process "
               "attribution), so topology equivalence is not an artifact of requests landing on "
               "one process.",
         kind="DIRECTLY MEASURED", metric="distinct serving processes per cell",
         source="app/m_routes.py worker attribution",
         result_file="results/processed/generality.summary.json"),
    dict(id="C30", section="Results/generality",
         claim="B0's hardened posture leaks $0 at every concurrency in every topology, including "
               "across two separate gateway containers.",
         kind="DIRECTLY MEASURED", metric="mean $-leak, hardened posture by topology",
         source="experiments/run_topology.py",
         result_file="results/processed/generality.summary.json"),
    dict(id="C31", section="Results/generality",
         claim="Outcomes are identical under a mutable-balance-row backend and an append-only "
               "ledger with a derived balance: 17/17 strongest cases byte-identical.",
         kind="DIRECTLY MEASURED", metric="leak, efficiency, violations, reconciliation",
         source="experiments/run_backend_comparison.py",
         result_file="results/tables/table_backend_generality.md",
         verify=("generality", "backend")),
    dict(id="C32", section="Results/generality",
         claim="A multi-worker deployment requires shared runtime posture and serialized schema "
               "creation; both defects were observed directly when building the topology.",
         kind="DIRECTLY MEASURED", metric="observed UniqueViolation on pg_class; per-process posture",
         source="app/main.py (advisory lock, Redis-backed posture)",
         result_file="results/raw/topology"),
    dict(id="C33", section="Defense sufficiency",
         claim="Stated conditions are sufficient WITHIN the accounting model; they are argued "
               "deductively, not machine-checked, and their necessity evidence is empirical.",
         kind="INFERRED", metric="model-level argument + ablation",
         source="paper/defense_sufficiency.md", result_file="paper/defense_sufficiency.md"),
    # ---- explicitly scoped non-claims -------------------------------------
    dict(id="C27", section="Threats",
         claim="Results do NOT generalize to commercial providers or production serving stacks.",
         kind="HYPOTHESIS", metric="n/a (scope statement)",
         source="paper/threats_to_validity.md", result_file="paper/threats_to_validity.md"),
]


def verify(c: dict) -> tuple[str, str]:
    """Return (status, note). status in {VERIFIED, MISSING ARTIFACT, VALUE MISMATCH}."""
    rf = ROOT / c["result_file"]
    if not rf.exists():
        return "MISSING ARTIFACT", f"{c['result_file']} not found"
    v = c.get("verify")
    if not v:
        return "VERIFIED", "artifact present"
    kind, arg = v
    if kind == "stats":
        txt = (RESULTS / "tables" / "stats_output.txt").read_text(encoding="utf-8")
        return ("VERIFIED", "value found in stats_output.txt") if arg in txt else \
               ("VALUE MISMATCH", f"'{arg}' not in stats_output.txt")
    if kind == "file_contains":
        path, needle = arg
        txt = (ROOT / path).read_text(encoding="utf-8")
        return ("VERIFIED", f"'{needle}' found") if needle in txt else \
               ("VALUE MISMATCH", f"'{needle}' not in {path}")
    if kind == "generality":
        gp = RESULTS / "processed" / "generality.summary.json"
        if not gp.exists():
            return "MISSING ARTIFACT", "generality.summary.json not found"
        g = json.loads(gp.read_text(encoding="utf-8"))
        if arg == "topology":
            return (("VERIFIED", f"{g['topology_cells_compared']} cells, "
                                 f"{len(g['topology_mismatches'])} mismatches")
                    if g["topology_all_consistent"] else
                    ("VALUE MISMATCH", f"{len(g['topology_mismatches'])} topology mismatches"))
        if arg == "backend":
            return (("VERIFIED", f"{g['backend_cases_compared']} cases identical")
                    if g["backend_identical"] else
                    ("VALUE MISMATCH", "backend outcomes differ"))
    if kind == "cross_val":
        files = sorted(glob.glob(str(RESULTS / "raw" / "cross_validation_*.json")))
        if not files:
            return "MISSING ARTIFACT", "no cross_validation_*.json"
        d = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
        s = d["summary"]
        return ("VERIFIED", f"all_agree={s['all_agree']} ({s['m2_cells']}/{s['m1_cells']}/{s['b0_cells']})") \
            if s["all_agree"] else ("VALUE MISMATCH", "implementations disagree")
    return "VERIFIED", ""


def main() -> None:
    rows = []
    for c in CLAIMS:
        status, note = verify(c)
        kind = "UNSUPPORTED" if status != "VERIFIED" else c["kind"]
        rows.append({
            "claim_id": c["id"], "section": c["section"], "claim": c["claim"],
            "classification": kind, "source": c["source"],
            "result_file": c["result_file"], "metric": c["metric"],
            "verification": status,
            "confidence": c.get("confidence", DEFAULT_CONFIDENCE.get(kind, "medium")),
            "limitation": c.get("limitation", DEFAULT_LIMITATION.get(kind, "")),
            "note": note,
        })

    cols = ["claim_id", "section", "claim", "classification", "source", "result_file",
            "metric", "verification", "confidence", "limitation", "note"]
    with (PAPER / "claim_evidence_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    md = ["# Claim-to-Evidence Matrix (Phase R)\n",
          "Every major paper claim, its classification, and the artifact that supports it.",
          "Classifications: **DIRECTLY MEASURED** / **INFERRED** / **LITERATURE-SUPPORTED** / "
          "**HYPOTHESIS** / **UNSUPPORTED**. Any row that fails artifact verification is "
          "reclassified UNSUPPORTED and must be deleted from the paper.\n",
          "| id | section | claim | class | evidence | metric | verified | confidence | limitation |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['claim_id']} | {r['section']} | {r['claim']} | **{r['classification']}** "
                  f"| `{r['result_file']}` | {r['metric']} | {r['verification']} "
                  f"| {r['confidence']} | {r['limitation']} |")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    md.append("\n## Totals\n")
    for k, v in sorted(counts.items()):
        md.append(f"- **{k}**: {v}")
    unsupported = [r for r in rows if r["classification"] == "UNSUPPORTED"]
    md.append(f"\n**UNSUPPORTED claims: {len(unsupported)}** "
              + ("(none — no deletions required)" if not unsupported else
                 "-- these MUST be removed from the paper:"))
    for r in unsupported:
        md.append(f"  - {r['claim_id']}: {r['note']}")
    (PAPER / "claim_evidence_matrix.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"{len(rows)} claims; " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if unsupported:
        print("UNSUPPORTED:")
        for r in unsupported:
            print("  ", r["claim_id"], r["note"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
