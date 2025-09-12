<#
ExpressATM - Actualizador de ChromeDriver (PowerShell)
Ahora delega en webdriver-manager vía script Python para asegurar compatibilidad.
#>

Write-Host ""; Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ExpressATM - Actualización ChromeDriver" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan; Write-Host ""

$venvPy = Join-Path (Join-Path (Get-Location) "venv") "Scripts/python.exe"
$pyCmd = $null
if (Test-Path $venvPy) {
    $pyCmd = $venvPy
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyCmd = "py"
}

if (-not $pyCmd) {
    Write-Host "❌ Python no encontrado. Ejecuta la instalación completa primero." -ForegroundColor Red
    Read-Host "Presiona Enter para continuar" | Out-Null
    exit 1
}

Write-Host "🔄 Instalando/actualizando ChromeDriver con webdriver-manager..." -ForegroundColor Yellow
& $pyCmd "scripts/setup_chromedriver.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Falló la actualización de ChromeDriver." -ForegroundColor Red
    Read-Host "Presiona Enter para continuar" | Out-Null
    exit $LASTEXITCODE
}

Write-Host ""; Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ CHROMEDRIVER ACTUALIZADO EXITOSAMENTE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green; Write-Host ""
Write-Host "🚀 Para probar: run.bat" -ForegroundColor Cyan
Read-Host "Presiona Enter para continuar" | Out-Null
