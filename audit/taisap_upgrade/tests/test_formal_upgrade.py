from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
RUNS = REPO / "audit" / "taisap_upgrade" / "formal_runs"


def test_primary_rerun_captures_full_expected_matrix() -> None:
    data = json.loads((RUNS / "primary_model_check_results.json").read_text(encoding="utf-8"))
    assert data["configurations"] == 10
    assert data["checks"] == 40
    assert data["disagreements"] == 0
    assert sum(row.get("distinct_states", 0) for row in data["results"]) == 27526


def test_preregistered_async_sweep_has_no_missing_or_relabelled_cells() -> None:
    data = json.loads((RUNS / "async_extension_results.json").read_text(encoding="utf-8"))
    assert data["configurations"] == 12
    assert data["checks"] == 36
    assert data["errors"] == 0
    assert data["unexpected"] == 0
    logs = list((RUNS / "logs").glob("*.txt"))
    assert len(logs) == 6
    assert all(path.name.startswith("vulnerable_") and "__Solvency" in path.name for path in logs)
    rows = {(row["mode"], row["n"], row["k"], row["invariant"]): row["observed"] for row in data["results"]}
    for n, k in ((3, 1), (4, 1), (4, 2), (5, 2), (6, 2), (6, 3)):
        assert rows[("atomic", n, k, "Solvency")] == "HOLDS"
        assert rows[("vulnerable", n, k, "Solvency")] == "VIOLATED"
        for invariant in ("AccountingIntegrity", "LedgerConservation"):
            assert rows[("atomic", n, k, invariant)] == "HOLDS"
            assert rows[("vulnerable", n, k, invariant)] == "HOLDS"
