"""
Instalador/actualizador de ChromeDriver para ExpressATM usando webdriver-manager.

- Descarga el ChromeDriver compatible con la versión de Chrome instalada (si existe).
- Copia el binario descargado al directorio local ./drivers/chromedriver.exe para compatibilidad con scripts existentes.
- Imprime la ruta final y la versión detectada.

Se ejecuta con el Python del entorno virtual preferentemente.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def ensure_drivers_dir() -> Path:
    drivers = Path(__file__).resolve().parents[1] / "drivers"
    drivers.mkdir(parents=True, exist_ok=True)
    return drivers


def install_chromedriver() -> Path:
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as e:  # pragma: no cover - entorno sin dependencia
        print("ERROR: webdriver-manager no está instalado.")
        print("Sugerencia: pip install webdriver-manager")
        raise

    # Descarga el driver adecuado (usa cache de usuario)
    path = ChromeDriverManager().install()
    return Path(path)


def copy_driver_to_local(src_path: Path, dst_dir: Path) -> Path:
    dst_path = dst_dir / ("chromedriver.exe" if os.name == "nt" else "chromedriver")
    try:
        shutil.copy2(src_path, dst_path)
        return dst_path
    except Exception:
        # Si falla la copia (permisos, antivirus), al menos informamos la ruta original
        return src_path


def get_driver_version(driver_path: Path) -> str | None:
    try:
        out = subprocess.check_output([str(driver_path), "--version"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)

    print("\n=== ExpressATM - Configuración de ChromeDriver (webdriver-manager) ===\n")
    drivers_dir = ensure_drivers_dir()
    try:
        cache_driver_path = install_chromedriver()
        print(f"Ruta del driver en caché: {cache_driver_path}")
    except Exception as e:
        print(f"❌ Error instalando ChromeDriver con webdriver-manager: {e}")
        return 1

    final_driver = copy_driver_to_local(cache_driver_path, drivers_dir)
    if final_driver.exists():
        print(f"✅ ChromeDriver disponible en: {final_driver}")
    else:
        print("⚠️ No se pudo copiar a carpeta local 'drivers'. Se usará la ruta en caché.")
        final_driver = cache_driver_path

    version = get_driver_version(final_driver)
    if version:
        print(f"🔍 Versión de ChromeDriver: {version}")
        print("✅ Instalación/actualización completada.")
        return 0
    else:
        print("⚠️ No se pudo verificar la versión ejecutando el binario. Verifique permisos/antivirus.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
