@echo off
echo ============================================================
echo ExpressATM - Sincronizacion de Datos
echo ============================================================
echo.
echo Descargando datos mas recientes del equipo...
git pull origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo SINCRONIZACION EXITOSA
    echo ============================================================
    echo - Base de datos actualizada con datos del equipo
    echo - Codigo actualizado con ultimas mejoras
    echo - Listo para ejecutar ExpressATM
    echo.
    echo Ejecuta 'run.bat' para iniciar la aplicacion
) else (
    echo.
    echo ============================================================
    echo ERROR EN SINCRONIZACION
    echo ============================================================
    echo - Verifica tu conexion a internet
    echo - Confirma permisos del repositorio
    echo - Contacta al administrador si persiste el error
)

echo.
pause
