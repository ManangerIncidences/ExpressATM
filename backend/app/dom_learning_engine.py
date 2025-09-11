#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 Sistema de Aprendizaje Automático para Patrones DOM - ExpressATM
Detecta automáticamente lentitud, cambios y optimiza selectores
"""

import sqlite3
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
"""
Las siguientes importaciones de scikit-learn son opcionales.
En entornos donde no esté disponible (por ejemplo, Python 3.13 sin ruedas binarias),
el sistema usará detectores de anomalías de respaldo (fallback) basados en IQR/z-score
para evitar que la app falle al iniciar.
"""
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import DBSCAN  # no se usa actualmente, pero se mantiene por compatibilidad
    SKLEARN_AVAILABLE = True
except Exception:
    IsolationForest = None  # type: ignore
    StandardScaler = None  # type: ignore
    DBSCAN = None  # type: ignore
    SKLEARN_AVAILABLE = False

class _IsolationForestFallback:
    """Detector simple de anomalías como respaldo cuando no hay scikit-learn.

    Implementa una interfaz mínima con fit_predict(X) devolviendo 1 para normal
    y -1 para outlier, usando un criterio robusto (IQR) sobre la primera columna.
    """
    def __init__(self, contamination: float = 0.1, random_state: int | None = None):
        self.contamination = max(0.0, min(0.5, contamination))

    def fit_predict(self, X):
        import numpy as _np
        X = _np.asarray(X, dtype=float)
        if X.ndim == 1:
            data = X
        else:
            # usar la columna total_duration si existe; por defecto primera
            data = X[:, 0]

        if data.size == 0:
            return _np.array([], dtype=int)

        q1 = _np.percentile(data, 25)
        q3 = _np.percentile(data, 75)
        iqr = max(q3 - q1, 1e-9)
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        preds = _np.where((data < lower) | (data > upper), -1, 1)

        # Ajustar a la tasa de contaminación aproximada si es necesario
        desired_outliers = int(self.contamination * data.size)
        if desired_outliers > 0:
            # marcar como outliers los más alejados del rango [lower, upper]
            dist = _np.where(data > upper, data - upper, _np.where(data < lower, lower - data, 0.0))
            idx = _np.argsort(-dist)
            preds[:] = 1
            preds[idx[:desired_outliers]] = -1
        return preds
import json

logger = logging.getLogger(__name__)

@dataclass
class DOMPattern:
    """Patrón detectado en el DOM"""
    selector: str
    action_type: str
    avg_duration: float
    success_rate: float
    context: str
    frequency: int
    last_seen: datetime

@dataclass
class DOMAnomaly:
    """Anomalía detectada en el DOM"""
    type: str  # 'performance', 'structure', 'timing'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    affected_selector: str
    baseline_value: float
    current_value: float
    confidence: float
    recommendation: str
    timestamp: datetime

@dataclass
class PerformanceInsight:
    """Insight de rendimiento"""
    insight_type: str
    title: str
    description: str
    impact_level: str
    optimization_suggestion: str
    expected_improvement: str

class DOMPatternLearner:
    """Sistema de aprendizaje automático para patrones DOM"""
    
    def __init__(self, db_path: str = "dom_intelligence.db"):
        self.db_path = db_path
        # Inicializar componentes de ML con fallback si scikit-learn no está disponible
        self.sklearn_available = SKLEARN_AVAILABLE
        try:
            self.scaler = StandardScaler() if self.sklearn_available else None
        except Exception:
            self.scaler = None
            self.sklearn_available = False

        try:
            if self.sklearn_available and IsolationForest is not None:
                self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
            else:
                self.anomaly_detector = _IsolationForestFallback(contamination=0.1)
        except Exception:
            self.anomaly_detector = _IsolationForestFallback(contamination=0.1)
        self.patterns_cache = {}
        self.baseline_metrics = {}
        
    def learn_patterns(self) -> List[DOMPattern]:
        """
        🔍 APRENDER PATRONES: Analiza interacciones históricas del DOM
        Detecta patrones normales para identificar anomalías
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Obtener datos de los últimos 7 días
            query = """
                SELECT 
                    selector,
                    action_type,
                    duration,
                    success,
                    page_context,
                    timestamp
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-7 days')
                ORDER BY timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) == 0:
                logger.warning("No hay datos DOM para aprender patrones")
                return []
            
            # Agrupar por selector y acción
            patterns = []
            
            grouped = df.groupby(['selector', 'action_type'])
            for (selector, action_type), group in grouped:
                if len(group) >= 3:  # Mínimo 3 interacciones para un patrón
                    pattern = DOMPattern(
                        selector=selector,
                        action_type=action_type,
                        avg_duration=float(group['duration'].mean()),
                        success_rate=float(group['success'].mean()),
                        context=group['page_context'].iloc[0] if 'page_context' in group.columns else 'unknown',
                        frequency=len(group),
                        last_seen=datetime.fromisoformat(group['timestamp'].iloc[0])
                    )
                    patterns.append(pattern)
            
            # Actualizar caché de patrones
            self.patterns_cache = {f"{p.selector}_{p.action_type}": p for p in patterns}
            
            logger.info(f"🧠 {len(patterns)} patrones DOM aprendidos")
            return patterns
            
        except Exception as e:
            logger.error(f"Error aprendiendo patrones DOM: {e}")
            return []
    
    def detect_anomalies(self) -> List[DOMAnomaly]:
        """
        🚨 DETECTAR ANOMALÍAS: Identifica comportamientos anómalos
        Como lentitud en tablas, timeouts, cambios estructurales
        """
        try:
            anomalies = []
            
            # 1. Detectar anomalías de rendimiento
            performance_anomalies = self._detect_performance_anomalies()
            anomalies.extend(performance_anomalies)
            
            # 2. Detectar cambios estructurales
            structure_anomalies = self._detect_structure_anomalies()
            anomalies.extend(structure_anomalies)
            
            # 3. Detectar patrones de timing anómalos
            timing_anomalies = self._detect_timing_anomalies()
            anomalies.extend(timing_anomalies)
            
            logger.info(f"🚨 {len(anomalies)} anomalías DOM detectadas")
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detectando anomalías DOM: {e}")
            return []
    
    def _detect_performance_anomalies(self) -> List[DOMAnomaly]:
        """Detectar anomalías de rendimiento como lentitud en tablas"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Analizar rendimiento de elementos críticos (tablas, botones, etc.)
            query = """
                SELECT 
                    selector,
                    action_type,
                    duration,
                    success,
                    timestamp,
                    strftime('%Y-%m-%d %H', timestamp) as hour_bucket
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-24 hours')
                    AND (selector LIKE '%table%' OR action_type IN ('wait_table', 'extract_table'))
                ORDER BY timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            anomalies = []
            
            if len(df) > 0:
                # Agrupar por selector
                for selector in df['selector'].unique():
                    selector_data = df[df['selector'] == selector]
                    
                    if len(selector_data) >= 5:  # Suficientes datos para análisis
                        recent_duration = selector_data.head(3)['duration'].mean()
                        baseline_duration = selector_data.tail(10)['duration'].mean()
                        
                        # ¿La duración reciente es significativamente mayor?
                        if recent_duration > baseline_duration * 1.5:  # 50% más lento
                            severity = self._calculate_severity(recent_duration, baseline_duration)
                            
                            anomaly = DOMAnomaly(
                                type='performance',
                                severity=severity,
                                description=f"Tabla {selector} cargando {recent_duration:.1f}s vs baseline {baseline_duration:.1f}s",
                                affected_selector=selector,
                                baseline_value=baseline_duration,
                                current_value=recent_duration,
                                confidence=min(0.9, (recent_duration - baseline_duration) / baseline_duration),
                                recommendation=self._get_performance_recommendation(recent_duration, baseline_duration),
                                timestamp=datetime.now()
                            )
                            anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detectando anomalías de rendimiento: {e}")
            return []
    
    def _detect_structure_anomalies(self) -> List[DOMAnomaly]:
        """Detectar cambios en estructura del DOM"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Buscar cambios en elementos esperados
            query = """
                SELECT 
                    selector,
                    COUNT(*) as frequency,
                    AVG(success) as success_rate,
                    MAX(timestamp) as last_seen
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-48 hours')
                GROUP BY selector
                HAVING frequency >= 2
                ORDER BY success_rate ASC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            anomalies = []
            
            for _, row in df.iterrows():
                if row['success_rate'] < 0.7:  # Menos del 70% de éxito
                    anomaly = DOMAnomaly(
                        type='structure',
                        severity='high' if row['success_rate'] < 0.5 else 'medium',
                        description=f"Selector {row['selector']} fallando frecuentemente ({row['success_rate']:.1%} éxito)",
                        affected_selector=row['selector'],
                        baseline_value=1.0,
                        current_value=row['success_rate'],
                        confidence=1.0 - row['success_rate'],
                        recommendation="Revisar si el elemento cambió en la página web",
                        timestamp=datetime.now()
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detectando anomalías estructurales: {e}")
            return []
    
    def _detect_timing_anomalies(self) -> List[DOMAnomaly]:
        """Detectar patrones de timing anómalos"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Analizar secuencias de acciones que tardan más de lo normal
            query = """
                SELECT 
                    page_context,
                    COUNT(*) as action_count,
                    SUM(duration) as total_duration,
                    AVG(duration) as avg_duration,
                    timestamp
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-6 hours')
                GROUP BY page_context, strftime('%Y-%m-%d %H:%M', timestamp)
                HAVING action_count >= 3
                ORDER BY total_duration DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            anomalies = []
            
            if len(df) > 3:
                # Usar isolation forest para detectar outliers en duración total
                durations = df[['total_duration', 'avg_duration']].values
                
                if len(durations) >= 5:
                    outliers = self.anomaly_detector.fit_predict(durations)
                    
                    for i, is_outlier in enumerate(outliers):
                        if is_outlier == -1:  # Es outlier
                            row = df.iloc[i]
                            
                            anomaly = DOMAnomaly(
                                type='timing',
                                severity='medium',
                                description=f"Secuencia en {row['page_context']} tardó {row['total_duration']:.1f}s (anómalo)",
                                affected_selector=row['page_context'],
                                baseline_value=df['total_duration'].median(),
                                current_value=row['total_duration'],
                                confidence=0.8,
                                recommendation="Verificar conectividad o carga del servidor",
                                timestamp=datetime.now()
                            )
                            anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detectando anomalías de timing: {e}")
            return []
    
    def _calculate_severity(self, current: float, baseline: float) -> str:
        """Calcular severidad basada en desviación del baseline"""
        ratio = current / baseline if baseline > 0 else float('inf')
        
        if ratio >= 3.0:
            return 'critical'
        elif ratio >= 2.0:
            return 'high'
        elif ratio >= 1.5:
            return 'medium'
        else:
            return 'low'
    
    def _get_performance_recommendation(self, current: float, baseline: float) -> str:
        """Generar recomendación basada en degradación de rendimiento"""
        ratio = current / baseline if baseline > 0 else float('inf')
        
        if ratio >= 3.0:
            return "🚨 CRÍTICO: Verificar servidor web, posible sobrecarga. Considerar retry con backoff exponencial."
        elif ratio >= 2.0:
            return "⚠️ ALTO: Implementar timeout dinámico. Verificar carga de red."
        elif ratio >= 1.5:
            return "📊 MEDIO: Aumentar timeout temporal. Monitorear tendencia."
        else:
            return "✅ BAJO: Dentro de variación normal."
    
    def generate_insights(self) -> List[PerformanceInsight]:
        """
        💡 GENERAR INSIGHTS: Análisis inteligente con recomendaciones
        """
        try:
            insights = []
            
            # Insight 1: Elementos más lentos
            slowest_elements = self._analyze_slowest_elements()
            if slowest_elements:
                insights.append(slowest_elements)
            
            # Insight 2: Patrones de fallo
            failure_patterns = self._analyze_failure_patterns()
            if failure_patterns:
                insights.append(failure_patterns)
            
            # Insight 3: Oportunidades de optimización
            optimization_opportunities = self._find_optimization_opportunities()
            insights.extend(optimization_opportunities)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generando insights: {e}")
            return []
    
    def _analyze_slowest_elements(self) -> Optional[PerformanceInsight]:
        """Analizar elementos más lentos"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
                SELECT 
                    selector,
                    AVG(duration) as avg_duration,
                    COUNT(*) as frequency
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-24 hours')
                    AND success = 1
                GROUP BY selector
                HAVING frequency >= 3
                ORDER BY avg_duration DESC
                LIMIT 3
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) > 0:
                slowest = df.iloc[0]
                return PerformanceInsight(
                    insight_type='performance',
                    title=f"Elemento más lento: {slowest['selector']}",
                    description=f"Promedio: {slowest['avg_duration']:.1f}s en {slowest['frequency']} interacciones",
                    impact_level='medium' if slowest['avg_duration'] > 5 else 'low',
                    optimization_suggestion="Considerar selector más específico o implementar cache",
                    expected_improvement=f"Potencial reducción de {slowest['avg_duration'] * 0.3:.1f}s"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error analizando elementos lentos: {e}")
            return None
    
    def _analyze_failure_patterns(self) -> Optional[PerformanceInsight]:
        """Analizar patrones de fallo"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
                SELECT 
                    selector,
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                    (SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as failure_rate
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-24 hours')
                GROUP BY selector
                HAVING total_attempts >= 3 AND failure_rate > 20
                ORDER BY failure_rate DESC
                LIMIT 3
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) > 0:
                problematic = df.iloc[0]
                return PerformanceInsight(
                    insight_type='reliability',
                    title=f"Selector problemático: {problematic['selector']}",
                    description=f"{problematic['failure_rate']:.1f}% de fallos ({problematic['failures']}/{problematic['total_attempts']})",
                    impact_level='high' if problematic['failure_rate'] > 50 else 'medium',
                    optimization_suggestion="Revisar selector o implementar fallback",
                    expected_improvement=f"Mejorar confiabilidad del {100 - problematic['failure_rate']:.0f}%"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error analizando patrones de fallo: {e}")
            return None
    
    def _find_optimization_opportunities(self) -> List[PerformanceInsight]:
        """Encontrar oportunidades de optimización"""
        insights = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Buscar selectores que se usan frecuentemente y podrían beneficiarse de optimización
            query = """
                SELECT 
                    selector,
                    action_type,
                    COUNT(*) as frequency,
                    AVG(duration) as avg_duration,
                    MIN(duration) as min_duration,
                    MAX(duration) as max_duration
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-48 hours')
                    AND success = 1
                GROUP BY selector, action_type
                HAVING frequency >= 5
                ORDER BY frequency DESC, avg_duration DESC
                LIMIT 5
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            for _, row in df.iterrows():
                # Variabilidad alta indica oportunidad de optimización
                variability = (row['max_duration'] - row['min_duration']) / row['avg_duration'] if row['avg_duration'] > 0 else 0
                
                if variability > 0.5:  # Alta variabilidad
                    insights.append(PerformanceInsight(
                        insight_type='optimization',
                        title=f"Alta variabilidad en {row['selector']}",
                        description=f"Duración varía entre {row['min_duration']:.1f}s y {row['max_duration']:.1f}s",
                        impact_level='medium',
                        optimization_suggestion="Implementar timeout adaptativo basado en condiciones",
                        expected_improvement="Reducir variabilidad del 30-50%"
                    ))
            
            return insights
            
        except Exception as e:
            logger.error(f"Error encontrando oportunidades: {e}")
            return []

    def detect_table_loading_anomalies(self) -> List[DOMAnomaly]:
        """
        🚨 DETECTAR LENTITUD EN TABLAS: Exactamente lo que observaste
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Analizar patrones de carga de tablas en las últimas 24 horas
            query = """
                SELECT 
                    selector,
                    action_type,
                    duration,
                    success,
                    timestamp,
                    strftime('%Y-%m-%d %H', timestamp) as hour_bucket
                FROM dom_interactions 
                WHERE timestamp >= datetime('now', '-24 hours')
                    AND (selector LIKE '%table%' OR action_type LIKE '%table%' OR selector LIKE '%tbody%')
                ORDER BY timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            anomalies = []
            
            if len(df) > 0:
                logger.info(f"🔍 Analizando {len(df)} interacciones de tabla")
                
                # Agrupar por selector para detectar cambios de rendimiento
                for selector in df['selector'].unique():
                    selector_data = df[df['selector'] == selector].sort_values('timestamp')
                    
                    if len(selector_data) >= 4:  # Suficientes datos
                        # Últimas 3 mediciones vs promedio histórico
                        recent_durations = selector_data.head(3)['duration'].values
                        historical_durations = selector_data.tail(10)['duration'].values
                        
                        recent_avg = np.mean(recent_durations)
                        historical_avg = np.mean(historical_durations)
                        
                        # ¿Degradación significativa?
                        if recent_avg > historical_avg * 1.4:  # 40% más lento
                            severity = self._calculate_severity(recent_avg, historical_avg)
                            
                            anomaly = DOMAnomaly(
                                type='performance',
                                severity=severity,
                                description=f"⚠️ TABLA LENTA: {selector} ahora tarda {recent_avg:.1f}s vs {historical_avg:.1f}s normal",
                                affected_selector=selector,
                                baseline_value=historical_avg,
                                current_value=recent_avg,
                                confidence=min(0.95, (recent_avg - historical_avg) / historical_avg),
                                recommendation=self._get_table_recommendation(recent_avg, historical_avg),
                                timestamp=datetime.now()
                            )
                            anomalies.append(anomaly)
                            
                            logger.warning(f"🚨 Lentitud detectada en {selector}: {recent_avg:.1f}s vs {historical_avg:.1f}s")
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detectando anomalías de tabla: {e}")
            return []
    
    def analyze_current_iteration_performance(self, iteration_duration: float, agencies_processed: int) -> Dict:
        """
        📊 ANALIZAR RENDIMIENTO DE ITERACIÓN ACTUAL
        Detecta si la iteración actual es más lenta de lo normal
        """
        try:
            # Calcular métricas por agencia
            time_per_agency = iteration_duration / agencies_processed if agencies_processed > 0 else 0
            
            # Obtener baseline de iteraciones anteriores
            baseline_time_per_agency = self._get_baseline_time_per_agency()
            
            analysis = {
                'current_time_per_agency': time_per_agency,
                'baseline_time_per_agency': baseline_time_per_agency,
                'performance_ratio': time_per_agency / baseline_time_per_agency if baseline_time_per_agency > 0 else 1.0,
                'is_slower_than_normal': False,
                'severity': 'normal',
                'recommendation': '',
                'potential_cause': ''
            }
            
            if baseline_time_per_agency > 0:
                ratio = time_per_agency / baseline_time_per_agency
                
                if ratio > 1.5:  # 50% más lento
                    analysis['is_slower_than_normal'] = True
                    analysis['severity'] = 'high' if ratio > 2.0 else 'medium'
                    analysis['recommendation'] = self._get_iteration_recommendation(ratio)
                    analysis['potential_cause'] = self._identify_potential_cause(ratio)
                    
                    logger.warning(f"🐌 Iteración lenta detectada: {time_per_agency:.1f}s/agencia vs {baseline_time_per_agency:.1f}s normal")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando rendimiento de iteración: {e}")
            return {'error': str(e)}
    
    def _get_baseline_time_per_agency(self) -> float:
        """Obtener tiempo baseline por agencia de iteraciones anteriores"""
        try:
            conn = sqlite3.connect("monitoring.db")
            
            # Últimas 10 iteraciones exitosas
            query = """
                SELECT 
                    (julianday(end_time) - julianday(start_time)) * 24 * 3600 as duration_seconds,
                    total_agencies_processed as agencies_processed
                FROM monitoring_sessions 
                WHERE total_agencies_processed > 0
                    AND start_time >= datetime('now', '-7 days')
                ORDER BY start_time DESC
                LIMIT 10
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) > 0:
                df['time_per_agency'] = df['duration_seconds'] / df['agencies_processed']
                return df['time_per_agency'].median()  # Usar mediana para estabilidad
            
            return 2.5  # Valor por defecto razonable
            
        except Exception as e:
            logger.error(f"Error obteniendo baseline: {e}")
            return 2.5
    
    def _get_table_recommendation(self, current: float, baseline: float) -> str:
        """Recomendación específica para lentitud de tablas"""
        ratio = current / baseline if baseline > 0 else 1.0
        
        if ratio >= 3.0:
            return "🚨 CRÍTICO: Servidor sobrecargado. Implementar retry con backoff exponencial y timeout dinámico."
        elif ratio >= 2.0:
            return "⚠️ ALTO: Aumentar timeout a 45s. Verificar conectividad. Considerar cache de resultados."
        elif ratio >= 1.4:
            return "📊 MEDIO: Monitorear próximas iteraciones. Posible throttling del servidor."
        else:
            return "✅ NORMAL: Dentro de variación esperada."
    
    def _get_iteration_recommendation(self, ratio: float) -> str:
        """Recomendación para iteraciones lentas"""
        if ratio >= 2.0:
            return "Implementar timeout adaptativo. Verificar carga del servidor web de loterías."
        elif ratio >= 1.5:
            return "Aumentar timeout temporal. Monitorear si es tendencia o incidente aislado."
        else:
            return "Optimizar selectores más utilizados."
    
    def _identify_potential_cause(self, ratio: float) -> str:
        """Identificar causa potencial de lentitud"""
        if ratio >= 3.0:
            return "Servidor web sobrecargado o mantenimiento"
        elif ratio >= 2.0:
            return "Throttling de red o conectividad lenta"
        elif ratio >= 1.5:
            return "Carga temporal del servidor o más datos en tabla"
        else:
            return "Variación normal del sistema"

    def get_recent_performance_trend(self) -> dict:
        """Analizar tendencia de rendimiento reciente para detectar problemas"""
        try:
            # Usar conexión temporal en lugar de self.db
            conn = sqlite3.connect(self.db_path)
            
            query = """
            SELECT duration, total_agencies_processed, timestamp, optimization_level
            FROM monitoring_sessions 
            WHERE timestamp >= datetime('now', '-2 hours')
            ORDER BY timestamp DESC
            LIMIT 10
            """
            
            result = conn.execute(query).fetchall()
            conn.close()
            
            if len(result) < 3:
                return {'declining_performance': False, 'insufficient_data': True}
            
            # Calcular métricas de tendencia
            durations = [row[0] for row in result if row[0] and row[0] > 0]
            agencies_counts = [row[1] for row in result if row[1] and row[1] > 0]
            
            if len(durations) < 3:
                return {'declining_performance': False, 'insufficient_data': True}
            
            # Verificar tendencia de duración (¿está aumentando?)
            recent_avg = sum(durations[:3]) / 3  # Promedio de últimas 3
            older_avg = sum(durations[3:6]) / len(durations[3:6]) if len(durations) > 3 else recent_avg
            
            duration_increase = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
            
            # Verificar eficiencia (agencias por minuto)
            recent_efficiency = [agencies_counts[i] / (durations[i] / 60) for i in range(min(3, len(durations))) if durations[i] > 0]
            older_efficiency = [agencies_counts[i] / (durations[i] / 60) for i in range(3, min(6, len(durations))) if durations[i] > 0]
            
            efficiency_decline = 0
            if recent_efficiency and older_efficiency:
                recent_eff_avg = sum(recent_efficiency) / len(recent_efficiency)
                older_eff_avg = sum(older_efficiency) / len(older_efficiency)
                efficiency_decline = ((older_eff_avg - recent_eff_avg) / older_eff_avg) * 100 if older_eff_avg > 0 else 0
            
            # Detectar anomalías
            declining_performance = (
                duration_increase > 25 or  # Duración aumentó >25%
                efficiency_decline > 20 or  # Eficiencia bajó >20%
                recent_avg > 180  # Duración absoluta >3 minutos
            )
            
            anomalous_duration = recent_avg > 300  # >5 minutos es anómalo
            
            return {
                'declining_performance': declining_performance,
                'anomalous_duration': anomalous_duration,
                'duration_increase_pct': duration_increase,
                'efficiency_decline_pct': efficiency_decline,
                'recent_avg_duration': recent_avg,
                'trend_analysis': {
                    'recent_durations': durations[:3],
                    'older_durations': durations[3:6] if len(durations) > 3 else [],
                    'recent_efficiency': recent_efficiency,
                    'older_efficiency': older_efficiency
                }
            }
            
        except Exception as e:
            logger.error(f"Error analizando tendencia de rendimiento: {e}")
            return {'declining_performance': False, 'error': str(e)}

# Instancia global
dom_learner = DOMPatternLearner() 