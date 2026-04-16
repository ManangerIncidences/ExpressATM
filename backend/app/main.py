from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from .api.routes import router as api_router
from .database import init_database
import os
import signal
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

# Crear directorio de logs ANTES de configurar handlers
os.makedirs("logs", exist_ok=True)

# Configurar logging centralizado con rotación
_log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_file_handler = RotatingFileHandler(
    'logs/app.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
)
_file_handler.setFormatter(_log_formatter)
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(_log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[_file_handler, _stream_handler]
)

# Importar versión
try:
    from version import VERSION
except ImportError:
    VERSION = "2.2.3"

# Lifespan: reemplaza on_event("startup"/"shutdown") deprecados
@asynccontextmanager
async def lifespan(app):
    # Startup
    logging.info("ExpressATM iniciado")
    logging.info("Dashboard disponible")
    logging.info("Documentacion API disponible")
    yield
    # Shutdown
    try:
        from .scheduler_hybrid import monitoring_scheduler
        if monitoring_scheduler.is_running:
            monitoring_scheduler.stop_monitoring()
    except Exception:
        pass
    logging.info("ExpressATM detenido")

# Inicializar la aplicación FastAPI
app = FastAPI(
    title="ExpressATM",
    description="Plataforma de monitoreo y análisis de agencias de lotería",
    version=VERSION,
    lifespan=lifespan
)

# Inicializar base de datos
init_database()

"""Montaje de recursos estáticos"""
try:
    ROOT = Path(__file__).resolve().parents[2]
    FRONTEND = ROOT / "frontend"
    STATIC = FRONTEND / "static"
    LOGOS = FRONTEND / "logos"
    SOUNDS = Path(__file__).resolve().parents[2] / "Sonidos"

    def _has_mount(path_prefix: str) -> bool:
        for r in getattr(app, "routes", []):
            if getattr(r, "path", "") == path_prefix and r.__class__.__name__ == "Mount":
                return True
        return False

    # Montar recursos estáticos si existen y no están montados
    if STATIC.exists() and not _has_mount("/static"):
        app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
    if LOGOS.exists() and not _has_mount("/logos"):
        app.mount("/logos", StaticFiles(directory=str(LOGOS)), name="logos")
    if SOUNDS.exists() and not _has_mount("/sounds"):
        app.mount("/sounds", StaticFiles(directory=str(SOUNDS)), name="sounds")

    def _route_exists(path: str) -> bool:
        for r in getattr(app, "routes", []):
            if getattr(r, "path", "") == path:
                return True
        return False

    def _serve_html(filename: str) -> HTMLResponse:
        file_path = FRONTEND / filename
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                content = file_path.read_text(errors="ignore")
            return HTMLResponse(content)
        return HTMLResponse("Not Found", status_code=404)

    # Rutas auxiliares del frontend (sw.js, favicon)
    if not _route_exists("/sw.js"):

        @app.get("/sw.js")
        def _service_worker():
            sw_path = FRONTEND / "sw.js"
            if sw_path.exists():
                return FileResponse(str(sw_path), media_type="application/javascript")
            return HTMLResponse("Not Found", status_code=404)

    # Favicon
    if not _route_exists("/favicon.ico"):

        @app.get("/favicon.ico")
        def _favicon():
            for cand in (
                LOGOS / "imag_logo.ico",
                LOGOS / "logo.ico",
            ):
                if cand.exists():
                    return FileResponse(str(cand))
            return HTMLResponse(status_code=204)
except Exception as e:
    logging.error(f"Error montando archivos estáticos: {e}")

# Health check para monitoreo del VPS
@app.get("/health")
async def health_check():
    from .database import SessionLocal
    from sqlalchemy import text
    db_status = "ok"
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception:
        db_status = "error"
    return JSONResponse({
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "timestamp": datetime.now().isoformat(),
        "version": app.version
    })

# Shutdown graceful: limpiar scrapers al recibir señal de terminación
def _graceful_shutdown(signum, frame):
    logging.info(f"🛑 Señal {signum} recibida, cerrando scrapers...")
    try:
        from .scheduler_hybrid import monitoring_scheduler
        monitoring_scheduler.stop_monitoring()
    except Exception as e:
        logging.error(f"Error en shutdown graceful: {e}")

try:
    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT, _graceful_shutdown)
except (OSError, ValueError):
    # signal.signal puede fallar en threads secundarios o en Windows sin consola
    pass

# Configurar templates
templates = Jinja2Templates(directory="frontend")

# Incluir rutas de la API
app.include_router(api_router, prefix="/api/v1", tags=["API"])

# Ruta principal para servir el frontend
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Servir la página principal del frontend"""
    return templates.TemplateResponse("index.html", {"request": request})

# Ruta para la vista de Analítica IA
@app.get("/ai", response_class=HTMLResponse)
async def read_ai(request: Request):
    """Servir la vista de análisis de IA"""
    return templates.TemplateResponse("ai.html", {"request": request})

# Ruta para el Dashboard Gráfico
@app.get("/dashboard", response_class=HTMLResponse)
async def read_graph_dashboard(request: Request):
    """Servir la vista del dashboard gráfico"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/reports", response_class=HTMLResponse)
async def read_reports(request: Request):
    """Servir la vista de reportes"""
    reports_html = Path(__file__).resolve().parents[2] / "frontend" / "static" / "reports-dist" / "index.html"
    if reports_html.exists():
        return HTMLResponse(reports_html.read_text(encoding="utf-8"))
    return HTMLResponse("Reports not found", status_code=404)

# Endpoint de bienvenida para la API
@app.get("/api/v1/")
async def api_root():
    """Endpoint raíz de la API"""
    return {
        "message": "Sistema de Monitoreo de Loterías API",
        "version": VERSION,
        "endpoints": {
            "dashboard": "/api/v1/dashboard",
            "alerts": "/api/v1/alerts",
            "agencies": "/api/v1/agencies",
            "monitoring": "/api/v1/monitoring/status",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)

# [INSPECTION_MARKER] Show file content below for analysis