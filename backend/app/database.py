from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from .models import Base
from backend.config import Config
import os

# Crear directorio para la base de datos si no existe
os.makedirs("logs", exist_ok=True)

# Configurar el motor de base de datos
engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Necesario para SQLite
)

# Habilitar WAL mode para permitir lecturas concurrentes durante escrituras
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

# Crear las tablas
Base.metadata.create_all(bind=engine)

# Configurar la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependencia para obtener la sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _migrate_alerts_status():
    """Migrar campo is_reported (Boolean) a status (String) si es necesario"""
    inspector = inspect(engine)
    if 'alerts' not in inspector.get_table_names():
        return
    columns = {col['name'] for col in inspector.get_columns('alerts')}
    
    with engine.begin() as conn:
        # Agregar columna status si no existe
        if 'status' not in columns:
            conn.execute(text("ALTER TABLE alerts ADD COLUMN status VARCHAR DEFAULT 'pendiente'"))
            # Migrar datos existentes: is_reported=1 -> 'reportada', is_reported=0 -> 'pendiente'
            if 'is_reported' in columns:
                conn.execute(text("UPDATE alerts SET status = 'reportada' WHERE is_reported = 1"))
                conn.execute(text("UPDATE alerts SET status = 'pendiente' WHERE is_reported = 0 OR is_reported IS NULL"))
            print("Migración: columna 'status' agregada a alerts")
        
        # Agregar columna confirmed_at si no existe
        if 'confirmed_at' not in columns:
            conn.execute(text("ALTER TABLE alerts ADD COLUMN confirmed_at DATETIME"))
            print("Migración: columna 'confirmed_at' agregada a alerts")

        # Agregar columnas del helper de re-alertado
        helper_columns = {
            'sales_at_reported': "FLOAT",
            'balance_at_reported': "FLOAT",
            'sales_at_confirmed': "FLOAT",
            'balance_at_confirmed': "FLOAT",
            'helper_cycle': "INTEGER DEFAULT 0",
            'helper_opt_in': "BOOLEAN DEFAULT 1",
        }
        for col_name, col_type in helper_columns.items():
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}"))
                print(f"Migración: columna '{col_name}' agregada a alerts")

def _ensure_helper_config():
    """Asegurar que exista un registro de configuración del helper"""
    from .models import HelperConfiguracion
    db = SessionLocal()
    try:
        existing = db.query(HelperConfiguracion).first()
        if not existing:
            config = HelperConfiguracion()
            db.add(config)
            db.commit()
            print("Helper: configuración por defecto creada")
    finally:
        db.close()

def init_database():
    """Inicializar la base de datos y crear las tablas"""
    Base.metadata.create_all(bind=engine)
    _migrate_alerts_status()
    _ensure_helper_config()
    print("Base de datos inicializada correctamente")