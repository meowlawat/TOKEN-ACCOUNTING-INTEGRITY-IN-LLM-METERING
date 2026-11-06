from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "audit" / "taisap_upgrade" / "scripts" / "check_baseline_inventory.py"

REQUIRED_CLAIMS = {
    "C-INVARIANT",
    "C-B0",
    "C-M1",
    "C-M2",
    "C-ORTHOGONALITY",
    "C-TLC-PRIMARY",
    "C-TLC-ASYNC",
    "C-M2-58.3",
    "C-M2-69.0",
    "C-M1-SEQUENTIAL",
    "C-M1-TWO-MACHINE",
    "C-OVERHEAD-0.1",
    "C-OPENGATELLM-254347",
}

ALLOWED_STATUSES = {
    "REPRODUCED",
    "SUPPORTED_BY_EXISTING_DATA",
    "UNVERIFIED",
    "FAILED",
    "PROPOSED_ONLY",
    "HUMAN_APPROVAL_REQUIRED",
}


def run_inventory(output: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(REPO),
            "--output",
            str(output),
            "--branch-point",
            "95103f1faafa62d926a1350295551f91d57e0f2f",
        ],
        check=True,
        text=True,
        capture_output=True,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_inventory_generator_emits_required_claim_contract(tmp_path: Path) -> None:
    run_inventory(tmp_path)
    rows = read_csv(tmp_path / "claim_evidence.csv")

    assert {row["claim_id"] for row in rows} == REQUIRED_CLAIMS
    assert {row["status"] for row in rows} <= ALLOWED_STATUSES
    assert all(row["claim_text"].strip() for row in rows)
    assert all(row["evidence_paths"].strip() for row in rows)
    assert all(row["proposed_test"].strip() for row in rows)


def test_every_claim_evidence_path_resolves_to_a_file(tmp_path: Path) -> None:
    run_inventory(tmp_path)
    rows = read_csv(tmp_path / "claim_evidence.csv")

    for row in rows:
        for evidence_path in row["evidence_paths"].split(";"):
            path = REPO / evidence_path
            assert path.is_file(), f"{row['claim_id']} cites missing or non-file evidence: {evidence_path}"


def test_manifest_contains_valid_sha256_for_existing_files(tmp_path: Path) -> None:
    run_inventory(tmp_path)
    rows = read_csv(tmp_path / "baseline" / "sha256_manifest.csv")

    assert rows
    assert all(len(row["sha256"]) == 64 for row in rows)
    assert all(set(row["sha256"]) <= set("0123456789abcdef") for row in rows)
    assert all((REPO / row["path"]).is_file() for row in rows)


def test_inventory_preserves_historical_and_raw_evidence_paths(tmp_path: Path) -> None:
    run_inventory(tmp_path)
    inventory = (tmp_path / "baseline" / "repository_inventory.txt").read_text(
        encoding="utf-8"
    )

    assert "paper/main_fgcs.tex" in inventory
    assert "results/raw" in inventory
    assert "PRESERVATION_POLICY=read-only historical and raw evidence" in inventory


def test_environment_records_branch_point_and_dirty_state(tmp_path: Path) -> None:
    run_inventory(tmp_path)
    environment = (tmp_path / "baseline" / "environment.txt").read_text(
        encoding="utf-8"
    )

    assert "BRANCH_POINT=95103f1faafa62d926a1350295551f91d57e0f2f" in environment
    assert "CURRENT_BRANCH=research/taisap-scientific-upgrade-2026" in environment
    assert "WORKTREE_STATUS=" in environment
