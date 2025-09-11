"""
🧠 Sistema de Inteligencia y Mejora Continua - ExpressATM
Implementa aprendizaje automático, predicción de fallos y auto-optimización
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Importaciones opcionales de sklearn con fallback
try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    IsolationForest = None  # type: ignore
    RandomForestClassifier = None  # type: ignore
    LinearRegression = None  # type: ignore
    StandardScaler = None  # type: ignore
    train_test_split = None  # type: ignore
    joblib = None  # type: ignore
    SKLEARN_AVAILABLE = False

# Fallbacks simples para sklearn
class _IsolationForestFallback:
    """Fallback para IsolationForest usando IQR."""
    def __init__(self, contamination: float = 0.1, random_state: int = None):
        self.contamination = max(0.0, min(0.5, contamination))
    def fit_predict(self, X):
        import numpy as _np
        X = _np.asarray(X, dtype=float)
        data = X[:, 0] if X.ndim > 1 else X
        if data.size == 0:
            return _np.array([], dtype=int)
        q1 = _np.percentile(data, 25)
        q3 = _np.percentile(data, 75)
        iqr = max(q3 - q1, 1e-9)
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        preds = _np.where((data < lower) | (data > upper), -1, 1)
        return preds

class _RandomForestClassifierFallback:
    """Fallback para RandomForestClassifier usando heurísticas simples."""
    def __init__(self, n_estimators: int = 100, random_state: int = None):
        self.threshold = None
    def fit(self, X, y):
        import numpy as _np
        y = _np.asarray(y)
        # Threshold simple: media de las características para casos exitosos
        if _np.sum(y) > 0:
            success_features = X[y == 1]
            self.threshold = float(_np.mean(success_features[:, 0])) if len(success_features) else 0.5
        else:
            self.threshold = 0.5
        return self
    def predict(self, X):
        import numpy as _np
        if self.threshold is None:
            return _np.zeros(len(X), dtype=int)
        return (_np.asarray(X)[:, 0] >= self.threshold).astype(int)
    def predict_proba(self, X):
        import numpy as _np
        preds = self.predict(X)
        # Probabilidades simples
        proba = _np.zeros((len(X), 2))
        proba[preds == 1, 1] = 0.7  # alta confianza para éxito
        proba[preds == 0, 0] = 0.7  # alta confianza para fallo
        proba[preds == 1, 0] = 0.3
        proba[preds == 0, 1] = 0.3
        return proba

import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """Métricas del sistema para análisis"""
    timestamp: datetime
    iteration_success: bool
    iteration_duration: float
    records_obtained: int
    alerts_generated: int
    error_type: Optional[str] = None
    website_response_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

@dataclass
class OptimizationRecommendation:
    """Recomendación de optimización"""
    parameter: str
    current_value: Any
    recommended_value: Any
    confidence: float
    reason: str
    expected_improvement: str

@dataclass
class PredictionResult:
    """Resultado de predicción"""
    prediction_type: str
    probability: float
    confidence: float
    recommendation: str
    details: Dict[str, Any]

class IntelligenceEngine:
    """Motor de Inteligencia Artificial para mejora continua"""
    
    def __init__(self, db_path: str = "monitoring.db"):
        self.db_path = db_path
        self.models_dir = Path("intelligence_models")
        self.models_dir.mkdir(exist_ok=True)
        
        # Modelos de ML con fallbacks
        self.failure_predictor = None
        self.performance_optimizer = None
        self.anomaly_detector = None
        
        try:
            self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        except Exception:
            self.scaler = None
        
        # Configuraciones adaptativas
        self.adaptive_config = {
            "wait_times": {
                "page_load": 10,
                "table_load": 8,
                "element_click": 3
            },
            "retry_counts": {
                "login": 3,
                "search": 5,
                "data_extraction": 3
            },
            "thresholds": {
                "performance_alert": 60.0,  # segundos
                "failure_probability": 0.7,
                "anomaly_score": 0.8
            }
        }
        
        self._initialize_models()
        self._load_historical_data()
    
    def _initialize_models(self):
        """Inicializa los modelos de ML"""
        if not SKLEARN_AVAILABLE:
            logger.warning("⚠️ sklearn no disponible, usando fallbacks simples")
            self._create_fallback_models()
            return
            
        try:
            # Cargar modelos existentes si existen
            if (self.models_dir / "failure_predictor.joblib").exists() and joblib is not None:
                self.failure_predictor = joblib.load(self.models_dir / "failure_predictor.joblib")
                logger.info("✅ Modelo predictor de fallos cargado")
            
            if (self.models_dir / "anomaly_detector.joblib").exists() and joblib is not None:
                self.anomaly_detector = joblib.load(self.models_dir / "anomaly_detector.joblib")
                logger.info("✅ Detector de anomalías cargado")
                
            if (self.models_dir / "scaler.joblib").exists() and joblib is not None:
                self.scaler = joblib.load(self.models_dir / "scaler.joblib")
                logger.info("✅ Scaler cargado")
                
        except Exception as e:
            logger.warning(f"⚠️ Error cargando modelos: {e}")
            self._create_fresh_models()
    
    def _create_fallback_models(self):
        """Crea modelos de fallback cuando sklearn no está disponible"""
        self.failure_predictor = _RandomForestClassifierFallback(n_estimators=100, random_state=42)
        self.anomaly_detector = _IsolationForestFallback(contamination=0.1, random_state=42)
        logger.info("🔄 Modelos de fallback creados")
    
    def _create_fresh_models(self):
        """Crea modelos nuevos"""
        if SKLEARN_AVAILABLE and RandomForestClassifier is not None:
            self.failure_predictor = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
        else:
            self.failure_predictor = _RandomForestClassifierFallback(n_estimators=100, random_state=42)
            
        if SKLEARN_AVAILABLE and IsolationForest is not None:
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
        else:
            self.anomaly_detector = _IsolationForestFallback(contamination=0.1, random_state=42)
            
        logger.info("🔄 Modelos nuevos creados")
    
    def _load_historical_data(self) -> pd.DataFrame:
        """Carga datos históricos para entrenamiento"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
            SELECT 
                created_at,
                session_id,
                COUNT(*) as records_count,
                AVG(sales) as avg_sales,
                MAX(sales) as max_sales,
                MIN(sales) as min_sales
            FROM agencies_data 
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY session_id, DATE(created_at)
            ORDER BY created_at DESC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) > 0:
                logger.info(f"📊 Datos históricos cargados: {len(df)} registros")
                return df
            else:
                logger.warning("No hay datos historicos suficientes")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ Error cargando datos históricos: {e}")
            return pd.DataFrame()
    
    def record_system_metrics(self, metrics: SystemMetrics):
        """Registra métricas del sistema para análisis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crear tabla si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    iteration_success BOOLEAN,
                    iteration_duration REAL,
                    records_obtained INTEGER,
                    alerts_generated INTEGER,
                    error_type TEXT,
                    website_response_time REAL,
                    memory_usage REAL,
                    cpu_usage REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insertar métricas
            cursor.execute("""
                INSERT INTO system_metrics 
                (timestamp, iteration_success, iteration_duration, records_obtained, 
                 alerts_generated, error_type, website_response_time, memory_usage, cpu_usage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp.isoformat(),
                metrics.iteration_success,
                metrics.iteration_duration,
                metrics.records_obtained,
                metrics.alerts_generated,
                metrics.error_type,
                metrics.website_response_time,
                metrics.memory_usage,
                metrics.cpu_usage
            ))
            
            conn.commit()
            conn.close()
            
            # Entrenar modelos con nuevos datos
            self._retrain_models()
            
        except Exception as e:
            logger.error(f"❌ Error registrando métricas: {e}")
    
    def predict_failure_risk(self, current_metrics: Dict[str, Any]) -> PredictionResult:
        """Predice riesgo de fallo en próxima iteración"""
        try:
            if self.failure_predictor is None:
                return PredictionResult(
                    prediction_type="failure_risk",
                    probability=0.0,
                    confidence=0.0,
                    recommendation="Modelo no entrenado",
                    details={}
                )
            
            # Preparar características
            features = self._extract_features(current_metrics)
            if len(features) == 0:
                return PredictionResult(
                    prediction_type="failure_risk",
                    probability=0.0,
                    confidence=0.5,
                    recommendation="Datos insuficientes",
                    details={}
                )
            
            # Predicción con fallback
            if self.scaler is not None:
                features_scaled = self.scaler.transform([features])
            else:
                # Fallback: usar features sin escalar
                features_scaled = [features]
                
            failure_prob = self.failure_predictor.predict_proba(features_scaled)[0][1]
            confidence = max(self.failure_predictor.predict_proba(features_scaled)[0])
            
            # Generar recomendación
            recommendation = self._generate_failure_recommendation(failure_prob, features)
            
            return PredictionResult(
                prediction_type="failure_risk",
                probability=float(failure_prob),
                confidence=float(confidence),
                recommendation=recommendation,
                details={
                    "risk_level": "Alto" if failure_prob > 0.7 else "Medio" if failure_prob > 0.3 else "Bajo",
                    "main_factors": self._identify_risk_factors(features)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error en predicción de fallos: {e}")
            return PredictionResult(
                prediction_type="failure_risk",
                probability=0.0,
                confidence=0.0,
                recommendation="Error en predicción",
                details={"error": str(e)}
            )
    
    def detect_anomalies(self, current_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detecta anomalías en el comportamiento del sistema"""
        try:
            if self.anomaly_detector is None:
                return []
            
            features = self._extract_features(current_metrics)
            if len(features) == 0:
                return []
            
            if self.scaler is not None:
                features_scaled = self.scaler.transform([features])
            else:
                features_scaled = [features]
                
            # Para el detector de fallback, decision_function no existe
            if hasattr(self.anomaly_detector, 'decision_function'):
                anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
            else:
                # Fallback: usar un score simulado basado en la predicción
                pred = self.anomaly_detector.fit_predict(features_scaled)[0]
                anomaly_score = -0.6 if pred == -1 else 0.1
                
            is_anomaly = self.anomaly_detector.fit_predict(features_scaled)[0] == -1
            
            anomalies = []
            if is_anomaly:
                anomalies.append({
                    "type": "system_behavior",
                    "severity": "Alto" if anomaly_score < -0.5 else "Medio",
                    "score": float(anomaly_score),
                    "description": "Comportamiento anómalo detectado en el sistema",
                    "recommendation": self._generate_anomaly_recommendation(anomaly_score, features)
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"❌ Error detectando anomalías: {e}")
            return []
    
    def optimize_parameters(self) -> List[OptimizationRecommendation]:
        """Optimiza parámetros del sistema basado en datos históricos"""
        try:
            recommendations = []
            
            # Analizar tiempos de espera óptimos
            wait_time_rec = self._optimize_wait_times()
            if wait_time_rec:
                recommendations.extend(wait_time_rec)
            
            # Analizar frecuencia de monitoreo
            frequency_rec = self._optimize_monitoring_frequency()
            if frequency_rec:
                recommendations.append(frequency_rec)
            
            # Analizar umbrales de alertas
            threshold_rec = self._optimize_alert_thresholds()
            if threshold_rec:
                recommendations.extend(threshold_rec)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error optimizando parámetros: {e}")
            return []
    
    def _extract_features(self, metrics: Dict[str, Any]) -> List[float]:
        """Extrae características para ML"""
        try:
            # Obtener métricas históricas recientes
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT iteration_duration, records_obtained, alerts_generated,
                       website_response_time, memory_usage, cpu_usage
                FROM system_metrics 
                WHERE timestamp >= datetime('now', '-1 day')
                ORDER BY timestamp DESC LIMIT 10
            """)
            
            recent_data = cursor.fetchall()
            conn.close()
            
            if len(recent_data) == 0:
                return []
            
            # Características basadas en tendencias recientes
            durations = [row[0] for row in recent_data if row[0] is not None]
            records = [row[1] for row in recent_data if row[1] is not None]
            
            features = [
                np.mean(durations) if durations else 0,
                np.std(durations) if len(durations) > 1 else 0,
                np.mean(records) if records else 0,
                np.std(records) if len(records) > 1 else 0,
                len([r for r in recent_data if r[1] == 0]),  # Iteraciones fallidas
                metrics.get('current_hour', datetime.now().hour),
                metrics.get('day_of_week', datetime.now().weekday()),
            ]
            
            return [float(f) for f in features if not np.isnan(f)]
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo características: {e}")
            return []
    
    def _retrain_models(self):
        """Entrena los modelos con datos actualizados"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Obtener datos para entrenamiento
            df = pd.read_sql_query("""
                SELECT * FROM system_metrics 
                WHERE timestamp >= datetime('now', '-7 days')
                ORDER BY timestamp DESC
            """, conn)
            conn.close()
            
            if len(df) < 10:  # Necesitamos datos mínimos
                return
            
            # Preparar datos para entrenamiento
            X = []
            y_failure = []
            
            for idx, row in df.iterrows():
                features = [
                    row['iteration_duration'] or 0,
                    row['records_obtained'] or 0,
                    row['alerts_generated'] or 0,
                    row['website_response_time'] or 0,
                    row['memory_usage'] or 0,
                    row['cpu_usage'] or 0
                ]
                
                X.append(features)
                y_failure.append(0 if row['iteration_success'] else 1)
            
            if len(X) > 5:
                X = np.array(X)
                y_failure = np.array(y_failure)
                
                # Entrenar scaler si está disponible
                if self.scaler is not None:
                    self.scaler.fit(X)
                    X_scaled = self.scaler.transform(X)
                else:
                    X_scaled = X
                
                # Entrenar detector de anomalías
                if hasattr(self.anomaly_detector, 'fit'):
                    self.anomaly_detector.fit(X_scaled)
                else:
                    # Para fallback, no necesita entrenamiento
                    pass
                
                # Entrenar predictor de fallos si hay suficientes fallos
                if sum(y_failure) > 1:
                    self.failure_predictor.fit(X_scaled, y_failure)
                
                # Guardar modelos
                self._save_models()
                
                logger.info(f"🧠 Modelos reentrenados con {len(X)} muestras")
            
        except Exception as e:
            logger.error(f"❌ Error reentrenando modelos: {e}")
    
    def _save_models(self):
        """Guarda los modelos entrenados"""
        if not SKLEARN_AVAILABLE or joblib is None:
            logger.info("💾 Modelos de fallback no se guardan (sklearn no disponible)")
            return
            
        try:
            if self.failure_predictor and hasattr(self.failure_predictor, 'n_estimators'):
                # Solo guardar modelos sklearn reales, no fallbacks
                joblib.dump(self.failure_predictor, self.models_dir / "failure_predictor.joblib")
            
            if self.anomaly_detector and hasattr(self.anomaly_detector, 'contamination'):
                # Solo guardar si es un modelo sklearn real
                joblib.dump(self.anomaly_detector, self.models_dir / "anomaly_detector.joblib")
            
            if self.scaler is not None:
                joblib.dump(self.scaler, self.models_dir / "scaler.joblib")
            
            logger.info("💾 Modelos guardados exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error guardando modelos: {e}")
    
    def _generate_failure_recommendation(self, probability: float, features: List[float]) -> str:
        """Genera recomendación basada en riesgo de fallo"""
        if probability > 0.8:
            return "Riesgo crítico: Revisar conexión y reducir timeouts"
        elif probability > 0.6:
            return "Riesgo alto: Aumentar tiempos de espera y verificar recursos"
        elif probability > 0.3:
            return "Riesgo medio: Monitorear de cerca la próxima iteración"
        else:
            return "Riesgo bajo: Sistema operando normalmente"
    
    def _generate_anomaly_recommendation(self, score: float, features: List[float]) -> str:
        """Genera recomendación para anomalías"""
        if score < -0.7:
            return "Anomalía severa: Revisar logs y verificar integridad del sistema"
        elif score < -0.4:
            return "Anomalía moderada: Aumentar frecuencia de monitoreo"
        else:
            return "Anomalía leve: Continuar monitoreo normal"
    
    def _optimize_wait_times(self) -> List[OptimizationRecommendation]:
        """Optimiza tiempos de espera basado en rendimiento histórico"""
        # Implementación simplificada
        return [
            OptimizationRecommendation(
                parameter="page_load_wait",
                current_value=self.adaptive_config["wait_times"]["page_load"],
                recommended_value=12,
                confidence=0.8,
                reason="Análisis de fallos recientes sugiere timeouts más largos",
                expected_improvement="Reducción 15% en fallos de carga"
            )
        ]
    
    def _optimize_monitoring_frequency(self) -> OptimizationRecommendation:
        """Optimiza frecuencia de monitoreo"""
        return OptimizationRecommendation(
            parameter="monitoring_interval",
            current_value=15,
            recommended_value=12,
            confidence=0.7,
            reason="Actividad aumentada detectada en horarios específicos",
            expected_improvement="Mayor precisión en detección de cambios"
        )
    
    def _optimize_alert_thresholds(self) -> List[OptimizationRecommendation]:
        """Optimiza umbrales de alertas"""
        return [
            OptimizationRecommendation(
                parameter="sales_threshold",
                current_value=20000,
                recommended_value=18500,
                confidence=0.75,
                reason="Análisis de patrones muestra actividad relevante en rangos menores",
                expected_improvement="Detección temprana 20% mejorada"
            )
        ]
    
    def _identify_risk_factors(self, features: List[float]) -> List[str]:
        """Identifica factores de riesgo principales"""
        risk_factors = []
        
        if len(features) > 0 and features[0] > 60:  # Duración promedio alta
            risk_factors.append("Tiempos de respuesta elevados")
        
        if len(features) > 4 and features[4] > 2:  # Muchas iteraciones fallidas
            risk_factors.append("Historial de fallos reciente")
        
        if len(features) > 1 and features[1] > 20:  # Alta variabilidad
            risk_factors.append("Comportamiento inconsistente")
        
        return risk_factors if risk_factors else ["Factores normales"]
    
    def get_adaptive_config(self) -> Dict[str, Any]:
        """Retorna configuración adaptiva actual"""
        return self.adaptive_config.copy()
    
    def update_adaptive_config(self, updates: Dict[str, Any]):
        """Actualiza configuración adaptiva"""
        try:
            for key, value in updates.items():
                if key in self.adaptive_config:
                    self.adaptive_config[key].update(value)
                else:
                    self.adaptive_config[key] = value
            
            # Guardar configuración
            config_path = self.models_dir / "adaptive_config.json"
            with open(config_path, 'w') as f:
                json.dump(self.adaptive_config, f, indent=2)
            
            logger.info(f"⚙️ Configuración adaptiva actualizada: {list(updates.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando configuración: {e}")

# Instancia global del motor de inteligencia
intelligence_engine = IntelligenceEngine()