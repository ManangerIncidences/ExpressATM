from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from .api.routes import router as api_router
from .database import init_database
import os
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

# Crear directorio de logs si no existe
os.makedirs("logs", exist_ok=True)

# Inicializar la aplicación FastAPI
app = FastAPI(
    title="ExpressATM",
    description="Plataforma de monitoreo y análisis de agencias de lotería",
    version="1.0.0"
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

    # Rutas principales del frontend
    if not _route_exists("/"):

        @app.get("/", response_class=HTMLResponse)
        def _root():
            return _serve_html("index.html")

    if not _route_exists("/dashboard"):

        @app.get("/dashboard", response_class=HTMLResponse)
        def _dashboard():
            return _serve_html("dashboard.html")

    if not _route_exists("/ai"):

        @app.get("/ai", response_class=HTMLResponse)
        def _ai():
            return _serve_html("ai.html")

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
except Exception:
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

# Endpoint de bienvenida para la API
@app.get("/api/v1/")
async def api_root():
    """Endpoint raíz de la API"""
    return {
        "message": "Sistema de Monitoreo de Loterías API",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/api/v1/dashboard",
            "alerts": "/api/v1/alerts",
            "agencies": "/api/v1/agencies",
            "monitoring": "/api/v1/monitoring/status",
            "docs": "/docs"
        }
    }

# Manejo de eventos de inicio y cierre
@app.on_event("startup")
async def startup_event():
    """Eventos al iniciar la aplicación"""
    logging.info("ExpressATM iniciado")
    logging.info("Dashboard disponible")
    logging.info("Documentacion API disponible")

@app.on_event("shutdown")
async def shutdown_event():
    """Eventos al cerrar la aplicación"""
    from .scheduler import monitoring_scheduler
    if monitoring_scheduler.is_running:
        monitoring_scheduler.stop_monitoring()
    logging.info("ExpressATM detenido")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)

# [INSPECTION_MARKER] Show file content below for analysis