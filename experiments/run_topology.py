"""Cross-topology validation (Phases 1-2): do the accounting results depend on
process/node locality?

Deliberately REUSES the existing, already-validated runners (`run_class6`, `run_m1`,
`run_m2`) against a different `--base-url`, rather than duplicating attack logic. The
only new thing here is orchestration + tagging, so a topology difference cannot be an
artifact of a different attack implementation.

Topologies (all share one PostgreSQL and one Redis):
  single       control     :8000  1 uvicorn worker, no proxy
  multiworker  Phase 1     :8001  nginx -> 4 uvicorn workers (4 event loops, 1 container)
  distributed  Phase 2     :8002  nginx LB -> gateway A + gateway B (2 containers x 2 workers)

Usage:
    python -m experiments.run_topology --topology multiworker --base-url http://localhost:8001
    python -m experiments.run_topology --topology distributed --base-url http://localhost:8002 --reduced
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw" / "topology"


def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def probe_workers(base_url: str, n: int = 24) -> dict:
    """Confirm the topology actually spreads load before we attribute anything to it."""
    seen: dict[str, int] = {}
    with httpx.Client(base_url=base_url, timeout=15.0) as c:
        for _ in range(n):
            try:
                w = c.get("/health").json().get("worker", "?")
                seen[w] = seen.get(w, 0) + 1
            except Exception:  # noqa: BLE001
                seen["error"] = seen.get("error", 0) + 1
    return seen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topology", required=True,
                    choices=["single", "multiworker", "distributed"])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--reduced", action="store_true",
                    help="reduced but statistically defensible matrix (Phase 2)")
    ap.add_argument("--skip-b0", action="store_true")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = args.topology
    py = sys.executable

    workers = probe_workers(args.base_url)
    print(f"[{tag}] distinct serving processes: {workers}")

    stages: list[dict] = []

    def stage(name: str, cmd: list[str], out: Path):
        print(f"[{tag}] {name} ...")
        code, log = run(cmd)
        ok = code == 0 and out.exists()
        stages.append({"stage": name, "exit_code": code, "output": str(out.relative_to(ROOT)),
                       "ok": ok, "tail": log.strip().splitlines()[-3:] if log else []})
        print(f"[{tag}] {name}: {'OK' if ok else 'FAILED (code %d)' % code}")

    # ---- B0: concurrency sensitivity must survive the topology --------------
    if not args.skip_b0:
        concs = ["10", "50"] if args.reduced else ["1", "2", "5", "10", "20", "30", "50"]
        reps = "10" if args.reduced else "20"
        out = RAW / f"b0_{tag}_{stamp}.json"
        stage("B0", [py, "-m", "experiments.run_class6", "--base-url", args.base_url,
                     "--affordable", "10", "--concurrency", *concs, "--reps", reps,
                     "--out", str(out)], out)

    # ---- M1: abort positions x concurrency ---------------------------------
    concs = ["10", "50"] if args.reduced else ["1", "5", "20", "50", "100"]
    aborts = ["25", "50", "90"] if args.reduced else ["0", "25", "50", "75", "90", "100"]
    out = RAW / f"m1_{tag}_{stamp}.json"
    stage("M1", [py, "-m", "experiments.run_m1", "--base-url", args.base_url,
                 "--concurrency", *concs, "--abort-pcts", *aborts,
                 "--requests-per-cell", "20", "--no-reset-db", "--out", str(out)], out)

    # ---- M2: strongest manipulations x concurrency --------------------------
    manips = (["honest", "under_report_output_90", "total_mismatch"] if args.reduced
              else ["honest", "under_report_output_50", "under_report_output_90",
                    "drop_reasoning", "inflate_cached", "total_mismatch", "rounding_shave"])
    out = RAW / f"m2_{tag}_{stamp}.json"
    stage("M2", [py, "-m", "experiments.run_m2", "--base-url", args.base_url,
                 "--concurrency", *concs, "--manipulations", *manips,
                 "--requests-per-cell", "20", "--no-reset-db", "--out", str(out)], out)

    manifest = {
        "experiment": "topology_validation", "topology": tag, "base_url": args.base_url,
        "generated_at": stamp, "reduced_matrix": args.reduced,
        "serving_processes_observed": workers,
        "distinct_processes": len([k for k in workers if k != "error"]),
        "stages": stages,
        "all_ok": all(s["ok"] for s in stages),
    }
    mp = RAW / f"manifest_{tag}_{stamp}.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n[{tag}] stages ok: {manifest['all_ok']}  -> {mp}")
    if not manifest["all_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
