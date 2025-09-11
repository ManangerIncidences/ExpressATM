@echo off
echo.
echo ========================================
echo  ExpressATM - Actualizacion Automatica
echo ========================================
echo.

REM Verificar si estamos en un repositorio Git
if not exist ".git" (
    echo ❌ Error: Este directorio no es un repositorio Git
    echo.
    echo 💡 SOLUCION:
    echo 1. Descargar proyecto completo desde GitHub
    echo 2. O ejecutar: git clone https://github.com/ManangerIncidences/ExpressATM.git
    echo.
    pause
    exit /b 1
)

echo 🔍 Verificando conexion a GitHub...
git remote -v | findstr "github.com" >nul
if %errorlevel% neq 0 (
    echo ❌ Error: No se detecta conexion con GitHub
    echo.
    echo 🔧 Configurando repositorio...
    git remote add origin https://github.com/ManangerIncidences/ExpressATM.git
)

echo ✅ Repositorio conectado a GitHub

REM Verificar estado del repositorio
echo.
echo 🔍 Verificando estado local...
git status --porcelain >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error verificando estado del repositorio
    pause
    exit /b 1
)

REM Detectar cambios locales
for /f %%i in ('git status --porcelain 2^>nul ^| find /c /v ""') do set LOCAL_CHANGES=%%i

if %LOCAL_CHANGES% gtr 0 (
    echo.
    echo ⚠️  CAMBIOS LOCALES DETECTADOS:
    git status --short
    echo.
    echo 💾 ¿Quieres respaldar tus cambios locales?
    echo    [S] Si - Crear respaldo antes de actualizar
    echo    [N] No - Descartar cambios y actualizar
    echo    [C] Cancelar actualizacion
    echo.
    set /p CHOICE="Selecciona opcion (S/N/C): "
    
    if /i "%CHOICE%"=="C" (
        echo ❌ Actualizacion cancelada por el usuario
        pause
        exit /b 0
    )
    
    if /i "%CHOICE%"=="S" (
        echo.
        echo 💾 Creando respaldo de cambios locales...
        set BACKUP_NAME=backup_local_%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
        set BACKUP_NAME=!BACKUP_NAME: =0!
        git stash push -m "!BACKUP_NAME!" --include-untracked
        echo ✅ Respaldo creado: !BACKUP_NAME!
        echo 💡 Para restaurar despues: git stash pop
    ) else (
        echo.
        echo 🗑️  Descartando cambios locales...
        git reset --hard HEAD
        git clean -fd
        echo ✅ Cambios locales descartados
    )
)

echo.
echo 📥 Descargando actualizaciones desde GitHub...
git fetch origin main

REM Verificar si hay actualizaciones disponibles
for /f %%i in ('git rev-list HEAD..origin/main --count 2^>nul') do set UPDATES_COUNT=%%i

if "%UPDATES_COUNT%"=="0" (
    echo.
    echo ✅ Tu version ya esta actualizada
    echo 🎉 No hay nuevas actualizaciones disponibles
    echo.
    pause
    exit /b 0
)

echo.
echo 🆕 Actualizaciones disponibles: %UPDATES_COUNT% commits
echo.
echo 📋 Ultimos cambios:
git log --oneline HEAD..origin/main -5
echo.

REM Aplicar actualizaciones
echo 🔄 Aplicando actualizaciones...
git merge origin/main --ff-only

if %errorlevel% neq 0 (
    echo.
    echo ❌ Error aplicando actualizaciones automaticamente
    echo 🔧 Intentando fusion manual...
    git merge origin/main
    
    if %errorlevel% neq 0 (
        echo.
        echo ❌ Error en fusion manual - conflictos detectados
        echo.
        echo 🛠️  ACCION REQUERIDA:
        echo 1. Revisar archivos con conflictos
        echo 2. Resolver conflictos manualmente
        echo 3. Ejecutar: git add . && git commit
        echo 4. Ejecutar este script nuevamente
        echo.
        pause
        exit /b 1
    )
)

echo ✅ Actualizaciones aplicadas exitosamente

REM Verificar si necesitamos actualizar dependencias
if exist "requirements.txt" (
    echo.
    echo 🔍 Verificando dependencias de Python...
    
    REM Comparar requirements.txt con version anterior
    git show HEAD~1:requirements.txt > temp_old_requirements.txt 2>nul
    if exist "temp_old_requirements.txt" (
        fc requirements.txt temp_old_requirements.txt >nul 2>&1
        if %errorlevel% neq 0 (
            echo 📦 Dependencias actualizadas detectadas
            echo 🔄 Actualizando entorno virtual...
            
            REM Activar entorno virtual si existe
            if exist "venv\Scripts\activate.bat" (
                call venv\Scripts\activate.bat
                python -m pip install --upgrade pip
                python -m pip install -r requirements.txt --upgrade
                echo ✅ Dependencias actualizadas
            ) else (
                echo ⚠️  Entorno virtual no encontrado
                echo 💡 Ejecuta install.bat para crear entorno virtual
            )
        ) else (
            echo ✅ Dependencias sin cambios
        )
        del temp_old_requirements.txt
    ) else (
        echo ℹ️  Primera actualizacion - verificando dependencias...
        if exist "venv\Scripts\activate.bat" (
            call venv\Scripts\activate.bat
            python -m pip install -r requirements.txt --upgrade
        )
    )
)

REM Verificar si necesitamos actualizar ChromeDriver
if exist "update_chromedriver.bat" (
    echo.
    echo 🌐 Verificando ChromeDriver...
    call update_chromedriver.bat
)

REM Ejecutar verificacion del sistema
if exist "check_system.bat" (
    echo.
    echo 🔍 Verificando integridad del sistema...
    call check_system.bat
)

echo.
echo ========================================
echo ✅ ACTUALIZACION COMPLETADA EXITOSAMENTE
echo ========================================
echo.
echo 🎉 ExpressATM actualizado a la ultima version
echo.
echo 🚀 Para usar la version actualizada:
echo    run.bat
echo.
echo 🌐 Acceso web:
echo    http://localhost:8000
echo.
echo 📝 Si realizaste respaldo de cambios:
echo    git stash list    (ver respaldos)
echo    git stash pop     (restaurar ultimo respaldo)
echo.
pause
