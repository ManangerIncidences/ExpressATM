"""Script de limpieza controlada del repositorio.

Acciones (por defecto en modo simulación --dry-run):
 1. Eliminar .bat y .ps1 excepto start.bat
 2. Eliminar scripts de actualización de chromedriver
 3. Eliminar archivos de reporte de robustez / logs antiguos
 4. Eliminar carpetas __pycache__
 5. (Opcional con --remove-logs) limpiar carpeta logs/ excepto app.log

Uso:
  python cleanup_repository.py                (simulación)
  python cleanup_repository.py --apply        (ejecuta cambios)
  python cleanup_repository.py --apply --remove-logs

Seguridad:
 - No toca bases de datos *.db ni datos fuente críticos.
 - No elimina drivers/ ni frontend/ ni backend/.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).parent.resolve()

BAT_KEEP = {"start.bat"}
LOG_KEEP = {"app.log"}

def gather_targets(remove_logs: bool):
    to_delete: list[Path] = []

    # 1) .bat / .ps1 excepto start.bat
    for p in ROOT.glob("*.bat"):
        if p.name not in BAT_KEEP:
            to_delete.append(p)
    for p in ROOT.glob("*.ps1"):
        to_delete.append(p)

    # 2) Reportes / logs específicos
    patterns = [
        "reporte_robustez_*.json",
        "suite_robustez_completa.log",
        "test_robustez.log",
    ]
    for pat in patterns:
        for p in ROOT.glob(pat):
            to_delete.append(p)

    # 3) __pycache__ recursivo
    for p in ROOT.rglob("__pycache__"):
        to_delete.append(p)

    # 4) logs/ (opcional)
    if remove_logs:
        logs_dir = ROOT / "logs"
        if logs_dir.is_dir():
            for p in logs_dir.iterdir():
                if p.name not in LOG_KEEP:
                    to_delete.append(p)

    # Deduplicar preservando orden
    seen = set()
    ordered = []
    for p in to_delete:
        if p not in seen:
            ordered.append(p)
            seen.add(p)
    return ordered

def delete_path(p: Path):
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p, ignore_errors=True)
    else:
        try:
            p.unlink(missing_ok=True)
        except TypeError:
            if p.exists():
                p.unlink()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Ejecuta realmente los borrados")
    ap.add_argument("--remove-logs", action="store_true", help="Incluye limpieza de logs/ (excepto app.log)")
    args = ap.parse_args()

    targets = gather_targets(remove_logs=args.remove_logs)
    if not targets:
        print("Nada para eliminar.")
        return

    print("Objetos marcados para eliminar ({}):".format(len(targets)))
    for p in targets:
        print(" -", p.relative_to(ROOT))

    if not args.apply:
        print("\nModo simulación. Añade --apply para ejecutar.")
        return

    for p in targets:
        delete_path(p)
    print("\nEliminación completada.")

if __name__ == "__main__":
    main()
