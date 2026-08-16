"""Build results/reproduction_manifest.json — the provenance record for a run.

Captures the exact commit, environment, package versions, stage commands, and
SHA-256 hashes of every generated artifact (raw, processed, tables, figures) plus
the compiled PDF, so a third party can verify they are looking at the same outputs.

Usage:
    python -m experiments.build_manifest [--runtime-seconds N] [--status PASS|FAIL]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

STAGES = [
    ("regression_b0", "python -m experiments.regression_class6"),
    ("regression_m", "python -m experiments.regression_m"),
    ("b0_sweep", "python -m experiments.run_class6 --affordable 10 "
                 "--concurrency 1 2 5 10 20 30 50 --reps 30"),
    ("b0_summary", "python -m experiments.summarize_class6"),
    ("m1_sweep", "python -m experiments.run_m1 --concurrency 1 5 20 50 100 --requests-per-cell 20"),
    ("m1_summary", "python -m experiments.summarize_m1"),
    ("m2_sweep", "python -m experiments.run_m2 --concurrency 1 5 20 50 100 --requests-per-cell 20"),
    ("m2_summary", "python -m experiments.summarize_m2"),
    ("overhead_mock", "python -m experiments.run_overhead"),
    ("tokenizer_benchmark", "python -m benchmarks.tokenizer_overhead"),
    ("gateway_recount", "python -m benchmarks.gateway_recount_overhead --sizes {S} "
                        "--duration 5 --repeats 3 (per size, then merge)"),
    ("ablation", "python -m experiments.run_ablation --reps 10"),
    ("failure_modes", "python -m experiments.run_failure_modes --reps 5"),
    ("cross_validation", "python -m experiments.run_cross_validation --reps 5"),
    ("economic_tiers", "python -m experiments.run_m2 --tiers low medium high --concurrency 1 "
                       "--requests-per-cell 20 --out results/raw/m2_tiers.json"),
    ("economic_analysis", "python -m experiments.economic_analysis"),
    ("real_model", "python -m benchmarks.real_model_recount --reps 5 --max-new-tokens 64"),
    ("metamorphic", "python -m experiments.metamorphic_checks"),
    ("figures", "python -m experiments.figures"),
    ("tables", "python -m experiments.tables"),
    ("statistics", "python -m experiments.statistical_analysis"),
    ("claim_matrix", "python -m experiments.build_claim_matrix"),
    ("paper", "tectonic main.tex (x2)"),
]


def sh(*argv: str) -> str | None:
    """Run a command as an argv list (no shell) and return trimmed stdout."""
    try:
        r = subprocess.run(list(argv), capture_output=True, text=True, timeout=60)
        return r.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-seconds", type=float, default=None)
    ap.add_argument("--status", default="UNKNOWN")
    args = ap.parse_args()

    import importlib.metadata as md
    pkgs = {}
    for p in ["fastapi", "uvicorn", "sqlalchemy", "asyncpg", "redis", "httpx", "numpy",
              "matplotlib", "scipy", "statsmodels", "tiktoken", "transformers",
              "tokenizers", "sentencepiece", "torch", "psutil", "pydantic"]:
        try:
            pkgs[p] = md.version(p)
        except Exception:  # noqa: BLE001
            pkgs[p] = None

    artifacts: dict[str, dict] = {}
    for sub in ("raw", "processed", "tables", "figures"):
        d = RESULTS / sub
        if not d.exists():
            continue
        for f in sorted(d.rglob("*")):
            if f.is_file() and f.name != ".gitkeep":
                artifacts[str(f.relative_to(ROOT)).replace("\\", "/")] = {
                    "sha256": sha256(f), "bytes": f.stat().st_size}
    for f in sorted(RESULTS.glob("class6_*")):
        if f.is_file():
            artifacts[str(f.relative_to(ROOT)).replace("\\", "/")] = {
                "sha256": sha256(f), "bytes": f.stat().st_size}

    pdf = ROOT / "paper" / "main.pdf"
    pdf_info = {"sha256": sha256(pdf), "bytes": pdf.stat().st_size} if pdf.exists() else None

    manifest = {
        "manifest_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reproduction_status": args.status,
        "runtime_seconds": args.runtime_seconds,
        "runtime_human": (f"{args.runtime_seconds/60:.1f} min" if args.runtime_seconds else None),
        "git": {
            "commit": sh("git", "rev-parse", "HEAD"),
            "short": sh("git", "rev-parse", "--short", "HEAD"),
            "branch": sh("git", "rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(sh("git", "status", "--porcelain")),
        },
        "environment": {
            "os": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count_logical": os.cpu_count(),
            "python_host": platform.python_version(),
            "docker": sh("docker", "--version"),
            "docker_compose": sh("docker", "compose", "version", "--short"),
            "postgres": sh("docker", "compose", "exec", "-T", "db", "postgres", "--version"),
            "redis": sh("docker", "compose", "exec", "-T", "redis", "redis-server", "--version"),
            "python_container": sh("docker", "compose", "exec", "-T", "app", "python", "--version"),
        },
        "packages": pkgs,
        "stages": [{"name": n, "command": c} for n, c in STAGES],
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "paper_pdf": pdf_info,
    }
    try:
        import psutil
        manifest["environment"]["ram_total_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
    except Exception:  # noqa: BLE001
        pass

    out = RESULTS / "reproduction_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest -> {out}")
    print(f"  commit={manifest['git']['short']} status={args.status} "
          f"artifacts={len(artifacts)} pdf={'yes' if pdf_info else 'NO'}")


if __name__ == "__main__":
    main()
