from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from .api.routes import router as api_router
from .database import init_database
import os
import logging

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
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
if os.path.isdir("Sonidos"):
    app.mount("/sounds", StaticFiles(directory="Sonidos"), name="sounds")
logo_dir_frontend = os.path.join("frontend", "logos")
if os.path.isdir(logo_dir_frontend):
    app.mount("/logos", StaticFiles(directory=logo_dir_frontend), name="logos")
elif os.path.isdir("logos"):
    # Fallback si el usuario decide mover la carpeta al raíz
    app.mount("/logos", StaticFiles(directory="logos"), name="logos")

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