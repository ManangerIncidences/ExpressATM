@echo off
setlocal enabledelayedexpansion
echo.
echo ========================================
echo         ExpressATM - Inicio Inteligente
echo ========================================
echo.

REM ===== DETECCION AUTOMATICA =====
echo 🔍 Analizando tu instalacion...

set NEEDS_INSTALL=false
set NEEDS_UPDATE=false
set NEEDS_CHROMEDRIVER=false
set NEEDS_REPAIR=false
set CAN_RUN=true

REM ===== VERIFICAR PYTHON =====
REM Inicializar variables
set PYTHON_CMD=
set PYTHON_VERSION=

REM Probar 'python' primero
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_found
)

REM Probar 'python3'
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_found
)

REM Probar 'py' (Python Launcher)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_found
)

REM Python no encontrado
echo ❌ Python no detectado
set NEEDS_INSTALL=true
set CAN_RUN=false
goto :continue_checks

:python_found
echo ✅ Python %PYTHON_VERSION% encontrado (comando: %PYTHON_CMD%)

:continue_checks

REM Verificar entorno virtual
if not exist "venv\Scripts\python.exe" (
    echo ❌ Entorno virtual no existe
    set NEEDS_INSTALL=true
    set CAN_RUN=false
) else (
    venv\Scripts\python.exe --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Entorno virtual corrupto
        set NEEDS_REPAIR=true
        set CAN_RUN=false
    )
)

REM Verificar dependencias principales
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -c "import fastapi, pandas" >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Dependencias faltantes
        set NEEDS_INSTALL=true
        set CAN_RUN=false
    )
)

REM Verificar archivos principales
if not exist "run.py" (
    echo ❌ Archivos principales faltantes
    set NEEDS_UPDATE=true
    set CAN_RUN=false
)

REM Verificar ChromeDriver
if not exist "drivers\chromedriver.exe" (
    echo ⚠️  ChromeDriver no encontrado
    set NEEDS_CHROMEDRIVER=true
) else (
    drivers\chromedriver.exe --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ⚠️  ChromeDriver corrupto
        set NEEDS_CHROMEDRIVER=true
    )
)

REM Verificar actualizaciones (si hay Git)
git --version >nul 2>&1
if %errorlevel% equ 0 (
    if exist ".git" (
        git fetch origin main >nul 2>&1
        if %errorlevel% equ 0 (
            for /f %%i in ('git rev-list HEAD..origin/main --count 2^>nul') do set UPDATE_COUNT=%%i
            if not "!UPDATE_COUNT!"=="" if !UPDATE_COUNT! gtr 0 (
                echo 🆕 !UPDATE_COUNT! actualizaciones disponibles
                set NEEDS_UPDATE=true
            )
        )
    )
)

echo.
echo ========================================
echo           DIAGNOSTICO COMPLETO
echo ========================================

REM ===== MOSTRAR RECOMENDACIONES =====
if "%CAN_RUN%"=="true" (
    echo.
    echo ✅ ¡TU INSTALACION ESTA LISTA!
    echo.
    if "%NEEDS_CHROMEDRIVER%"=="true" (
        echo ⚠️  Recomendacion: Instalar ChromeDriver para scraping completo
    )
    if "%NEEDS_UPDATE%"=="true" (
        echo 🆕 Hay actualizaciones disponibles
    )
    echo.
    echo 🚀 OPCIONES DISPONIBLES:
    echo    [1] Ejecutar ExpressATM ahora
    if "%NEEDS_CHROMEDRIVER%"=="true" echo    [2] Instalar ChromeDriver primero
    if "%NEEDS_UPDATE%"=="true" echo    [3] Actualizar sistema
    echo    [4] Abrir Centro de Control
    echo    [0] Salir
    echo.
    set /p CHOICE="Que deseas hacer? (1-4, 0): "
    
    if "!CHOICE!"=="1" goto RUN_NOW
    if "!CHOICE!"=="2" goto INSTALL_CHROMEDRIVER
    if "!CHOICE!"=="3" goto UPDATE_NOW
    if "!CHOICE!"=="4" goto CONTROL_CENTER
    if "!CHOICE!"=="0" goto EXIT
    
) else (
    echo.
    echo ❌ TU INSTALACION NECESITA ATENCION
    echo.
    echo 🔧 ACCIONES REQUERIDAS:
    if "%NEEDS_INSTALL%"=="true" echo    • Instalacion completa necesaria
    if "%NEEDS_REPAIR%"=="true" echo    • Reparacion de entorno virtual
    if "%NEEDS_UPDATE%"=="true" echo    • Actualizacion de archivos
    echo.
    echo 💡 SOLUCIONES AUTOMATICAS:
    echo    [1] Instalacion Completa      (Recomendado)
    echo    [2] Reparar Instalacion      (Si ya tenias ExpressATM)
    echo    [3] Solo Actualizar          (Si falta algo menor)
    echo    [4] Centro de Control        (Opciones avanzadas)
    echo    [0] Salir
    echo.
    set /p CHOICE="Que solucion prefieres? (1-4, 0): "
    
    if "!CHOICE!"=="1" goto INSTALL_COMPLETE
    if "!CHOICE!"=="2" goto REPAIR_INSTALL
    if "!CHOICE!"=="3" goto UPDATE_NOW
    if "!CHOICE!"=="4" goto CONTROL_CENTER
    if "!CHOICE!"=="0" goto EXIT
)

echo ❌ Opcion invalida
timeout /t 2 >nul
goto START

:RUN_NOW
echo.
echo 🚀 Iniciando ExpressATM...
echo.
echo    🌐 Panel Principal: http://localhost:8000
echo    📊 Dashboard: http://localhost:8000/dashboard
echo    🧠 Analisis IA: http://localhost:8000/ai
echo.
echo Presiona Ctrl+C para detener el servidor
echo.
timeout /t 3 /nobreak >nul
call run.bat
goto EXIT

:INSTALL_CHROMEDRIVER
echo.
echo 🌐 Instalando ChromeDriver...
call update_chromedriver.bat
echo.
echo ✅ ChromeDriver instalado. ¿Ejecutar ExpressATM ahora? (S/N)
set /p RUN_AFTER="Respuesta: "
if /i "!RUN_AFTER!"=="S" goto RUN_NOW
goto EXIT

:UPDATE_NOW
echo.
echo 🔄 Actualizando sistema...
call update.bat
echo.
echo ✅ Sistema actualizado. ¿Ejecutar ExpressATM ahora? (S/N)
set /p RUN_AFTER="Respuesta: "
if /i "!RUN_AFTER!"=="S" goto RUN_NOW
goto EXIT

:INSTALL_COMPLETE
echo.
echo 🚀 Iniciando Instalacion Completa...
call install_complete.bat
goto EXIT

:REPAIR_INSTALL
echo.
echo 🔧 Iniciando Reparacion...
call repair_installation.bat
echo.
echo ✅ Reparacion completada. ¿Ejecutar ExpressATM ahora? (S/N)
set /p RUN_AFTER="Respuesta: "
if /i "!RUN_AFTER!"=="S" goto RUN_NOW
goto EXIT

:CONTROL_CENTER
echo.
call express_control.bat
goto EXIT

:EXIT
echo.
echo 👋 ¡Gracias por usar ExpressATM!
echo.
pause
exit /b 0
