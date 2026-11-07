from pathlib import Path
import re

from pypdf import PdfReader


ROOT = Path(__file__).parents[3]
PACKAGE = ROOT / "audit" / "taisap_upgrade" / "submission_package"
REPORT = ROOT / "audit" / "taisap_upgrade" / "07_submission_preflight.md"


def test_preflight_report_and_package_exist():
    assert REPORT.exists()
    assert (PACKAGE / "named" / "main_taisap_upgrade.pdf").exists()
    assert (PACKAGE / "anonymous" / "main_taisap_upgrade_anon.pdf").exists()


def test_pdfs_have_expected_pages_and_no_missing_citations():
    for pdf in (PACKAGE / "named" / "main_taisap_upgrade.pdf", PACKAGE / "anonymous" / "main_taisap_upgrade_anon.pdf"):
        reader = PdfReader(str(pdf))
        assert 30 <= len(reader.pages) <= 35
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "[?]" not in text
        assert "(?)" not in text


def test_named_source_has_verified_orcid_and_accessible_figures():
    source = (PACKAGE / "named" / "main_taisap_upgrade.tex").read_text(encoding="utf-8")
    assert r"\orcid{0009-0001-1642-6669}" in source
    assert source.count(r"\Description[") >= 6
    assert (PACKAGE / "named" / "references_taisap.bib").exists()
    assert (PACKAGE / "named" / "main_taisap_upgrade.bbl").exists()


def test_anonymous_source_contains_no_author_identity_or_artifact_identifiers():
    source = (PACKAGE / "anonymous" / "main_taisap_upgrade_anon.tex").read_text(encoding="utf-8")
    for marker in ("Hardik", "Natasha Kaila", "iitp.ac.in", "vipstc.edu.in", "22085827", "23261555", "22086254", r"\orcid"):
        assert marker not in source
    assert r"\email" not in source
    assert "anonymous" in source.splitlines()[4]


def test_author_action_blockers_are_explicit():
    report = REPORT.read_text(encoding="utf-8")
    assert "Natasha" in report
    assert "ORCID" in report
    assert "exclusivity" in report.lower()
    assert "REQUIRES AUTHOR ACTION" in report
