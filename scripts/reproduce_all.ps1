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

Write-Host "== 5. M1 metering-commit timing =="
python -m experiments.run_m1 --reps 10
python -m experiments.summarize_m1

Write-Host "== 6. M2 usage-record authority =="
python -m experiments.run_m2 --reps 10
python -m experiments.summarize_m2

Write-Host "== 7. defense overhead (RQ4) =="
python -m experiments.run_overhead

Write-Host "== 8. figures, tables, power analysis =="
python -m experiments.figures
python -m experiments.tables
python -m experiments.power_analysis

Write-Host "== 9. compile paper (optional) =="
if (Get-Command tectonic -ErrorAction SilentlyContinue) {
  Push-Location paper; tectonic main.tex; tectonic main.tex; Pop-Location
  Write-Host "paper/main.pdf written"
} else {
  Write-Host "tectonic not found; skipping PDF. Install tectonic and run: cd paper; tectonic main.tex; tectonic main.tex"
}

Write-Host "== DONE. See results/{raw,processed,figures,tables} and paper/main.pdf =="
