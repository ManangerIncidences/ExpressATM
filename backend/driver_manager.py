import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any


def get_chromedriver_path() -> str:
    """Obtiene la ruta del ChromeDriver automáticamente.

    Intenta:
      1) Variable de entorno CHROMEDRIVER_PATH
      2) webdriver-manager para descarga/gestión automática
      3) Fallback a drivers locales conocidos en el repo
    """
    env_path = os.getenv("CHROMEDRIVER_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    try:
        from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
        # webdriver-manager devuelve la ruta del binario instalado en cache
        return ChromeDriverManager().install()
    except Exception:
        pass

    # Fallback: buscar en directorios locales
    candidates = [
        Path("drivers/chromedriver.exe"),
        Path("drivers/chromedriver-win64/chromedriver.exe"),
        Path("drivers/chromedriver"),
        Path("../drivers/chromedriver.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p.resolve())

    raise FileNotFoundError(
        "ChromeDriver no encontrado. Configure CHROMEDRIVER_PATH o instale Chrome/Driver compatible."
    )


def build_chrome_service():
    """Crea el Service de Selenium para Chrome usando la ruta detectada."""
    from selenium.webdriver.chrome.service import Service  # type: ignore

    return Service(get_chromedriver_path())


def get_chrome_binary_path() -> Optional[str]:
    """Detecta la ruta del binario de Chrome/Chromium en Windows de forma heurística.

    Respeta la variable de entorno CHROME_BINARY si está presente.
    Explora ubicaciones comunes de instalación para Windows.
    """
    env_bin = os.getenv("CHROME_BINARY")
    if env_bin and Path(env_bin).exists():
        return str(Path(env_bin).resolve())

    candidates = []
    # Rutas típicas en Windows
    program_files = os.getenv("PROGRAMFILES", r"C:\\Program Files")
    program_files_x86 = os.getenv("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
    local_app_data = os.getenv("LOCALAPPDATA", os.path.expanduser(r"~\\AppData\\Local"))

    candidates.extend([
        Path(program_files) / "Google/Chrome/Application/chrome.exe",
        Path(program_files_x86) / "Google/Chrome/Application/chrome.exe",
        Path(local_app_data) / "Google/Chrome/Application/chrome.exe",
        # Opcionales: soportar Chromium portable si se incluye en el repo
        Path("drivers/chrome-win64/chrome.exe"),
        Path("drivers/chrome-win/chrome.exe"),
    ])

    for p in candidates:
        if p and Path(p).exists():
            return str(Path(p).resolve())

    return None


def get_chrome_and_driver_info() -> Dict[str, Any]:
    """Devuelve información útil de diagnóstico para Chrome/Driver.

    Incluye rutas detectadas, env y notas, para logging/soporte.
    """
    info: Dict[str, Any] = {}
    try:
        info["env_CHROMEDRIVER_PATH"] = os.getenv("CHROMEDRIVER_PATH")
        info["env_CHROME_BINARY"] = os.getenv("CHROME_BINARY")
        try:
            info["chromedriver_path"] = get_chromedriver_path()
        except Exception as e:
            info["chromedriver_path_error"] = str(e)
        info["chrome_binary_path"] = get_chrome_binary_path()
    except Exception as e:
        info["error"] = str(e)
    return info
