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

echo "== 5. M1 metering-commit timing (with controlled concurrency) =="
python -m experiments.run_m1 --concurrency 1 5 20 50 100 --requests-per-cell 20
python -m experiments.summarize_m1

echo "== 6. M2 usage-record authority (with controlled concurrency) =="
python -m experiments.run_m2 --concurrency 1 5 20 50 100 --requests-per-cell 20
python -m experiments.summarize_m2

echo "== 7. defense overhead, mock path (RQ4) =="
python -m experiments.run_overhead

echo "== 7b. REAL tokenizer benchmarks =="
echo "     (requires: bash scripts/populate_tokenizer_cache.sh once, with network)"
python -m benchmarks.tokenizer_overhead
# gateway sweep is run per-size so each chunk stays short, then merged
for S in 256 1024 4096 16384; do
  python -m benchmarks.gateway_recount_overhead --sizes $S --duration 5 --repeats 3 \
      --out results/raw/gw_part_$S.json
done
python -m benchmarks.merge_gateway_parts
python -m benchmarks.summarize_benchmarks

echo "== 7c. architectural ablation, failure modes, cross-validation =="
python -m experiments.run_ablation --reps 10
python -m experiments.run_failure_modes --reps 5
python -m experiments.run_cross_validation --reps 5
python -m experiments.summarize_ablation

echo "== 7d. economic sensitivity (3 price tiers) =="
python -m experiments.run_m2 --tiers low medium high --concurrency 1 \
    --requests-per-cell 20 --out results/raw/m2_tiers.json
python -m experiments.economic_analysis

echo "== 7e. local real-model external-validity experiment =="
python -m benchmarks.real_model_recount --reps 5 --max-new-tokens 64

echo "== 7f. harness validation (fault injection + metamorphic) =="
python -m experiments.metamorphic_checks

echo "== 8. figures, tables, statistics, claim matrix =="
python -m experiments.figures
python -m experiments.tables
python -m experiments.power_analysis
python -m experiments.statistical_analysis
python -m experiments.build_claim_matrix

echo "== 8b. provenance manifest =="
python -m experiments.build_manifest --status PASS

echo "== 9. compile paper (optional) =="
if command -v tectonic >/dev/null 2>&1; then
  ( cd paper && tectonic main.tex && tectonic main.tex )
  echo "paper/main.pdf written"
else
  echo "tectonic not found on PATH; skipping PDF. Install tectonic and run:"
  echo "    (cd paper && tectonic main.tex && tectonic main.tex)"
fi

echo "== DONE. See results/{raw,processed,figures,tables} and paper/main.pdf =="
