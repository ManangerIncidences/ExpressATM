@echo off
setlocal enabledelayedexpansion
:MENU
cls
echo.
echo ========================================
echo      ExpressATM - Centro de Control
echo ========================================
echo.
echo 🎯 INSTALACION Y CONFIGURACION:
echo    [1] Instalacion Completa         (Nuevo usuario - Todo automatico)
echo    [2] Instalacion Rapida           (Solo dependencias)
echo    [3] Reparar Instalacion          (Problemas existentes)
echo.
echo 🔄 ACTUALIZACION:
echo    [4] Verificar Actualizaciones    (Ver que hay nuevo)
echo    [5] Actualizar Sistema           (Descargar cambios)
echo.
echo 🔍 DIAGNOSTICO:
echo    [6] Verificar Sistema            (Estado actual)
echo    [7] Instalar ChromeDriver        (Solo navegador)
echo.
echo 🚀 EJECUCION:
echo    [8] Ejecutar ExpressATM          (Iniciar aplicacion)
echo    [9] Ver Version                  (Info del sistema)
echo.
echo ⚙️  HERRAMIENTAS:
echo    [A] Limpiar Sistema              (Cache y temporales)
echo    [B] Crear Respaldo               (Guardar configuracion)
echo    [C] Sincronizar Equipo           (Datos compartidos)
echo.
echo    [0] Salir
echo.
echo ========================================
set /p CHOICE="Selecciona una opcion (1-9, A-C, 0): "

if "%CHOICE%"=="1" goto INSTALL_COMPLETE
if "%CHOICE%"=="2" goto INSTALL_FAST
if "%CHOICE%"=="3" goto REPAIR
if "%CHOICE%"=="4" goto CHECK_UPDATES
if "%CHOICE%"=="5" goto UPDATE
if "%CHOICE%"=="6" goto CHECK_SYSTEM
if "%CHOICE%"=="7" goto INSTALL_CHROMEDRIVER
if "%CHOICE%"=="8" goto RUN_APP
if "%CHOICE%"=="9" goto SHOW_VERSION
if /i "%CHOICE%"=="A" goto CLEANUP
if /i "%CHOICE%"=="B" goto BACKUP
if /i "%CHOICE%"=="C" goto SYNC_TEAM
if "%CHOICE%"=="0" goto EXIT

echo ❌ Opcion invalida
timeout /t 2 >nul
goto MENU

:INSTALL_COMPLETE
echo.
echo 🚀 Ejecutando Instalacion Completa...
call install_complete.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:INSTALL_FAST
echo.
echo ⚡ Ejecutando Instalacion Rapida...
call install.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:REPAIR
echo.
echo 🔧 Ejecutando Reparacion de Instalacion...
call repair_installation.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:CHECK_UPDATES
echo.
echo 🔍 Verificando Actualizaciones...
call check_updates.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:UPDATE
echo.
echo 🔄 Actualizando Sistema...
call update.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:CHECK_SYSTEM
echo.
echo 🔍 Verificando Estado del Sistema...
call check_system.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:INSTALL_CHROMEDRIVER
echo.
echo 🌐 Instalando ChromeDriver...
call update_chromedriver.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:RUN_APP
echo.
echo 🚀 Iniciando ExpressATM...
echo    Panel: http://localhost:8000
echo    Dashboard: http://localhost:8000/dashboard
echo    IA: http://localhost:8000/ai
echo.
echo Presiona Ctrl+C para detener
call run.bat
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:SHOW_VERSION
echo.
echo 📋 Informacion de Version:
python run.py --version 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  No se pudo obtener informacion de version
    echo 💡 Ejecutar: Instalacion Completa
)
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:CLEANUP
echo.
echo 🧹 Limpiando Sistema...
echo Eliminando archivos temporales...
if exist "*.tmp" del "*.tmp" /q
if exist "*.temp" del "*.temp" /q
if exist "temp_*" del "temp_*" /q
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "backend\__pycache__" rmdir /s /q "backend\__pycache__"
if exist "backend\app\__pycache__" rmdir /s /q "backend\app\__pycache__"

echo Limpiando logs antiguos...
if exist "logs\*.log" (
    for /f %%f in ('dir /b logs\*.log 2^>nul') do (
        echo Respaldando %%f...
        copy "logs\%%f" "logs\%%f.backup" >nul 2>&1
    )
)

echo ✅ Limpieza completada
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:BACKUP
echo.
echo 💾 Creando Respaldo...
set BACKUP_DIR=backup_%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set BACKUP_DIR=%BACKUP_DIR: =0%

if not exist "backups" mkdir backups
mkdir "backups\%BACKUP_DIR%"

echo Respaldando base de datos...
if exist "*.db" copy "*.db" "backups\%BACKUP_DIR%\" >nul

echo Respaldando configuracion...
if exist "config.py" copy "config.py" "backups\%BACKUP_DIR%\" >nul
if exist ".env" copy ".env" "backups\%BACKUP_DIR%\" >nul

echo Respaldando logs...
if exist "logs\*.log" copy "logs\*.log" "backups\%BACKUP_DIR%\" >nul

echo ✅ Respaldo creado en: backups\%BACKUP_DIR%
echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:SYNC_TEAM
echo.
echo 🔄 Sincronizacion de Equipo...
echo.
echo [1] Descargar datos del equipo (sync_data.bat)
echo [2] Subir mis datos al equipo (update_data.bat)
echo [3] Volver al menu principal
echo.
set /p SYNC_CHOICE="Selecciona opcion (1-3): "

if "%SYNC_CHOICE%"=="1" (
    echo.
    echo 📥 Descargando datos del equipo...
    call sync_data.bat
) else if "%SYNC_CHOICE%"=="2" (
    echo.
    echo 📤 Subiendo datos al equipo...
    call update_data.bat
) else if "%SYNC_CHOICE%"=="3" (
    goto MENU
) else (
    echo ❌ Opcion invalida
    timeout /t 2 >nul
    goto SYNC_TEAM
)

echo.
echo Presiona cualquier tecla para volver al menu...
pause >nul
goto MENU

:EXIT
echo.
echo 👋 ¡Gracias por usar ExpressATM!
echo.
echo 💡 Para ejecutar directamente: run.bat
echo 🌐 Panel web: http://localhost:8000
echo.
exit /b 0
