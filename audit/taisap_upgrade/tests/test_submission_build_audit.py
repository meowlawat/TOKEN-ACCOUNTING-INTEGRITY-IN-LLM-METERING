from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "audit" / "taisap_upgrade" / "scripts" / "audit_submission_build.py"


def load_module():
    spec = importlib.util.spec_from_file_location("submission_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bibliography_parser_reconciles_current_sources() -> None:
    audit = load_module()
    paper = REPO / "paper"
    cited = audit.cited_keys((paper / "main_taisap.tex").read_text(encoding="utf-8"))
    available = audit.bib_keys((paper / "references_taisap.bib").read_text(encoding="utf-8"))

    assert len(cited) == 85
    assert cited <= available
    assert len(audit.bbl_keys((paper / "main_taisap.bbl").read_text(encoding="utf-8"))) == 85


def test_anonymous_source_scan_detects_current_identity_and_doi_leaks() -> None:
    audit = load_module()
    source = (REPO / "paper" / "main_taisap_anon.tex").read_text(encoding="utf-8")
    findings = audit.identity_findings(source)

    assert "hardik" in findings
    assert "natasha" in findings
    assert "zenodo" in findings


def test_log_scanner_distinguishes_errors_and_undefined_references() -> None:
    audit = load_module()

    clean = audit.log_findings("Rerun to get cross-references right")
    dirty = audit.log_findings("LaTeX Error: bad\nCitation `missing' undefined")

    assert clean == []
    assert "latex_error" in dirty
    assert "undefined_reference_or_citation" in dirty
