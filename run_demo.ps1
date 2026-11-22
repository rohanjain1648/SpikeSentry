# Guided demo for the screen recording. Run:  powershell -ExecutionPolicy Bypass -File run_demo.ps1
# Press ENTER to advance each step, so you control the pace while narrating.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

function Step($title, $cmd) {
    Write-Host ""
    Write-Host "=== $title ===" -ForegroundColor Cyan
    Read-Host "(ENTER to run)" | Out-Null
    Write-Host "> $cmd" -ForegroundColor Yellow
    Invoke-Expression $cmd
}

Clear-Host
Write-Host "SpikeSentry - explainable offline spike detection (AEGYTHON 2026, Challenge 03)" -ForegroundColor Green
Step "1. Synthetic input: header, normal rows, and the burst"  "Get-Content data\sample.csv | Select-Object -First 4; '...'; Select-String -Path data\sample.csv -Pattern 'bot-1' | Select-Object -First 3 | ForEach-Object Line; '...'; Get-Content data\sample.csv | Select-Object -Last 3"
Step "2. Analyse: dedup, windows, spike flag, explanation"       "python spikesentry.py data\sample.csv"
Step "3. Offline HTML dashboard"                                  "python spikesentry.py data\sample.csv --html report.html *> $null; Start-Process report.html; 'opened report.html'"
Step "4. Invalid input is handled, not fatal"                     "'timestamp,request_id,client,endpoint','not-a-date,x1,c,/a','1000,,c,/a','1000,ok,c,/a' | python spikesentry.py - --min-count 1"
Step "5. Tests (normal / edge / invalid)"                         "python -m unittest discover -s tests -t . -v 2>&1 | Select-Object -Last 8"
Step "6. Validation vs. mean/stddev on 500 labeled synthetic series" "python evaluate.py"
Write-Host ""
Write-Host "Done. Finish on the README 'Known limitations' section." -ForegroundColor Green

