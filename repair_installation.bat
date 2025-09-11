@echo off
echo.
echo ========================================
echo  ExpressATM - Reparar Instalacion
echo ========================================
echo.

echo 🔧 Detectando problema...

REM Verificar si estamos en un entorno virtual corrupto
if defined VIRTUAL_ENV (
    echo ⚠️  Entorno virtual activo detectado
    echo 📍 Ruta actual: %VIRTUAL_ENV%
    echo.
    echo 🧹 Desactivando entorno virtual corrupto...
    call deactivate 2>nul
)

REM Eliminar entorno virtual corrupto
if exist "venv" (
    echo 🗑️  Eliminando entorno virtual corrupto...
    rmdir /S /Q venv
    if %errorlevel% neq 0 (
        echo ❌ Error eliminando venv. Intenta manualmente:
        echo    rmdir /S venv
        pause
        exit /b 1
    )
    echo ✅ Entorno virtual eliminado
)

echo.
echo 🔨 Creando nuevo entorno virtual...
python -m venv venv

if %errorlevel% neq 0 (
    echo ❌ Error creando entorno virtual
    echo.
    echo 🔧 SOLUCION:
    echo 1. Verificar que Python este instalado: python --version
    echo 2. Reinstalar Python desde: https://python.org
    echo 3. ✅ Marcar "Add Python to PATH"
    pause
    exit /b 1
)

echo ✅ Nuevo entorno virtual creado

echo.
echo 🔌 Activando entorno virtual...
call venv\Scripts\activate.bat

echo ✅ Entorno virtual activado

echo.
echo 📦 Actualizando pip...
python -m pip install --upgrade pip

echo.
echo 📚 Instalando dependencias...
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error instalando dependencias
    echo.
    echo 🔧 Intentando metodos alternativos...
    
    echo 📥 Instalando dependencias criticas una por una...
    python -m pip install fastapi
    python -m pip install uvicorn
    python -m pip install pandas
    python -m pip install selenium
    python -m pip install numpy
    python -m pip install sqlalchemy
    
    echo.
    echo 🔄 Intentando instalacion completa nuevamente...
    python -m pip install -r requirements.txt
)

REM Verificar instalacion
echo.
echo 🧪 Verificando instalacion...
python -c "import fastapi; import pandas; print('✅ Dependencias principales verificadas')" 2>nul

if %errorlevel% neq 0 (
    echo ❌ Algunas dependencias faltan. Ejecutando diagnostico...
    python -c "
try:
    import fastapi
    print('✅ FastAPI: OK')
except ImportError:
    print('❌ FastAPI: FALTA')

try:
    import pandas
    print('✅ Pandas: OK')
except ImportError:
    print('❌ Pandas: FALTA')

try:
    import selenium
    print('✅ Selenium: OK')
except ImportError:
    print('❌ Selenium: FALTA')
"
)

echo.
echo 🌐 Configurando ChromeDriver...
if exist "update_chromedriver.bat" (
    call update_chromedriver.bat
) else (
    echo ⚠️  update_chromedriver.bat no encontrado
)

echo.
echo ========================================
echo ✅ REPARACION COMPLETADA
echo ========================================
echo.
echo 🚀 Para ejecutar ExpressATM:
echo    run.bat
echo.
echo 🌐 Acceso web:
echo    http://localhost:8000
echo.
echo 💡 Si persisten problemas:
echo    1. Cerrar todas las ventanas de terminal
echo    2. Abrir nueva ventana como Administrador
echo    3. Ejecutar este script nuevamente
echo.
pause
