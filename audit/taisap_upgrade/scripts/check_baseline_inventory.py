from __future__ import annotations

import argparse
import csv
import hashlib
import os
import platform
import subprocess
import sys
from pathlib import Path


CLAIM_FIELDS = [
    "claim_id",
    "claim_text",
    "status",
    "evidence_paths",
    "evidence_kind",
    "reviewer_risk",
    "proposed_test",
]

CLAIMS = [
    ("C-INVARIANT", "For every request, delivered value does not exceed net committed debit: V(r) <= N(r).", "paper/main_taisap.tex;formal/TokenAccounting.tla", "model + manuscript"),
    ("C-B0", "A non-atomic shared-state decrement can undercharge concurrently authorized requests; the atomic control does not.", "results/class6_20260816T123031Z.json;experiments/summarize_class6.py", "raw experiment + analysis"),
    ("C-M1", "Commitment-timing architectures can deliver value on terminal paths without a durable debit; reserve-and-reconcile closes the tested paths.", "results/raw/m1_20260816T123351Z.json;experiments/summarize_m1.py", "raw experiment + analysis"),
    ("C-M2", "Client-authoritative billed usage can diverge from true usage; server-authoritative billing closes the tested manipulations.", "results/raw/m2_20260816T123522Z.json;experiments/summarize_m2.py", "raw experiment + analysis"),
    ("C-ORTHOGONALITY", "Reservation and abort-safe finalization are orthogonal: each alone secures only one of solvency and accounting integrity.", "paper/main_taisap.tex;formal/TokenAccounting.tla", "manuscript + model"),
    ("C-TLC-PRIMARY", "The primary model reports 10 configurations, four invariants, 40 outcomes, and 27,526 distinct states.", "formal/check.py;formal/TokenAccounting.tla;results/formal/model_check_results.json", "model checker output"),
    ("C-TLC-ASYNC", "The asynchronous model reports 22,521 distinct and 91,921 generated states for the stated configuration.", "formal/AsyncSettlementTOCTOU.tla;formal/cfg_async/vulnerable_n6_k2.cfg;formal/async_settlement_vulnerable_n6_k2_counterexample.txt", "model checker output"),
    ("C-M2-58.3", "Controlled M2 output under-reporting leaks 58.3 percent of delivered value in the stated workload.", "results/processed/m2_tiers.summary.csv;paper/main_taisap.tex", "processed experiment + manuscript"),
    ("C-M2-69.0", "The real llama.cpp stack M2 configuration leaks 69.0 percent in the stated workload.", "results/raw/real_stack_20260818T152742Z.json;results/processed/real_stack.summary.json;paper/main_taisap.tex", "processed real-stack experiment"),
    ("C-M1-SEQUENTIAL", "Deferred settlement produces over-serving under strictly sequential, non-overlapping arrivals once delay exceeds the arrival gap.", "results/raw/async_accounting_20260818T153903Z.json;results/processed/async_accounting.summary.json;experiments/summarize_async.py", "processed async experiment"),
    ("C-M1-TWO-MACHINE", "The sequential deferred-settlement condition persists in the recorded network-separated two-machine run.", "results/two_machine/C2_sequential_20261007T123546Z.summary.json;experiments/two_machine/raw/C2_sequential_20261007T123546Z.jsonl;experiments/two_machine/raw/C2_sequential_20261007T123546Z.manifest.json", "processed + raw two-machine experiment"),
    ("C-OVERHEAD-0.1", "Server-authoritative recount costs under 0.1 percent of end-to-end time in the stated real-inference configuration.", "results/raw/real_model_recount_20260816T132240Z.json;results/processed/tokenizer_overhead.csv;paper/main_taisap.tex", "benchmark + manuscript"),
    ("C-OPENGATELLM-254347", "A public OpenGateLLM issue reports 254,347 completion tokens delivered and unbilled; this is third-party evidence, not our measurement.", "paper/references_taisap.bib;paper/main_taisap.tex;paper/reference_verification.json", "third-party report"),
]

MANIFEST_ROOTS = (
    "app",
    "attacks",
    "benchmarks",
    "defenses",
    "deploy",
    "experiments",
    "formal",
    "lab",
    "paper",
    "results",
    "scripts",
)

TOP_LEVEL_FILES = (
    "ARTIFACT_README.md",
    "CITATION.cff",
    "CLAUDE.md",
    "docker-compose.yml",
    "docker-compose.distributed.yml",
    "docker-compose.machineA.yml",
    "docker-compose.machineB.yml",
    "docker-compose.multiworker.yml",
    "docker-compose.override.yml",
    "Dockerfile",
    "RELEASE_FREEZE.md",
    "RELEASE_MANIFEST.md",
    "requirements.txt",
)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relevant_files(repo: Path) -> list[Path]:
    files: set[Path] = set()
    for relative in TOP_LEVEL_FILES:
        candidate = repo / relative
        if candidate.is_file():
            files.add(candidate)
    for root_name in MANIFEST_ROOTS:
        root = repo / root_name
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(repo)
            if relative.parts[:2] == ("audit", "taisap_upgrade"):
                continue
            if any(part in {"__pycache__", ".pytest_cache", ".git"} for part in relative.parts):
                continue
            files.add(candidate)
    return sorted(files, key=lambda path: path.relative_to(repo).as_posix())


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_claims(output: Path) -> None:
    rows = []
    for claim_id, text, paths, kind in CLAIMS:
        rows.append(
            {
                "claim_id": claim_id,
                "claim_text": text,
                "status": "UNVERIFIED",
                "evidence_paths": paths,
                "evidence_kind": kind,
                "reviewer_risk": "Existing evidence has not yet been independently rerun in this upgrade.",
                "proposed_test": "Independently rederive from the cited source files and compare with the exact manuscript wording.",
            }
        )
    write_csv(output / "claim_evidence.csv", CLAIM_FIELDS, rows)


def write_manifest(repo: Path, output: Path) -> None:
    rows = []
    for path in relevant_files(repo):
        stat = path.stat()
        rows.append(
            {
                "path": path.relative_to(repo).as_posix(),
                "bytes": str(stat.st_size),
                "sha256": sha256(path),
            }
        )
    write_csv(output / "baseline" / "sha256_manifest.csv", ["path", "bytes", "sha256"], rows)


def write_environment(repo: Path, output: Path, branch_point: str) -> None:
    status = git(repo, "status", "--porcelain=v1").replace("\n", " | ")
    lines = [
        f"BRANCH_POINT={branch_point}",
        f"CURRENT_HEAD={git(repo, 'rev-parse', 'HEAD')}",
        f"CURRENT_BRANCH={git(repo, 'branch', '--show-current')}",
        f"WORKTREE_STATUS={status}",
        f"PYTHON={sys.version.replace(os.linesep, ' ')}",
        f"PYTHON_EXECUTABLE={sys.executable}",
        f"PLATFORM={platform.platform()}",
        f"MACHINE={platform.machine()}",
    ]
    path = output / "baseline" / "environment.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def list_paths(repo: Path, prefix: str) -> list[str]:
    root = repo / prefix
    if not root.exists():
        return [f"{prefix} [MISSING]"]
    return [path.relative_to(repo).as_posix() for path in sorted(root.rglob("*")) if path.is_file()]


def write_inventory(repo: Path, output: Path) -> None:
    sections = [
        "PRESERVATION_POLICY=read-only historical and raw evidence",
        "",
        "[BRANCHES]",
        git(repo, "branch", "--all", "--verbose", "--no-abbrev"),
        "",
        "[RECENT_COMMITS]",
        git(repo, "log", "--oneline", "--decorate", "-20"),
    ]
    for label, prefix in (
        ("MANUSCRIPTS_AND_SUBMISSION", "paper"),
        ("FORMAL_MODELS", "formal"),
        ("EXPERIMENTS", "experiments"),
        ("RAW_AND_PROCESSED_RESULTS", "results"),
        ("APPLICATION", "app"),
        ("DEPLOYMENT", "deploy"),
        ("SCRIPTS", "scripts"),
    ):
        sections.extend(["", f"[{label}]", *list_paths(repo, prefix)])
    path = output / "baseline" / "repository_inventory.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sections) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--branch-point", required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_claims(output)
    write_manifest(repo, output)
    write_environment(repo, output, args.branch_point)
    write_inventory(repo, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
