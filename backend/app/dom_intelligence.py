"""
🧠 DOM Intelligence System - ExpressATM
Sistema de Observación Inteligente del DOM con Machine Learning
Observa, aprende y optimiza automáticamente las interacciones web
"""

import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import time
import statistics
from collections import defaultdict, deque
"""
Las dependencias de scikit-learn son opcionales en entornos donde no haya ruedas
para la versión de Python. Usamos fallbacks sencillos para no romper el arranque.
"""
try:
    from sklearn.ensemble import RandomForestRegressor, IsolationForest
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    import joblib
    SKLEARN_AVAILABLE = True
except Exception:
    RandomForestRegressor = None  # type: ignore
    IsolationForest = None  # type: ignore
    LinearRegression = None  # type: ignore
    StandardScaler = None  # type: ignore
    KMeans = None  # type: ignore
    joblib = None  # type: ignore
    SKLEARN_AVAILABLE = False

class _IsoForestFallback:
    """Fallback simple tipo IsolationForest basado en IQR."""
    def __init__(self, contamination: float = 0.1, random_state: int | None = None):
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
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        preds = _np.where((data < lower) | (data > upper), -1, 1)
        desired = int(self.contamination * data.size)
        if desired > 0:
            dist = _np.where(data > upper, data - upper, _np.where(data < lower, lower - data, 0.0))
            idx = _np.argsort(-dist)
            preds[:] = 1
            preds[idx[:desired]] = -1
        return preds

class _RFRegressorFallback:
    """Regresor de respaldo: media móvil simple."""
    def __init__(self, n_estimators: int = 50, random_state: int | None = None):
        self.y_mean = None
    def fit(self, X, y):  # noqa: D401
        import numpy as _np
        y = _np.asarray(y, dtype=float)
        self.y_mean = float(_np.mean(y)) if y.size else 0.0
        return self
    def predict(self, X):
        import numpy as _np
        if self.y_mean is None:
            return _np.zeros((len(X),), dtype=float)
        return _np.full((len(X),), self.y_mean, dtype=float)
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class DOMInteraction:
    """Registro de una interacción con el DOM"""
    timestamp: datetime
    action_type: str  # find_element, click, send_keys, wait, etc.
    selector: str
    selector_type: str  # css, xpath, id, etc.
    duration: float
    success: bool
    element_found: bool
    page_url: str
    context: str  # filtros, datos, navegacion, etc.
    retry_count: int = 0
    error_message: Optional[str] = None
    element_properties: Optional[Dict] = None

@dataclass
class ElementPerformance:
    """Métricas de rendimiento de un elemento específico"""
    selector: str
    total_interactions: int
    success_rate: float
    avg_duration: float
    min_duration: float
    max_duration: float
    optimal_timeout: float
    failure_patterns: List[str]
    alternative_selectors: List[str]
    context_performance: Dict[str, float]

@dataclass
class OptimizationRecommendation:
    """Recomendación de optimización"""
    optimization_type: str  # timeout, selector, sequence, etc.
    current_value: Any
    recommended_value: Any
    confidence: float
    expected_improvement: str
    reason: str
    affected_elements: List[str]

class DOMIntelligenceDB:
    """Base de datos para almacenar observaciones del DOM"""
    
    def __init__(self, db_path: str = "dom_intelligence.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializar esquema de base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de interacciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dom_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                selector TEXT NOT NULL,
                selector_type TEXT NOT NULL,
                duration REAL NOT NULL,
                success BOOLEAN NOT NULL,
                element_found BOOLEAN NOT NULL,
                page_url TEXT NOT NULL,
                context TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                element_properties TEXT
            )
        """)
        
        # Tabla de rendimiento de elementos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS element_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                selector TEXT NOT NULL UNIQUE,
                total_interactions INTEGER NOT NULL,
                success_rate REAL NOT NULL,
                avg_duration REAL NOT NULL,
                min_duration REAL NOT NULL,
                max_duration REAL NOT NULL,
                optimal_timeout REAL NOT NULL,
                failure_patterns TEXT,
                alternative_selectors TEXT,
                context_performance TEXT,
                last_updated TEXT NOT NULL
            )
        """)
        
        # Tabla de optimizaciones aplicadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applied_optimizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_type TEXT NOT NULL,
                target_element TEXT NOT NULL,
                old_value TEXT NOT NULL,
                new_value TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success BOOLEAN,
                performance_improvement REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_interaction(self, interaction: DOMInteraction):
        """Guardar interacción en la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO dom_interactions 
            (timestamp, action_type, selector, selector_type, duration, 
             success, element_found, page_url, context, retry_count, 
             error_message, element_properties)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.timestamp.isoformat(),
            interaction.action_type,
            interaction.selector,
            interaction.selector_type,
            interaction.duration,
            interaction.success,
            interaction.element_found,
            interaction.page_url,
            interaction.context,
            interaction.retry_count,
            interaction.error_message,
            json.dumps(interaction.element_properties) if interaction.element_properties else None
        ))
        
        conn.commit()
        conn.close()

class DOMPatternAnalyzer:
    """Analizador de patrones en interacciones DOM"""
    
    def __init__(self, db: DOMIntelligenceDB):
        self.db = db
        self.sklearn_available = SKLEARN_AVAILABLE
        try:
            self.scaler = StandardScaler() if self.sklearn_available else None
        except Exception:
            self.scaler = None
            self.sklearn_available = False
        self.models = {}
        
    def analyze_element_performance(self, selector: str, days_back: int = 7) -> ElementPerformance:
        """Analizar rendimiento de un elemento específico"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Obtener interacciones recientes
        query = """
            SELECT duration, success, context, timestamp, error_message
            FROM dom_interactions 
            WHERE selector = ? AND timestamp > datetime('now', '-{} days')
            ORDER BY timestamp DESC
        """.format(days_back)
        
        df = pd.read_sql_query(query, conn, params=[selector])
        conn.close()
        
        if df.empty:
            return None
        
        # Calcular métricas
        total_interactions = len(df)
        success_rate = df['success'].mean()
        successful_durations = df[df['success'] == True]['duration']
        
        if len(successful_durations) == 0:
            avg_duration = df['duration'].mean()
            min_duration = df['duration'].min()
            max_duration = df['duration'].max()
        else:
            avg_duration = successful_durations.mean()
            min_duration = successful_durations.min()
            max_duration = successful_durations.max()
        
        # Calcular timeout óptimo (percentil 95 de duraciones exitosas)
        optimal_timeout = successful_durations.quantile(0.95) if len(successful_durations) > 0 else avg_duration * 2
        
        # Analizar patrones de fallo
        failure_patterns = []
        failed_interactions = df[df['success'] == False]
        if len(failed_interactions) > 0:
            error_counts = failed_interactions['error_message'].value_counts()
            failure_patterns = error_counts.index.tolist()[:3]  # Top 3 errores
        
        # Rendimiento por contexto
        context_performance = {}
        for context in df['context'].unique():
            context_data = df[df['context'] == context]
            context_performance[context] = {
                'success_rate': context_data['success'].mean(),
                'avg_duration': context_data[context_data['success'] == True]['duration'].mean()
            }
        
        return ElementPerformance(
            selector=selector,
            total_interactions=total_interactions,
            success_rate=success_rate,
            avg_duration=avg_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            optimal_timeout=optimal_timeout,
            failure_patterns=failure_patterns,
            alternative_selectors=[],  # Se implementará en futuras versiones
            context_performance=context_performance
        )
    
    def detect_performance_anomalies(self, days_back: int = 7) -> List[Dict]:
        """Detectar anomalías en el rendimiento"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Obtener datos de rendimiento recientes
        query = """
            SELECT selector, duration, success, timestamp, context
            FROM dom_interactions 
            WHERE timestamp > datetime('now', '-{} days')
        """.format(days_back)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return []
        
        anomalies = []
        
        # Agrupar por selector
        for selector in df['selector'].unique():
            selector_data = df[df['selector'] == selector]
            
            if len(selector_data) < 10:  # Necesitamos suficientes datos
                continue
            
            # Preparar datos para detección de anomalías
            features = selector_data[['duration']].values
            
            # Usar Isolation Forest
            iso_forest = (IsolationForest(contamination=0.1, random_state=42)
                          if self.sklearn_available and IsolationForest is not None
                          else _IsoForestFallback(contamination=0.1))
            anomaly_labels = iso_forest.fit_predict(features)
            
            # Identificar anomalías
            anomaly_indices = np.where(anomaly_labels == -1)[0]
            
            for idx in anomaly_indices:
                anomaly_row = selector_data.iloc[idx]
                anomalies.append({
                    'selector': selector,
                    'timestamp': anomaly_row['timestamp'],
                    'duration': anomaly_row['duration'],
                    'context': anomaly_row['context'],
                    'anomaly_type': 'performance_outlier',
                    'severity': 'high' if anomaly_row['duration'] > selector_data['duration'].quantile(0.9) else 'medium'
                })
        
        return anomalies
    
    def predict_optimal_timeouts(self) -> Dict[str, float]:
        """Predecir timeouts óptimos usando ML"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Obtener datos históricos
        query = """
            SELECT selector, duration, success, context, 
                   strftime('%H', timestamp) as hour,
                   strftime('%w', timestamp) as weekday
            FROM dom_interactions 
            WHERE timestamp > datetime('now', '-30 days')
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return {}
        
        optimal_timeouts = {}
        
        # Entrenar modelo para cada selector con suficientes datos
        for selector in df['selector'].unique():
            selector_data = df[df['selector'] == selector]
            
            if len(selector_data) < 20:  # Necesitamos suficientes datos
                continue
            
            # Preparar features
            features = pd.get_dummies(selector_data[['context', 'hour', 'weekday']])
            target = selector_data['duration']
            
            # Solo usar interacciones exitosas para predecir tiempo óptimo
            successful_data = selector_data[selector_data['success'] == True]
            if len(successful_data) < 10:
                continue
            
            # Entrenar modelo de regresión
            features_successful = pd.get_dummies(successful_data[['context', 'hour', 'weekday']])
            target_successful = successful_data['duration']
            
            model = (RandomForestRegressor(n_estimators=50, random_state=42)
                     if self.sklearn_available and RandomForestRegressor is not None
                     else _RFRegressorFallback(n_estimators=50, random_state=42))
            model.fit(features_successful, target_successful)
            
            # Predecir timeout óptimo (añadir margen de seguridad)
            predicted_avg = model.predict(features_successful).mean()
            optimal_timeout = predicted_avg * 1.5  # 50% de margen
            
            optimal_timeouts[selector] = optimal_timeout
        
        return optimal_timeouts

class DOMOptimizer:
    """Optimizador automático de interacciones DOM"""
    
    def __init__(self, db: DOMIntelligenceDB, analyzer: DOMPatternAnalyzer):
        self.db = db
        self.analyzer = analyzer
        self.current_optimizations = {}
    
    def generate_recommendations(self) -> List[OptimizationRecommendation]:
        """Generar recomendaciones de optimización"""
        recommendations = []
        
        # Obtener timeouts óptimos
        optimal_timeouts = self.analyzer.predict_optimal_timeouts()
        
        for selector, timeout in optimal_timeouts.items():
            # Obtener rendimiento actual
            performance = self.analyzer.analyze_element_performance(selector)
            
            if performance and performance.total_interactions >= 10:
                # Comparar con timeout actual (asumiendo 10s por defecto)
                current_timeout = 10.0
                
                if abs(timeout - current_timeout) > 1.0:  # Diferencia significativa
                    improvement = abs(timeout - current_timeout) / current_timeout * 100
                    
                    recommendations.append(OptimizationRecommendation(
                        optimization_type="timeout",
                        current_value=current_timeout,
                        recommended_value=round(timeout, 2),
                        confidence=min(performance.success_rate * 0.8 + 0.2, 1.0),
                        expected_improvement=f"{improvement:.1f}% mejora en eficiencia",
                        reason=f"Análisis de {performance.total_interactions} interacciones sugiere timeout óptimo",
                        affected_elements=[selector]
                    ))
        
        # Detectar elementos problemáticos
        conn = sqlite3.connect(self.db.db_path)
        
        query = """
            SELECT selector, 
                   COUNT(*) as total,
                   AVG(CAST(success AS FLOAT)) as success_rate,
                   AVG(duration) as avg_duration
            FROM dom_interactions 
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY selector
            HAVING total >= 5
            ORDER BY success_rate ASC, avg_duration DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Recomendar revisión de elementos con baja tasa de éxito
        for _, row in df.iterrows():
            if row['success_rate'] < 0.8:  # Menos del 80% de éxito
                recommendations.append(OptimizationRecommendation(
                    optimization_type="selector_review",
                    current_value=row['selector'],
                    recommended_value="Revisar selector o estrategia alternativa",
                    confidence=1.0 - row['success_rate'],
                    expected_improvement="Potencial mejora del 20-50% en tasa de éxito",
                    reason=f"Tasa de éxito del {row['success_rate']*100:.1f}% es inferior al umbral del 80%",
                    affected_elements=[row['selector']]
                ))
        
        return recommendations
    
    def apply_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """Aplicar una optimización automáticamente"""
        try:
            if recommendation.optimization_type == "timeout":
                # Aplicar nuevo timeout (se implementará en el scraper)
                self.current_optimizations[recommendation.affected_elements[0]] = {
                    'type': 'timeout',
                    'value': recommendation.recommended_value,
                    'applied_at': datetime.now()
                }
                
                # Registrar optimización aplicada
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO applied_optimizations 
                    (optimization_type, target_element, old_value, new_value, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    recommendation.optimization_type,
                    recommendation.affected_elements[0],
                    str(recommendation.current_value),
                    str(recommendation.recommended_value),
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Optimización aplicada: {recommendation.optimization_type} "
                           f"para {recommendation.affected_elements[0]}")
                return True
                
        except Exception as e:
            logger.error(f"Error aplicando optimización: {e}")
            return False
        
        return False

class DOMIntelligenceEngine:
    """Motor principal de inteligencia DOM"""
    
    def __init__(self, db_path: str = "dom_intelligence.db"):
        self.db = DOMIntelligenceDB(db_path)
        self.analyzer = DOMPatternAnalyzer(self.db)
        self.optimizer = DOMOptimizer(self.db, self.analyzer)
        self.interaction_buffer = deque(maxlen=1000)  # Buffer para interacciones recientes
        self.is_enabled = True
        self.learning_active = True
        
    def record_interaction(self, interaction: DOMInteraction):
        """Registrar una nueva interacción"""
        if not self.is_enabled:
            return
        
        # Añadir al buffer
        self.interaction_buffer.append(interaction)
        
        # Guardar en base de datos
        self.db.save_interaction(interaction)
        
        # Análisis en tiempo real para interacciones críticas
        if not interaction.success and interaction.retry_count > 2:
            self._analyze_critical_failure(interaction)
    
    def _analyze_critical_failure(self, interaction: DOMInteraction):
        """Analizar fallos críticos en tiempo real"""
        # Buscar patrones de fallo recientes para este selector
        recent_failures = [
            i for i in self.interaction_buffer 
            if i.selector == interaction.selector and not i.success 
            and (datetime.now() - i.timestamp).seconds < 3600  # Última hora
        ]
        
        if len(recent_failures) >= 3:
            logger.warning(f"Patrón de fallo detectado para selector: {interaction.selector}")
            # Aquí se podría implementar una respuesta automática
    
    def get_optimization_for_element(self, selector: str) -> Optional[Dict]:
        """Obtener optimización específica para un elemento"""
        return self.optimizer.current_optimizations.get(selector)
    
    def generate_performance_report(self) -> Dict:
        """Generar reporte de rendimiento del DOM"""
        # Obtener estadísticas generales
        conn = sqlite3.connect(self.db.db_path)
        
        # Estadísticas de las últimas 24 horas
        query_24h = """
            SELECT 
                COUNT(*) as total_interactions,
                AVG(CAST(success AS FLOAT)) as success_rate,
                AVG(duration) as avg_duration,
                COUNT(DISTINCT selector) as unique_selectors
            FROM dom_interactions 
            WHERE timestamp > datetime('now', '-1 day')
        """
        
        stats_24h = pd.read_sql_query(query_24h, conn).iloc[0].to_dict()
        
        # Top elementos problemáticos
        query_problems = """
            SELECT selector, 
                   COUNT(*) as interactions,
                   AVG(CAST(success AS FLOAT)) as success_rate,
                   AVG(duration) as avg_duration
            FROM dom_interactions 
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY selector
            HAVING interactions >= 3
            ORDER BY success_rate ASC, avg_duration DESC
            LIMIT 5
        """
        
        problem_elements = pd.read_sql_query(query_problems, conn).to_dict('records')
        
        conn.close()
        
        # Obtener recomendaciones
        recommendations = self.optimizer.generate_recommendations()
        
        # Detectar anomalías
        anomalies = self.analyzer.detect_performance_anomalies()
        
        return {
            'stats_24h': stats_24h,
            'problem_elements': problem_elements,
            'recommendations': [asdict(r) for r in recommendations],
            'anomalies': anomalies,
            'current_optimizations': len(self.optimizer.current_optimizations),
            'learning_status': 'active' if self.learning_active else 'paused'
        }
    
    def toggle_learning(self) -> bool:
        """Activar/desactivar aprendizaje"""
        self.learning_active = not self.learning_active
        return self.learning_active
    
    def reset_optimizations(self):
        """Resetear todas las optimizaciones aplicadas"""
        self.optimizer.current_optimizations.clear()
        logger.info("Optimizaciones DOM reseteadas")

# Instancia global del motor de inteligencia DOM
dom_intelligence = DOMIntelligenceEngine() 