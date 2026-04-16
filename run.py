#!/usr/bin/env python3
"""
ExpressATM - Sistema de Monitoreo para Agencias de Lotería
===========================================================

Este archivo sirve como punto de entrada principal para la aplicación ExpressATM.
Configura el servidor FastAPI y maneja la inicialización del sistema.

Uso:
    python run.py [--port PORT] [--host HOST] [--dev] [--version]

Argumentos:
    --port, -p      Puerto del servidor (default: 8000)
    --host          Host del servidor (default: 0.0.0.0)
    --dev           Modo desarrollo con recarga automática
    --version, -v   Mostrar información de versión
    --help, -h      Mostrar esta ayuda

Ejemplos:
    python run.py                    # Servidor en puerto 8000
    python run.py --port 8080        # Servidor en puerto 8080
    python run.py --version          # Mostrar versión actual
    python run.py --dev              # Modo desarrollo
"""

import argparse
import sys
import os
import logging
import socket
from pathlib import Path

# Directorio del proyecto y PATH
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Asegurar que el proceso trabaje desde la carpeta del proyecto
try:
    os.chdir(str(PROJECT_ROOT))
except Exception:
    pass

# Importar información de versión
try:
    from version import get_version_info, print_version
except ImportError:
    def get_version_info():
        return {"version": "2.0.0", "build_date": "2025-09-10", "release_notes": []}
    def print_version():
        print("ExpressATM v2.0.0")

def setup_logging():
    """Logging ya configurado centralmente en backend.app.main — no-op aquí"""
    Path("logs").mkdir(exist_ok=True)

def check_requirements():
    """Verifica que todas las dependencias estén instaladas"""
    missing_packages = []
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('sqlalchemy', 'sqlalchemy'),
        ('selenium', 'selenium'),
        ('pandas', 'pandas'),
        ('openpyxl', 'openpyxl'),
        ('fpdf2', 'fpdf')  # El paquete es fpdf2 pero se importa como fpdf
    ]
    
    for display_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(display_name)
    
    if missing_packages:
        print("❌ Faltan dependencias:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Ejecuta: pip install -r requirements.txt")
        return False
    
    return True

def check_chromedriver():
    """Verifica que ChromeDriver esté disponible"""
    drivers_dir = Path("drivers")
    chrome_paths = [
        drivers_dir / "chromedriver.exe",
        drivers_dir / "chromedriver",
        "chromedriver.exe",
        "chromedriver"
    ]
    
    for path in chrome_paths:
        if isinstance(path, Path):
            if path.exists():
                return True
        else:
            # Comprobar en PATH (Windows: where, Unix: which)
            check_cmd = "where" if os.name == "nt" else "which"
            rc = os.system(f"{check_cmd} {path} >nul 2>&1" if os.name == "nt" else f"{check_cmd} {path} >/dev/null 2>&1")
            if rc == 0:
                return True
    
    print("⚠️ ChromeDriver no encontrado")
    print("💡 Ejecuta uno de estos comandos:")
    print("   - Windows: update_chromedriver.bat")
    print("   - Linux: sudo apt install chromium-chromedriver")
    print("   - macOS: brew install chromedriver")
    return False

def create_initial_directories():
    """Crea directorios necesarios si no existen"""
    directories = [
        "logs",
        "drivers", 
        "data",
        "frontend/logos"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def _env_port_fallback(cli_port: int) -> int:
    """Determina el puerto a usar: ENV (EXPRESSATM_PORT/PORT) tiene prioridad si se especifica.

    Si no hay ENV, usa el del CLI. """
    env_val = os.getenv("EXPRESSATM_PORT") or os.getenv("PORT")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            return cli_port
    return cli_port


def _is_port_open(addr: str, port: int, timeout: float = 0.2) -> bool:
    """Retorna True si hay algo escuchando en addr:port (evita falsos positivos de bind en Windows)."""
    try:
        with socket.create_connection((addr, port), timeout=timeout):
            return True
    except OSError:
        return False


def _find_available_port(host: str, start_port: int, attempts: int = 15) -> int:
    """Devuelve un puerto libre, intentando desde start_port e incrementando.

    Considera colisiones tanto en 127.0.0.1 como en 0.0.0.0 (wildcard) en Windows.
    """
    loopback = "127.0.0.1"
    host_check = host if host and host != "0.0.0.0" else loopback
    port = start_port
    for _ in range(max(1, attempts)):
        # Si hay algo escuchando en loopback o en el host indicado, consideramos ocupado
        if not _is_port_open(loopback, port) and not _is_port_open(host_check, port):
            return port
        port += 1
    return port


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="ExpressATM - Sistema de Monitoreo para Agencias de Lotería",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python run.py                    # Servidor estándar
  python run.py --port 8080        # Puerto personalizado
  python run.py --dev              # Modo desarrollo
  python run.py --host 127.0.0.1   # Solo localhost
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
    default=8000,
        help='Puerto del servidor (default: 8000)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host del servidor (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Modo desarrollo con recarga automática'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help='Mostrar información de versión'
    )
    
    args = parser.parse_args()
    
    # Mostrar versión si se solicita
    if args.version:
        print_version()
        sys.exit(0)
    
    # Determinar host/puerto por ENV y evitar colisiones
    env_host = os.getenv("EXPRESSATM_HOST") or os.getenv("HOST")
    if env_host:
        args.host = env_host
    args.port = _env_port_fallback(args.port)

    # Banner de inicio
    print("=" * 60)
    print("ExpressATM - Sistema de Monitoreo")
    print("=" * 60)
    
    # Configurar logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Verificaciones iniciales
    print("Verificando sistema...")
    if not check_requirements():
        sys.exit(1)
    
    create_initial_directories()
    
    if not check_chromedriver():
        print("Continuando sin ChromeDriver (funcionalidad limitada)")
    
    # Configurar variables de entorno desde .env ANTES de importar backend
    env_file = Path(".env")
    if env_file.exists():
        try:
            import dotenv
            dotenv.load_dotenv()
            print("Variables de entorno cargadas desde .env")
        except ImportError:
            print("💡 Instala python-dotenv para usar archivo .env")

    # Importar y ejecutar la aplicación
    try:
        import uvicorn
        from backend.app.main import app

        # Ajustar puerto si está ocupado (considerando loopback)
        selected_port = _find_available_port(args.host, int(args.port or 8000))
        if selected_port != args.port:
            print(f"⚠️  Puerto {args.port} ocupado. Usando puerto alternativo {selected_port}.")
            args.port = selected_port

        print(f"Iniciando servidor en http://{args.host}:{args.port}")
        print(f"Panel principal: http://localhost:{args.port}")
        print(f"Dashboard: http://localhost:{args.port}/dashboard")
        print(f"Analisis IA: http://localhost:{args.port}/ai")
        print(f"Documentacion API: http://localhost:{args.port}/docs")
        print()
        print("Presiona Ctrl+C para detener el servidor")
        print("=" * 60)

        # Configuración de uvicorn
        config = {
            "app": app,
            "host": args.host,
            "port": args.port,
            "log_level": "info"
        }

        if args.dev:
            config.update({
                "reload": True,
                # Usar rutas absolutas para evitar ver/observar otros proyectos
                "reload_dirs": [str(ROOT / "backend"), str(ROOT / "frontend")]
            })
            print("Modo desarrollo: recarga automatica activada")

        uvicorn.run(**config)

    except ImportError as e:
        logger.error(f"Error importando dependencias: {e}")
        print("Error: Faltan dependencias criticas")
        print("Ejecuta: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario")
        logger.info("Servidor detenido por KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        print(f"Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 