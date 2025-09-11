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
    """Descarga e instala ChromeDriver automáticamente"""
    print_colored("🌐 Configurando ChromeDriver...", Colors.OKBLUE)
    
    drivers_dir = Path("drivers")
    drivers_dir.mkdir(exist_ok=True)
    
    system = platform.system().lower()
    if system == "windows":
        chrome_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
        try:
            # Obtener última versión
            with urllib.request.urlopen(chrome_url) as response:
                version = response.read().decode().strip()
            
            # Descargar ChromeDriver
            driver_url = f"https://chromedriver.storage.googleapis.com/{version}/chromedriver_win32.zip"
            zip_path = drivers_dir / "chromedriver.zip"
            
            print_colored(f"📥 Descargando ChromeDriver {version}...", Colors.WARNING)
            urllib.request.urlretrieve(driver_url, zip_path)
            
            # Extraer
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(drivers_dir)
            
            zip_path.unlink()  # Eliminar zip
            print_colored("✅ ChromeDriver instalado correctamente", Colors.OKGREEN)
            
        except Exception as e:
            print_colored(f"⚠️ Error descargando ChromeDriver: {e}", Colors.WARNING)
            print_colored("💡 Por favor, descarga ChromeDriver manualmente desde:", Colors.WARNING)
            print_colored("   https://chromedriver.chromium.org/", Colors.WARNING)
    else:
        print_colored("⚠️ Sistema no-Windows detectado. Instala ChromeDriver manualmente:", Colors.WARNING)
        print_colored("   Ubuntu/Debian: sudo apt install chromium-chromedriver", Colors.WARNING)
        print_colored("   macOS: brew install chromedriver", Colors.WARNING)

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
BROWSER_HEADLESS=true
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
