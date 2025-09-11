@echo off
echo ============================================================
echo ExpressATM - Actualizar Base de Datos Compartida
echo ============================================================
echo.
echo Agregando cambios en base de datos...
git add monitoring.db dom_intelligence.db vision_learning.db

echo.
echo Creando commit con timestamp...
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%"
set "datestamp=%YYYY%-%MM%-%DD% %HH%:%Min%"

git commit -m "Actualizar datos de monitoreo - %datestamp%"

echo.
echo Subiendo datos al repositorio compartido...
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo DATOS ACTUALIZADOS EXITOSAMENTE
    echo ============================================================
    echo - Base de datos subida a GitHub
    echo - Disponible para todo el equipo
    echo - Otros miembros pueden sincronizar con 'sync_data.bat'
    echo.
    echo El equipo ya puede acceder a los datos actualizados
) else (
    echo.
    echo ============================================================
    echo ERROR SUBIENDO DATOS
    echo ============================================================
    echo - Verifica tu conexion a internet
    echo - Confirma que tienes permisos de escritura
    echo - Usa 'git status' para ver el estado actual
)

echo.
pause
