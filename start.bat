@echo off
echo ========================================
echo ExpressATM - Instalacion Basica
echo ========================================
echo.
echo Verificando Python...

REM Verificar si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Por favor instala Python desde https://python.org
    pause
    exit /b 1
)

echo Python encontrado
echo.
echo Instalando dependencias basicas...

REM Instalar dependencias
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)

echo.
echo ========================================
echo Instalacion basica completada
echo ========================================
echo.
echo Usa 'run.bat' para ejecutar ExpressATM
echo O usa 'install.bat' para instalacion completa con entorno virtual
echo.
pause
