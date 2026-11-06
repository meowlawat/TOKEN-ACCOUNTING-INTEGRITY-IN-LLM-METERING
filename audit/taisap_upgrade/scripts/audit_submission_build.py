from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path


IDENTITY_PATTERNS = {
    "hardik": re.compile(r"hardik", re.I),
    "natasha": re.compile(r"natasha", re.I),
    "iit_patna": re.compile(r"iitp|indian institute of technology patna", re.I),
    "vips": re.compile(r"vivekananda institute|vipstc", re.I),
    "orcid": re.compile(r"0009-0001-1642-6669", re.I),
    "author_email": re.compile(r"hardik_24a12res263|09617711924_aids", re.I),
    "github_account": re.compile(r"meowlawat", re.I),
    "zenodo": re.compile(r"zenodo|10\.5281/zenodo", re.I),
}


def cited_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for group in re.findall(r"\\cite[a-zA-Z*]*\s*(?:\[[^]]*\]\s*)*\{([^}]+)\}", text):
        keys.update(key.strip() for key in group.split(",") if key.strip())
    return keys


def bib_keys(text: str) -> set[str]:
    return set(re.findall(r"(?m)^@\w+\s*[({]\s*([^,\s]+)\s*,", text))


def bib_key_list(text: str) -> list[str]:
    return re.findall(r"(?m)^@\w+\s*[({]\s*([^,\s]+)\s*,", text)


def bbl_keys(text: str) -> set[str]:
    return set(re.findall(r"\\bibitem(?:\s*\[[^]]*\])?\s*%?\s*\{([^}]+)\}", text, re.S))


def identity_findings(text: str) -> list[str]:
    return [name for name, pattern in IDENTITY_PATTERNS.items() if pattern.search(text)]


def log_findings(text: str) -> list[str]:
    findings = []
    if re.search(r"(?:LaTeX|Package) Error|^! ", text, re.I | re.M):
        findings.append("latex_error")
    if re.search(r"(?:citation|reference).*(?:undefined|not found)|undefined (?:citation|reference)", text, re.I):
        findings.append("undefined_reference_or_citation")
    return findings


def pdf_facts(path: Path) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
    return {
        "pages": len(reader.pages),
        "metadata": metadata,
        "identity_findings_text": identity_findings(text),
        "identity_findings_metadata": identity_findings(json.dumps(metadata, sort_keys=True)),
        "rendered_reference_count": len(re.findall(r"(?m)^\[\d+\]\s", text)),
    }


def build_one(tectonic: Path, work: Path, stem: str, output: Path) -> dict:
    command = [str(tectonic), "-X", "compile", f"{stem}.tex", "--keep-logs", "--keep-intermediates"]
    completed = subprocess.run(command, cwd=work, capture_output=True, text=True)
    chatter = completed.stdout + completed.stderr
    source_log = work / f"{stem}.log"
    log = chatter + ("\n" + source_log.read_text(encoding="utf-8", errors="replace") if source_log.exists() else "")
    (output / f"build_{'anonymous' if stem.endswith('_anon') else 'named'}.log").write_text(log, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Tectonic failed for {stem}:\n{chatter[-4000:]}")
    pdf = work / f"{stem}.pdf"
    bbl = work / f"{stem}.bbl"
    facts = pdf_facts(pdf)
    generated_bbl_keys = bbl_keys(bbl.read_text(encoding="utf-8", errors="replace")) if bbl.exists() else set()
    facts.update({
        "stem": stem,
        "command": command,
        "log_findings": log_findings(log),
        "bbl_keys": sorted(generated_bbl_keys),
        "rendered_reference_count": len(generated_bbl_keys),
        "pdf_sha256": __import__("hashlib").sha256(pdf.read_bytes()).hexdigest(),
    })
    return facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tectonic", type=Path, required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paper = repo / "paper"
    existing_hashes = {}
    for stem in ("main_taisap", "main_taisap_anon"):
        existing_pdf = paper / f"{stem}.pdf"
        existing_hashes[stem] = (__import__("hashlib").sha256(existing_pdf.read_bytes()).hexdigest()
                                 if existing_pdf.exists() else None)

    with tempfile.TemporaryDirectory(prefix="taisap-clean-build-") as temporary:
        work = Path(temporary) / "paper"
        shutil.copytree(paper, work)
        for pattern in ("main_taisap.*", "main_taisap_anon.*"):
            for path in work.glob(pattern):
                if path.suffix not in {".tex"}:
                    path.unlink()
        named = build_one(args.tectonic.resolve(), work, "main_taisap", output)
        anonymous = build_one(args.tectonic.resolve(), work, "main_taisap_anon", output)

    tex = (paper / "main_taisap.tex").read_text(encoding="utf-8")
    anon_tex = (paper / "main_taisap_anon.tex").read_text(encoding="utf-8")
    bib = (paper / "references_taisap.bib").read_text(encoding="utf-8")
    cited, available = cited_keys(tex), bib_keys(bib)
    all_bib_keys = bib_key_list(bib)
    generated = set(named["bbl_keys"])
    rows = []
    for key in sorted(available | cited | generated):
        complete = key in available and key in cited and key in generated
        rows.append({
            "key": key, "in_bib": key in available, "cited": key in cited,
            "in_clean_bbl": key in generated,
            "verification_status": "INHERITED_UNCHECKED_CURRENT_UPGRADE" if complete else "BROKEN_OR_UNCERTAIN",
        })
    with (output / "bibliography_reconciliation.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "in_bib", "cited", "in_clean_bbl", "verification_status"])
        writer.writeheader(); writer.writerows(rows)

    report = {
        "named": named,
        "anonymous": anonymous,
        "tools": {
            "python": sys.version,
            "tectonic": subprocess.run([str(args.tectonic.resolve()), "--version"], capture_output=True, text=True).stdout.strip(),
        },
        "existing_pdf_comparison": {
            "named_existing_sha256": existing_hashes["main_taisap"],
            "named_matches_clean": existing_hashes["main_taisap"] == named["pdf_sha256"],
            "anonymous_existing_sha256": existing_hashes["main_taisap_anon"],
            "anonymous_matches_clean": existing_hashes["main_taisap_anon"] == anonymous["pdf_sha256"],
        },
        "bibliography": {
            "bib_entries": len(available), "cited_keys": len(cited), "clean_bbl_entries": len(generated),
            "duplicate_bib_keys": sorted({key for key in all_bib_keys if all_bib_keys.count(key) > 1}),
            "missing_from_bib": sorted(cited - available), "cited_missing_from_bbl": sorted(cited - generated),
            "unused_bib_entries": sorted(available - cited),
        },
        "anonymous_source_identity_findings": identity_findings(anon_tex),
    }
    (output / "build_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Clean TAISAP PDF inspection", "",
        f"- Named build: {named['pages']} pages; {named['rendered_reference_count']} rendered numbered references; log findings: {named['log_findings'] or 'none'}.",
        f"- Anonymous build: {anonymous['pages']} pages; {anonymous['rendered_reference_count']} rendered numbered references; log findings: {anonymous['log_findings'] or 'none'}.",
        f"- Bibliography: {len(available)} entries, {len(cited)} cited keys, {len(generated)} clean-build BBL entries.",
        "- Reference-verification class: all 85 are inherited/unchecked in this upgrade; prior verification reports are inputs, not independent evidence for this checkpoint.",
        f"- Missing cited keys: {sorted(cited - available) or 'none'}; cited keys absent from clean BBL: {sorted(cited - generated) or 'none'}.",
        f"- Anonymous source identity/artifact findings: {identity_findings(anon_tex) or 'none'}.",
        f"- Anonymous rendered-text findings: {anonymous['identity_findings_text'] or 'none'}.",
        f"- Anonymous PDF metadata findings: {anonymous['identity_findings_metadata'] or 'none'}.",
        f"- Existing named PDF matches clean build: {existing_hashes['main_taisap'] == named['pdf_sha256']}; existing anonymous PDF matches clean build: {existing_hashes['main_taisap_anon'] == anonymous['pdf_sha256']} (creation timestamps make byte equality non-semantic, so page/text findings govern).",
        "",
        "The anonymous source retains author metadata inside `\\author` commands; the class may suppress it visually, but source submission would disclose it. Public Zenodo DOIs also remain in rendered text and are author-linked. Both are anonymity defects, not clean-build failures.",
    ]
    (output / "pdf_inspection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
