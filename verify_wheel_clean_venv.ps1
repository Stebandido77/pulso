# Crear venv limpio, instalar wheel, correr smoke test, limpiar.
# Uso: .\verify_wheel_clean_venv.ps1
$ErrorActionPreference = "Stop"
$cleanVenv = "$env:TEMP\test-rc2-$(Get-Random)"
$wheelPath = "dist\pulso_co-1.0.0rc2-py3-none-any.whl"

if (-not (Test-Path $wheelPath)) {
    Write-Host "ERROR: wheel no existe en $wheelPath" -ForegroundColor Red
    Write-Host "Construir con: python -m build" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Crear venv limpio en $cleanVenv ===" -ForegroundColor Cyan
python -m venv $cleanVenv

Write-Host ""
Write-Host "=== Activar venv limpio ===" -ForegroundColor Cyan
& "$cleanVenv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "=== Verificar venv limpio ===" -ForegroundColor Cyan
$installed = pip list 2>&1 | Select-String -Pattern "pulso"
if ($installed) {
    Write-Host "ERROR: el venv ya tiene pulso instalado" -ForegroundColor Red
    deactivate
    Remove-Item -Recurse -Force $cleanVenv
    exit 1
}
Write-Host "OK: venv limpio"

Write-Host ""
Write-Host "=== Instalar wheel: $wheelPath ===" -ForegroundColor Cyan
pip install $wheelPath

Write-Host ""
Write-Host "=== Smoke test ===" -ForegroundColor Cyan
# Copy the smoke script to TEMP and run it from there, so sys.path[0]
# is the temp directory (not the project root). Otherwise Python
# imports the source `pulso/` package next to the script instead of
# the installed wheel.
$smokeScriptSrc = (Resolve-Path "verify_wheel_smoke.py").Path
$smokeScriptDst = Join-Path $env:TEMP "verify_wheel_smoke_isolated.py"
Copy-Item $smokeScriptSrc $smokeScriptDst -Force
$savedCwd = Get-Location
Set-Location $env:TEMP
python $smokeScriptDst
$exitCode = $LASTEXITCODE
Set-Location $savedCwd
Remove-Item $smokeScriptDst -Force

Write-Host ""
Write-Host "=== Limpiar venv temporal ===" -ForegroundColor Cyan
deactivate
Remove-Item -Recurse -Force $cleanVenv

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "SMOKE TEST PASS" -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "SMOKE TEST FAIL" -ForegroundColor Red
    exit 1
}
