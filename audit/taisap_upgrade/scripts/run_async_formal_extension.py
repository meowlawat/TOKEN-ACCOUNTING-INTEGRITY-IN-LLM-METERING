from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path


POINTS = ((3, 1), (4, 1), (4, 2), (5, 2), (6, 2), (6, 3))
INVARIANTS = ("AccountingIntegrity", "Solvency", "LedgerConservation")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def java_exe() -> str:
    try:
        import jdk4py
        return str(jdk4py.JAVA)
    except ImportError:
        return "java"


def config_text(n: int, k: int, atomic: bool, invariant: str) -> str:
    requests = ", ".join(f"r{i}" for i in range(1, n + 1))
    return f"""SPECIFICATION Spec

CONSTANTS
    Requests = {{{requests}}}
    Value = 1
    InitialBalance = {k}
    AtomicCommit = {'TRUE' if atomic else 'FALSE'}

INVARIANTS
    TypeOK
    {invariant}
"""


def parse_states(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"([0-9,]+) states generated, ([0-9,]+) distinct states found", text)
    return ((int(match.group(1).replace(",", "")), int(match.group(2).replace(",", "")))
            if match else (None, None))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    configs, logs = output / "configs", output / "logs"
    configs.mkdir(exist_ok=True); logs.mkdir(exist_ok=True)
    for stale in (*configs.glob("*.cfg"), *logs.glob("*.txt")):
        stale.unlink()
    spec = repo / "formal" / "AsyncSettlementTOCTOU.tla"
    jar = repo / "formal" / "tools" / "tla2tools.jar"
    results = []
    errors = unexpected = 0
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for n, k in POINTS:
        for mode, atomic in (("vulnerable", False), ("atomic", True)):
            for invariant in INVARIANTS:
                name = f"{mode}_n{n}_k{k}__{invariant}"
                cfg = configs / f"{name}.cfg"
                cfg.write_text(config_text(n, k, atomic, invariant), encoding="utf-8")
                command = [java_exe(), "-XX:+UseParallelGC", "-cp", str(jar), "tlc2.TLC",
                           "-config", str(cfg), "-workers", "1", "-cleanup", "-deadlock", spec.name]
                run = subprocess.run(command, cwd=repo / "formal", capture_output=True, text=True)
                transcript = run.stdout + run.stderr
                violated = f"Invariant {invariant} is violated" in transcript
                semantic_error = "Parsing or semantic analysis failed" in transcript
                observed = "VIOLATED" if violated else "HOLDS"
                expected = "VIOLATED" if (mode == "vulnerable" and invariant == "Solvency") else "HOLDS"
                generated, distinct = parse_states(transcript)
                is_error = semantic_error or (run.returncode != 0 and not violated) or generated is None
                errors += int(is_error)
                unexpected += int(observed != expected)
                if violated or is_error or observed != expected:
                    (logs / f"{name}.txt").write_text(transcript, encoding="utf-8", errors="replace")
                results.append({
                    "mode": mode, "n": n, "k": k, "invariant": invariant,
                    "expected": expected, "observed": observed,
                    "exit_code": run.returncode, "states_generated": generated,
                    "distinct_states": distinct, "config_sha256": sha256(cfg),
                    "command": command, "error": is_error,
                })
    payload = {
        "spec": "formal/AsyncSettlementTOCTOU.tla", "spec_sha256": sha256(spec),
        "jar_sha256": sha256(jar), "java": java_exe(), "started_at": started,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "configurations": len(POINTS) * 2, "checks": len(results),
        "errors": errors, "unexpected": unexpected, "results": results,
    }
    (output / "async_extension_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 1 if errors or unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
