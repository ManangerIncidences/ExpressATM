#!/usr/bin/env python3
"""
ExpressATM - Sistema de Monitoreo para Agencias de Lotería
===========================================================

Este archivo sirve como punto de entrada principal para la aplicación ExpressATM.
Configura el servidor FastAPI y maneja la inicialización del sistema.

Uso:
    python run.py [--port PORT] [--host HOST] [--dev]

Argumentos:
    --port, -p      Puerto del servidor (default: 8000)
    --host          Host del servidor (default: 0.0.0.0)
    --dev           Modo desarrollo con recarga automática
    --help, -h      Mostrar esta ayuda

Ejemplos:
    python run.py                    # Servidor en puerto 8000
    python run.py --port 8080        # Servidor en puerto 8080
    python run.py --dev              # Modo desarrollo
"""

import argparse
import sys
import os
import logging
from pathlib import Path

# Añadir el directorio raíz al path de Python
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Configura el sistema de logging"""
    # Crear directorio de logs si no existe
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configurar formato de logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / "app.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configurar codificación UTF-8 para Windows
    if sys.platform == "win32":
        try:
            # Intentar configurar codificación UTF-8 en Windows
            os.system("chcp 65001 > nul 2>&1")
        except:
            pass

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
        if path.exists() or (isinstance(path, str) and os.system(f"which {path} > /dev/null 2>&1") == 0):
            return True
    
    print("⚠️ ChromeDriver no encontrado")
    print("💡 Ejecuta uno de estos comandos:")
    print("   - Windows: python update_chromedriver.py")
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
    
    args = parser.parse_args()
    
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
    
    # Configurar variables de entorno desde .env si existe
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
                "reload_dirs": ["backend", "frontend"]
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