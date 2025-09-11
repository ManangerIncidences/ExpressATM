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
echo ⏱️  Tiempo estimado: 3-5 minutos
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
echo ✅ Python %PYTHON_VERSION% encontrado (comando: %PYTHON_CMD%)

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
%PYTHON_CMD% -m venv venv
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

echo.
echo ==========================================
echo    FASE 3: INSTALACION DE DEPENDENCIAS
echo ==========================================

REM ===== ACTUALIZAR PIP =====
echo.
echo 📦 [5/8] Actualizando pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo ⚠️  Advertencia: No se pudo actualizar pip, continuando
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

%PYTHON_CMD% -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ❌ ERROR instalando dependencias
    echo.
    echo 🔧 Intentando instalacion de dependencias criticas
    %PYTHON_CMD% -m pip install fastapi uvicorn pandas selenium numpy sqlalchemy --quiet
    
    echo 🔄 Reintentando instalacion completa
    %PYTHON_CMD% -m pip install -r requirements.txt
    
    if %errorlevel% neq 0 (
        echo ❌ ERROR: No se pudieron instalar todas las dependencias
        echo 💡 Revisa tu conexion a internet y intenta nuevamente
        pause
        exit /b 1
    )
)

echo ✅ Dependencias instaladas exitosamente

REM ===== VERIFICAR DEPENDENCIAS CRITICAS =====
echo.
echo 🧪 Verificando dependencias criticas...
%PYTHON_CMD% -c "import fastapi, pandas, selenium; print('✅ Dependencias principales verificadas')" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  Algunas dependencias pueden faltar, pero continuando
)

echo.
echo ==========================================
echo    FASE 4: CONFIGURACION DE CHROMEDRIVER
echo ==========================================

REM ===== INSTALAR CHROMEDRIVER =====
echo.
echo 🌐 [7/8] Configurando ChromeDriver...

if not exist "drivers" mkdir drivers

if "%CHROME_AVAILABLE%"=="true" (
    echo 📥 Descargando ChromeDriver automaticamente
    
    REM Obtener version de Chrome
    for /f "tokens=*" %%i in ('powershell -command "& {(Get-ItemProperty '%CHROME_PATH%').VersionInfo.ProductVersion}"') do set CHROME_VERSION=%%i
    
    if not "!CHROME_VERSION!"=="" (
        for /f "tokens=1 delims=." %%a in ("!CHROME_VERSION!") do set CHROME_MAJOR=%%a
        echo 📍 Detectada version Chrome: !CHROME_VERSION! (Principal: !CHROME_MAJOR!)
        
        REM Descargar ChromeDriver
        powershell -command "& {try { $latest = Invoke-RestMethod -Uri 'https://chromedriver.storage.googleapis.com/LATEST_RELEASE_!CHROME_MAJOR!' -ErrorAction Stop; $url = 'https://chromedriver.storage.googleapis.com/' + $latest + '/chromedriver_win32.zip'; Invoke-WebRequest -Uri $url -OutFile 'drivers\chromedriver.zip' -ErrorAction Stop; Expand-Archive -Path 'drivers\chromedriver.zip' -DestinationPath 'drivers\' -Force; Remove-Item 'drivers\chromedriver.zip' -Force; Write-Host '✅ ChromeDriver instalado exitosamente' } catch { Write-Host '❌ Error:', $_.Exception.Message; exit 1 }}"
        
        if %errorlevel% equ 0 (
            echo ✅ ChromeDriver configurado exitosamente
        ) else (
            echo ⚠️  Error descargando ChromeDriver automaticamente
            echo 💡 El scraping puede fallar, instalar manualmente desde: https://chromedriver.chromium.org
        )
    ) else (
        echo ⚠️  No se pudo detectar version de Chrome
        echo 💡 ChromeDriver se puede instalar manualmente despues
    )
) else (
    echo ⚠️  Chrome no detectado, saltando instalacion de ChromeDriver
    echo 💡 Para scraping, instalar Chrome y ejecutar: update_chromedriver.bat
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
venv\Scripts\python.exe --version 2>nul
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
echo    3. Comando: %PYTHON_CMD% run.py
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
    %PYTHON_CMD% run.py
) else (
    echo.
    echo ✅ Instalacion completa. Para ejecutar usa: run.bat
)

echo.
pause
