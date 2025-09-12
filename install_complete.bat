@echo off
setlocal enabledelayedexpansion
echo.
echo ========================================
echo    ExpressATM - Instalador Universal
echo ========================================
echo.
echo 🎯 Este script realiza TODA la instalacion automaticamente:
echo    ✅ Verificacion del sistema
echo    ✅ Creacion de entorno virtual
echo    ✅ Instalacion de dependencias
echo    ✅ Configuracion de ChromeDriver
echo    ✅ Verificacion final
echo    ✅ Prueba de funcionamiento
echo.
echo ⏱️  Tiempo estimado: 3-7 minutos
echo.
set /p CONTINUE="¿Continuar con la instalacion completa? (S/N): "
if /i not "%CONTINUE%"=="S" (
    echo ❌ Instalacion cancelada
    pause
    exit /b 0
)

echo.
echo ==========================================
echo    FASE 1: VERIFICACION DEL SISTEMA
echo ==========================================

REM ===== VERIFICAR PYTHON =====
echo.
echo 🔍 [1/8] Verificando Python...

REM Probar diferentes comandos de Python
set PYTHON_CMD=
set PYTHON_VERSION=

REM Probar 'python'
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto python_found
)

REM Probar 'python3'
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto python_found
)

REM Probar 'py' (Python Launcher)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto python_found
)

REM Intentar localizar python por ruta exacta (where)
for /f "delims=" %%p in ('where python 2^>nul') do (
    if not defined PYTHON_CMD (
        set "PYTHON_CMD=%%p"
        for /f "tokens=2" %%i in ('"%%p" --version 2^>^&1') do set PYTHON_VERSION=%%i
        goto python_found
    )
)

for /f "delims=" %%p in ('where python3 2^>nul') do (
    if not defined PYTHON_CMD (
        set "PYTHON_CMD=%%p"
        for /f "tokens=2" %%i in ('"%%p" --version 2^>^&1') do set PYTHON_VERSION=%%i
        goto python_found
    )
)

REM Intentar localizar python desde el registro (PowerShell)
for /f "usebackq delims=" %%p in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$keys=@('HKLM:\\SOFTWARE\\Python\\PythonCore','HKCU:\\SOFTWARE\\Python\\PythonCore','HKLM:\\SOFTWARE\\WOW6432Node\\Python\\PythonCore'); foreach($k in $keys){ if(Test-Path $k){ $v=Get-ChildItem $k | Sort-Object -Property PSChildName -Descending | Select-Object -First 1; if($v){ $ip=(Get-ItemProperty $v.PSPath -Name InstallPath -ErrorAction SilentlyContinue).InstallPath; if($ip){ $exe=Join-Path $ip 'python.exe'; if(Test-Path $exe){ Write-Output $exe; break } } } } }" 2^>^&1` ) do (
    if not defined PYTHON_CMD (
        set "PYTHON_CMD=%%p"
        for /f "tokens=2" %%i in ('"%%p" --version 2^>^&1') do set PYTHON_VERSION=%%i
        goto python_found
    )
)

REM Python no encontrado
echo ❌ ERROR: Python no esta instalado o no esta en PATH
echo.
echo 🔧 SOLUCION REQUERIDA:
echo 1. Instalar Python 3.8+ desde: https://python.org/downloads
echo 2. ✅ IMPORTANTE: Marcar "Add Python to PATH" durante instalacion
echo 3. Reiniciar PC
echo 4. Ejecutar este script nuevamente
echo.
echo 💡 ALTERNATIVA - Verificar instalacion existente:
echo    • Buscar "python.exe" en tu PC
echo    • Agregar carpeta a PATH manualmente
echo    • O reinstalar Python con opcion PATH marcada
echo.
pause
exit /b 1

:python_found
echo ✅ Python %PYTHON_VERSION% encontrado (comando/ruta: %PYTHON_CMD%)

REM ===== VERIFICAR GIT (opcional) =====
echo.
echo 🔍 [2/8] Verificando Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Git no encontrado (opcional)
    echo 💡 Para actualizaciones automaticas instalar desde: https://git-scm.com
    set GIT_AVAILABLE=false
) else (
    echo ✅ Git disponible
    set GIT_AVAILABLE=true
)

REM ===== VERIFICAR CHROME =====
echo.
echo 🔍 [3/8] Verificando Google Chrome...
set CHROME_PATH=""
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if %CHROME_PATH%=="" (
    echo ⚠️  Google Chrome no encontrado
    echo 💡 RECOMENDACION: Instalar Chrome desde https://www.google.com/chrome/
    echo    (El scraping funcionara con limitaciones)
    set CHROME_AVAILABLE=false
) else (
    echo ✅ Chrome encontrado en: %CHROME_PATH%
    set CHROME_AVAILABLE=true
)

echo.
echo ==========================================
echo    FASE 2: PREPARACION DEL ENTORNO
echo ==========================================

REM ===== LIMPIAR ENTORNO VIRTUAL CORRUPTO =====
echo.
echo 🧹 [4/8] Preparando entorno virtual...
if exist "venv" (
    echo Eliminando entorno virtual existente (puede tener rutas incorrectas)
    rmdir /S /Q venv
    if %errorlevel% neq 0 (
        echo ⚠️  No se pudo eliminar completamente, continuando
    )
)

echo ✅ Creando nuevo entorno virtual
"%PYTHON_CMD%" -m venv venv
if %errorlevel% neq 0 (
    echo ❌ ERROR: No se pudo crear entorno virtual
    echo 💡 Verifica que Python este correctamente instalado
    pause
    exit /b 1
)

echo ✅ Activando entorno virtual...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ ERROR: No se pudo activar entorno virtual
    pause
    exit /b 1
)

REM Siempre usar el Python del entorno virtual para instalar y ejecutar
set "VENV_PY=venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo ❌ ERROR: Python del entorno virtual no encontrado
    pause
    exit /b 1
)

REM Preparar carpeta de logs
if not exist "logs" mkdir logs >nul 2>&1
set "INSTALL_LOG=logs\install_pip.log"
echo. > "%INSTALL_LOG%"

echo.
echo ==========================================
echo    FASE 3: INSTALACION DE DEPENDENCIAS
echo ==========================================

REM ===== ACTUALIZAR PIP =====
echo.
echo 📦 [5/8] Actualizando pip...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel --quiet >> "%INSTALL_LOG%" 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Advertencia: No se pudo actualizar pip/setuptools/wheel, continuando
)

REM ===== INSTALAR DEPENDENCIAS =====
echo.
echo 📚 [6/8] Instalando dependencias de ExpressATM...
echo    (Esto puede tomar 2-3 minutos)

if not exist "requirements.txt" (
    echo ❌ ERROR: requirements.txt no encontrado
    echo 💡 Verifica que estas en el directorio correcto de ExpressATM
    pause
    exit /b 1
)

REM Pre-instalar paquetes pesados con binarios (evitar compilaciones)
"%VENV_PY%" -m pip install --only-binary :all: numpy -q >> "%INSTALL_LOG%" 2>&1
"%VENV_PY%" -m pip install --only-binary :all: scikit-learn -q >> "%INSTALL_LOG%" 2>&1

REM Instalar el resto de dependencias
"%VENV_PY%" -m pip install -r requirements.txt --quiet >> "%INSTALL_LOG%" 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR instalando dependencias
    echo.
    echo 🔧 Intentando instalacion de dependencias criticas
    "%VENV_PY%" -m pip install fastapi uvicorn pandas selenium numpy sqlalchemy --quiet >> "%INSTALL_LOG%" 2>&1
    
    echo 🔄 Reintentando instalacion completa (salida en %INSTALL_LOG%)
    "%VENV_PY%" -m pip install -r requirements.txt >> "%INSTALL_LOG%" 2>&1
    
    if %errorlevel% neq 0 (
        echo ❌ ERROR: No se pudieron instalar todas las dependencias
        echo 📄 Revisa el log: %INSTALL_LOG%
        echo 💡 Revisa tu conexion a internet y intenta nuevamente
        pause
        exit /b 1
    )
)

echo ✅ Dependencias instaladas exitosamente

REM Comprobar integridad de dependencias
"%VENV_PY%" -m pip check >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Se detectaron conflictos de dependencias (ver %INSTALL_LOG%)
)

REM ===== VERIFICAR DEPENDENCIAS CRITICAS =====
echo.
echo 🧪 Verificando dependencias criticas...
"%VENV_PY%" -c "import fastapi, pandas, selenium, sklearn, sqlalchemy, uvicorn, jinja2, apscheduler, psutil, numpy, openpyxl, fpdf; print('OK')" 1>nul 2>>"%INSTALL_LOG%"
if %errorlevel% neq 0 (
    echo ⚠️  Algunas dependencias pueden faltar, pero continuando
)

echo.
echo ==========================================
echo    FASE 4: CONFIGURACION DE CHROMEDRIVER
echo ==========================================

REM ===== INSTALAR CHROMEDRIVER (webdriver-manager) =====
echo.
echo 🌐 [7/8] Configurando ChromeDriver con webdriver-manager...

if not exist "drivers" mkdir drivers

"%VENV_PY%" scripts\setup_chromedriver.py
if %errorlevel% neq 0 (
    echo ⚠️  No se pudo instalar ChromeDriver automaticamente. Puedes reintentar luego con update_chromedriver.bat
)

echo.
echo ==========================================
echo    FASE 5: VERIFICACION FINAL
echo ==========================================

REM ===== VERIFICAR INSTALACION =====
echo.
echo 🔍 [8/8] Verificando instalacion completa...

echo.
echo 📍 Archivos principales:
if exist "run.py" (echo    ✅ run.py) else (echo    ❌ run.py FALTANTE)
if exist "requirements.txt" (echo    ✅ requirements.txt) else (echo    ❌ requirements.txt FALTANTE)  
if exist "backend\app\main.py" (echo    ✅ backend\app\main.py) else (echo    ❌ backend\app\main.py FALTANTE)

echo.
echo 📍 Entorno virtual:
"%VENV_PY%" --version 2>nul
if %errorlevel% equ 0 (
    echo    ✅ Entorno virtual funcional
) else (
    echo    ❌ Problemas con entorno virtual
)

echo.
echo 📍 ChromeDriver:
if exist "drivers\chromedriver.exe" (
    drivers\chromedriver.exe --version 2>nul
    if %errorlevel% equ 0 (
        echo    ✅ ChromeDriver funcional
    ) else (
        echo    ⚠️  ChromeDriver presente pero puede tener problemas
    )
) else (
    echo    ⚠️  ChromeDriver no instalado
)

REM ===== CREAR ACCESO DIRECTO =====
echo.
echo 🖥️  Creando acceso directo en escritorio
set "scriptPath=%~dp0run.bat"
set "desktopPath=%USERPROFILE%\Desktop"
set "shortcutPath=%desktopPath%\ExpressATM.lnk"

powershell -command "& {try { $WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%shortcutPath%'); $Shortcut.TargetPath = '%scriptPath%'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = 'ExpressATM - Sistema de Monitoreo'; $Shortcut.Save(); Write-Host '✅ Acceso directo creado' } catch { Write-Host '⚠️ No se pudo crear acceso directo' }}"

echo.
echo ==========================================
echo           INSTALACION COMPLETADA
echo ==========================================
echo.
echo 🎉 ¡ExpressATM instalado exitosamente!
echo.
echo 🚀 FORMAS DE EJECUTAR:
echo    1. Doble clic en "ExpressATM" en el escritorio
echo    2. Ejecutar: run.bat
echo    3. Comando: "%VENV_PY%" run.py
echo.
echo 🌐 ACCESO WEB (despues de ejecutar):
echo    • Panel Principal: http://localhost:8000
echo    • Dashboard: http://localhost:8000/dashboard
echo    • Analisis IA: http://localhost:8000/ai
echo.
echo 💡 SCRIPTS UTILES:
echo    • update.bat           - Actualizar desde GitHub
echo    • check_updates.bat    - Verificar actualizaciones
echo    • check_system.bat     - Diagnosticar problemas
echo.
echo 📚 DOCUMENTACION:
echo    • README.md            - Guia principal
echo    • INSTALACION_EQUIPO.md - Guia del equipo
echo    • ACTUALIZACION.md     - Guia de actualizacion
echo.

REM ===== PROBAR EJECUCION =====
echo.
set /p TEST_RUN="¿Probar ExpressATM ahora? (S/N): "
if /i "%TEST_RUN%"=="S" (
    echo.
    echo 🚀 Iniciando ExpressATM
    echo    (Se abrira en el navegador automaticamente)
    echo    (Presiona Ctrl+C para detener)
    echo.
    timeout /t 3 /nobreak >nul
    "%VENV_PY%" run.py
) else (
    echo.
    echo ✅ Instalacion completa. Para ejecutar usa: run.bat
)

echo.
pause
