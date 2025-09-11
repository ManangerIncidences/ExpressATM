from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Agency(Base):
    __tablename__ = "agencies"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # Código de agencia (ej: "011221")
    name = Column(String, index=True)  # Nombre completo de la agencia
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class SalesRecord(Base):
    __tablename__ = "sales_records"
    
    id = Column(Integer, primary_key=True, index=True)
    agency_code = Column(String, index=True)
    agency_name = Column(String)
    sales = Column(Float)  # Ventas
    prizes = Column(Float)  # Premios
    prizes_paid = Column(Float)  # Premios Pagados
    balance = Column(Float)  # Balance
    
    # Nuevo campo para tipo de lotería
    lottery_type = Column(String, index=True)  # 'CHANCE_EXPRESS', 'RULETA_EXPRESS'
    
    # Metadatos de captura
    capture_date = Column(DateTime, default=func.now())
    capture_day = Column(String, index=True)  # YYYY-MM-DD para agrupación diaria
    iteration_time = Column(DateTime, default=func.now())
    
class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    agency_code = Column(String, index=True)
    agency_name = Column(String)
    alert_type = Column(String)  # 'threshold', 'growth_variation', 'sustained_growth'
    alert_message = Column(Text)
    
    # Nuevo campo para tipo de lotería
    lottery_type = Column(String, index=True)  # 'CHANCE_EXPRESS', 'RULETA_EXPRESS'
    
    # Datos que generaron la alerta
    current_sales = Column(Float)
    current_balance = Column(Float)
    previous_sales = Column(Float, nullable=True)
    growth_amount = Column(Float, nullable=True)
    
    # Estado de la alerta
    is_reported = Column(Boolean, default=False)
    reported_at = Column(DateTime, nullable=True)
    
    # Fechas
    alert_date = Column(DateTime, default=func.now())
    alert_day = Column(String, index=True)  # YYYY-MM-DD para reseteo diario
    created_at = Column(DateTime, default=func.now())

class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_date = Column(String, index=True)  # YYYY-MM-DD
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, stopped, error
    total_iterations = Column(Integer, default=0)
    total_agencies_processed = Column(Integer, default=0)
    total_alerts_generated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)  # INFO, WARNING, ERROR
    message = Column(Text)
    module = Column(String)  # scraper, alerts, api, etc.
    timestamp = Column(DateTime, default=func.now())
    session_id = Column(Integer, nullable=True) 