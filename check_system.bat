@echo off
echo.
echo ========================================
echo  ExpressATM - Verificacion de Sistema
echo ========================================
echo.

echo 🔍 Verificando componentes del sistema...
echo.

REM Verificar Python
echo 📍 Python:
python --version 2>nul
if %errorlevel% neq 0 (
    echo    ❌ Python NO encontrado
    echo    💡 Instalar desde: https://python.org
) else (
    echo    ✅ Python disponible
)

REM Verificar entorno virtual
echo.
echo 📍 Entorno Virtual:
if exist "venv\Scripts\python.exe" (
    echo    ✅ Entorno virtual existe
    
    REM Verificar si las rutas son correctas
    venv\Scripts\python.exe -c "import sys; print('   📂 Ruta:', sys.executable)" 2>nul
    if %errorlevel% neq 0 (
        echo    ❌ Entorno virtual corrupto (rutas incorrectas)
        echo    💡 Ejecutar: repair_installation.bat
    ) else (
        echo    ✅ Entorno virtual funcional
    )
) else (
    echo    ❌ Entorno virtual NO existe
    echo    💡 Ejecutar: install.bat
)

REM Verificar dependencias principales
echo.
echo 📍 Dependencias Python:
if exist "venv\Scripts\python.exe" (
    echo    Verificando FastAPI...
    venv\Scripts\python.exe -c "import fastapi; print('   ✅ FastAPI:', fastapi.__version__)" 2>nul
    if %errorlevel% neq 0 echo    ❌ FastAPI no instalado
    
    echo    Verificando Pandas...
    venv\Scripts\python.exe -c "import pandas; print('   ✅ Pandas:', pandas.__version__)" 2>nul
    if %errorlevel% neq 0 echo    ❌ Pandas no instalado
    
    echo    Verificando Selenium...
    venv\Scripts\python.exe -c "import selenium; print('   ✅ Selenium:', selenium.__version__)" 2>nul
    if %errorlevel% neq 0 echo    ❌ Selenium no instalado
    
    echo    Verificando SQLAlchemy...
    venv\Scripts\python.exe -c "import sqlalchemy; print('   ✅ SQLAlchemy:', sqlalchemy.__version__)" 2>nul
    if %errorlevel% neq 0 echo    ❌ SQLAlchemy no instalado
) else (
    echo    ⚠️  No se puede verificar (sin entorno virtual)
)

REM Verificar archivos principales
echo.
echo 📍 Archivos del Proyecto:
if exist "run.py" (
    echo    ✅ run.py
) else (
    echo    ❌ run.py falta
)

if exist "requirements.txt" (
    echo    ✅ requirements.txt
) else (
    echo    ❌ requirements.txt falta
)

if exist "backend\app\main.py" (
    echo    ✅ backend\app\main.py
) else (
    echo    ❌ backend\app\main.py falta
)

REM Verificar ChromeDriver
echo.
echo 📍 ChromeDriver:
if exist "drivers\chromedriver.exe" (
    echo    ✅ ChromeDriver encontrado
) else (
    echo    ❌ ChromeDriver no encontrado
    echo    💡 Ejecutar: update_chromedriver.bat
)

REM Verificar puertos disponibles
echo.
echo 📍 Puertos de Red:
netstat -an | findstr ":8000" >nul
if %errorlevel% equ 0 (
    echo    ⚠️  Puerto 8000 ocupado
    echo    💡 Usar: python run.py --port 8001
) else (
    echo    ✅ Puerto 8000 disponible
)

echo.
echo ========================================
echo 📋 RESUMEN DE DIAGNOSTICO
echo ========================================
echo.

REM Generar recomendaciones
echo 💡 Recomendaciones:
echo.

if not exist "venv\Scripts\python.exe" (
    echo    1. Crear entorno virtual: install.bat
)

venv\Scripts\python.exe -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo    2. Instalar dependencias: repair_installation.bat
)

if not exist "drivers\chromedriver.exe" (
    echo    3. Instalar ChromeDriver: update_chromedriver.bat
)

echo.
echo 🚀 Si todo esta OK, ejecutar: run.bat
echo 🌐 Luego abrir: http://localhost:8000
echo.
pause
