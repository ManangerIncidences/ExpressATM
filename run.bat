@echo off
cd /d "%~dp0"

REM Buscar Python (entorno virtual primero)
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe run.py
) else (
    python run.py
)

pause
