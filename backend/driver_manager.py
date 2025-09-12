import os
from pathlib import Path
from typing import Optional


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
