#!/usr/bin/env python3
"""
ExpressATM - Script de Instalación Automática
==============================================

Este script configura automáticamente el entorno para ExpressATM.
Detecta el sistema operativo e instala dependencias necesarias.

Uso:
    python install.py

Requisitos previos:
    - Python 3.8+ instalado
    - pip funcional
    - Conexión a internet
"""

import sys
import subprocess
import os
import platform
import urllib.request
import zipfile
import shutil
from pathlib import Path

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color=Colors.ENDC):
    """Imprime texto con color en terminal"""
    print(f"{color}{text}{Colors.ENDC}")

def check_python_version():
    """Verifica que Python sea >= 3.8"""
    print_colored("🐍 Verificando versión de Python...", Colors.OKBLUE)
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_colored(f"❌ Error: Python {version.major}.{version.minor} detectado. Se requiere Python 3.8+", Colors.FAIL)
        sys.exit(1)
    print_colored(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK", Colors.OKGREEN)

def install_requirements():
    """Instala dependencias desde requirements.txt"""
    print_colored("📦 Instalando dependencias...", Colors.OKBLUE)
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print_colored("✅ Dependencias instaladas correctamente", Colors.OKGREEN)
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Error instalando dependencias: {e}", Colors.FAIL)
        sys.exit(1)

def setup_chromedriver():
    """Instala/gestiona ChromeDriver usando webdriver-manager (portable)."""
    print_colored("🌐 Configurando ChromeDriver (webdriver-manager)...", Colors.OKBLUE)

    # Crear carpeta drivers por compatibilidad (aunque webdriver-manager usa caché propia)
    Path("drivers").mkdir(exist_ok=True)

    try:
        from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
        driver_path = ChromeDriverManager().install()
        print_colored(f"✅ ChromeDriver listo en: {driver_path}", Colors.OKGREEN)
        print_colored("ℹ️ La ruta se resolverá automáticamente en runtime (sin rutas hardcodeadas).", Colors.OKBLUE)
    except Exception as e:
        print_colored(f"⚠️ No se pudo instalar automáticamente con webdriver-manager: {e}", Colors.WARNING)
        print_colored("💡 Puedes especificar manualmente CHROMEDRIVER_PATH en .env si ya tienes el binario.", Colors.WARNING)
        # Mensaje adicional por SO
        system = platform.system().lower()
        if system == "windows":
            print_colored("Descarga manual: https://googlechromelabs.github.io/chrome-for-testing/", Colors.WARNING)
        else:
            print_colored("Linux: apt install chromium-chromedriver | macOS: brew install chromedriver", Colors.WARNING)

def create_env_file():
    """Crea archivo .env con configuración por defecto"""
    print_colored("⚙️ Creando configuración por defecto...", Colors.OKBLUE)
    
    env_content = """# ExpressATM - Configuración de Entorno
# =====================================

# Base de datos principal
DATABASE_URL=sqlite:///./monitoring.db

# Base de datos de inteligencia DOM
DOM_INTELLIGENCE_DB=dom_intelligence.db

# Configuración de monitoreo
MONITORING_INTERVAL_MINUTES=15
MAX_PDF_EXPORT_ROWS=800

# Configuración del navegador
CHROME_HEADLESS=true
BROWSER_TIMEOUT_SECONDS=30

# Puerto del servidor (cambiar si 8000 está ocupado)
SERVER_PORT=8000
SERVER_HOST=0.0.0.0

# Configuración de logs
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# URLs base (ajustar según entorno)
FRONTEND_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000/api

# Configuración de alertas
SALES_THRESHOLD=20000
BALANCE_THRESHOLD=6000
GROWTH_VARIATION_THRESHOLD=1500
SUSTAINED_GROWTH_THRESHOLD=500

# Archivo de datos de agencias (opcional)
AGENCIES_DATA_FILE=DataAgencias.xlsx
"""
    
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(env_content)
        print_colored("✅ Archivo .env creado", Colors.OKGREEN)
    else:
        print_colored("⚠️ Archivo .env ya existe, no se sobrescribirá", Colors.WARNING)

def create_directories():
    """Crea directorios necesarios"""
    print_colored("📁 Creando directorios necesarios...", Colors.OKBLUE)
    
    directories = [
        "logs",
        "drivers",
        "data",
        "frontend/logos",
        "__pycache__",
        "backend/__pycache__",
        "backend/app/__pycache__"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print_colored("✅ Directorios creados", Colors.OKGREEN)

def run_initial_setup():
    """Ejecuta configuración inicial de la base de datos"""
    print_colored("🗄️ Inicializando base de datos...", Colors.OKBLUE)
    try:
        # Crear las tablas ejecutando el script principal brevemente
        subprocess.run([sys.executable, "-c", """
import sys
sys.path.append('.')
from backend.app.database import engine
from backend.app.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Tablas de base de datos creadas')
"""], check=True, capture_output=True, text=True)
        print_colored("✅ Base de datos inicializada", Colors.OKGREEN)
    except subprocess.CalledProcessError as e:
        print_colored(f"⚠️ Error inicializando BD (se creará automáticamente): {e}", Colors.WARNING)

def main():
    """Función principal de instalación"""
    print_colored("=" * 60, Colors.HEADER)
    print_colored("🚀 ExpressATM - Instalación Automática", Colors.HEADER)
    print_colored("=" * 60, Colors.HEADER)
    print()
    
    # Verificaciones
    check_python_version()
    
    # Configuración
    create_directories()
    create_env_file()
    install_requirements()
    setup_chromedriver()
    run_initial_setup()
    
    print()
    print_colored("=" * 60, Colors.HEADER)
    print_colored("🎉 ¡Instalación completada exitosamente!", Colors.OKGREEN)
    print_colored("=" * 60, Colors.HEADER)
    print()
    print_colored("📋 Próximos pasos:", Colors.OKBLUE)
    print_colored("1. Ejecutar: python run.py", Colors.WARNING)
    print_colored("2. Abrir navegador en: http://localhost:8000", Colors.WARNING)
    print_colored("3. Revisar configuración en archivo .env si es necesario", Colors.WARNING)
    print()
    print_colored("📖 Documentación:", Colors.OKBLUE)
    print_colored("- Técnica: DOCUMENTACION_TECNICA.md", Colors.WARNING)
    print_colored("- Usuario: GUIA_USUARIOS.md", Colors.WARNING)
    print()
    print_colored("¡Disfruta usando ExpressATM! 🎯", Colors.OKGREEN)

if __name__ == "__main__":
    main()
