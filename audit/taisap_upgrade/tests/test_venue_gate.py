from __future__ import annotations

import csv
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "audit" / "taisap_upgrade"


def test_prior_work_matrix_has_required_evidence_contract() -> None:
    path = ROOT / "prior_work_matrix.csv"
    assert path.is_file()
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert 15 <= len(rows) <= 25
    required = {"work_id", "year", "primary_url", "observed_on", "mechanism", "overlap", "difference", "verification"}
    assert required <= set(rows[0])
    assert all(row["primary_url"].startswith("http") for row in rows)
    assert all(row["observed_on"] == "2026-11-06" for row in rows)


def test_venue_gate_contains_one_route_and_falsifiable_switches() -> None:
    files = [
        "01_novelty_and_venue_fit.md",
        "01B_editorial_history_and_venue_matrix.md",
        "01C_primary_contribution_decision.md",
        "01D_submission_route_recommendation.md",
    ]
    texts = {}
    for name in files:
        path = ROOT / name
        assert path.is_file()
        texts[name] = path.read_text(encoding="utf-8")

    combined = "\n".join(texts.values())
    for venue in ("TAISAP", "Wiley Security and Privacy", "TOPS", "IJIS"):
        assert venue in combined
    assert combined.count("## Hostile-editor abstract") >= 3
    assert "Gate: CONDITIONAL GO" in texts["01C_primary_contribution_decision.md"]
    assert "Primary venue: TAISAP" in texts["01D_submission_route_recommendation.md"]
    assert "Fallback venue:" in texts["01D_submission_route_recommendation.md"]
    assert "Switch condition" in texts["01D_submission_route_recommendation.md"]
