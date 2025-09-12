#!/usr/bin/env python3
"""
Diagnóstico y reparación básica de instalación ExpressATM.
- Verifica Python, pip, versiones y paquetes claves.
- Prueba importaciones críticas.
- Verifica Chrome, webdriver-manager, y resolución de ChromeDriver.
- Inicializa la base de datos si falta.
"""
import os
import sys
import subprocess
from pathlib import Path

OK = "[OK]"
ERR = "[ERR]"
INF = "[INF]"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=False)


def check_python():
    print(f"{INF} Python: {sys.version}")
    if sys.version_info < (3, 8):
        print(f"{ERR} Se requiere Python 3.8+.")
        return False
    return True


def check_pip():
    r = run([sys.executable, "-m", "pip", "--version"])
    print(f"{INF} pip: {r.stdout.strip() or r.stderr.strip()}")
    return r.returncode == 0


REQUIRED = [
    "fastapi",
    "uvicorn",
    "selenium",
    "sqlalchemy",
    "webdriver-manager",
    "python-dotenv",
]


def check_packages():
    ok = True
    for pkg in REQUIRED:
        r = run([sys.executable, "-c", f"import importlib, sys; sys.exit(0 if importlib.util.find_spec('{pkg.replace('-', '_')}') else 1)"])
        if r.returncode == 0:
            print(f"{OK} {pkg}")
        else:
            print(f"{ERR} Falta paquete: {pkg}")
            ok = False
    return ok


def check_env():
    env = Path(".env")
    print(f"{INF} .env presente: {env.exists()} ({env.resolve()})")
    if not env.exists():
        print(f"{INF} Usa .env.example como base y copia a .env")


def check_driver_resolution():
    try:
        from backend.driver_manager import get_chromedriver_path
        p = get_chromedriver_path()
        print(f"{OK} ChromeDriver resuelto: {p}")
    except Exception as e:
        print(f"{ERR} No se pudo resolver ChromeDriver: {e}")


def init_db():
    try:
        from backend.app.database import engine
        from backend.app.models import Base
        Base.metadata.create_all(bind=engine)
        print(f"{OK} Tablas creadas (si no existían)")
    except Exception as e:
        print(f"{ERR} Error creando tablas: {e}")


def main():
    print("== Diagnóstico ExpressATM ==")
    ok = check_python() and check_pip()
    check_env()
    pkgs = check_packages()
    check_driver_resolution()
    init_db()
    if not (ok and pkgs):
        print("-- Sugerencias --")
        print("python -m pip install -r requirements.txt")
    print("Listo.")


if __name__ == "__main__":
    main()
