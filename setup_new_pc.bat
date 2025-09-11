@echo off
echo.
echo ========================================
echo  ExpressATM - Instalacion Nueva PC
echo ========================================
echo.

REM Verificar si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python no esta instalado
    echo.
    echo 🔧 SOLUCION:
    echo 1. Ir a: https://python.org/downloads
    echo 2. Descargar Python 3.8+
    echo 3. ✅ Marcar "Add Python to PATH"
    echo 4. Instalar y reiniciar PC
    echo 5. Ejecutar este script de nuevo
    echo.
    pause
    exit /b 1
)

echo ✅ Python detectado
python --version

REM Verificar si Git esta instalado
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Git no detectado - usando descarga manual
    echo 📥 Por favor descarga el proyecto desde:
    echo https://github.com/ManangerIncidences/ExpressATM
    echo.
    echo 1. Clic en "Code" ^> "Download ZIP"
    echo 2. Extraer en esta carpeta
    echo 3. Ejecutar install.bat
    echo.
    pause
    exit /b 1
)

echo ✅ Git detectado
git --version

REM Clonar o actualizar repositorio
if exist ".git" (
    echo.
    echo 🔄 Actualizando proyecto existente...
    git pull origin main
) else (
    echo.
    echo 📥 Descargando ExpressATM desde GitHub...
    git clone https://github.com/ManangerIncidences/ExpressATM.git temp_download
    if %errorlevel% neq 0 (
        echo ❌ Error al descargar desde GitHub
        echo Verifica tu conexion a internet
        pause
        exit /b 1
    )
    
    echo 📁 Moviendo archivos...
    xcopy "temp_download\*" "." /E /Y /Q
    rmdir "temp_download" /S /Q
    
    echo ✅ Proyecto descargado exitosamente
)

REM Verificar archivo requirements.txt
if not exist "requirements.txt" (
    echo ❌ Error: requirements.txt no encontrado
    echo El proyecto no se descargo correctamente
    pause
    exit /b 1
)

REM Limpiar entorno virtual existente si existe (puede tener rutas incorrectas)
if exist "venv" (
    echo.
    echo 🧹 Limpiando entorno virtual existente...
    rmdir /S /Q venv
)

echo.
echo 🔧 Creando nuevo entorno virtual...
python -m venv venv

echo ✅ Activando entorno virtual...
call venv\Scripts\activate.bat

echo 🔧 Instalando dependencias de Python...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error instalando dependencias
    echo 🔧 Intentando solucion alternativa...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)

REM Verificar e instalar ChromeDriver
echo.
echo 🌐 Configurando ChromeDriver...
if exist "drivers\chromedriver.exe" (
    echo ✅ ChromeDriver ya existe
    drivers\chromedriver.exe --version 2>nul
    if %errorlevel% neq 0 (
        echo ⚠️  ChromeDriver corrupto, reinstalando...
        call update_chromedriver.bat
    ) else (
        echo ✅ ChromeDriver funcional
    )
) else (
    echo 📥 Instalando ChromeDriver...
    if exist "update_chromedriver.bat" (
        call update_chromedriver.bat
    ) else (
        echo ❌ update_chromedriver.bat no encontrado
        echo 💡 Descargar manualmente ChromeDriver desde: https://chromedriver.chromium.org/
    )
)

REM Crear acceso directo en escritorio
echo.
echo 🖥️  Creando acceso directo en escritorio...
set "scriptPath=%~dp0run.bat"
set "desktopPath=%USERPROFILE%\Desktop"
set "shortcutPath=%desktopPath%\ExpressATM.lnk"

powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%shortcutPath%'); $Shortcut.TargetPath = '%scriptPath%'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.IconLocation = '%~dp0frontend\logos\imag_logo.ico'; $Shortcut.Description = 'ExpressATM - Sistema de Monitoreo'; $Shortcut.Save()}"

echo.
echo ========================================
echo ✅ INSTALACION COMPLETADA EXITOSAMENTE
echo ========================================
echo.
echo 🚀 Para ejecutar ExpressATM:
echo.
echo Opcion 1: Doble clic en "ExpressATM" en el escritorio
echo Opcion 2: Ejecutar "run.bat" en esta carpeta
echo Opcion 3: Abrir navegador en http://localhost:8000
echo.
echo 📊 Para sincronizar datos del equipo:
echo - sync_data.bat    (antes de trabajar)
echo - update_data.bat  (despues de trabajar)
echo.
echo 📖 Documentacion completa: INSTALACION_EQUIPO.md
echo.
pause
