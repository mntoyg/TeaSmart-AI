# One command to get a working checkout. Windows.
#
#   ./scripts/setup.ps1          GPU build of torch (needs an NVIDIA card)
#   ./scripts/setup.ps1 -Cpu     CPU build, which is all the tests need
#
# Two virtualenvs on purpose: the API has no reason to carry torch, and the ML
# package has no reason to carry FastAPI. They are never activated - every
# command goes through the interpreter path explicitly, so there is no
# "which venv am I in" failure mode.

param([switch]$Cpu)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

$torchIndex = if ($Cpu) {
    'https://download.pytorch.org/whl/cpu'
} else {
    'https://download.pytorch.org/whl/cu124'
}

function Initialize-Venv {
    param([string]$Package, [string[]]$ExtraArgs = @())

    $dir = Join-Path $root $Package
    $python = Join-Path $dir '.venv\Scripts\python.exe'

    if (-not (Test-Path $python)) {
        Write-Output "creating $Package/.venv"
        python -m venv (Join-Path $dir '.venv')
    }
    & $python -m pip install --quiet --upgrade pip
    & $python -m pip install --quiet -r (Join-Path $dir 'requirements.txt') @ExtraArgs
    if ($LASTEXITCODE -ne 0) { throw "$Package dependencies failed" }
    Write-Output "$Package ready"
}

Initialize-Venv -Package 'backend'
Initialize-Venv -Package 'ml' -ExtraArgs @('--extra-index-url', $torchIndex)

if (Test-Path (Join-Path $root 'frontend\package.json')) {
    Push-Location (Join-Path $root 'frontend')
    try {
        if (Test-Path 'package-lock.json') { npm ci } else { npm install }
        Write-Output 'frontend ready'
    } finally { Pop-Location }
} else {
    Write-Output 'frontend not in this checkout; skipping'
}

Write-Output ''
Write-Output 'Done. Next: ./scripts/test.ps1'
