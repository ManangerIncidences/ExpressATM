import os
from pathlib import Path

# Configuración de la aplicación
class Config:
    # Credenciales del sitio web
    LOGIN_URL = "https://app.appltk.com/"
    USERNAME = "Jorge.marte@06"
    PASSWORD = "40200175368Escanio"
    
    # Ruta del ChromeDriver (automática y portable)
    CHROMEDRIVER_PATH = r"C:\Users\pc\documents\projects\expressATM\drivers\chromedriver.exe"
    
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
    
    # Configuración de base de datos
    DATABASE_URL = "sqlite:///./monitoring.db"
    
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
    HEADLESS_MODE = False  # Cambiar a True para modo headless
    
    # Configuración de email (opcional)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_USER = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    
    # Logs
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/monitoring.log"

# Variables globales para compatibilidad
CHROMEDRIVER_PATH = r"C:\Users\pc\documents\projects\expressATM\drivers\chromedriver.exe"