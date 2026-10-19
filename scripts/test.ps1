# Everything CI runs, in the same order, so a green run here means a green run
# there. Windows.
#
#   ./scripts/test.ps1           everything present in this checkout
#   ./scripts/test.ps1 -Quick    skip the frontend build, which is the slow part

param([switch]$Quick)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$failures = @()

function Invoke-Step {
    param([string]$Name, [scriptblock]$Body)

    Write-Output ''
    Write-Output "--- $Name"
    # Plain invocation: a native command's stdout goes to the pipeline, and so
    # does Write-Output above it, so the header and the output it labels stay
    # in order even when the whole script is piped to a log. Write-Host and
    # Out-Host both bypass the pipeline and split them into two streams.
    & $Body
    if ($LASTEXITCODE -ne 0) {
        $script:failures += $Name
        Write-Output "FAILED: $Name"
    }
}

$backend = Join-Path $root 'backend\.venv\Scripts\python.exe'
$ml = Join-Path $root 'ml\.venv\Scripts\python.exe'

if (-not (Test-Path $backend) -or -not (Test-Path $ml)) {
    throw 'Virtualenvs are missing. Run ./scripts/setup.ps1 first.'
}

# Lint before tests: an import-order complaint should not wait behind a
# four-minute suite.
Invoke-Step 'lint backend' { Push-Location (Join-Path $root 'backend'); & $ml -m ruff check app tests; Pop-Location }
Invoke-Step 'lint ml' { Push-Location (Join-Path $root 'ml'); & $ml -m ruff check teasmart_ml tests; Pop-Location }
Invoke-Step 'test backend' { Push-Location (Join-Path $root 'backend'); & $backend -m pytest -q; Pop-Location }
Invoke-Step 'test ml' { Push-Location (Join-Path $root 'ml'); & $ml -m pytest -q; Pop-Location }

if (Test-Path (Join-Path $root 'frontend\package.json')) {
    Invoke-Step 'test frontend' { Push-Location (Join-Path $root 'frontend'); npm test --silent; Pop-Location }
    if (-not $Quick) {
        Invoke-Step 'build frontend' { Push-Location (Join-Path $root 'frontend'); npm run build; Pop-Location }
    }
}

Write-Output ''
if ($failures.Count -gt 0) {
    Write-Output ("FAILED: " + ($failures -join ', '))
    exit 1
}
Write-Output 'All green.'
