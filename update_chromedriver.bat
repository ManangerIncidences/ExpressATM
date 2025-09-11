@echo off
echo.
echo ========================================
echo  ExpressATM - Actualizacion ChromeDriver
echo ========================================
echo.

REM Crear directorio drivers si no existe
if not exist "drivers" mkdir drivers

echo 🔍 Detectando version de Chrome instalada...

REM Buscar Chrome en ubicaciones comunes
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
    echo ❌ Google Chrome no encontrado
    echo.
    echo 💡 SOLUCION:
    echo 1. Instalar Google Chrome desde: https://www.google.com/chrome/
    echo 2. Ejecutar este script nuevamente
    echo.
    pause
    exit /b 1
)

echo ✅ Chrome encontrado en: %CHROME_PATH%

REM Obtener version de Chrome
for /f "tokens=*" %%i in ('powershell -command "& {(Get-ItemProperty '%CHROME_PATH%').VersionInfo.ProductVersion}"') do set CHROME_VERSION=%%i

if "%CHROME_VERSION%"=="" (
    echo ⚠️  No se pudo detectar la version de Chrome automaticamente
    echo 💡 Usando version mas reciente disponible...
    set CHROME_MAJOR=119
) else (
    echo ✅ Version de Chrome detectada: %CHROME_VERSION%
    for /f "tokens=1 delims=." %%a in ("%CHROME_VERSION%") do set CHROME_MAJOR=%%a
    echo 📍 Version principal: %CHROME_MAJOR%
)

echo.
echo 📥 Descargando ChromeDriver compatible...

REM URL de descarga de ChromeDriver
set CHROMEDRIVER_URL=https://chromedriver.storage.googleapis.com/LATEST_RELEASE_%CHROME_MAJOR%

REM Usar PowerShell para descargar
echo 🔄 Obteniendo version exacta de ChromeDriver...
powershell -command "& {try { $latest = Invoke-RestMethod -Uri '%CHROMEDRIVER_URL%' -ErrorAction Stop; Write-Host 'Version ChromeDriver:' $latest; $url = 'https://chromedriver.storage.googleapis.com/' + $latest + '/chromedriver_win32.zip'; Write-Host 'Descargando de:' $url; Invoke-WebRequest -Uri $url -OutFile 'drivers\chromedriver.zip' -ErrorAction Stop; Write-Host '✅ Descarga completada' } catch { Write-Host '❌ Error en descarga:', $_.Exception.Message; exit 1 }}"

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error descargando ChromeDriver automaticamente
    echo.
    echo 🔧 DESCARGA MANUAL:
    echo 1. Ir a: https://chromedriver.chromium.org/downloads
    echo 2. Descargar version compatible con Chrome %CHROME_MAJOR%
    echo 3. Extraer chromedriver.exe en carpeta: drivers\
    echo.
    pause
    exit /b 1
)

echo.
echo 📂 Extrayendo ChromeDriver...

REM Eliminar chromedriver existente
if exist "drivers\chromedriver.exe" del "drivers\chromedriver.exe"

REM Extraer con PowerShell
powershell -command "& {try { Expand-Archive -Path 'drivers\chromedriver.zip' -DestinationPath 'drivers\' -Force; Write-Host '✅ Extraccion completada' } catch { Write-Host '❌ Error extrayendo:', $_.Exception.Message; exit 1 }}"

if %errorlevel% neq 0 (
    echo ❌ Error extrayendo archivo ZIP
    echo 💡 Extrae manualmente chromedriver.zip en carpeta drivers\
    pause
    exit /b 1
)

REM Limpiar archivo ZIP
if exist "drivers\chromedriver.zip" del "drivers\chromedriver.zip"

REM Verificar instalacion
if exist "drivers\chromedriver.exe" (
    echo.
    echo ✅ ChromeDriver instalado exitosamente
    echo 📍 Ubicacion: drivers\chromedriver.exe
    
    REM Verificar version de ChromeDriver
    echo.
    echo 🔍 Verificando version de ChromeDriver...
    drivers\chromedriver.exe --version 2>nul
    if %errorlevel% equ 0 (
        echo ✅ ChromeDriver funcional
    ) else (
        echo ⚠️  ChromeDriver instalado pero puede tener problemas
    )
) else (
    echo ❌ Error: ChromeDriver no se instalo correctamente
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ CHROMEDRIVER ACTUALIZADO EXITOSAMENTE
echo ========================================
echo.
echo 🎉 ExpressATM ya puede realizar scraping
echo.
echo 🚀 Para probar:
echo    run.bat
echo.
pause
