# FinPulse local development launcher for Windows PowerShell
# Run from anywhere: .\run-dev.ps1 (when at the project root)
$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host 'FinPulse backend environment is not set up yet.' -ForegroundColor Yellow
    Write-Host 'From the FinPulse root, run:'
    Write-Host '  cd backend'
    Write-Host '  py -3.12 -m venv .venv'
    Write-Host '  .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $frontend 'node_modules'))) {
    Write-Host 'FinPulse frontend dependencies are not installed.' -ForegroundColor Yellow
    Write-Host 'From the FinPulse root, run:'
    Write-Host '  cd frontend'
    Write-Host '  npm install'
    exit 1
}

if (-not (Get-Command 'npm.cmd' -ErrorAction SilentlyContinue)) {
    Write-Host 'npm was not found. Install Node.js or reopen PowerShell after installation.' -ForegroundColor Red
    exit 1
}

Write-Host 'Starting FinPulse...' -ForegroundColor Cyan
Start-Process -FilePath 'powershell.exe' -WorkingDirectory $backend -ArgumentList '-NoExit -Command .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000'
Start-Process -FilePath 'powershell.exe' -WorkingDirectory $frontend -ArgumentList '-NoExit -Command npm.cmd run dev'

Write-Host 'Backend:  http://127.0.0.1:8000' -ForegroundColor Green
Write-Host 'Frontend: http://localhost:5173' -ForegroundColor Green
Write-Host 'Keep the two new terminal windows open. Use Ctrl+C in each to stop.'
