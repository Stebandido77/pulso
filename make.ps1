# make.ps1 - PowerShell wrapper for Windows users.
# Usage: ./make.ps1 <target>   (e.g. ./make.ps1 test)

param([Parameter(Position=0)][string]$Target = "help")

function Invoke-SyncData {
    python scripts/sync_data.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Target) {
    "sync-data"   { Invoke-SyncData }
    "dev-install" { Invoke-SyncData; Set-Location python; pip install -e ".[dev]"; Set-Location .. }
    "test"        { Invoke-SyncData; Set-Location python; pytest -v; Set-Location .. }
    "test-r"      { Rscript scripts/sync_data_to_r.R; Set-Location r; Rscript -e "devtools::test()"; Set-Location .. }
    "lint"        { Set-Location python; ruff check pulso tests scripts; Set-Location .. }
    "format"      { Set-Location python; ruff format pulso tests scripts; Set-Location .. }
    "build"       { Invoke-SyncData; Set-Location python; python -m build; Set-Location .. }
    "clean"       {
        Remove-Item -Recurse -Force python/dist, python/build, python/*.egg-info -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force python/pulso/data, r/inst/extdata -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force r/.Rcheck, r/*.tar.gz -ErrorAction SilentlyContinue
    }
    "help"        {
        Write-Host "Targets: sync-data, dev-install, test, test-r, lint, format, build, clean"
    }
    default { Write-Host "Unknown target: $Target"; Write-Host "Run: ./make.ps1 help"; exit 1 }
}
