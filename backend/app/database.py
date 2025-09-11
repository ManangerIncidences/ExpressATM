from sqlalchemy import create_engine
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

def init_database():
    """Inicializar la base de datos y crear las tablas"""
    Base.metadata.create_all(bind=engine)
    print("Base de datos inicializada correctamente") 