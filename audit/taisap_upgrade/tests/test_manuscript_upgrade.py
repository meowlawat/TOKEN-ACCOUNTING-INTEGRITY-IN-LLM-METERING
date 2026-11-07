from __future__ import annotations

import csv
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "paper" / "main_taisap_upgrade.tex"
BIB = REPO / "paper" / "references_taisap.bib"
LEDGER = REPO / "audit" / "taisap_upgrade" / "claim_evidence.csv"


def manuscript() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_selected_intellectual_spine_and_bounded_formal_language() -> None:
    text = manuscript()
    assert "Bounded Evidence for Client-Side Under-Payment" in text
    assert "bounded exhaustive model checking" in text
    assert "six preregistered $(N,k)$ points" in text
    assert "verify the lifecycle exhaustively" not in text
    assert "verified conditions" not in text.lower()


def test_closest_provider_side_work_is_cited_and_contrasted() -> None:
    text = manuscript()
    flat = " ".join(text.split())
    bib = BIB.read_text(encoding="utf-8")
    assert "\\citep{ptia,auditingpaypertoken}" in text
    assert "opposite trust direction" in flat
    assert "@misc{ptia" in bib
    assert "@misc{auditingpaypertoken" in bib


def test_workload_scope_and_unexecuted_extensions_are_explicit() -> None:
    text = manuscript()
    flat = " ".join(text.split())
    assert "one controlled testbed, one llama.cpp/SmolLM2 stack" in flat
    assert "The preregistered 1,200-trial terminal-path fault matrix was not executed" in flat
    assert "No independent second-host replication was executed in this upgrade" in flat
    assert "does not establish production prevalence" in flat


def test_verified_headline_numbers_remain_linked() -> None:
    text = manuscript()
    for value in ("58.3\\%", "69.0\\%", "27{,}526", "22{,}521", "91{,}921", "0.023693\\%"):
        assert value in text


def test_claim_ledger_records_upgrade_outcomes() -> None:
    with LEDGER.open(encoding="utf-8", newline="") as handle:
        rows = {row["claim_id"]: row for row in csv.DictReader(handle)}
    for claim_id in (
        "C-TLC-PRIMARY", "C-TLC-ASYNC", "C-M2-58.3", "C-M2-69.0", "C-OVERHEAD-0.1"
    ):
        assert rows[claim_id]["status"] == "REPRODUCED"
    assert rows["C-M1-TWO-MACHINE"]["status"] == "SUPPORTED_BY_EXISTING_DATA"
