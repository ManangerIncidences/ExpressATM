"""
🔗 Scheduler Híbrido - ExpressATM
Scheduler que soporta tanto el sistema clásico como el inteligente
Permite migración gradual y comparación de rendimiento
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, date, timedelta
import logging
import time
import psutil
from .scraper import LotteryMonitorScraper
from .alerts import AlertSystem
from .database import SessionLocal
from .models import MonitoringSession, SystemLog
from backend.config import Config, SITE_EXPRESS, SITE_REAL
from .dom_learning_engine import dom_learner

# 🧠 Importar sistema inteligente
try:
    from .scraper_intelligent import IntelligentLotteryMonitorScraper  # type: ignore
    from .intelligence import intelligence_engine  # type: ignore
    from .dom_intelligence import dom_intelligence  # type: ignore
    INTELLIGENT_SYSTEM_AVAILABLE = True
    print("Sistema inteligente disponible")
except ImportError as e:
    INTELLIGENT_SYSTEM_AVAILABLE = False
    print(f"Sistema inteligente no disponible: {e}")

logger = logging.getLogger(__name__)

class HybridMonitoringScheduler:
    """Scheduler híbrido que soporta migración gradual"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.current_session_id = None
        
        # Configuración de migración
        self.use_intelligent_system = False  # Flag principal
        self.intelligent_percentage = 0     # Porcentaje de ejecuciones con IA
        self.comparison_mode = False        # Ejecutar ambos y comparar
        
        # � MODO CONTINUO PARA PRUEBAS
        self.continuous_mode = False        # Modo de ejecución continua
        self.continuous_delay = 10          # Segundos entre ejecuciones continuas
        
        # �🔧 INICIALIZACIÓN LAZY DE SCRAPERS (solo cuando se necesiten)
        self._classic_scraper = None
        self._intelligent_scraper = None
        
        # Sistema de alertas
        self.alert_system = AlertSystem()
        
        # Métricas de comparación
        self.performance_metrics = {
            'classic': {'count': 0, 'total_time': 0, 'errors': 0},
            'intelligent': {'count': 0, 'total_time': 0, 'errors': 0}
        }
        
        self.intelligence_enabled = False
        self._total_iterations = 0  # Contador de iteraciones completadas
        self._failed_sites = []     # Sitios que fallaron para reintento inteligente
        # === Estado de progreso (similar al scheduler clásico) ===
        import threading
        self._progress_lock = threading.Lock()
        self._progress = {"active": False, "steps": []}

        logger.info("Scheduler hibrido inicializado (scrapers lazy)")

    # ====== Gestión de progreso ======
    def _now_iso(self):
        from datetime import datetime as _dt
        return _dt.utcnow().isoformat()

    def _progress_steps_template(self):
        steps = [
            {"key": "login", "label": "Login EXPRESS", "status": "pending"},
            {"key": "navigate", "label": "Navegación EXPRESS", "status": "pending"},
            {"key": "base_filters", "label": "Filtros EXPRESS", "status": "pending"},
        ]
        for lot in SITE_EXPRESS.lotteries:
            steps.append({"key": lot["step_key"], "label": lot["name"], "status": "pending"})
        steps.append({"key": "login_real", "label": "Login REAL", "status": "pending"})
        steps.append({"key": "navigate_real", "label": "Navegación REAL", "status": "pending"})
        steps.append({"key": "base_filters_real", "label": "Filtros REAL", "status": "pending"})
        for lot in SITE_REAL.lotteries:
            steps.append({"key": lot["step_key"], "label": lot["name"], "status": "pending"})
        steps.extend([
            {"key": "data_ready", "label": "Datos listos", "status": "pending"},
            {"key": "generate_alerts", "label": "Generando alertas", "status": "pending"},
            {"key": "complete", "label": "Completado", "status": "pending"},
        ])
        return steps

    def _start_progress(self):
        with self._progress_lock:
            self._progress = {
                "active": True,
                "started_at": self._now_iso(),
                "updated_at": self._now_iso(),
                "version": 1,
                "steps": self._progress_steps_template(),
                "current": None,
                "error": None
            }
            logger.debug("[H-PROGRESS][start] version=1 steps=%s", [(s['key'], s['status']) for s in self._progress['steps']])

    def _update_progress_step(self, key: str, status: str = "running", message: str | None = None):
        with self._progress_lock:
            if not self._progress.get("active"):
                return
            steps = self._progress.get("steps", [])
            if status == "running" and self._progress.get("current") and self._progress["current"] != key:
                for s in steps:
                    if s["key"] == self._progress["current"] and s["status"] == "running":
                        s["status"] = "success"
                        s["finished_at"] = self._now_iso()
                        break
            for s in steps:
                if s["key"] == key:
                    if status == "error":
                        s["status"] = "error"
                        s["error_message"] = message or "Error"
                        s["finished_at"] = self._now_iso()
                        self._progress["error"] = s.get("error_message")
                        self._progress["current"] = None
                    elif status == "running":
                        if s["status"] in ("pending", "running"):
                            s["status"] = "running"
                            s.setdefault("started_at", self._now_iso())
                            self._progress["current"] = key
                    elif status == "success":
                        if s["status"] != "success":
                            s["status"] = "success"
                            s["finished_at"] = self._now_iso()
                            if self._progress.get("current") == key:
                                self._progress["current"] = None
                    break
            self._progress["updated_at"] = self._now_iso()
            self._progress["version"] = self._progress.get("version", 0) + 1
            try:
                logger.debug("[H-PROGRESS][update] step=%s status=%s version=%s snapshot=%s", key, status, self._progress['version'], [(s['key'], s['status']) for s in steps])
            except Exception:
                pass

    def _finish_progress(self, success: bool):
        with self._progress_lock:
            if not self._progress.get("active"):
                return
            if self._progress.get("current"):
                for s in self._progress["steps"]:
                    if s["key"] == self._progress["current"] and s["status"] == "running":
                        s["status"] = "success" if success else "error"
                        s["finished_at"] = self._now_iso()
                        break
            for s in self._progress["steps"]:
                if s["key"] == "complete" and s["status"] in ("pending", "running"):
                    s["status"] = "success" if success and not self._progress.get("error") else "error"
                    s["finished_at"] = self._now_iso()
                    break
            self._progress["active"] = False
            self._progress["finished_at"] = self._now_iso()
            self._progress["current"] = None
            self._progress["updated_at"] = self._now_iso()
            self._progress["version"] = self._progress.get("version", 0) + 1
            try:
                logger.debug("[H-PROGRESS][finish] success=%s version=%s steps=%s", success, self._progress['version'], [(s['key'], s['status']) for s in self._progress['steps']])
            except Exception:
                pass

    def get_progress(self) -> dict:
        with self._progress_lock:
            prog = self._progress.copy()
            prog["steps"] = [s.copy() for s in prog.get("steps", [])]
            return prog
        
    @property
    def classic_scraper(self):
        """Obtener scraper clásico (lazy initialization)"""
        if self._classic_scraper is None:
            logger.info("🔄 Inicializando scraper clásico...")
            self._classic_scraper = LotteryMonitorScraper()
        return self._classic_scraper
    
    @property
    def intelligent_scraper(self):
        """Obtener scraper inteligente (lazy initialization)"""
        if not INTELLIGENT_SYSTEM_AVAILABLE:
            return None
            
        if self._intelligent_scraper is None:
            logger.info("🧠 Inicializando scraper inteligente...")
            self._intelligent_scraper = IntelligentLotteryMonitorScraper()
        return self._intelligent_scraper
    
    def cleanup_scrapers(self):
        """Limpiar scrapers activos de forma segura"""
        try:
            if self._classic_scraper is not None:
                if hasattr(self._classic_scraper, 'cleanup_safe'):
                    self._classic_scraper.cleanup_safe()
                elif hasattr(self._classic_scraper, 'driver') and self._classic_scraper.driver:
                    try:
                        self._classic_scraper.driver.quit()
                    except:
                        pass
                logger.info("🔄 Scraper clásico cerrado")
                self._classic_scraper = None
                
            if self._intelligent_scraper is not None:
                if hasattr(self._intelligent_scraper, 'cleanup_safe'):
                    self._intelligent_scraper.cleanup_safe()
                elif hasattr(self._intelligent_scraper, 'driver') and self._intelligent_scraper.driver:
                    try:
                        self._intelligent_scraper.driver.quit()
                    except:
                        pass
                logger.info("🧠 Scraper inteligente cerrado")
                self._intelligent_scraper = None
                
        except Exception as e:
            logger.warning(f"Error limpiando scrapers: {e}")
    
    def enable_intelligent_system(self, percentage: float = 100.0):
        """Habilitar sistema inteligente gradualmente"""
        if not INTELLIGENT_SYSTEM_AVAILABLE:
            logger.warning("Sistema inteligente no disponible")
            return False
            
        self.use_intelligent_system = True
        self.intelligent_percentage = min(100.0, max(0.0, percentage))
        self.intelligence_enabled = True
        
        logger.info(f"🧠 Sistema inteligente habilitado al {self.intelligent_percentage}%")
        return True
    
    def disable_intelligent_system(self):
        """Deshabilitar sistema inteligente"""
        self.use_intelligent_system = False
        self.intelligent_percentage = 0
        self.intelligence_enabled = False
        logger.info("🔄 Volviendo al sistema clásico")
    
    def enable_comparison_mode(self):
        """Habilitar modo comparación (ejecutar ambos sistemas)"""
        if not INTELLIGENT_SYSTEM_AVAILABLE:
            return False
            
        self.comparison_mode = True
        logger.info("⚖️  Modo comparación habilitado")
        return True
    
    def disable_comparison_mode(self):
        """Deshabilitar modo comparación"""
        self.comparison_mode = False
        logger.info("⚖️  Modo comparación deshabilitado")
    
    def update_settings(self, settings_dict: dict) -> bool:
        """Actualizar configuración de monitorización y umbrales en caliente en modo híbrido"""
        try:
            # Actualizar intervalo de monitoreo
            interval = settings_dict.get('monitoringInterval')
            if interval:
                from apscheduler.triggers.interval import IntervalTrigger
                Config.MONITORING_INTERVAL = interval
                job = self.scheduler.get_job('monitoring_job')
                if job:
                    job.reschedule(trigger=IntervalTrigger(minutes=interval))
                logger.info(f"Intervalo de monitoreo actualizado a {interval} minutos (híbrido)")
            # Actualizar umbrales de alerta
            Config.ALERT_THRESHOLDS['sales_threshold'] = settings_dict.get('salesThreshold', Config.ALERT_THRESHOLDS['sales_threshold'])
            Config.ALERT_THRESHOLDS['balance_threshold'] = settings_dict.get('balanceThreshold', Config.ALERT_THRESHOLDS['balance_threshold'])
            Config.ALERT_THRESHOLDS['growth_variation'] = settings_dict.get('growthVariation', Config.ALERT_THRESHOLDS['growth_variation'])
            Config.ALERT_THRESHOLDS['sustained_growth'] = settings_dict.get('sustainedGrowth', Config.ALERT_THRESHOLDS['sustained_growth'])
            # Actualizar headless y flags de filtros y alertas
            Config.HEADLESS_MODE = settings_dict.get('browserHeadless', Config.HEADLESS_MODE)
            Config.FILTER_SURIEL = settings_dict.get('filterSuriel', getattr(Config, 'FILTER_SURIEL', True))
            Config.FILTER_TOTAL_GENERAL = settings_dict.get('filterTotalGeneral', getattr(Config, 'FILTER_TOTAL_GENERAL', True))
            Config.ENABLE_GROWTH_ALERTS = settings_dict.get('enableGrowthAlerts', getattr(Config, 'ENABLE_GROWTH_ALERTS', True))
            Config.ENABLE_THRESHOLD_ALERTS = settings_dict.get('enableThresholdAlerts', getattr(Config, 'ENABLE_THRESHOLD_ALERTS', True))
            return True
        except Exception as e:
            logger.error(f"Error actualizando configuración en HybridScheduler: {e}")
            return False

    def get_settings(self) -> dict:
        """Obtener configuración actual del sistema híbrido"""
        try:
            return {
                'monitoringInterval': Config.MONITORING_INTERVAL,
                'browserHeadless': Config.HEADLESS_MODE,
                'filterSuriel': getattr(Config, 'FILTER_SURIEL', True),
                'filterTotalGeneral': getattr(Config, 'FILTER_TOTAL_GENERAL', True),
                'enableGrowthAlerts': getattr(Config, 'ENABLE_GROWTH_ALERTS', True),
                'enableThresholdAlerts': getattr(Config, 'ENABLE_THRESHOLD_ALERTS', True),
                'salesThreshold': Config.ALERT_THRESHOLDS.get('sales_threshold'),
                'balanceThreshold': Config.ALERT_THRESHOLDS.get('balance_threshold'),
                'growthVariation': Config.ALERT_THRESHOLDS.get('growth_variation'),
                'sustainedGrowth': Config.ALERT_THRESHOLDS.get('sustained_growth')
            }
        except Exception as e:
            logger.error(f"Error obteniendo configuración en HybridScheduler: {e}")
            return {}
    
    def should_use_intelligent_system(self) -> bool:
        """Determinar si usar sistema inteligente en esta iteración"""
        if not self.use_intelligent_system or not INTELLIGENT_SYSTEM_AVAILABLE:
            return False
        
        if self.intelligent_percentage >= 100:
            return True
        
        # Usar porcentaje para decidir
        import random
        return random.random() * 100 < self.intelligent_percentage
    
    def execute_iteration_classic(self) -> dict:
        """Ejecutar iteración clásica con scraping paralelo multi-sitio"""
        start_time = time.time()
        vision_activated = False
        
        try:
            logger.info("🔄 Ejecutando iteración clásica (multi-sitio paralelo)...")
            if not self._progress.get("active"):
                self._start_progress()
            self._update_progress_step("login", "running")
            
            # ===== MONITOREO PREVENTIVO DE IRREGULARIDADES =====
            irregularities_detected = self._detect_pre_execution_irregularities()
            if irregularities_detected:
                logger.warning("🚨 IRREGULARIDADES DETECTADAS - Activando visión preventiva...")
                vision_activated = self._activate_preventive_vision()
            
            # === EJECUCIÓN PARALELA MULTI-SITIO ===
            import threading
            
            _real_generic_map = {"login": "login_real", "navigate": "navigate_real", "base_filters": "base_filters_real"}
            def _real_progress_cb(key, status, message=None):
                mapped = _real_generic_map.get(key, key)
                self._update_progress_step(mapped, status, message)
            
            site_results = {}  # site_id -> list[dict]
            site_scrapers = []  # para cleanup
            
            def _run_site(site_config, cb):
                try:
                    scraper = LotteryMonitorScraper(progress_callback=cb, site_config=site_config)
                    site_scrapers.append(scraper)
                    data = scraper.scrape_all_data()
                    site_results[site_config.site_id] = data or []
                    logger.info(f"✅ Sitio {site_config.site_id}: {len(data or [])} registros")
                except Exception as e:
                    logger.error(f"❌ Sitio {site_config.site_id} falló: {e}")
                    site_results[site_config.site_id] = []
                    # Asegurar cleanup del scraper en caso de excepción
                    if site_scrapers:
                        try:
                            site_scrapers[-1].cleanup_safe()
                        except Exception:
                            pass
            
            t_express = threading.Thread(target=_run_site, args=(SITE_EXPRESS, self._update_progress_step), daemon=True)
            t_real = threading.Thread(target=_run_site, args=(SITE_REAL, _real_progress_cb), daemon=True)
            
            t_express.start()
            t_real.start()
            
            t_express.join(timeout=600)
            t_real.join(timeout=600)
            
            if t_express.is_alive():
                logger.warning("⏱️ Timeout en sitio EXPRESS")
            if t_real.is_alive():
                logger.warning("⏱️ Timeout en sitio REAL")
            
            # Forzar cleanup de todos los scrapers (incluso si hilos siguen vivos)
            for s in site_scrapers:
                try:
                    s.cleanup_safe()
                except Exception:
                    pass
            
            # Detectar sitios que fallaron para reintento inteligente
            for site_cfg in [SITE_EXPRESS, SITE_REAL]:
                if not site_results.get(site_cfg.site_id):
                    self._failed_sites.append(site_cfg)
                    logger.warning(f"⚠️ Sitio {site_cfg.site_id} sin datos, marcado para reintento")
            
            # Combinar resultados parciales (resiliencia)
            scraped_data = []
            for data in site_results.values():
                scraped_data.extend(data)
            
            # Cleanup de scrapers creados en hilos
            for s in site_scrapers:
                try:
                    s.cleanup_safe()
                except Exception:
                    pass
            # Limpiar referencia al scraper clásico legacy
            self._classic_scraper = None
            
            if not scraped_data:
                logger.warning("No se obtuvieron datos del scraping multi-sitio")
                if not vision_activated:
                    logger.critical("🆘 ACTIVANDO VISIÓN DE EMERGENCIA - Sin datos obtenidos")
                    self._activate_emergency_vision()
                
                self._update_progress_step("data_ready", "error", "Sin datos")
                self._finish_progress(False)
                return {
                    'success': False,
                    'method': 'classic',
                    'duration': time.time() - start_time,
                    'data_count': 0,
                    'error': 'No data obtained',
                    'vision_activated': vision_activated
                }
            
            # Procesar alertas
            self._update_progress_step("data_ready", "success")
            self._update_progress_step("generate_alerts", "running")
            with SessionLocal() as db:
                alerts_generated = self.alert_system.process_agencies_data(scraped_data, db)
            self._update_progress_step("generate_alerts", "success")
            
            duration = time.time() - start_time
            self.performance_metrics['classic']['count'] += 1
            self.performance_metrics['classic']['total_time'] += duration
            
            express_count = len(site_results.get("express", []))
            real_count = len(site_results.get("real", []))
            logger.info(f"✅ Iteración clásica completada: EXPRESS={express_count}, REAL={real_count}, total={len(scraped_data)} agencias, {len(alerts_generated)} alertas en {duration:.2f}s")
            
            self._finish_progress(True)
            return {
                'success': True,
                'method': 'classic',
                'duration': duration,
                'data_count': len(scraped_data),
                'alerts_count': len(alerts_generated),
                'data': scraped_data,
                'vision_activated': vision_activated
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.performance_metrics['classic']['errors'] += 1
            logger.error(f"❌ Error en iteración clásica: {e}")
            
            if not vision_activated:
                logger.critical("🆘 ACTIVANDO VISIÓN DE EMERGENCIA - Error detectado")
                self._activate_emergency_vision()
            
            self._update_progress_step("complete", "error", str(e))
            self._finish_progress(False)
            return {
                'success': False,
                'method': 'classic', 
                'duration': duration,
                'error': str(e),
                'vision_activated': vision_activated
            }
    
    def _detect_pre_execution_irregularities(self) -> bool:
        """🔍 Detectar irregularidades ANTES de ejecutar scraping"""
        try:
            # 1. Verificar uso anómalo de CPU/memoria
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > 80 or memory_percent > 85:
                logger.warning(f"🚨 Recursos del sistema elevados: CPU {cpu_percent}%, RAM {memory_percent}%")
                return True
            
            # 2. Verificar historial de fallos recientes
            recent_failures = self._check_recent_failures()
            if recent_failures > 2:
                logger.warning(f"🚨 {recent_failures} fallos recientes detectados")
                return True
                
            # 3. Verificar lentitud en iteraciones anteriores usando DOM Learning
            try:
                from .dom_learning_engine import dom_learner
                historical_performance = dom_learner.get_recent_performance_trend()
                
                if historical_performance.get('declining_performance', False):
                    logger.warning("🚨 Rendimiento declinante detectado en iteraciones recientes")
                    return True
                    
                if historical_performance.get('anomalous_duration', False):
                    logger.warning("🚨 Duración anómala detectada en análisis DOM")
                    return True
                    
            except Exception as e:
                logger.debug(f"No se pudo verificar rendimiento DOM: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error detectando irregularidades: {e}")
            return False
    
    def _check_recent_failures(self) -> int:
        """Verificar fallos recientes en base de datos"""
        try:
            with SessionLocal() as db:
                from datetime import datetime, timedelta
                recent_time = datetime.now() - timedelta(hours=2)
                
                failures = db.query(SystemLog).filter(
                    SystemLog.timestamp >= recent_time,
                    SystemLog.level == 'ERROR'
                ).count()
                
                return failures
        except Exception:
            return 0
    
    def _activate_preventive_vision(self) -> bool:
        """👁️ Activar sistema de visión preventiva"""
        try:
            logger.info("👁️ ACTIVANDO SISTEMA DE VISIÓN PREVENTIVA...")
            
            # Verificar si el sistema de visión está disponible
            if not hasattr(self.classic_scraper, 'vision_engine'):
                logger.warning("⚠️ Sistema de visión no disponible en scraper clásico")
                return False
            
            # Activar visión por tiempo limitado (30 segundos)
            vision_result = self.classic_scraper.vision_engine.activate_preventive_monitoring(duration=30)
            
            if vision_result['success']:
                logger.info(f"✅ Visión preventiva activada: {vision_result['monitoring_type']}")
                
                # Log insights capturados
                insights = vision_result.get('insights', [])
                for insight in insights:
                    logger.info(f"💡 Insight visual: {insight}")
                
                return True
            else:
                logger.warning(f"❌ No se pudo activar visión preventiva: {vision_result.get('error', 'Unknown')}")
                return False
                
        except Exception as e:
            logger.error(f"Error activando visión preventiva: {e}")
            return False
    
    def _activate_emergency_vision(self):
        """🆘 Activar visión de emergencia cuando ya ocurrió el fallo"""
        try:
            logger.critical("🆘 ACTIVANDO VISIÓN DE EMERGENCIA...")
            
            # Verificar si tenemos sistema de visión disponible
            if not hasattr(self.classic_scraper, 'vision_engine') or not self.classic_scraper.vision_engine:
                logger.error("⚠️ Sistema de visión no disponible para emergencia")
                return
            
            # Verificar si el driver está activo antes de capturar
            driver_available = False
            try:
                if hasattr(self.classic_scraper, 'driver') and self.classic_scraper.driver:
                    # Verificar si el driver está realmente activo
                    _ = self.classic_scraper.driver.title
                    driver_available = True
            except Exception as e:
                logger.warning(f"Driver no disponible para visión de emergencia: {e}")
                driver_available = False
            
            if not driver_available:
                logger.critical("📸 Estado de emergencia capturado: Screenshot FALLÓ - Driver no disponible")
                
                # Registrar el fallo sin intentar captura
                with SessionLocal() as db:
                    emergency_log = SystemLog(
                        level='CRITICAL',
                        message="Visión de emergencia: Driver no disponible para captura - Sistema en estado crítico",
                        module='scheduler_hybrid',
                        timestamp=datetime.now()
                    )
                    db.add(emergency_log)
                    db.commit()
                return
            
            # Capturar estado visual actual para diagnóstico
            emergency_result = self.classic_scraper.vision_engine.capture_emergency_state()
            
            if emergency_result['success']:
                logger.critical(f"📸 Estado de emergencia capturado: {emergency_result['state_description']}")
                
                # Guardar evidencia del fallo
                with SessionLocal() as db:
                    emergency_log = SystemLog(
                        level='CRITICAL',
                        message=f"Visión de emergencia: {emergency_result['state_description']} - Detalles: {str(emergency_result)}",
                        module='scheduler_hybrid',
                        timestamp=datetime.now()
                    )
                    db.add(emergency_log)
                    db.commit()
                    
                # Intentar diagnóstico automático
                diagnosis = emergency_result.get('auto_diagnosis', {})
                if diagnosis:
                    logger.critical(f"🔬 Diagnóstico automático: {diagnosis.get('probable_cause', 'Desconocido')}")
                    logger.critical(f"💡 Recomendación: {diagnosis.get('recommendation', 'Reiniciar sistema')}")
            else:
                logger.critical(f"📸 Estado de emergencia capturado: Screenshot FALLÓ - {emergency_result.get('error', 'Error desconocido')}")
            
        except Exception as e:
            logger.error(f"Error en visión de emergencia: {e}")
    
    def _execute_scraping_with_monitoring(self):
        """Ejecutar scraping con monitoreo continuo de irregularidades"""
        try:
            # Verificar si hay señales de problema cada 10 segundos durante el scraping
            import threading
            import time
            
            monitoring_active = True
            vision_triggered = False
            
            def monitor_during_scraping():
                nonlocal monitoring_active, vision_triggered
                while monitoring_active:
                    time.sleep(10)  # Verificar cada 10 segundos
                    
                    if not monitoring_active:
                        break
                        
                    # Verificar señales de problemas durante ejecución
                    cpu_percent = psutil.cpu_percent()
                    if cpu_percent > 90 and not vision_triggered:
                        logger.warning("🚨 CPU crítico durante scraping - Activando visión")
                        self._activate_preventive_vision()
                        vision_triggered = True
            
            # Iniciar monitoreo en hilo separado
            monitor_thread = threading.Thread(target=monitor_during_scraping, daemon=True)
            monitor_thread.start()
            
            try:
                # Ejecutar scraping normal
                scraped_data = self.classic_scraper.scrape_all_data()
                
                # Pequeña pausa para permitir que el sistema de visión procese si es necesario
                time.sleep(2)
                
                return scraped_data
            finally:
                # Detener monitoreo
                monitoring_active = False
                
        except Exception as e:
            logger.error(f"Error en scraping con monitoreo: {e}")
            return self.classic_scraper.scrape_all_data()  # Fallback normal
    
    def execute_iteration_intelligent(self) -> dict:
        """Ejecutar iteración con sistema inteligente"""
        start_time = time.time()
        try:
            logger.info("🧠 Ejecutando iteración inteligente...")
            if not self._progress.get("active"):
                self._start_progress()
            self._update_progress_step("login", "running")
            
            # Ejecutar scraping inteligente
            # Asegurar callback también en inteligente
            if self._intelligent_scraper is None:
                self._intelligent_scraper = IntelligentLotteryMonitorScraper(progress_callback=self._update_progress_step) if INTELLIGENT_SYSTEM_AVAILABLE else None
            else:
                try:
                    self._intelligent_scraper._progress_cb = self._update_progress_step
                except Exception:
                    pass
            scraped_data = self.intelligent_scraper.scrape_all_data_intelligent()
            
            if not scraped_data:
                logger.warning("No se obtuvieron datos del scraping inteligente")
                self._update_progress_step("data_ready", "error", "Sin datos")
                self._finish_progress(False)
                return {
                    'success': False,
                    'method': 'intelligent',
                    'duration': time.time() - start_time,
                    'data_count': 0,
                    'error': 'No data obtained'
                }
            
            # Procesar alertas
            self._update_progress_step("data_ready", "success")
            self._update_progress_step("generate_alerts", "running")
            with SessionLocal() as db:
                alerts_generated = self.alert_system.process_agencies_data(scraped_data, db)
            self._update_progress_step("generate_alerts", "success")
            
            duration = time.time() - start_time
            self.performance_metrics['intelligent']['count'] += 1
            self.performance_metrics['intelligent']['total_time'] += duration
            
            logger.info(f"🧠 Iteración inteligente completada: {len(scraped_data)} agencias, {len(alerts_generated)} alertas en {duration:.2f}s")
            
            self._finish_progress(True)
            return {
                'success': True,
                'method': 'intelligent',
                'duration': duration,
                'data_count': len(scraped_data),
                'alerts_count': len(alerts_generated),
                'data': scraped_data,
                'intelligence_summary': self.intelligent_scraper.get_intelligence_summary() if self.intelligent_scraper else None
            }
            
        except Exception as e:
            duration = time.time() - start_time
            self.performance_metrics['intelligent']['errors'] += 1
            logger.error(f"❌ Error en iteración inteligente: {e}")
            
            self._update_progress_step("complete", "error", str(e))
            self._finish_progress(False)
            return {
                'success': False,
                'method': 'intelligent',
                'duration': duration,
                'error': str(e)
            }
    
    def execute_comparison_iteration(self) -> dict:
        """Ejecutar ambos sistemas y comparar resultados"""
        logger.info("⚖️  Ejecutando iteración comparativa...")
        
        classic_result = self.execute_iteration_classic()
        intelligent_result = self.execute_iteration_intelligent()
        
        # Analizar diferencias
        comparison = self.analyze_results_comparison(classic_result, intelligent_result)
        
        # Usar el resultado más exitoso
        primary_result = intelligent_result if intelligent_result['success'] else classic_result
        
        return {
            **primary_result,
            'comparison_mode': True,
            'classic_result': classic_result,
            'intelligent_result': intelligent_result,
            'comparison_analysis': comparison
        }
    
    def analyze_results_comparison(self, classic_result: dict, intelligent_result: dict) -> dict:
        """Analizar diferencias entre resultados clásicos e inteligentes"""
        try:
            analysis = {
                'both_successful': classic_result['success'] and intelligent_result['success'],
                'performance_difference': None,
                'data_difference': None,
                'recommendation': 'continue_testing'
            }
            
            if analysis['both_successful']:
                # Comparar rendimiento
                time_improvement = ((classic_result['duration'] - intelligent_result['duration']) / classic_result['duration']) * 100
                analysis['performance_difference'] = {
                    'classic_duration': classic_result['duration'],
                    'intelligent_duration': intelligent_result['duration'],
                    'improvement_percentage': time_improvement
                }
                
                # Comparar datos obtenidos
                analysis['data_difference'] = {
                    'classic_count': classic_result.get('data_count', 0),
                    'intelligent_count': intelligent_result.get('data_count', 0),
                    'data_consistency': abs(classic_result.get('data_count', 0) - intelligent_result.get('data_count', 0)) <= 2
                }
                
                # Generar recomendación
                if time_improvement > 20 and analysis['data_difference']['data_consistency']:
                    analysis['recommendation'] = 'migrate_to_intelligent'
                elif time_improvement < -10:  # Sistema inteligente es más lento
                    analysis['recommendation'] = 'stick_to_classic'
                else:
                    analysis['recommendation'] = 'continue_testing'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analizando comparación: {e}")
            return {'error': str(e)}
    
    def execute_single_iteration(self):
        """Ejecutar una sola iteración (punto de entrada principal)"""
        logger.info("🔄 INICIANDO ITERACIÓN AUTOMÁTICA PROGRAMADA")
        try:
            if self.comparison_mode:
                logger.info("🔄 Ejecutando en modo comparación")
                result = self.execute_comparison_iteration()
            elif self.should_use_intelligent_system():
                logger.info("🔄 Ejecutando iteración inteligente")
                result = self.execute_iteration_intelligent()
            else:
                logger.info("🔄 Ejecutando iteración clásica automática")
                result = self.execute_iteration_classic()
                
        except Exception as e:
            logger.error(f"❌ Error en ejecución de iteración automática: {e}")
            return {
                'success': False,
                'method': 'unknown',
                'error': str(e),
                'duration': 0
            }
        
        finally:
            self._total_iterations += 1
            # Limpiar estado al finalizar
            import os
            current_pid = os.getpid()
            logging.info(f"PID: {current_pid} - Proceso de monitoreo finalizado. Total iteraciones: {self._total_iterations}")
            # Reintento inteligente: si algún sitio falló, programar reintento en 2 minutos
            if self._failed_sites:
                failed_copy = list(self._failed_sites)
                self._failed_sites.clear()
                logger.info(f"🔄 Programando reintento inteligente para sitios fallidos: {[s.site_id for s in failed_copy]} en 120s")
                import threading
                def _retry():
                    time.sleep(120)
                    if not self._progress.get("active"):
                        self._execute_site_scraping(failed_copy)
                threading.Thread(target=_retry, daemon=True).start()

        if result and result.get("status") == "success":
            return {"status": "completed", "message": "Monitoreo finalizado con éxito", "data": result}
        else:
            return {"status": "failed", "message": "Monitoreo finalizado con errores", "data": result}

    def enable_continuous_mode(self, delay_seconds: int = 10):
        """🚀 Activar modo continuo de ejecución (para pruebas)"""
        self.continuous_mode = True
        self.continuous_delay = delay_seconds
        logger.info(f"🚀 MODO CONTINUO ACTIVADO: {delay_seconds}s entre ejecuciones")
        return {
            'success': True,
            'message': f'Modo continuo activado con {delay_seconds}s de delay',
            'continuous_mode': True,
            'delay_seconds': delay_seconds
        }
    
    def disable_continuous_mode(self):
        """🛑 Desactivar modo continuo de ejecución"""
        self.continuous_mode = False
        # Cancelar job continuo si existe
        try:
            self.scheduler.remove_job('continuous_iteration')
            logger.info("🚀 Job continuo cancelado")
        except:
            pass
        logger.info("🛑 MODO CONTINUO DESACTIVADO")
        return {
            'success': True,
            'message': 'Modo continuo desactivado',
            'continuous_mode': False
        }
    
    def _execute_site_scraping(self, site_configs):
        """Ejecutar scraping para una lista de sitios específicos (reintento o dirigido)"""
        import threading
        start_time = time.time()
        logger.info(f"🎯 Ejecutando scraping dirigido para: {[s.site_id for s in site_configs]}")
        
        if not self._progress.get("active"):
            self._start_progress()
        
        _real_generic_map = {"login": "login_real", "navigate": "navigate_real", "base_filters": "base_filters_real"}
        def _real_progress_cb(key, status, message=None):
            mapped = _real_generic_map.get(key, key)
            self._update_progress_step(mapped, status, message)
        
        site_results = {}
        site_scrapers = []
        
        def _run_site(site_config, cb):
            try:
                scraper = LotteryMonitorScraper(progress_callback=cb, site_config=site_config)
                site_scrapers.append(scraper)
                data = scraper.scrape_all_data()
                site_results[site_config.site_id] = data or []
                logger.info(f"✅ Sitio {site_config.site_id}: {len(data or [])} registros")
            except Exception as e:
                logger.error(f"❌ Sitio {site_config.site_id} falló: {e}")
                site_results[site_config.site_id] = []
        
        threads = []
        for sc in site_configs:
            cb = _real_progress_cb if sc.site_id == "real" else self._update_progress_step
            t = threading.Thread(target=_run_site, args=(sc, cb), daemon=True)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=600)
        
        for s in site_scrapers:
            try:
                s.cleanup_safe()
            except Exception:
                pass
        
        scraped_data = []
        for data in site_results.values():
            scraped_data.extend(data)
        
        if scraped_data:
            with SessionLocal() as db:
                alerts_generated = self.alert_system.process_agencies_data(scraped_data, db)
            logger.info(f"✅ Scraping dirigido completado: {len(scraped_data)} agencias, {len(alerts_generated)} alertas en {time.time()-start_time:.2f}s")
            self._total_iterations += 1
        else:
            alerts_generated = []
            logger.warning("⚠️ Scraping dirigido sin datos obtenidos")
        
        self._finish_progress(bool(scraped_data))
        return {
            'success': bool(scraped_data),
            'data_count': len(scraped_data),
            'alerts_count': len(alerts_generated),
            'sites': [s.site_id for s in site_configs],
            'duration': time.time() - start_time
        }
    
    def execute_targeted_iteration(self, site_id: str):
        """Ejecutar scraping dirigido a un sitio específico desde la UI"""
        site_map = {"express": SITE_EXPRESS, "real": SITE_REAL}
        site_config = site_map.get(site_id)
        if not site_config:
            return {'success': False, 'error': f'Sitio desconocido: {site_id}'}
        
        if self._progress.get("active"):
            return {'success': False, 'error': 'Ya hay una iteración en progreso'}
        
        import threading
        def _run():
            try:
                self._execute_site_scraping([site_config])
            except Exception as e:
                logger.exception(f"Error en scraping dirigido {site_id}: %s", e)
                self._finish_progress(False)
        
        threading.Thread(target=_run, daemon=True).start()
        return {'success': True, 'message': f'Scraping dirigido a {site_id} iniciado'}
    
    def execute_manual_iteration(self):
        """🔄 Ejecutar una iteración manual de monitoreo"""
        try:
            logger.info("🔄 Iniciando iteración manual asíncrona (no bloqueante)...")
            if self._progress.get("active"):
                return {
                    'success': False,
                    'message': 'Ya hay una iteración en progreso',
                    'result': None
                }
            # Inicio temprano de progreso
            self._start_progress()
            self._update_progress_step("login", "running")
            import threading
            def _run():
                try:
                    self.execute_single_iteration()
                except Exception as e:
                    logger.exception("Error en hilo de iteración manual: %s", e)
                    self._update_progress_step("complete", "error", str(e))
                    self._finish_progress(False)
            threading.Thread(target=_run, daemon=True).start()
            return {
                'success': True,
                'message': 'Iteración manual lanzada',
                'result': None
            }
            
        except Exception as e:
            logger.error(f"❌ Error en iteración manual: {e}")
            return {
                'success': False,
                'message': f'Error en iteración manual: {str(e)}',
                'result': None
            }
    
    def _update_monitoring_interval(self, interval: int):
        """Actualizar intervalo de monitoreo"""
        try:
            # Actualizar configuración local
            Config.MONITORING_INTERVAL = interval
            
            # Si hay un job activo, reagendarlo
            if self.is_running:
                job = self.scheduler.get_job('monitoring_job')
                if job:
                    from apscheduler.triggers.interval import IntervalTrigger
                    job.reschedule(trigger=IntervalTrigger(minutes=interval))
                    logger.info(f"Intervalo de monitoreo actualizado a {interval} minutos")
            
            return True
        except Exception as e:
            logger.error(f"Error actualizando intervalo: {e}")
            return False
    
    def _update_sales_threshold(self, threshold: float):
        """Actualizar umbral de ventas"""
        try:
            Config.ALERT_THRESHOLDS['sales_threshold'] = threshold
            logger.info(f"Umbral de ventas actualizado a {threshold}")
            return True
        except Exception as e:
            logger.error(f"Error actualizando umbral de ventas: {e}")
            return False
    
    def _update_wait_time(self, wait_type: str, wait_time: float):
        """Actualizar tiempos de espera"""
        try:
            if wait_type == "page_load":
                Config.WAIT_TIME_PAGE_LOAD = wait_time
            elif wait_type == "element":
                Config.WAIT_TIME_ELEMENT = wait_time
            else:
                logger.warning(f"Tipo de wait_time desconocido: {wait_type}")
                return False
            
            logger.info(f"Tiempo de espera {wait_type} actualizado a {wait_time}s")
            return True
        except Exception as e:
            logger.error(f"Error actualizando wait_time: {e}")
            return False
    
    def _schedule_continuous_iteration(self):
        """🔄 Método helper para programar iteración continua (usado en reintentos)"""
        try:
            from datetime import timedelta
            next_run_time = datetime.now() + timedelta(seconds=self.continuous_delay)
            logger.info(f"🔄 Reintentando programación continua para: {next_run_time.strftime('%H:%M:%S')}")
            
            self.scheduler.add_job(
                self.execute_single_iteration,
                'date',
                run_date=next_run_time,
                id='continuous_iteration',
                replace_existing=True
            )
            logger.info("✅ Iteración continua reprogramada exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Fallo en reprogramación continua: {e}")
    
    def get_status(self):
        """Obtener estado del scheduler"""
        status = {
            'is_running': self.is_running,
            'monitoring_interval': Config.MONITORING_INTERVAL,
            'use_intelligent_system': self.use_intelligent_system,
            'intelligent_percentage': self.intelligent_percentage,
            'comparison_mode': self.comparison_mode,
            'intelligent_system_available': INTELLIGENT_SYSTEM_AVAILABLE,
            # 'performance_metrics': self.get_performance_comparison(),
            # 🚀 Estado del modo continuo
            'continuous_mode': self.continuous_mode,
            'continuous_delay': self.continuous_delay if self.continuous_mode else None,
            'total_iterations': self._total_iterations
        }
        
        # Agregar tiempo de próxima ejecución del job de monitoreo
        try:
            job = self.scheduler.get_job('monitoring_job')
            if job and job.next_run_time:
                status['next_run_time'] = job.next_run_time.isoformat()
        except Exception:
            pass
        
        # Agregar tiempo de próxima ejecución continua si existe
        try:
            continuous_job = self.scheduler.get_job('continuous_iteration')
            if continuous_job and continuous_job.next_run_time:
                status['next_continuous_run'] = continuous_job.next_run_time.isoformat()
        except Exception:
            pass
            
        return status
    
    def get_intelligence_status(self):
        """Obtener estado completo del sistema de inteligencia"""
        if not INTELLIGENT_SYSTEM_AVAILABLE:
            return {
                'intelligence_enabled': False,
                'error': 'Sistema inteligente no disponible'
            }
            
        try:
            adaptive_config = intelligence_engine.get_adaptive_config() if hasattr(intelligence_engine, 'get_adaptive_config') else {}
            failure_prediction = intelligence_engine.predict_failure_risk({'current_hour': datetime.now().hour}) if hasattr(intelligence_engine, 'predict_failure_risk') else None
            
            return {
                'intelligence_enabled': self.intelligence_enabled,
                'adaptive_config': adaptive_config,
                'failure_prediction': failure_prediction,
                'system_metrics': {
                    'prediction_accuracy': 0.85,  # Placeholder
                    'optimizations_applied': len(dom_intelligence.optimizer.current_optimizations) if dom_intelligence else 0
                },
                'anomalies_detected': 0,  # Placeholder
                'optimizations_available': len(adaptive_config) if adaptive_config else 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de inteligencia: {e}")
            return {
                'intelligence_enabled': self.intelligence_enabled,
                'error': str(e)
            }
    
    def toggle_intelligence(self, enabled: bool):
        """Activar/desactivar sistema de inteligencia"""
        if enabled:
            return self.enable_intelligent_system()
        else:
            self.disable_intelligent_system()
            return True
    
    def start_monitoring(self) -> bool:
        """Iniciar el monitoreo automático"""
        try:
            if self.is_running:
                logger.warning("El monitoreo ya está en ejecución")
                return False
            
            # Crear nueva sesión de monitoreo
            db = SessionLocal()
            session = MonitoringSession(
                session_date=date.today().isoformat(),
                status="active"
            )
            db.add(session)
            db.commit()
            self.current_session_id = session.id
            db.close()
            
            # Configurar tarea programada
            self.scheduler.add_job(
                func=self.execute_single_iteration,
                trigger=IntervalTrigger(minutes=Config.MONITORING_INTERVAL),
                id='monitoring_job',
                replace_existing=True
            )
            
            # Iniciar el scheduler
            if not self.scheduler.running:
                self.scheduler.start()
            
            self.is_running = True
            logger.info(f"✅ Monitoreo híbrido iniciado (intervalo: {Config.MONITORING_INTERVAL} min)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando monitoreo: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Detener el monitoreo automático"""
        try:
            if not self.is_running:
                logger.warning("El monitoreo no está en ejecución")
                return False
            
            # Remover el job de monitoreo
            try:
                self.scheduler.remove_job('monitoring_job')
            except Exception:
                pass
            
            # Actualizar sesión actual como completada
            if self.current_session_id:
                db = SessionLocal()
                session = db.query(MonitoringSession).filter(
                    MonitoringSession.id == self.current_session_id
                ).first()
                if session:
                    session.status = "completed"
                    db.commit()
                db.close()
            
            self.is_running = False
            logger.info("⏹️ Monitoreo híbrido detenido")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo monitoreo: {e}")
            return False

# Crear instancia global del scheduler híbrido
monitoring_scheduler = HybridMonitoringScheduler()

# Alias para compatibilidad
MonitoringScheduler = HybridMonitoringScheduler
