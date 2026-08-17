# Reproduce the entire study from a clean checkout (Windows PowerShell).
# Requires: Docker Desktop, Python 3.11+ with httpx, numpy, matplotlib on the host.
# Optional (for the PDF): tectonic.exe on PATH.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "== 1. build + start stack =="
docker compose up --build -d
Write-Host "== waiting for gateway =="
for ($i = 0; $i -lt 40; $i++) {
  try { Invoke-RestMethod http://localhost:8000/health -TimeoutSec 3 | Out-Null; break } catch { Start-Sleep 2 }
}
Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Compress

Write-Host "== 2. clean schema =="
Invoke-RestMethod -Method Post http://localhost:8000/admin/reset-db | Out-Null

Write-Host "== 3. control / regression suites (must all PASS) =="
python -m experiments.regression_class6
python -m experiments.regression_m

Write-Host "== 4. B0 baseline =="
python -m experiments.run_class6 --affordable 10 --concurrency 1 2 5 10 20 30 50 --reps 30
python -m experiments.summarize_class6

Write-Host "== 5. M1 metering-commit timing (controlled concurrency) =="
python -m experiments.run_m1 --concurrency 1 5 20 50 100 --requests-per-cell 20
python -m experiments.summarize_m1

Write-Host "== 6. M2 usage-record authority (controlled concurrency) =="
python -m experiments.run_m2 --concurrency 1 5 20 50 100 --requests-per-cell 20
python -m experiments.summarize_m2

Write-Host "== 7. defense overhead, mock path (RQ4) =="
python -m experiments.run_overhead

Write-Host "== 7b. REAL tokenizer benchmarks =="
Write-Host "     (run scripts/populate_tokenizer_cache.sh once first, with network)"
python -m benchmarks.tokenizer_overhead
foreach ($S in 256, 1024, 4096, 16384) {
  python -m benchmarks.gateway_recount_overhead --sizes $S --duration 5 --repeats 3 --out "results/raw/gw_part_$S.json"
}
python -m benchmarks.merge_gateway_parts
python -m benchmarks.summarize_benchmarks

Write-Host "== 7c. architectural ablation, failure modes, cross-validation =="
python -m experiments.run_ablation --reps 10
python -m experiments.run_failure_modes --reps 5
python -m experiments.run_cross_validation --reps 5
python -m experiments.summarize_ablation

Write-Host "== 7d. economic sensitivity (3 price tiers) =="
python -m experiments.run_m2 --tiers low medium high --concurrency 1 --requests-per-cell 20 --out results/raw/m2_tiers.json
python -m experiments.economic_analysis

Write-Host "== 7e. local real-model external-validity experiment =="
python -m benchmarks.real_model_recount --reps 5 --max-new-tokens 64

Write-Host "== 7f. harness validation (fault injection + metamorphic) =="
python -m experiments.metamorphic_checks

Write-Host "== 8. figures, tables, statistics, claim matrix =="
python -m experiments.figures
python -m experiments.tables
python -m experiments.power_analysis
python -m experiments.statistical_analysis
python -m experiments.build_claim_matrix

Write-Host "== 8c. cross-architecture generality (optional; needs the alt topologies) =="
Write-Host "     multi-worker:  docker compose -f docker-compose.multiworker.yml -p taimw up -d   (:8001)"
Write-Host "     distributed :  docker compose -f docker-compose.distributed.yml -p taidist up -d (:8002)"
Write-Host "     then: python -m experiments.run_topology --topology multiworker --base-url http://localhost:8001"
Write-Host "           python -m experiments.run_topology --topology distributed --base-url http://localhost:8002 --reduced"
Write-Host "           python -m experiments.run_backend_comparison --base-url http://localhost:8002"
python -m experiments.summarize_generality

Write-Host "== 8b. provenance manifest =="
python -m experiments.build_manifest --status PASS

Write-Host "== 9. compile paper (optional) =="
if (Get-Command tectonic -ErrorAction SilentlyContinue) {
  Push-Location paper; tectonic main.tex; tectonic main.tex; Pop-Location
  Write-Host "paper/main.pdf written"
} else {
  Write-Host "tectonic not found; skipping PDF. Install tectonic and run: cd paper; tectonic main.tex; tectonic main.tex"
}

Write-Host "== DONE. See results/{raw,processed,figures,tables} and paper/main.pdf =="
