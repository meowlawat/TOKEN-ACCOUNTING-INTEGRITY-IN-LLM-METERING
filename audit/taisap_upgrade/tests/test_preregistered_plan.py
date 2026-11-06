from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "audit" / "taisap_upgrade"


def test_preregistered_plan_locks_decisive_fields() -> None:
    text = (ROOT / "02_preregistered_extension_plan.md").read_text(encoding="utf-8")
    for experiment in ("E1", "E2", "E3", "E4"):
        assert f"## {experiment}" in text
    for field in (
        "Hypothesis:", "Null/falsifying outcome:", "Controls:", "Sample size:",
        "Exclusions:", "Locked metrics:", "Positive interpretation:",
        "Null interpretation:", "Resources:", "Execution status:",
    ):
        assert text.count(field) == 4
    assert "designed to falsify the central claim" in text
    assert "HUMAN_APPROVAL_REQUIRED" in text
    assert "PROPOSED_ONLY" in text


def test_experiment_manifest_schema_is_valid_and_requires_status() -> None:
    schema = json.loads((ROOT / "protocols" / "experiment_manifest.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("schema")
    assert "execution_status" in schema["required"]
    statuses = schema["properties"]["execution_status"]["enum"]
    assert statuses == ["PROPOSED_ONLY", "EXECUTED", "FAILED", "HUMAN_APPROVAL_REQUIRED"]
    assert {"hypothesis", "metrics", "sample_size", "artifacts"} <= set(schema["required"])
