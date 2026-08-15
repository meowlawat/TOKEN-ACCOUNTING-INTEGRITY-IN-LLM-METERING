#!/usr/bin/env bash
# Reproduce the entire study from a clean checkout (Linux/macOS/Git-Bash).
# Requires: Docker, Python 3.11+ with httpx, numpy, matplotlib on the host.
# Optional (for the PDF): `tectonic` on PATH (https://tectonic-typesetting.github.io).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1. build + start stack =="
docker compose up --build -d
echo "== waiting for gateway =="
for i in $(seq 1 40); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && break || sleep 2; done
curl -s http://localhost:8000/health; echo

echo "== 2. clean schema =="
curl -s -X POST http://localhost:8000/admin/reset-db >/dev/null

echo "== 3. control / regression suites (must all PASS) =="
python -m experiments.regression_class6
python -m experiments.regression_m

echo "== 4. B0 baseline (credit-decrement race) =="
python -m experiments.run_class6 --affordable 10 --concurrency 1 2 5 10 20 30 50 --reps 30
python -m experiments.summarize_class6

echo "== 5. M1 metering-commit timing =="
python -m experiments.run_m1 --reps 10
python -m experiments.summarize_m1

echo "== 6. M2 usage-record authority =="
python -m experiments.run_m2 --reps 10
python -m experiments.summarize_m2

echo "== 7. defense overhead (RQ4) =="
python -m experiments.run_overhead

echo "== 8. figures, tables, power analysis =="
python -m experiments.figures
python -m experiments.tables
python -m experiments.power_analysis

echo "== 9. compile paper (optional) =="
if command -v tectonic >/dev/null 2>&1; then
  ( cd paper && tectonic main.tex && tectonic main.tex )
  echo "paper/main.pdf written"
else
  echo "tectonic not found on PATH; skipping PDF. Install tectonic and run:"
  echo "    (cd paper && tectonic main.tex && tectonic main.tex)"
fi

echo "== DONE. See results/{raw,processed,figures,tables} and paper/main.pdf =="
