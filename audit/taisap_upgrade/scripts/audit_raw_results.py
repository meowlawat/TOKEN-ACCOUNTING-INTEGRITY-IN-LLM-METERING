from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path


D = Decimal
FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")
SAFE_AUTHORITIES = {"upstream", "server_recount", "hybrid_reconcile"}
PRICERS = {
    "category_additive": {"input_tokens": D("1"), "output_tokens": D("3"), "cached_input_tokens": D("0.1"), "reasoning_tokens": D("3")},
    "mixed_1_0.1_5_2": {"input_tokens": D("1"), "output_tokens": D("5"), "cached_input_tokens": D("0.1"), "reasoning_tokens": D("2")},
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def records(data: dict) -> list[dict]:
    return [record for trial in data["trials"] for record in trial.get("records", [])]


def cost(usage: dict, basis: str) -> Decimal:
    if basis == "flat_total":
        total = usage.get("declared_total")
        if total is None:
            total = usage.get("total", sum(int(usage.get(field, 0)) for field in FIELDS))
        return D(str(total))
    return sum(D(str(usage.get(field, 0))) * PRICERS[basis][field] for field in FIELDS)


def efficiency(trial: dict) -> float:
    true_cost = sum(D(record["authoritative_cost"]) for record in trial["records"])
    leak = sum(D(record["leak"]) for record in trial["records"])
    return float(leak / true_cost) if true_cost else 0.0


def find_trial(data: dict, architecture: str, manipulation: str, **filters) -> dict:
    matches = [trial for trial in data["trials"]
               if trial.get("mechanism") == "m2"
               and trial.get("architecture") == architecture
               and trial.get("manipulation") == manipulation
               and all(trial.get(key) == value for key, value in filters.items())]
    if len(matches) != 1:
        raise ValueError(f"expected one {architecture}/{manipulation}/{filters} trial, found {len(matches)}")
    return matches[0]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "m1": repo / "results/raw/m1_20260816T123351Z.json",
        "m2": repo / "results/raw/m2_20260816T123522Z.json",
        "m2_tiers": repo / "results/raw/m2_tiers.json",
        "real": repo / "results/raw/real_stack_20260818T152742Z.json",
        "b0": repo / "results/class6_20260816T123031Z.json",
        "overhead": repo / "results/raw/real_model_recount_20260816T132240Z.json",
        "failures": repo / "results/raw/failure_modes_20260816T130439Z.json",
    }
    data = {name: load(path) for name, path in paths.items()}
    m1_records, m2_records = records(data["m1"]), records(data["m2"])
    audited_records = m1_records + m2_records
    mismatches = missing = 0
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    required = {"request_id", "authoritative_cost", "committed_debit", "refund", "net_debit", "leak"}
    for dataset, rows in (("m1", m1_records), ("m2", m2_records)):
        for row in rows:
            missing += len(required - set(row))
            if not required <= set(row):
                continue
            identity = (dataset, row["request_id"])
            duplicates += int(identity in seen); seen.add(identity)
            net = D(row["committed_debit"]) - D(row["refund"])
            leak = D(row["authoritative_cost"]) - net
            if net != D(row["net_debit"]) or leak != D(row["leak"]):
                mismatches += 1

    repricing_records = [record for source in (data["m2_tiers"], data["real"])
                         for trial in source["trials"] if trial.get("mechanism") == "m2"
                         for record in trial.get("records", [])]
    positive_safe = dependency_violations = 0
    repriced_cells = 0
    for row in repricing_records:
        extra = row.get("extra") or {}
        true_usage, declared = extra.get("true"), extra.get("declared")
        if not true_usage or not declared:
            missing += 1
            continue
        billed_usage = true_usage if row["architecture"] in SAFE_AUTHORITIES else declared
        for basis in (*PRICERS, "flat_total"):
            true_cost, billed_cost = cost(true_usage, basis), cost(billed_usage, basis)
            leak = true_cost - billed_cost
            repriced_cells += 1
            positive_safe += int(row["architecture"] in SAFE_AUTHORITIES and leak > 0)
            if leak > 0:
                if basis == "flat_total":
                    dependency_violations += int(cost(true_usage, basis) == cost(declared, basis))
                else:
                    changed_read_field = any(
                        PRICERS[basis][field] != 0 and int(true_usage.get(field, 0)) != int(declared.get(field, 0))
                        for field in FIELDS
                    )
                    dependency_violations += int(not changed_read_field)

    controlled = find_trial(data["m2"], "client", "under_report_output_90", price_tier="medium", concurrency=1)
    real = find_trial(data["real"], "client", "under_report_output_90")
    overhead_fractions = [float(run["recount_frac_of_e2e"]) for run in data["overhead"]["runs"]
                          if run["posture"] != "none"]
    f4 = [row for row in data["failures"]["results"] if row["failure_id"] == "F4"]
    fail_closed = (len(f4) == 1 and f4[0].get("http_status") == 400
                   and not f4[0]["inference_delivered"] and D(f4[0]["net_debit"]) == 0)
    result = {
        "inputs": {name: {"path": path.relative_to(repo).as_posix(), "sha256": sha256(path)} for name, path in paths.items()},
        "m1_records": len(m1_records), "m2_records": len(m2_records),
        "b0_trials": len(data["b0"]["trials"]),
        "arithmetic_mismatches": mismatches, "duplicate_request_ids": duplicates,
        "missing_required_fields": missing,
        "controlled_m2_output90_efficiency": efficiency(controlled),
        "real_stack_m2_output90_efficiency": efficiency(real),
        "maximum_real_recount_fraction": max(overhead_fractions),
        "recount_failure_fail_closed": fail_closed,
        "repricing": {
            "raw_records_audited": len(repricing_records), "repriced_record_basis_cells": repriced_cells,
            "server_authoritative_positive_leak_cells": positive_safe,
            "field_dependency_violations": dependency_violations,
        },
    }
    (output / "independent_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 1 if mismatches or duplicates or missing or positive_safe or dependency_violations or not fail_closed else 0


if __name__ == "__main__":
    raise SystemExit(main())
