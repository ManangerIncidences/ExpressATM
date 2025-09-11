#!/usr/bin/env python3
"""
Limpieza de producción: elimina .py innecesarios (tests y utilidades) y conserva solo lo esencial
- Modo por defecto: dry-run (solo lista)
- Para aplicar: python cleanup_production.py --apply
"""
import os
import sys
from pathlib import Path
from fnmatch import fnmatch

ROOT = Path(__file__).resolve().parent

# Directorios y archivos esenciales
KEEP_DIRS = {
    'backend',
    'frontend',
    'drivers',
    'logs',
    'intelligence_models',
}

KEEP_ROOT_FILES = {
    'run.py',
    'start.bat',
    'README.md',  # Será eliminado si se solicita borrar .md (control más abajo)
    'configuracion_especifica_chance.py',
    'DataAgencias.xlsx',
    'monitoring.db',
    'dom_intelligence.db',
    'vision_learning.db',
}

# Módulos esenciales dentro de backend/app
KEEP_BACKEND_APP_FILES = {
    '__init__.py',
    'main.py',
    'database.py',
    'models.py',
    'alerts.py',
    'scheduler.py',
    'scheduler_hybrid.py',  # se conserva como fallback
    'scraper.py',
    'web_driver_observer.py',
    'dom_intelligence.py',
    'dom_learning_engine.py',
    'intelligence.py',
    'agency_behavior_analyzer.py',
    'agency_matcher.py',
}

# API
KEEP_BACKEND_APP_API_FILES = {
    '__init__.py',
    'routes.py',
}

# Archivos de respaldo/experimentales a eliminar si existen
DELETE_BACKEND_APP_OPTIONAL = {
    'scraper_backup.py',
    'scheduler_original_backup.py',
    'scraper_intelligent.py',
    'vision_learning_engine.py',
}

# Patrones de tests/utilidades a eliminar en raíz
DELETE_PATTERNS_ROOT = [
    'test_*.py',
    '*test*.py',
    '*verificacion*.py',
    '*verify*.py',
    '*diagnostico*.py',
    '*integracion*.py',
    '*instal*robusto*.py',
    '*fix*database*.py',
    '*fix*monitor*.py',
    '*quick*test*.py',
    '*probar*iteracion*.py',
    '*stability*.py',
    '*suite*robustez*.py',
    '*ejecutar*robustez*.py',
    '*descargar*chromedriver*.py',
    '*actualizar*dependencias*.py',
    '*analizar*base*datos*.py',
    '*corregir*base*datos*.py',
    '*corregir*rutas*.py',
    'ExpressATM_Launcher.py',
    'integration_routes_addon.py',
]


def should_keep_root_file(p: Path) -> bool:
    if p.name in KEEP_ROOT_FILES:
        return True
    # mantener este script
    if p.name == 'cleanup_production.py':
        return True
    return False


def list_doc_candidates() -> list[Path]:
    """Listar todos los .md y .txt recursivamente para borrar."""
    docs = []
    # Excluir .venv y __pycache__
    exclude_dirs = {'.venv', '__pycache__'}
    for p in ROOT.rglob('*'):
        if p.is_dir():
            continue
        if any(part in exclude_dirs for part in p.parts):
            continue
        if p.suffix.lower() in {'.md', '.txt'}:
            docs.append(p)
    return docs


def list_candidates() -> list[Path]:
    to_delete: list[Path] = []

    # 0) Documentos (.md, .txt) en todo el repo
    to_delete.extend(list_doc_candidates())

    # 1) Raíz: eliminar .py no esenciales según patrones
    for p in ROOT.glob('*.py'):
        if should_keep_root_file(p):
            continue
        # marcar si coincide patrón de borrado
        if any(fnmatch(p.name, pat) for pat in DELETE_PATTERNS_ROOT):
            to_delete.append(p)
        else:
            # scripts sueltos no esenciales (conservamos solo run.py y configuracion_especifica_chance.py)
            to_delete.append(p)

    # 2) backend/config.py se conserva; otros .py fuera de app también
    backend_dir = ROOT / 'backend'
    if backend_dir.exists():
        for p in backend_dir.glob('*.py'):
            if p.name == 'config.py':
                continue
            # otros .py en backend raíz se eliminan
            to_delete.append(p)

        # 3) backend/app
        app_dir = backend_dir / 'app'
        if app_dir.exists():
            for p in app_dir.glob('*.py'):
                if p.name in KEEP_BACKEND_APP_FILES:
                    continue
                if p.name in DELETE_BACKEND_APP_OPTIONAL:
                    to_delete.append(p)
                else:
                    # módulos no listados explícitamente se eliminan
                    to_delete.append(p)

            # 4) backend/app/api
            api_dir = app_dir / 'api'
            if api_dir.exists():
                for p in api_dir.glob('*.py'):
                    if p.name in KEEP_BACKEND_APP_API_FILES:
                        continue
                    to_delete.append(p)

    # Depurar duplicados
    unique = []
    seen = set()
    for p in to_delete:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if rp not in seen:
            unique.append(p)
            seen.add(rp)
    return unique


def main():
    apply = '--apply' in sys.argv

    candidates = list_candidates()

    print('\nLimpieza de producción (dry-run=%s)\n' % (not apply))
    if not candidates:
        print('No hay archivos para eliminar. ✅')
        return 0

    print('Archivos que se eliminarían (%d):' % len(candidates))
    for p in candidates:
        try:
            print(' -', p.relative_to(ROOT))
        except Exception:
            print(' -', p)

    if not apply:
        print('\nEjecuta con --apply para eliminar estos archivos de forma irreversible.')
        return 0

    # Aplicar borrado
    errors = 0
    removed = 0
    for p in candidates:
        try:
            p.unlink(missing_ok=True)
            removed += 1
        except Exception as e:
            errors += 1
            print(f'❌ No se pudo eliminar {p}: {e}')

    print('\nResumen:')
    print(' Eliminados:', removed)
    print(' Fallidos  :', errors)
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
