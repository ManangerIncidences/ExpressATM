import os
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field

def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class SiteConfig:
    """Configuración de un sitio de scraping"""
    site_id: str
    login_url: str
    username: str
    password: str
    lotteries: List[Dict[str, str]] = field(default_factory=list)
    # lotteries: [{"name": "CHANCE EXPRESS", "lottery_type": "CHANCE_EXPRESS", "step_key": "chance"}, ...]


SITE_EXPRESS = SiteConfig(
    site_id="express",
    login_url=os.getenv("EXPRESS_LOGIN_URL", "https://app.appltk.com/"),
    username=os.getenv("EXPRESS_USERNAME", "Jorge.marte@06"),
    password=os.getenv("EXPRESS_PASSWORD", "40200175368Escanio"),
    lotteries=[
        {"name": "CHANCE EXPRESS", "lottery_type": "CHANCE_EXPRESS", "step_key": "chance"},
        {"name": "CHANCE EXPRESS EXTRAORDINARIO", "lottery_type": "CHANCE_EXTRAORDINARIO", "step_key": "chance_extra"},
        {"name": "RULETA EXPRESS", "lottery_type": "RULETA_EXPRESS", "step_key": "ruleta"},
    ],
)

SITE_REAL = SiteConfig(
    site_id="real",
    login_url=os.getenv("REAL_LOGIN_URL", "https://app.applotr.com/acceso2.aspx"),
    username=os.getenv("REAL_USERNAME", "jorge.marte@06"),
    password=os.getenv("REAL_PASSWORD", "40200175368"),
    lotteries=[
        {"name": "DOMINO REAL", "lottery_type": "DOMINO_REAL", "step_key": "domino_real"},
        {"name": "LOTO POOL REAL", "lottery_type": "LOTO_POOL_REAL", "step_key": "loto_pool_real"},
        {"name": "LOTO REAL", "lottery_type": "LOTO_REAL", "step_key": "loto_real"},
        {"name": "NUEVA YOL REAL", "lottery_type": "NUEVA_YOL_REAL", "step_key": "nueva_yol_real"},
        {"name": "NUEVA YOL REAL 5 MIN", "lottery_type": "NUEVA_YOL_REAL_5MIN", "step_key": "nueva_yol_5min"},
        {"name": "PEGA 3 REAL", "lottery_type": "PEGA_3_REAL", "step_key": "pega_3_real"},
        # {"name": "PEGA 4 REAL", "lottery_type": "PEGA_4_REAL", "step_key": "pega_4_real"},  # temporalmente deshabilitado
        # {"name": "SUEÑO REAL", "lottery_type": "SUENO_REAL", "step_key": "sueno_real"},  # temporalmente deshabilitado
        {"name": "RAPIDITA EXTRAORDINARIA", "lottery_type": "RAPIDITA_EXTRAORDINARIA", "step_key": "rapidita_extraordinaria"},
        {"name": "REPARTIDERA REAL", "lottery_type": "REPARTIDERA_REAL", "step_key": "repartidera_real"},
        {"name": "TU FECHA REAL", "lottery_type": "TU_FECHA_REAL", "step_key": "tu_fecha_real"},
    ],
)

ALL_SITES = [SITE_EXPRESS, SITE_REAL]


# Configuración de la aplicación
class Config:
    # Credenciales del sitio web (legacy — usadas como fallback si no se provee SiteConfig)
    LOGIN_URL = os.getenv("EXPRESS_LOGIN_URL", "https://app.appltk.com/")
    USERNAME = os.getenv("EXPRESS_USERNAME", "Jorge.marte@06")
    PASSWORD = os.getenv("EXPRESS_PASSWORD", "40200175368Escanio")
    
    # Ruta del ChromeDriver (automática y portable)
    # Puede ser provista por entorno; si no, se detecta automáticamente en runtime
    CHROMEDRIVER_PATH: Optional[str] = os.getenv("CHROMEDRIVER_PATH")
    
    # Selectores CSS/XPath para automatización
    SELECTORS = {
        # Login
        "username_input": "#txtUser",
        "password_input": "#txtPwd", 
        "login_button": "#icmdLogin",
        
        # Navegación
        "monitoreo_menu": "a[href='#']:has(span:contains('Monitoreo'))",
        "monitor_ventas": "a[href='Monitor.aspx']",
        
        # Filtros - usando selectores más específicos para Element UI
        "tipo_loteria_select": ".el-select__wrapper:has(+ *:contains('Tipo Lotería')) .el-select__selection",
        "tipo_loteria_option_no_tradicionales": "li:contains('Loterias No Tradicionales')",
        
        "loteria_select": ".el-select__wrapper:has(+ *:contains('Lotería')) .el-select__selection", 
        "loteria_option_chance_express": "li:contains('CHANCE EXPRESS')",
        
        "filtro_select": ".el-select__wrapper:has(+ *:contains('Filtro')) .el-select__selection",
        "filtro_option_ventas_mayor": "li:contains('Ventas Mayor o Igual a')",
        
        "monto_input": "input[id*='el-id-'][min='0']",
        "buscar_button": ".btn-primary:contains('Buscar')",
        
        # Tabla de resultados
        "results_table": "table.table-bordered tbody",
        "table_rows": "table.table-bordered tbody tr:not(:first-child)", # Excluir Total General
        "cargar_mas_btn": "a:contains('Cargar más')"
    }
    
    # Configuración de base de datos (ruta absoluta para evitar ambigüedad con cwd)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{Path(__file__).resolve().parent.parent / 'monitoring.db'}"
    )
    
    # Configuración de alertas
    ALERT_THRESHOLDS = {
        "balance_threshold": 6000,
        "sales_threshold": 20000,
        "growth_variation": 1500,
        "sustained_growth": 500
    }
    # Flags dinámicos para filtros y alertas
    FILTER_SURIEL = True
    FILTER_TOTAL_GENERAL = True
    ENABLE_GROWTH_ALERTS = True
    ENABLE_THRESHOLD_ALERTS = True
    
    # Configuración de monitoreo
    MONITORING_INTERVAL = 15  # minutos
    
    # Configuración de tiempos de espera
    WAIT_TIME_PAGE_LOAD = 10  # segundos
    WAIT_TIME_ELEMENT = 5     # segundos
    
    # Configuración de navegador
    HEADLESS_MODE = _bool_env("CHROME_HEADLESS", False)
    
    # Configuración de email (opcional)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_USER = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    
    # Logs
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/monitoring.log")

# Variables globales legacy para compatibilidad (se usarán si se importan directamente)
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")