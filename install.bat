@echo off
REM ExpressATM - Script de Instalación para Windows
REM ===============================================

echo ========================================
echo ExpressATM - Instalacion Windows
echo ========================================
echo.

REM Verificar Python
echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado. Por favor instala Python 3.8+ desde python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% encontrado

REM Crear entorno virtual
echo.
echo Creando entorno virtual...

REM Eliminar entorno virtual existente si existe (puede tener rutas incorrectas)
if exist "venv" (
    echo Limpiando entorno virtual existente...
    rmdir /S /Q venv
)

python -m venv venv
call venv\Scripts\activate.bat

REM Instalar dependencias
echo.
echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Crear directorios
echo.
echo Creando directorios...
if not exist "logs" mkdir logs
if not exist "drivers" mkdir drivers
if not exist "data" mkdir data
if not exist "frontend\logos" mkdir frontend\logos

REM Configurar .env
echo.
echo Configurando variables de entorno...
if not exist ".env" (
    copy ".env.example" ".env"
    echo Archivo .env creado
) else (
    echo Archivo .env ya existe
)

REM Configurar ChromeDriver (webdriver-manager)
echo.
echo Configurando ChromeDriver con webdriver-manager...
python scripts\setup_chromedriver.py
if errorlevel 1 (
    echo Advertencia: No se pudo instalar ChromeDriver automaticamente. Puedes reintentar con update_chromedriver.bat
)

REM Inicializar base de datos
echo.
echo Inicializando base de datos...
python -c "import sys; sys.path.append('.'); from backend.app.database import engine; from backend.app.models import Base; Base.metadata.create_all(bind=engine); print('Base de datos inicializada')" 2>nul || echo Base de datos se creara al primer uso

echo.
echo ========================================
echo Instalacion completada!
echo ========================================
echo.
echo Proximos pasos:
echo 1. Ejecutar: python run.py
echo 2. Abrir navegador en: http://localhost:8000
echo 3. Revisar configuracion en .env si es necesario
echo.
echo Configuracion adicional:
echo - Edita .env para personalizar configuracion
echo - Revisa DataAgencias.xlsx para configurar agencias
echo.
echo Disfruta usando ExpressATM!
pause
