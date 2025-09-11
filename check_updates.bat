@echo off
echo.
echo ========================================
echo  ExpressATM - Verificar Actualizaciones
echo ========================================
echo.

REM Verificar si estamos en un repositorio Git
if not exist ".git" (
    echo ❌ Error: Este directorio no es un repositorio Git
    echo 💡 Ejecuta: git clone https://github.com/ManangerIncidences/ExpressATM.git
    pause
    exit /b 1
)

echo 🔍 Conectando con GitHub...
git fetch origin main >nul 2>&1

if %errorlevel% neq 0 (
    echo ❌ Error conectando con GitHub
    echo 🔧 Verifica tu conexion a internet
    pause
    exit /b 1
)

echo ✅ Conexion establecida

REM Verificar version local
echo.
echo 📍 Version Local:
if exist "version.py" (
    python -c "
try:
    from version import get_version_info
    info = get_version_info()
    print(f'   ExpressATM v{info[\"version\"]} ({info[\"build_date\"]})')
except:
    print('   Version no detectada')
"
) else (
    echo    Version anterior (sin informacion de version)
)

REM Verificar actualizaciones disponibles
echo.
echo 🔍 Verificando actualizaciones...
for /f %%i in ('git rev-list HEAD..origin/main --count 2^>nul') do set UPDATES_COUNT=%%i

if "%UPDATES_COUNT%"=="" set UPDATES_COUNT=0

if %UPDATES_COUNT% gtr 0 (
    echo.
    echo 🆕 ¡ACTUALIZACIONES DISPONIBLES!
    echo    📊 Commits pendientes: %UPDATES_COUNT%
    echo.
    echo 📋 Ultimos cambios:
    git log --oneline HEAD..origin/main -5 --pretty=format:"   %%h - %%s"
    echo.
    echo.
    echo 🚀 Para actualizar ejecuta:
    echo    update.bat
    echo.
) else (
    echo.
    echo ✅ ¡TU VERSION ESTA ACTUALIZADA!
    echo    🎉 No hay nuevas actualizaciones disponibles
    echo.
)

REM Mostrar informacion del commit actual
echo 📍 Commit Actual:
git log --oneline -1 --pretty=format:"   %%h - %%s (%%ar)"
echo.
echo.

REM Verificar integridad de archivos importantes
echo 🔍 Verificando integridad del proyecto...
set MISSING_FILES=0

if not exist "run.py" (
    echo    ❌ run.py falta
    set /a MISSING_FILES+=1
)
if not exist "requirements.txt" (
    echo    ❌ requirements.txt falta  
    set /a MISSING_FILES+=1
)
if not exist "backend\app\main.py" (
    echo    ❌ backend\app\main.py falta
    set /a MISSING_FILES+=1
)

if %MISSING_FILES% gtr 0 (
    echo.
    echo ⚠️  Se detectaron %MISSING_FILES% archivos faltantes
    echo 💡 Ejecuta update.bat para reparar
) else (
    echo    ✅ Archivos principales verificados
)

echo.
echo ========================================
if %UPDATES_COUNT% gtr 0 (
    echo 🔄 ACTUALIZACION RECOMENDADA
    echo.
    echo Ejecuta: update.bat
) else (
    echo ✅ SISTEMA ACTUALIZADO
    echo.
    echo Ejecuta: run.bat
)
echo ========================================
echo.
pause
