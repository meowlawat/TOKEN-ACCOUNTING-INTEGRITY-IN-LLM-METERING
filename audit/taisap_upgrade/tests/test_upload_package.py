from pathlib import Path
import zipfile

from pypdf import PdfReader


ROOT = Path(__file__).parents[3]
UPLOAD = ROOT / "audit" / "taisap_upgrade" / "upload_ready"
PDF = UPLOAD / "Main_Document_Anonymous.pdf"
SOURCE_ZIP = UPLOAD / "Source_Document.zip"
FORBIDDEN = (
    "hardik",
    "natasha",
    "iitp",
    "vipstc",
    "meowlawat",
    "22085827",
    "23261555",
    "22086254",
    "0009-0001-1642-6669",
    "0009-0006-4252-9705",
)


def test_upload_files_exist_and_source_is_below_100_mib() -> None:
    assert PDF.is_file()
    assert SOURCE_ZIP.is_file()
    assert SOURCE_ZIP.stat().st_size < 100 * 1024 * 1024


def test_main_pdf_is_anonymous_and_resolved() -> None:
    reader = PdfReader(str(PDF))
    assert len(reader.pages) == 32
    metadata = {str(key).lower(): str(value).lower() for key, value in (reader.metadata or {}).items()}
    assert "/author" not in metadata
    text = "\n".join(page.extract_text() or "" for page in reader.pages).lower()
    assert "[?]" not in text
    assert "(?)" not in text
    for marker in FORBIDDEN:
        assert marker not in text


def test_source_zip_is_anonymous_and_contains_only_submission_inputs() -> None:
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        names = [name.replace("\\", "/") for name in archive.namelist()]
        assert "paper/main.tex" in names
        assert "paper/main.bbl" in names
        assert "paper/references_taisap.bib" in names
        assert any(name.startswith("paper/figures_cose/") for name in names)
        assert any(name.startswith("results/figures/") for name in names)
        assert not any(name.lower().endswith((".aux", ".log", ".out", ".blg")) for name in names)
        for original_name, normalized_name in zip(archive.namelist(), names):
            content = archive.read(original_name).decode("latin-1", errors="ignore").lower()
            for marker in FORBIDDEN:
                assert marker not in content, f"identity marker in {normalized_name}"
