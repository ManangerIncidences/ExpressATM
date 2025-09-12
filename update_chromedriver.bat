@echo off
setlocal
echo.
echo ========================================
echo  ExpressATM - Actualizacion ChromeDriver
echo ========================================
echo.

REM Preferir Python del entorno virtual si existe
set "VENV_PY=venv\Scripts\python.exe"
set "PY_CMD="

if exist "%VENV_PY%" (
    set "PY_CMD=%VENV_PY%"
) else (
    python --version >nul 2>&1 && set "PY_CMD=python"
    if not defined PY_CMD (
        py --version >nul 2>&1 && set "PY_CMD=py"
    )
)

if not defined PY_CMD (
    echo ❌ Python no encontrado. Instala/ejecuta la instalacion completa primero.
    pause
    exit /b 1
)

echo � Instalando/actualizando ChromeDriver con webdriver-manager...
"%PY_CMD%" scripts\setup_chromedriver.py
if errorlevel 1 (
    echo ❌ Fallo la actualizacion de ChromeDriver.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ CHROMEDRIVER ACTUALIZADO EXITOSAMENTE
echo ========================================
echo.
echo 🚀 Para probar: run.bat
echo.
pause
