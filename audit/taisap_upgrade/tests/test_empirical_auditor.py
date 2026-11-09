from __future__ import annotations

import json
import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
RESULT = REPO / "audit" / "taisap_upgrade" / "results" / "independent_audit.json"


def test_independent_auditor_reconciles_raw_records_and_headlines() -> None:
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    assert data["arithmetic_mismatches"] == 0
    assert data["duplicate_request_ids"] == 0
    assert data["m1_records"] == 2400
    assert data["m2_records"] == 4800
    assert data["b0_trials"] == 420
    assert round(data["controlled_m2_output90_efficiency"] * 100, 1) == 58.3
    assert round(data["real_stack_m2_output90_efficiency"] * 100, 1) == 69.0
    assert data["maximum_real_recount_fraction"] < 0.001


def test_preregistered_m2_repricing_and_fail_closed_checks() -> None:
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    assert data["repricing"]["server_authoritative_positive_leak_cells"] == 0
    assert data["repricing"]["field_dependency_violations"] == 0
    assert data["repricing"]["raw_records_audited"] > 0
    assert data["recount_failure_fail_closed"] is True
    assert data["missing_required_fields"] == 0


def test_figure_generator_allows_explicit_evidence_selection(tmp_path: Path) -> None:
    module_path = REPO / "experiments" / "figures.py"
    spec = importlib.util.spec_from_file_location("figures_under_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    older = tmp_path / "locked.summary.json"
    newer = tmp_path / "newer.summary.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")

    assert module._select(older, "*.summary.json", tmp_path) == older.resolve()


def test_table_generator_allows_explicit_evidence_selection(tmp_path: Path) -> None:
    module_path = REPO / "experiments" / "tables.py"
    spec = importlib.util.spec_from_file_location("tables_under_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    older = tmp_path / "locked.summary.json"
    newer = tmp_path / "newer.summary.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")

    assert module._select(older, "*.summary.json", tmp_path) == older.resolve()
