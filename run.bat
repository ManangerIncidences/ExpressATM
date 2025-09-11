@echo off
cd /d "%~dp0"

REM Buscar Python (entorno virtual primero)
if exist "venv\Scripts\python.exe" (
    echo Iniciando con entorno virtual local...
    "venv\Scripts\python.exe" run.py
) else if exist ".venv\Scripts\python.exe" (
    echo Iniciando con entorno virtual .venv...
    ".venv\Scripts\python.exe" run.py
) else (
    echo Entorno virtual no encontrado. Intentando con Python del sistema...
    where py >nul 2>&1 && ( py run.py ) || (
        python run.py
    )
)

pause
