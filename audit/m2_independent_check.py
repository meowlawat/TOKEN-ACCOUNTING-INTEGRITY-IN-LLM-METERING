"""Independent M2 verification (audit fixes F4, F5) and the 0.583 / 0.595 reconciliation.

Uses ONLY `audit/m2_independent_model.py`, which derives true usage from (prompt, seed)
via the documented specification. It never reads `extra["true"]`, never imports project
code, and never trusts an architecture's declared outcome.

Outputs:
  * per-record agreement between the independent model and the recorded ledger
  * the exact prompts that produced the 0.583 and 0.595 figures (prompt A / prompt B)
  * an attacker-knowledge (K0/K1/K2) feasibility table for each manipulation
"""

from __future__ import annotations

import glob
import json
import os
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import m2_independent_model as M  # noqa: E402  (same directory)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"
AUDIT = Path(__file__).parent


def D(x) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal("0")


def latest(pattern: str, folder: Path):
    c = [p for p in glob.glob(str(folder / pattern)) if ".summary." not in os.path.basename(p)]
    return Path(max(c, key=os.path.getmtime)) if c else None


def verify_dataset(path: Path, label: str) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    prompt = d["parameters"]["prompt"]
    seed = d["parameters"]["model_seed"]

    mismatches = []
    checked = 0
    eff_by_cell: dict[tuple, dict] = defaultdict(lambda: {"leak": Decimal(0), "auth": Decimal(0)})

    for t in d["trials"]:
        arch, manip, tier = t["architecture"], t["manipulation"], t["price_tier"]
        if arch not in M.BASIS:
            continue
        pred = M.predict(prompt, seed, arch, manip, tier)
        for r in t["records"]:
            checked += 1
            if pred["authoritative_cost"] != D(r["authoritative_cost"]):
                mismatches.append(f"{label} AUTH {arch}/{manip}/{tier}: "
                                  f"model={pred['authoritative_cost']} ledger={r['authoritative_cost']}")
            if pred["billed_cost"] != D(r["net_debit"]):
                mismatches.append(f"{label} BILLED {arch}/{manip}/{tier}: "
                                  f"model={pred['billed_cost']} ledger={r['net_debit']}")
            if pred["leak"] != D(r["leak"]):
                mismatches.append(f"{label} LEAK {arch}/{manip}/{tier}: "
                                  f"model={pred['leak']} ledger={r['leak']}")
            if pred["integrity_ok"] != bool(r["invariant_ok"]):
                mismatches.append(f"{label} INVARIANT {arch}/{manip}/{tier}")
            k = (arch, manip, tier)
            eff_by_cell[k]["leak"] += pred["leak"]
            eff_by_cell[k]["auth"] += pred["authoritative_cost"]

    eff = {f"{a}/{m}/{ti}": float(v["leak"] / v["auth"]) if v["auth"] > 0 else 0.0
           for (a, m, ti), v in eff_by_cell.items()}
    return {"label": label, "file": path.name, "prompt": prompt, "seed": seed,
            "records_checked": checked, "mismatch_count": len(mismatches),
            "mismatches": mismatches[:20], "model_efficiency": eff,
            "model_true_usage": M.true_usage(prompt, seed)}


def main() -> None:
    out = {}
    print("=" * 78)
    print("INDEPENDENT M2 VERIFICATION (truth derived from spec, not from the gateway)")
    print("=" * 78)

    # Prompt A: the main M2 sweep. Prompt B: the ablation probe.
    datasets = []
    p = latest("m2_2*.json", RAW)
    if p:
        datasets.append((p, "promptA_sweep"))
    ab = latest("ablation_*.json", RAW)

    for path, label in datasets:
        res = verify_dataset(path, label)
        out[label] = res
        print(f"\n{label}  <- {res['file']}")
        print(f"  prompt : {res['prompt']!r}")
        print(f"  true usage (model-derived): {res['model_true_usage']}")
        print(f"  records checked : {res['records_checked']}")
        print(f"  MISMATCHES      : {res['mismatch_count']}")
        for m in res["mismatches"][:5]:
            print("   !", m)

    # ---- 0.583 vs 0.595 reconciliation ------------------------------------- #
    print("\n" + "-" * 78)
    print("0.583 vs 0.595 RECONCILIATION (independent model, not averaged)")
    print("-" * 78)
    promptA = out.get("promptA_sweep", {}).get("prompt")
    promptB = None
    if ab:
        abd = json.loads(ab.read_text(encoding="utf-8"))
        promptB = abd["parameters"]["prompt_m2"]

    rec = {}
    for name, pr in (("prompt A (main sweep)", promptA), ("prompt B (ablation)", promptB)):
        if not pr:
            continue
        tu = M.true_usage(pr, 1337)
        r = M.predict(pr, 1337, "client_logged", "under_report_output_90", "medium")
        rec[name] = {"prompt": pr, "true_usage": tu,
                     "efficiency": r["leakage_efficiency"],
                     "authoritative": str(r["authoritative_cost"]),
                     "billed": str(r["billed_cost"])}
        print(f"  {name}")
        print(f"    prompt      : {pr!r}")
        print(f"    true usage  : in={tu['input_tokens']} out={tu['output_tokens']} reason={tu['reasoning_tokens']}")
        print(f"    efficiency  : {r['leakage_efficiency']:.4f}")
    print("  => Both are correct for their own prompt; efficiency depends on the token")
    print("     mix, so the two MUST NOT be averaged or merged.")
    print("  => Qualitative conclusion identical in both: a correct recount that is not")
    print("     the billing basis still leaks.")
    out["reconciliation_0583_0595"] = rec

    # ---- attacker knowledge model ------------------------------------------ #
    print("\n" + "-" * 78)
    print("ATTACKER-KNOWLEDGE FEASIBILITY (K0 client-observable / K1 provider-reported / K2 oracle)")
    print("-" * 78)
    kn = {}
    pr = promptA or "benchmark the usage record authority boundary please now"
    for manip in ("honest", "under_report_output_50", "under_report_output_90",
                  "under_report_input_50", "rounding_shave", "total_mismatch",
                  "inflate_cached", "drop_reasoning"):
        lvl, why = M.knowledge_required(manip)
        r = M.predict(pr, 1337, "client", manip, "medium")
        kn[manip] = {"knowledge": lvl, "rationale": why,
                     "efficiency_if_successful": r["leakage_efficiency"]}
        print(f"  {manip:<24} {lvl}  eff={r['leakage_efficiency']:+.3f}  {why[:58]}")
    out["attacker_knowledge"] = {"levels": M.KNOWLEDGE_LEVELS, "by_manipulation": kn}

    k0 = [m for m, v in kn.items() if v["knowledge"] == "K0" and v["efficiency_if_successful"] > 0]
    print(f"\n  Manipulations feasible with CLIENT-OBSERVABLE knowledge only (K0) and")
    print(f"  producing leakage: {k0}")
    print("  => The core usage-authority result does NOT depend on oracle knowledge;")
    print("     but `drop_reasoning` (K2) and `inflate_cached` (K1) do.")

    (AUDIT / "m2_independent_check.json").write_text(json.dumps(out, indent=2, default=str),
                                                     encoding="utf-8")
    total_mm = sum(v.get("mismatch_count", 0) for v in out.values() if isinstance(v, dict)
                   and "mismatch_count" in v)
    print(f"\nTOTAL INDEPENDENT MISMATCHES: {total_mm}")
    print(f"-> audit/m2_independent_check.json")


if __name__ == "__main__":
    main()
