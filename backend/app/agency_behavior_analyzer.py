#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Analizador de Comportamiento de Agencias - ExpressATM
Sistema para evaluación INSTANTÁNEA de normalidad de comportamiento de agencias
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class AlertNormalityLevel(Enum):
    """Niveles de normalidad de una alerta"""
    VERY_NORMAL = "muy_normal"      # Comportamiento típico 
    NORMAL = "normal"               # Dentro de rangos esperados
    UNUSUAL = "inusual"             # Fuera de lo normal pero no crítico
    VERY_UNUSUAL = "muy_inusual"    # Comportamiento altamente anómalo
    UNPRECEDENTED = "sin_precedentes" # Nunca visto antes

class GrowthNormalityLevel(Enum):
    """Niveles de normalidad del crecimiento"""
    TYPICAL_GROWTH = "crecimiento_tipico"
    ACCELERATED_GROWTH = "crecimiento_acelerado" 
    SUSPICIOUS_GROWTH = "crecimiento_sospechoso"
    ANOMALOUS_GROWTH = "crecimiento_anomalo"

@dataclass
class AgencyNormalityReport:
    """Reporte de normalidad de una agencia"""
    agency_code: str
    agency_name: str
    alert_normality: AlertNormalityLevel
    growth_normality: GrowthNormalityLevel
    confidence_score: float  # 0.0 a 1.0
    
    # Datos contextuales
    current_sales: float
    historical_avg_sales: float
    percentile_position: float  # Posición percentil (0-100)
    
    # Comparaciones
    vs_own_history: str  # "120% superior al promedio"
    vs_similar_agencies: str  # "En rango normal para agencias similares"
    
    # Explicación rápida
    quick_explanation: str
    detailed_analysis: str
    recommendation: str
    
    # Datos para gráficos
    historical_trend: List[float]
    similar_agencies_range: Tuple[float, float]

@dataclass
class QuickAnalysisResult:
    """Resultado de análisis rápido"""
    is_unusual: bool
    confidence: float
    explanation: str
    recommendation: str

class AgencyBehaviorAnalyzer:
    """Analizador de comportamiento de agencias"""
    
    def __init__(self, db_path: str = "monitoring.db"):
        self.db_path = db_path
        
    def analyze_agency_alert_normality(self, 
                                     agency_code: str, 
                                     current_sales: float, 
                                     alert_type: str,
                                     lottery_type: str) -> AgencyNormalityReport:
        """
        🎯 FUNCIÓN PRINCIPAL: Analiza si una alerta es normal o inusual
        Respuesta en < 200ms
        """
        try:
            # 1. Obtener datos históricos de la agencia
            historical_data = self._get_agency_historical_data(agency_code, lottery_type)
            
            # 2. Obtener datos de agencias similares
            similar_agencies_data = self._get_similar_agencies_data(agency_code, lottery_type)
            
            # 3. Calcular métricas de normalidad
            alert_normality = self._calculate_alert_normality(
                current_sales, historical_data, similar_agencies_data, alert_type
            )
            
            # 4. Analizar patrón de crecimiento
            growth_normality = self._analyze_growth_pattern(historical_data, current_sales)
            
            # 5. Calcular confianza del análisis
            confidence = self._calculate_confidence(historical_data, similar_agencies_data)
            
            # 6. Generar explicaciones
            explanations = self._generate_explanations(
                agency_code, current_sales, historical_data, 
                similar_agencies_data, alert_normality, growth_normality
            )
            
            # 7. Construir reporte
            return self._build_report(
                agency_code, current_sales, historical_data, similar_agencies_data,
                alert_normality, growth_normality, confidence, explanations
            )
            
        except Exception as e:
            logger.error(f"Error analizando agencia {agency_code}: {e}")
            return self._build_error_report(agency_code, current_sales)
    
    def _get_agency_historical_data(self, agency_code: str, lottery_type: str) -> pd.DataFrame:
        """Obtener historial de la agencia específica"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Últimos 30 días de datos de esta agencia
            query = """
                SELECT 
                    sales, balance, capture_day, iteration_time,
                    strftime('%H', iteration_time) as hour,
                    strftime('%w', iteration_time) as day_of_week
                FROM sales_records 
                WHERE agency_code = ? 
                    AND lottery_type = ?
                    AND capture_day >= date('now', '-30 days')
                ORDER BY iteration_time DESC
            """
            
            df = pd.read_sql_query(query, conn, params=[agency_code, lottery_type])
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            return pd.DataFrame()
    
    def _get_similar_agencies_data(self, agency_code: str, lottery_type: str) -> pd.DataFrame:
        """Obtener datos de agencias similares para comparación"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Agencias con volumen de ventas similar en los últimos 7 días
            query = """
                WITH agency_avg AS (
                    SELECT AVG(sales) as avg_sales
                    FROM sales_records 
                    WHERE agency_code = ? 
                        AND lottery_type = ?
                        AND capture_day >= date('now', '-7 days')
                ),
                similar_agencies AS (
                    SELECT sr.agency_code, AVG(sr.sales) as avg_sales
                    FROM sales_records sr, agency_avg aa
                    WHERE sr.lottery_type = ?
                        AND sr.capture_day >= date('now', '-7 days')
                        AND sr.agency_code != ?
                        AND sr.agency_name NOT LIKE '%SURIEL%'
                        AND sr.agency_name NOT LIKE '%Total General%'
                    GROUP BY sr.agency_code
                    HAVING avg_sales BETWEEN aa.avg_sales * 0.5 AND aa.avg_sales * 2.0
                    ORDER BY ABS(avg_sales - aa.avg_sales)
                    LIMIT 20
                )
                SELECT sr.* 
                FROM sales_records sr
                INNER JOIN similar_agencies sa ON sr.agency_code = sa.agency_code
                WHERE sr.lottery_type = ?
                    AND sr.capture_day >= date('now', '-7 days')
            """
            
            df = pd.read_sql_query(query, conn, params=[
                agency_code, lottery_type, lottery_type, agency_code, lottery_type
            ])
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo agencias similares: {e}")
            return pd.DataFrame()
    
    def _calculate_alert_normality(self, 
                                 current_sales: float, 
                                 historical_data: pd.DataFrame,
                                 similar_agencies_data: pd.DataFrame,
                                 alert_type: str) -> AlertNormalityLevel:
        """Calcula el nivel de normalidad de la alerta"""
        
        if len(historical_data) == 0:
            return AlertNormalityLevel.UNPRECEDENTED
        
        # Análisis vs historial propio
        historical_sales = historical_data['sales'].values
        historical_mean = np.mean(historical_sales)
        historical_std = np.std(historical_sales)
        
        if historical_std == 0:
            z_score_own = 0 if current_sales == historical_mean else float('inf')
        else:
            z_score_own = (current_sales - historical_mean) / historical_std
        
        # Análisis vs agencias similares
        if len(similar_agencies_data) > 0:
            similar_sales = similar_agencies_data['sales'].values
            percentile_vs_similar = (similar_sales < current_sales).mean() * 100
        else:
            percentile_vs_similar = 50  # Neutro si no hay datos
        
        # Determinar normalidad basada en múltiples factores
        if alert_type == "threshold":
            # Para alertas de umbral, evaluar si es común superar umbrales
            if z_score_own <= 1.5 and percentile_vs_similar <= 85:
                return AlertNormalityLevel.VERY_NORMAL
            elif z_score_own <= 2.0 and percentile_vs_similar <= 90:
                return AlertNormalityLevel.NORMAL
            elif z_score_own <= 3.0 and percentile_vs_similar <= 95:
                return AlertNormalityLevel.UNUSUAL
            elif z_score_own <= 4.0:
                return AlertNormalityLevel.VERY_UNUSUAL
            else:
                return AlertNormalityLevel.UNPRECEDENTED
        
        elif alert_type in ["growth_variation", "sustained_growth"]:
            # Para alertas de crecimiento, evaluar velocidad de cambio
            if z_score_own <= 2.0 and percentile_vs_similar <= 80:
                return AlertNormalityLevel.VERY_NORMAL
            elif z_score_own <= 2.5 and percentile_vs_similar <= 88:
                return AlertNormalityLevel.NORMAL
            elif z_score_own <= 3.5 and percentile_vs_similar <= 94:
                return AlertNormalityLevel.UNUSUAL
            elif z_score_own <= 5.0:
                return AlertNormalityLevel.VERY_UNUSUAL
            else:
                return AlertNormalityLevel.UNPRECEDENTED
        
        else:
            # Análisis genérico
            if z_score_own <= 1.0:
                return AlertNormalityLevel.VERY_NORMAL
            elif z_score_own <= 2.0:
                return AlertNormalityLevel.NORMAL
            elif z_score_own <= 3.0:
                return AlertNormalityLevel.UNUSUAL
            elif z_score_own <= 4.0:
                return AlertNormalityLevel.VERY_UNUSUAL
            else:
                return AlertNormalityLevel.UNPRECEDENTED
    
    def _analyze_growth_pattern(self, 
                              historical_data: pd.DataFrame, 
                              current_sales: float) -> GrowthNormalityLevel:
        """Analiza el patrón de crecimiento"""
        
        if len(historical_data) < 3:
            return GrowthNormalityLevel.TYPICAL_GROWTH
        
        # Obtener últimas 5 mediciones para analizar tendencia
        recent_sales = historical_data.head(5)['sales'].values
        
        # Calcular tasa de crecimiento
        if len(recent_sales) >= 2:
            growth_rates = []
            for i in range(len(recent_sales) - 1):
                if recent_sales[i+1] > 0:
                    growth_rate = (recent_sales[i] - recent_sales[i+1]) / recent_sales[i+1]
                    growth_rates.append(growth_rate)
            
            if growth_rates:
                avg_growth_rate = np.mean(growth_rates)
                growth_consistency = 1.0 - np.std(growth_rates) if len(growth_rates) > 1 else 1.0
                
                # Clasificar el crecimiento
                if avg_growth_rate < 0.1:  # Menos del 10%
                    return GrowthNormalityLevel.TYPICAL_GROWTH
                elif avg_growth_rate < 0.3 and growth_consistency > 0.7:  # 10-30% consistente
                    return GrowthNormalityLevel.ACCELERATED_GROWTH
                elif avg_growth_rate < 0.5:  # 30-50%
                    return GrowthNormalityLevel.SUSPICIOUS_GROWTH
                else:  # Más del 50%
                    return GrowthNormalityLevel.ANOMALOUS_GROWTH
        
        return GrowthNormalityLevel.TYPICAL_GROWTH
    
    def _calculate_confidence(self, 
                            historical_data: pd.DataFrame, 
                            similar_agencies_data: pd.DataFrame) -> float:
        """Calcula la confianza del análisis"""
        
        confidence = 0.0
        
        # Factor 1: Cantidad de datos históricos propios
        if len(historical_data) >= 10:
            confidence += 0.4
        elif len(historical_data) >= 5:
            confidence += 0.2
        elif len(historical_data) >= 2:
            confidence += 0.1
        
        # Factor 2: Cantidad de agencias similares para comparación
        unique_agencies = len(similar_agencies_data['agency_code'].unique()) if len(similar_agencies_data) > 0 else 0
        if unique_agencies >= 10:
            confidence += 0.3
        elif unique_agencies >= 5:
            confidence += 0.2
        elif unique_agencies >= 2:
            confidence += 0.1
        
        # Factor 3: Consistencia de datos
        if len(historical_data) > 0:
            cv = np.std(historical_data['sales']) / np.mean(historical_data['sales']) if np.mean(historical_data['sales']) > 0 else 0
            if cv < 0.5:  # Coeficiente de variación bajo = más confiable
                confidence += 0.2
            elif cv < 1.0:
                confidence += 0.1
        
        # Factor 4: Diversidad temporal
        if len(historical_data) > 0:
            unique_days = len(historical_data['capture_day'].unique())
            if unique_days >= 7:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_explanations(self, 
                             agency_code: str,
                             current_sales: float,
                             historical_data: pd.DataFrame,
                             similar_agencies_data: pd.DataFrame,
                             alert_normality: AlertNormalityLevel,
                             growth_normality: GrowthNormalityLevel) -> Dict[str, str]:
        """Genera explicaciones para el usuario"""
        
        explanations = {}
        
        # Calcular métricas para explicaciones
        if len(historical_data) > 0:
            historical_avg = np.mean(historical_data['sales'])
            vs_own_percent = ((current_sales - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0
            
            if len(similar_agencies_data) > 0:
                similar_avg = np.mean(similar_agencies_data['sales'])
                vs_similar_percent = ((current_sales - similar_avg) / similar_avg * 100) if similar_avg > 0 else 0
            else:
                vs_similar_percent = 0
        else:
            vs_own_percent = 0
            vs_similar_percent = 0
        
        # Explicación rápida basada en normalidad
        if alert_normality == AlertNormalityLevel.VERY_NORMAL:
            explanations['quick'] = f"✅ NORMAL: Ventas de ${current_sales:,.0f} están dentro del rango habitual de esta agencia"
        elif alert_normality == AlertNormalityLevel.NORMAL:
            explanations['quick'] = f"✅ ESPERADO: Ventas de ${current_sales:,.0f} son {vs_own_percent:+.0f}% vs promedio, dentro de variación normal"
        elif alert_normality == AlertNormalityLevel.UNUSUAL:
            explanations['quick'] = f"⚠️ INUSUAL: Ventas de ${current_sales:,.0f} son {vs_own_percent:+.0f}% superiores al promedio histórico"
        elif alert_normality == AlertNormalityLevel.VERY_UNUSUAL:
            explanations['quick'] = f"🚨 MUY INUSUAL: Ventas de ${current_sales:,.0f} exceden significativamente el patrón histórico ({vs_own_percent:+.0f}%)"
        else:  # UNPRECEDENTED
            explanations['quick'] = f"🔥 SIN PRECEDENTES: Ventas de ${current_sales:,.0f} nunca vistas en esta agencia"
        
        # Análisis detallado
        details = []
        
        if len(historical_data) > 0:
            days_of_data = len(historical_data['capture_day'].unique())
            details.append(f"📊 Basado en {len(historical_data)} registros de {days_of_data} días")
            details.append(f"📈 Promedio histórico: ${np.mean(historical_data['sales']):,.0f}")
            details.append(f"🎯 Ventas actuales: {vs_own_percent:+.1f}% vs su promedio")
        
        if len(similar_agencies_data) > 0:
            similar_agencies_count = len(similar_agencies_data['agency_code'].unique())
            details.append(f"🔄 Comparado con {similar_agencies_count} agencias similares")
            details.append(f"📊 Posición relativa: {vs_similar_percent:+.1f}% vs agencias similares")
        
        # Análisis de crecimiento
        if growth_normality == GrowthNormalityLevel.TYPICAL_GROWTH:
            details.append("📈 Patrón de crecimiento: Normal y estable")
        elif growth_normality == GrowthNormalityLevel.ACCELERATED_GROWTH:
            details.append("⚡ Patrón de crecimiento: Acelerado pero consistente")
        elif growth_normality == GrowthNormalityLevel.SUSPICIOUS_GROWTH:
            details.append("⚠️ Patrón de crecimiento: Rápido, requiere monitoreo")
        else:
            details.append("🚨 Patrón de crecimiento: Anómalo, revisar inmediatamente")
        
        explanations['detailed'] = "\n".join(details)
        
        # Recomendación
        if alert_normality in [AlertNormalityLevel.VERY_NORMAL, AlertNormalityLevel.NORMAL]:
            explanations['recommendation'] = "✅ Continuar monitoreo normal. Comportamiento dentro de parámetros esperados."
        elif alert_normality == AlertNormalityLevel.UNUSUAL:
            explanations['recommendation'] = "⚠️ Aumentar frecuencia de monitoreo. Verificar si hay eventos especiales."
        elif alert_normality == AlertNormalityLevel.VERY_UNUSUAL:
            explanations['recommendation'] = "🚨 Investigar inmediatamente. Contactar agencia para verificar actividad."
        else:
            explanations['recommendation'] = "🔥 ACCIÓN URGENTE: Comportamiento sin precedentes requiere investigación inmediata."
        
        return explanations
    
    def _build_report(self, 
                     agency_code: str,
                     current_sales: float,
                     historical_data: pd.DataFrame,
                     similar_agencies_data: pd.DataFrame,
                     alert_normality: AlertNormalityLevel,
                     growth_normality: GrowthNormalityLevel,
                     confidence: float,
                     explanations: Dict[str, str]) -> AgencyNormalityReport:
        """Construye el reporte final"""
        
        # Obtener nombre de agencia
        agency_name = "Agencia Desconocida"
        if len(historical_data) > 0:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT agency_name FROM sales_records WHERE agency_code = ? LIMIT 1", [agency_code])
                result = cursor.fetchone()
                if result:
                    agency_name = result[0]
                conn.close()
            except:
                pass
        
        # Calcular métricas
        historical_avg = np.mean(historical_data['sales']) if len(historical_data) > 0 else 0
        
        # Calcular percentil
        all_sales = list(historical_data['sales']) + list(similar_agencies_data['sales']) if len(similar_agencies_data) > 0 else list(historical_data['sales'])
        percentile = (np.array(all_sales) < current_sales).mean() * 100 if all_sales else 50
        
        # Comparaciones textuales
        vs_own = f"{((current_sales - historical_avg) / historical_avg * 100):+.0f}% vs promedio histórico" if historical_avg > 0 else "Sin historial suficiente"
        
        similar_avg = np.mean(similar_agencies_data['sales']) if len(similar_agencies_data) > 0 else 0
        vs_similar = f"{((current_sales - similar_avg) / similar_avg * 100):+.0f}% vs agencias similares" if similar_avg > 0 else "Sin agencias comparables"
        
        # Tendencia histórica para gráfico
        trend = list(historical_data.head(10)['sales']) if len(historical_data) > 0 else []
        
        # Rango de agencias similares
        if len(similar_agencies_data) > 0:
            similar_min = np.min(similar_agencies_data['sales'])
            similar_max = np.max(similar_agencies_data['sales'])
            similar_range = (similar_min, similar_max)
        else:
            similar_range = (0, 0)
        
        return AgencyNormalityReport(
            agency_code=agency_code,
            agency_name=agency_name,
            alert_normality=alert_normality,
            growth_normality=growth_normality,
            confidence_score=confidence,
            current_sales=current_sales,
            historical_avg_sales=historical_avg,
            percentile_position=percentile,
            vs_own_history=vs_own,
            vs_similar_agencies=vs_similar,
            quick_explanation=explanations['quick'],
            detailed_analysis=explanations['detailed'],
            recommendation=explanations['recommendation'],
            historical_trend=trend,
            similar_agencies_range=similar_range
        )
    
    def _build_error_report(self, agency_code: str, current_sales: float) -> AgencyNormalityReport:
        """Construye un reporte de error"""
        return AgencyNormalityReport(
            agency_code=agency_code,
            agency_name="Error en análisis",
            alert_normality=AlertNormalityLevel.UNPRECEDENTED,
            growth_normality=GrowthNormalityLevel.TYPICAL_GROWTH,
            confidence_score=0.0,
            current_sales=current_sales,
            historical_avg_sales=0,
            percentile_position=0,
            vs_own_history="Error en datos",
            vs_similar_agencies="Error en datos", 
            quick_explanation="❌ Error analizando la agencia",
            detailed_analysis="No se pudieron obtener datos suficientes para el análisis",
            recommendation="Verificar conectividad a base de datos",
            historical_trend=[],
            similar_agencies_range=(0, 0)
        )

    def quick_analysis(self, agency_code: str, current_sales: float, lottery_type: str = "RULETA_EXPRESS") -> QuickAnalysisResult:
        """
        🚀 ANÁLISIS RÁPIDO: Respuesta en menos de 100ms
        Determina si una agencia es inusual comparado con su historial
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Obtener historial de los últimos 14 días
            query = """
                SELECT sales, capture_day, iteration_time
                FROM sales_records 
                WHERE agency_code = ? 
                    AND lottery_type = ?
                    AND capture_day >= date('now', '-14 days')
                ORDER BY iteration_time DESC
                LIMIT 50
            """
            
            cursor = conn.cursor()
            cursor.execute(query, [agency_code, lottery_type])
            historical_data = cursor.fetchall()
            
            if len(historical_data) < 3:
                conn.close()
                return QuickAnalysisResult(
                    is_unusual=True,
                    confidence=0.3,
                    explanation=f"🔍 DATOS INSUFICIENTES: Solo {len(historical_data)} registros históricos. Ventas: ${current_sales:,.0f}",
                    recommendation="⚠️ Requiere más historial para análisis confiable"
                )
            
            # Análisis estadístico rápido
            historical_sales = [row[0] for row in historical_data]
            avg_sales = np.mean(historical_sales)
            std_sales = np.std(historical_sales)
            
            # Calcular Z-score
            if std_sales > 0:
                z_score = (current_sales - avg_sales) / std_sales
            else:
                z_score = 0 if current_sales == avg_sales else float('inf')
            
            # Determinar si es inusual
            is_unusual = abs(z_score) > 2.0  # Más de 2 desviaciones estándar
            
            # Calcular confianza basada en cantidad de datos
            confidence = min(0.9, 0.3 + (len(historical_data) * 0.02))
            
            # Generar explicación
            percent_change = ((current_sales - avg_sales) / avg_sales * 100) if avg_sales > 0 else 0
            
            if not is_unusual:
                explanation = f"✅ NORMAL: ${current_sales:,.0f} ({percent_change:+.0f}% vs promedio de ${avg_sales:,.0f})"
                recommendation = "✅ Continuar monitoreo normal"
            elif z_score > 3.0:
                explanation = f"🔥 EXTREMADAMENTE INUSUAL: ${current_sales:,.0f} ({percent_change:+.0f}% vs promedio). Z-score: {z_score:.1f}"
                recommendation = "🚨 INVESTIGAR INMEDIATAMENTE - Comportamiento sin precedentes"
            elif z_score > 2.5:
                explanation = f"🚨 MUY INUSUAL: ${current_sales:,.0f} ({percent_change:+.0f}% vs promedio). Z-score: {z_score:.1f}"
                recommendation = "⚠️ Verificar actividad de la agencia"
            else:
                explanation = f"⚠️ INUSUAL: ${current_sales:,.0f} ({percent_change:+.0f}% vs promedio). Z-score: {z_score:.1f}"
                recommendation = "📊 Monitorear más frecuentemente"
            
            conn.close()
            
            return QuickAnalysisResult(
                is_unusual=bool(is_unusual),
                confidence=float(confidence),
                explanation=explanation,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Error en análisis rápido: {e}")
            return QuickAnalysisResult(
                is_unusual=True,
                confidence=0.0,
                explanation=f"❌ ERROR: No se pudo analizar agencia {agency_code}",
                recommendation="🔧 Verificar sistema"
            )
    
    def analyze_growth_normality(self, agency_code: str, lottery_type: str = "RULETA_EXPRESS") -> str:
        """
        📈 ANÁLISIS DE CRECIMIENTO: Evalúa si el patrón de crecimiento es normal
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Obtener últimas 10 mediciones
            query = """
                SELECT sales, iteration_time
                FROM sales_records 
                WHERE agency_code = ? 
                    AND lottery_type = ?
                ORDER BY iteration_time DESC
                LIMIT 10
            """
            
            cursor = conn.cursor()
            cursor.execute(query, [agency_code, lottery_type])
            data = cursor.fetchall()
            conn.close()
            
            if len(data) < 4:
                return f"📊 DATOS INSUFICIENTES: Solo {len(data)} mediciones para análisis de tendencia"
            
            # Calcular cambios entre mediciones consecutivas
            sales_values = [row[0] for row in data]
            changes = []
            
            for i in range(len(sales_values) - 1):
                if sales_values[i+1] > 0:  # Evitar división por cero
                    change_percent = ((sales_values[i] - sales_values[i+1]) / sales_values[i+1]) * 100
                    changes.append(change_percent)
            
            if not changes:
                return "📊 No se pueden calcular cambios (valores en cero)"
            
            avg_change = np.mean(changes)
            consistency = 1.0 - (np.std(changes) / 100.0) if len(changes) > 1 else 1.0  # Normalizado
            
            # Clasificar el patrón de crecimiento
            if abs(avg_change) < 5:  # Menos de 5% de cambio promedio
                return f"📈 CRECIMIENTO ESTABLE: {avg_change:+.1f}% promedio entre mediciones"
            elif avg_change > 5 and avg_change < 15 and consistency > 0.7:
                return f"⚡ CRECIMIENTO ACELERADO NORMAL: {avg_change:+.1f}% promedio, consistente"
            elif avg_change > 15 and avg_change < 30:
                return f"⚠️ CRECIMIENTO RÁPIDO: {avg_change:+.1f}% promedio - Monitorear de cerca"
            elif avg_change > 30:
                return f"🚨 CRECIMIENTO ANÓMALO: {avg_change:+.1f}% promedio - INVESTIGAR"
            elif avg_change < -15:
                return f"📉 DECRECIMIENTO SIGNIFICATIVO: {avg_change:+.1f}% promedio - Verificar"
            else:
                return f"📊 FLUCTUACIÓN NORMAL: {avg_change:+.1f}% promedio"
                
        except Exception as e:
            logger.error(f"Error analizando crecimiento: {e}")
            return f"❌ Error analizando patrón de crecimiento"

# Función de conveniencia para uso inmediato
def is_agency_unusual(agency_code: str, current_sales: float, lottery_type: str = "RULETA_EXPRESS") -> str:
    """
    🎯 FUNCIÓN ULTRA-RÁPIDA: Respuesta inmediata si una agencia es inusual
    
    Uso en alerts.py:
    explanation = is_agency_unusual("012345", 25000, "RULETA_EXPRESS")
    """
    analyzer = AgencyBehaviorAnalyzer()
    result = analyzer.quick_analysis(agency_code, current_sales, lottery_type)
    return result.explanation

# Instancia global
agency_analyzer = AgencyBehaviorAnalyzer() 