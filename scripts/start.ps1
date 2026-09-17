param([switch]$Dev, [switch]$Hosted)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run uv sync --extra voice first.' }
if ($Dev) {
    Write-Host 'Start the frontend in another terminal: cd frontend; npm run dev'
} elseif (-not $Hosted -and -not (Test-Path 'frontend\dist\index.html')) {
    throw 'Build the frontend first: cd frontend; npm ci; npm run build'
}
& '.venv\Scripts\python.exe' -m uvicorn localvoiceai.app:app --host 127.0.0.1 --port 8017 --ws-max-size 65536
