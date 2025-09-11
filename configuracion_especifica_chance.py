#!/usr/bin/env python3
"""
🎯 CONFIGURACIÓN ESPECÍFICA PARA CHANCE EXPRESS
==============================================
Basado en la observación del usuario de que CHANCE EXPRESS tarda más 
que RULETA EXPRESS, este módulo implementa:

1. 🔍 Detección específica de lentitud en CHANCE EXPRESS
2. ⏰ Timeouts adaptativos por lotería
3. 👁️ Monitoreo visual específico para placeholders
4. 🧠 ML especializado en patrones de CHANCE EXPRESS
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ChanceExpressOptimizer:
    """
    Optimizador específico para CHANCE EXPRESS
    """
    
    def __init__(self):
        self.lottery_configs = {
            "CHANCE EXPRESS": {
                "base_timeout": 45,  # Timeout base más alto
                "table_wait_multiplier": 1.5,  # 50% más tiempo de espera
                "retry_attempts": 3,
                "visual_confirmation_required": True,
                "placeholder_patterns": [
                    "Total General", "$0.00", "0.00", 
                    "Cargando...", "Procesando...", "---"
                ],
                "expected_min_rows": 10,  # Mínimo esperado para datos reales
                "stability_checks": 3  # Verificaciones de estabilidad extra
            },
            "RULETA EXPRESS": {
                "base_timeout": 30,  # Timeout normal
                "table_wait_multiplier": 1.0,  # Tiempo normal
                "retry_attempts": 2,
                "visual_confirmation_required": False,  # Funciona bien
                "placeholder_patterns": ["Total General", "$0.00"],
                "expected_min_rows": 20,  # Generalmente más agencias
                "stability_checks": 2
            }
        }
        
        # Estadísticas de rendimiento por lotería
        self.performance_stats = {
            "CHANCE EXPRESS": {
                "avg_load_time": 0,
                "success_rate": 0,
                "placeholder_incidents": 0,
                "total_attempts": 0
            },
            "RULETA EXPRESS": {
                "avg_load_time": 0,
                "success_rate": 0,
                "placeholder_incidents": 0,
                "total_attempts": 0
            }
        }
    
    def get_lottery_config(self, lottery_name: str) -> Dict[str, Any]:
        """Obtener configuración específica para una lotería"""
        return self.lottery_configs.get(lottery_name, self.lottery_configs["RULETA EXPRESS"])
    
    def should_use_enhanced_monitoring(self, lottery_name: str) -> bool:
        """Determinar si usar monitoreo mejorado para una lotería específica"""
        config = self.get_lottery_config(lottery_name)
        
        if lottery_name == "CHANCE EXPRESS":
            # Siempre usar monitoreo mejorado para CHANCE EXPRESS
            return True
        
        # Para otras loterías, usar si hay historial de problemas
        stats = self.performance_stats.get(lottery_name, {})
        success_rate = stats.get('success_rate', 1.0)
        
        return success_rate < 0.8  # Usar si menos del 80% de éxito
    
    def calculate_adaptive_timeout(self, lottery_name: str, base_timeout: int = 30) -> int:
        """Calcular timeout adaptativo basado en historial de la lotería"""
        config = self.get_lottery_config(lottery_name)
        stats = self.performance_stats.get(lottery_name, {})
        
        # Timeout base específico de la lotería
        adaptive_timeout = config["base_timeout"]
        
        # Ajustar basado en rendimiento histórico
        avg_load_time = stats.get('avg_load_time', 0)
        if avg_load_time > 0:
            # Usar 2x el tiempo promedio como mínimo
            adaptive_timeout = max(adaptive_timeout, int(avg_load_time * 2))
        
        # Aplicar multiplicador específico
        adaptive_timeout = int(adaptive_timeout * config["table_wait_multiplier"])
        
        logger.info(f"🕐 Timeout adaptativo para {lottery_name}: {adaptive_timeout}s")
        return adaptive_timeout
    
    def detect_chance_express_issues(self, lottery_name: str, duration: float, 
                                   data_count: int, visual_state: Optional[Dict] = None) -> Dict[str, Any]:
        """Detectar problemas específicos de CHANCE EXPRESS"""
        
        issues = {
            "has_issues": False,
            "issue_type": None,
            "severity": "normal",
            "recommendation": "",
            "specific_problems": []
        }
        
        if lottery_name != "CHANCE EXPRESS":
            return issues  # Solo para CHANCE EXPRESS
        
        config = self.get_lottery_config(lottery_name)
        
        # 1. Detectar carga anormalmente lenta
        if duration > config["base_timeout"]:
            issues["has_issues"] = True
            issues["specific_problems"].append(f"Carga lenta: {duration:.1f}s > {config['base_timeout']}s")
            issues["severity"] = "high"
        
        # 2. Detectar datos insuficientes (probable placeholders)
        if data_count < config["expected_min_rows"]:
            issues["has_issues"] = True
            issues["specific_problems"].append(f"Datos insuficientes: {data_count} < {config['expected_min_rows']} esperado")
            issues["severity"] = "critical" if data_count <= 1 else "high"
        
        # 3. Analizar estado visual si está disponible
        if visual_state:
            completeness = visual_state.get('data_completeness', 1.0)
            if completeness < 0.5:
                issues["has_issues"] = True
                issues["specific_problems"].append(f"Completitud visual baja: {completeness:.1%}")
                issues["severity"] = "high"
        
        # 4. Generar recomendación específica
        if issues["has_issues"]:
            if issues["severity"] == "critical":
                issues["recommendation"] = "🚨 CHANCE EXPRESS: Reiniciar proceso, posible problema del servidor"
            elif issues["severity"] == "high":
                issues["recommendation"] = "⚠️ CHANCE EXPRESS: Aumentar timeout y usar confirmación visual ML"
            else:
                issues["recommendation"] = "💡 CHANCE EXPRESS: Monitorear próximas iteraciones"
        
        return issues
    
    def update_performance_stats(self, lottery_name: str, duration: float, 
                               data_count: int, success: bool):
        """Actualizar estadísticas de rendimiento"""
        if lottery_name not in self.performance_stats:
            self.performance_stats[lottery_name] = {
                "avg_load_time": 0, "success_rate": 0,
                "placeholder_incidents": 0, "total_attempts": 0
            }
        
        stats = self.performance_stats[lottery_name]
        stats["total_attempts"] += 1
        
        # Actualizar tiempo promedio (media móvil)
        if stats["avg_load_time"] == 0:
            stats["avg_load_time"] = duration
        else:
            stats["avg_load_time"] = (stats["avg_load_time"] * 0.7) + (duration * 0.3)
        
        # Actualizar tasa de éxito
        successful_attempts = stats["total_attempts"] * stats["success_rate"]
        if success:
            successful_attempts += 1
        stats["success_rate"] = successful_attempts / stats["total_attempts"]
        
        # Detectar incidente de placeholders
        config = self.get_lottery_config(lottery_name)
        if data_count < config["expected_min_rows"]:
            stats["placeholder_incidents"] += 1
        
        logger.info(f"📊 Stats {lottery_name}: {duration:.1f}s, éxito: {success}, "
                   f"tasa éxito: {stats['success_rate']:.1%}")
    
    def get_enhanced_scraping_strategy(self, lottery_name: str) -> Dict[str, Any]:
        """Obtener estrategia de scraping mejorada para lotería específica"""
        config = self.get_lottery_config(lottery_name)
        
        strategy = {
            "lottery_name": lottery_name,
            "timeout": self.calculate_adaptive_timeout(lottery_name),
            "use_visual_ml": config["visual_confirmation_required"],
            "retry_attempts": config["retry_attempts"],
            "stability_checks": config["stability_checks"],
            "placeholder_patterns": config["placeholder_patterns"],
            "wait_strategy": "enhanced" if lottery_name == "CHANCE EXPRESS" else "standard"
        }
        
        return strategy
    
    def log_lottery_comparison(self):
        """Log comparación entre loterías para análisis"""
        chance_stats = self.performance_stats.get("CHANCE EXPRESS", {})
        ruleta_stats = self.performance_stats.get("RULETA EXPRESS", {})
        
        logger.info("📊 COMPARACIÓN DE RENDIMIENTO POR LOTERÍA:")
        logger.info(f"   🎲 CHANCE EXPRESS: {chance_stats.get('avg_load_time', 0):.1f}s avg, "
                   f"{chance_stats.get('success_rate', 0):.1%} éxito")
        logger.info(f"   🎰 RULETA EXPRESS: {ruleta_stats.get('avg_load_time', 0):.1f}s avg, "
                   f"{ruleta_stats.get('success_rate', 0):.1%} éxito")
        
        # Detectar diferencia significativa
        if (chance_stats.get('avg_load_time', 0) > 0 and 
            ruleta_stats.get('avg_load_time', 0) > 0):
            
            tiempo_diff = (chance_stats['avg_load_time'] - ruleta_stats['avg_load_time'])
            if tiempo_diff > 10:  # Más de 10 segundos de diferencia
                logger.warning(f"🚨 CHANCE EXPRESS es {tiempo_diff:.1f}s más lenta que RULETA EXPRESS")
                return True
        
        return False

# Instancia global del optimizador
chance_optimizer = ChanceExpressOptimizer()

def apply_lottery_specific_config(lottery_name: str, scraper_instance):
    """Aplicar configuración específica de lotería al scraper"""
    
    strategy = chance_optimizer.get_enhanced_scraping_strategy(lottery_name)
    
    logger.info(f"🎯 Aplicando estrategia específica para {lottery_name}:")
    logger.info(f"   ⏰ Timeout: {strategy['timeout']}s")
    logger.info(f"   👁️ Visión ML: {'Habilitada' if strategy['use_visual_ml'] else 'Deshabilitada'}")
    logger.info(f"   🔄 Reintentos: {strategy['retry_attempts']}")
    logger.info(f"   🔍 Estrategia: {strategy['wait_strategy']}")
    
    # Aplicar configuración específica al scraper
    if hasattr(scraper_instance, 'vision_engine') and strategy['use_visual_ml']:
        logger.info("👁️ Configurando confirmación visual ML para esta lotería")
    
    return strategy

def monitor_lottery_performance(lottery_name: str, start_time: float, 
                              data_count: int, success: bool) -> Dict[str, Any]:
    """Monitorear y analizar rendimiento de lotería específica"""
    
    duration = time.time() - start_time
    
    # Actualizar estadísticas
    chance_optimizer.update_performance_stats(lottery_name, duration, data_count, success)
    
    # Detectar problemas específicos de CHANCE EXPRESS
    issues = chance_optimizer.detect_chance_express_issues(lottery_name, duration, data_count)
    
    # Log resultados
    if issues["has_issues"]:
        logger.warning(f"🚨 PROBLEMAS DETECTADOS EN {lottery_name}:")
        for problem in issues["specific_problems"]:
            logger.warning(f"   • {problem}")
        logger.warning(f"   💡 {issues['recommendation']}")
    else:
        logger.info(f"✅ {lottery_name}: Rendimiento normal ({duration:.1f}s, {data_count} registros)")
    
    # Comparar rendimiento entre loterías
    comparison_needed = chance_optimizer.log_lottery_comparison()
    
    return {
        "duration": duration,
        "data_count": data_count,
        "success": success,
        "issues": issues,
        "needs_comparison_analysis": comparison_needed
    }

if __name__ == "__main__":
    # Ejemplo de uso
    print("🎯 CONFIGURACIÓN ESPECÍFICA PARA CHANCE EXPRESS")
    print("=" * 50)
    
    # Simular análisis
    optimizer = ChanceExpressOptimizer()
    
    print("\n📊 Configuraciones por lotería:")
    for lottery in ["CHANCE EXPRESS", "RULETA EXPRESS"]:
        config = optimizer.get_lottery_config(lottery)
        print(f"\n{lottery}:")
        print(f"  Timeout base: {config['base_timeout']}s")
        print(f"  Visión ML requerida: {config['visual_confirmation_required']}")
        print(f"  Filas mínimas esperadas: {config['expected_min_rows']}")
    
    print("\n✨ Sistema listo para optimización específica por lotería!") 