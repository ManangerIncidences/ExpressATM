from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, date
import logging
import time
import psutil
import threading
from .scraper import LotteryMonitorScraper
from .alerts import AlertSystem
from .database import SessionLocal
from .models import MonitoringSession, SystemLog
from .intelligence import intelligence_engine, SystemMetrics, PredictionResult
from backend.config import Config

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.current_session_id = None
        self.scraper = None
        self.intelligence_enabled = True
        self.iteration_start_time = None
        # Estado de progreso de la iteración actual
        self._progress_lock = threading.Lock()
        self._progress = {"active": False, "steps": []}

    # =============================
    # Gestión de progreso
    # =============================
    def _now_iso(self):
        return datetime.utcnow().isoformat()

    def _progress_steps_template(self):
        return [
            {"key": "login", "label": "Login", "status": "pending"},
            {"key": "navigate", "label": "Navegación", "status": "pending"},
            {"key": "base_filters", "label": "Filtros base", "status": "pending"},
            {"key": "chance", "label": "CHANCE EXPRESS", "status": "pending"},
            {"key": "chance_extra", "label": "CHANCE EXTRAORDINARIO", "status": "pending"},
            {"key": "ruleta", "label": "RULETA EXPRESS", "status": "pending"},
            {"key": "data_ready", "label": "Datos listos", "status": "pending"},
            {"key": "generate_alerts", "label": "Generando alertas", "status": "pending"},
            {"key": "complete", "label": "Completado", "status": "pending"}
        ]

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
            logger.debug("[PROGRESS][start] version=1 steps=%s", [(s['key'], s['status']) for s in self._progress['steps']])

    def _update_progress_step(self, key: str, status: str = "running", message: str | None = None):
        with self._progress_lock:
            if not self._progress.get("active"):
                return
            steps = self._progress.get("steps", [])
            # Cerrar paso previo en ejecución si cambiamos a otro
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
            # Marcar un contador de versión para forzar cambio observable
            self._progress["version"] = self._progress.get("version", 0) + 1
            try:
                logger.debug("[PROGRESS][update] step=%s status=%s version=%s snapshot=%s", key, status, self._progress['version'], [(s['key'], s['status']) for s in steps])
            except Exception:
                pass

    def _finish_progress(self, success: bool):
        with self._progress_lock:
            if not self._progress.get("active"):
                return
            # Cerrar paso actual
            if self._progress.get("current"):
                for s in self._progress["steps"]:
                    if s["key"] == self._progress["current"] and s["status"] == "running":
                        s["status"] = "success" if success else "error"
                        s["finished_at"] = self._now_iso()
                        break
            # Marcar complete
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
                logger.debug("[PROGRESS][finish] success=%s version=%s steps=%s", success, self._progress['version'], [(s['key'], s['status']) for s in self._progress['steps']])
            except Exception:
                pass

    def get_progress(self) -> dict:
        with self._progress_lock:
            # Copia superficial segura
            prog = self._progress.copy()
            prog["steps"] = [s.copy() for s in prog.get("steps", [])]
            return prog
        
    def start_monitoring(self) -> bool:
        """Iniciar el monitoreo automático con inteligencia integrada"""
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
            
            # Obtener configuración adaptiva del motor de inteligencia
            adaptive_config = intelligence_engine.get_adaptive_config()
            monitoring_interval = adaptive_config.get("monitoring_interval", Config.MONITORING_INTERVAL)
            
            # Configurar tarea programada con intervalo adaptivo
            self.scheduler.add_job(
                func=self._intelligent_monitoring_iteration,
                trigger=IntervalTrigger(minutes=monitoring_interval),
                id='monitoring_job',
                name='Monitoreo de Agencias',
                replace_existing=True
            )
            
            # Ejecutar primera iteración inmediatamente
            self.scheduler.add_job(
                func=self._intelligent_monitoring_iteration,
                trigger='date',
                run_date=datetime.now(),
                id='initial_monitoring',
                name='Monitoreo Inicial'
            )
            
            self.scheduler.start()
            self.is_running = True
            
            self._log_system_event("INFO", "Monitoreo inteligente iniciado", "scheduler")
            logger.info(f"🧠 Monitoreo inteligente iniciado. Sesión ID: {self.current_session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando monitoreo: {str(e)}")
            self._log_system_event("ERROR", f"Error iniciando monitoreo: {str(e)}", "scheduler")
            return False
    
    def stop_monitoring(self) -> bool:
        """Detener el monitoreo automático"""
        try:
            if not self.is_running:
                logger.warning("El monitoreo no está en ejecución")
                return False
            
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            
            # Actualizar sesión de monitoreo
            if self.current_session_id:
                db = SessionLocal()
                session = db.query(MonitoringSession).filter(
                    MonitoringSession.id == self.current_session_id
                ).first()
                if session:
                    session.end_time = datetime.now()
                    session.status = "stopped"
                    db.commit()
                db.close()
            
            # Cerrar scraper si está activo
            if self.scraper:
                self.scraper.close()
                self.scraper = None
            
            self._log_system_event("INFO", "Monitoreo detenido", "scheduler")
            logger.info("Monitoreo detenido")
            return True
            
        except Exception as e:
            logger.error(f"Error deteniendo monitoreo: {str(e)}")
            self._log_system_event("ERROR", f"Error deteniendo monitoreo: {str(e)}", "scheduler")
            return False
    
    def update_settings(self, settings_dict: dict) -> bool:
        """Actualizar configuración de monitorización y umbrales en caliente"""
        try:
            # Actualizar intervalo de monitoreo
            interval = settings_dict.get('monitoringInterval')
            if interval:
                # Persistir en Config
                Config.MONITORING_INTERVAL = interval
                job = self.scheduler.get_job('monitoring_job')
                if job:
                    job.reschedule(trigger=IntervalTrigger(minutes=interval))
                logger.info(f"Intervalo de monitoreo actualizado a {interval} minutos")
            # Actualizar umbrales de alerta
            Config.ALERT_THRESHOLDS['sales_threshold'] = settings_dict.get('salesThreshold', Config.ALERT_THRESHOLDS['sales_threshold'])
            Config.ALERT_THRESHOLDS['balance_threshold'] = settings_dict.get('balanceThreshold', Config.ALERT_THRESHOLDS['balance_threshold'])
            Config.ALERT_THRESHOLDS['growth_variation'] = settings_dict.get('growthVariation', Config.ALERT_THRESHOLDS['growth_variation'])
            Config.ALERT_THRESHOLDS['sustained_growth'] = settings_dict.get('sustainedGrowth', Config.ALERT_THRESHOLDS['sustained_growth'])
            # Actualizar headless y flags de filtros y alertas
            Config.HEADLESS_MODE = settings_dict.get('browserHeadless', Config.HEADLESS_MODE)
            Config.FILTER_SURIEL = settings_dict.get('filterSuriel', Config.FILTER_SURIEL)
            Config.FILTER_TOTAL_GENERAL = settings_dict.get('filterTotalGeneral', Config.FILTER_TOTAL_GENERAL)
            Config.ENABLE_GROWTH_ALERTS = settings_dict.get('enableGrowthAlerts', Config.ENABLE_GROWTH_ALERTS)
            Config.ENABLE_THRESHOLD_ALERTS = settings_dict.get('enableThresholdAlerts', Config.ENABLE_THRESHOLD_ALERTS)
            return True
        except Exception as e:
            logger.error(f"Error actualizando settings: {e}")
            return False
    
    def _intelligent_monitoring_iteration(self):
        """Ejecutar iteración inteligente con predicción y auto-optimización"""
        scraper = None
        start_time = time.time()
        iteration_success = False
        records_obtained = 0
        alerts_generated = 0
        error_type = None
        
        try:
            logger.info("Iniciando iteración de monitoreo...")
            self.iteration_start_time = datetime.now()
            
            # Iniciar progreso
            self._start_progress()
            self._update_progress_step("login", "running")

            # 🧠 FASE 1: Predicción pre-iteración
            if self.intelligence_enabled:
                current_metrics = {
                    'current_hour': datetime.now().hour,
                    'day_of_week': datetime.now().weekday(),
                    'memory_usage': psutil.virtual_memory().percent,
                    'cpu_usage': psutil.cpu_percent(interval=1)
                }
                
                # Predecir riesgo de fallo
                failure_prediction = intelligence_engine.predict_failure_risk(current_metrics)
                
                if failure_prediction.probability > 0.7:
                    logger.warning(f"🚨 Alto riesgo de fallo detectado: {failure_prediction.recommendation}")
                    # Aplicar configuración defensiva
                    self._apply_defensive_config()
                
                # Detectar anomalías
                anomalies = intelligence_engine.detect_anomalies(current_metrics)
                for anomaly in anomalies:
                    logger.warning(f"⚠️ Anomalía detectada: {anomaly['description']}")
            
            # 🔧 FASE 2: Ejecución adaptiva
            # Inicializar scraper con configuración adaptiva
            scraper = LotteryMonitorScraper(progress_callback=self._update_progress_step)
            alert_system = AlertSystem()
            
            # Aplicar configuración adaptiva al scraper
            if self.intelligence_enabled:
                self._apply_adaptive_config(scraper)
            
            # Ejecutar scraping con monitoreo de rendimiento
            start_scraping = time.time()
            agencies_data = scraper.scrape_all_data()
            website_response_time = time.time() - start_scraping
            
            if agencies_data:
                iteration_success = True
                records_obtained = len(agencies_data)
                self._update_progress_step("data_ready", "success")
                self._update_progress_step("generate_alerts", "running")
                
                # Procesar datos y generar alertas
                db = SessionLocal()
                try:
                    alerts_generated_list = alert_system.process_agencies_data(agencies_data, db)
                    alerts_generated = len(alerts_generated_list)
                    
                    # Actualizar estadísticas de sesión
                    if self.current_session_id:
                        session = db.query(MonitoringSession).filter(
                            MonitoringSession.id == self.current_session_id
                        ).first()
                        if session:
                            session.total_iterations += 1
                            session.total_agencies_processed += len(agencies_data)
                            session.total_alerts_generated += len(alerts_generated_list)
                            db.commit()
                    
                    # Log resultados
                    message = f"Iteración completada: {len(agencies_data)} agencias procesadas, {len(alerts_generated_list)} alertas generadas"
                    self._log_system_event("INFO", message, "monitoring")
                    logger.info(message)
                    
                    # Log alertas generadas
                    for alert in alerts_generated_list:
                        alert_msg = f"ALERTA - {alert['type']}: {alert['agency_name']} - {alert['message']}"
                        self._log_system_event("WARNING", alert_msg, "alerts")
                        logger.warning(alert_msg)
                    self._update_progress_step("generate_alerts", "success")
                        
                finally:
                    db.close()
            
            else:
                error_type = "no_data_obtained"
                self._log_system_event("WARNING", "No se obtuvieron datos en esta iteración", "monitoring")
                logger.warning("No se obtuvieron datos en esta iteración")
                self._update_progress_step("data_ready", "error", "Sin datos")
            
            # 📊 FASE 3: Registro de métricas y aprendizaje
            if self.intelligence_enabled:
                iteration_duration = time.time() - start_time
                
                # Crear métricas del sistema
                system_metrics = SystemMetrics(
                    timestamp=self.iteration_start_time,
                    iteration_success=iteration_success,
                    iteration_duration=iteration_duration,
                    records_obtained=records_obtained,
                    alerts_generated=alerts_generated,
                    error_type=error_type,
                    website_response_time=website_response_time,
                    memory_usage=psutil.virtual_memory().percent,
                    cpu_usage=psutil.cpu_percent()
                )
                
                # Registrar métricas para aprendizaje automático
                intelligence_engine.record_system_metrics(system_metrics)
                
                # 🎯 FASE 4: Auto-optimización
                if iteration_success:
                    self._apply_post_iteration_optimizations()
            
        except Exception as e:
            iteration_success = False
            error_type = type(e).__name__
            error_msg = f"Error en iteración de monitoreo: {str(e)}"
            logger.error(error_msg)
            self._log_system_event("ERROR", error_msg, "monitoring")
            # Marcar error si no se había marcado
            self._update_progress_step("complete", "error", error_msg)
            
            # 🧠 Aprendizaje de errores
            if self.intelligence_enabled:
                iteration_duration = time.time() - start_time
                system_metrics = SystemMetrics(
                    timestamp=self.iteration_start_time or datetime.now(),
                    iteration_success=False,
                    iteration_duration=iteration_duration,
                    records_obtained=0,
                    alerts_generated=0,
                    error_type=error_type,
                    website_response_time=0.0,
                    memory_usage=psutil.virtual_memory().percent,
                    cpu_usage=psutil.cpu_percent()
                )
                intelligence_engine.record_system_metrics(system_metrics)
            
            # Marcar sesión como error
            if self.current_session_id:
                try:
                    db = SessionLocal()
                    session = db.query(MonitoringSession).filter(
                        MonitoringSession.id == self.current_session_id
                    ).first()
                    if session:
                        session.status = "error"
                        session.error_message = str(e)
                        db.commit()
                    db.close()
                except Exception as db_error:
                    logger.error(f"Error actualizando sesión: {db_error}")
        
        finally:
            # Asegurar limpieza del scraper
            if scraper:
                try:
                    scraper.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Error limpiando scraper: {cleanup_error}")
            self._finish_progress(iteration_success)
    
    def _apply_defensive_config(self):
        """Aplica configuración defensiva cuando se detecta alto riesgo"""
        try:
            defensive_updates = {
                "wait_times": {
                    "page_load": 15,  # Aumentar timeouts
                    "table_load": 12,
                    "element_click": 5
                },
                "retry_counts": {
                    "login": 5,  # Más reintentos
                    "search": 7,
                    "data_extraction": 5
                }
            }
            intelligence_engine.update_adaptive_config(defensive_updates)
            logger.info("🛡️ Configuración defensiva aplicada")
        except Exception as e:
            logger.error(f"Error aplicando configuración defensiva: {e}")
    
    def _apply_adaptive_config(self, scraper):
        """Aplica configuración adaptiva al scraper"""
        try:
            adaptive_config = intelligence_engine.get_adaptive_config()
            
            # Aplicar timeouts adaptativos
            if hasattr(scraper, 'update_timeouts'):
                scraper.update_timeouts(adaptive_config["wait_times"])
            
            # Aplicar contadores de reintentos adaptativos  
            if hasattr(scraper, 'update_retry_counts'):
                scraper.update_retry_counts(adaptive_config["retry_counts"])
                
            logger.debug("⚙️ Configuración adaptiva aplicada al scraper")
        except Exception as e:
            logger.error(f"Error aplicando configuración adaptiva: {e}")
    
    def _apply_post_iteration_optimizations(self):
        """Aplica optimizaciones después de una iteración exitosa"""
        try:
            # Obtener recomendaciones de optimización
            recommendations = intelligence_engine.optimize_parameters()
            
            for rec in recommendations:
                if rec.confidence > 0.7:  # Solo aplicar recomendaciones de alta confianza
                    logger.info(f"🎯 Aplicando optimización: {rec.parameter} = {rec.recommended_value} (confianza: {rec.confidence:.2f})")
                    
                    # Aplicar optimizaciones específicas
                    if rec.parameter == "monitoring_interval":
                        self._update_monitoring_interval(rec.recommended_value)
                    elif rec.parameter == "sales_threshold":
                        self._update_sales_threshold(rec.recommended_value)
                    elif rec.parameter == "page_load_wait":
                        self._update_wait_time("page_load", rec.recommended_value)
                        
        except Exception as e:
            logger.error(f"Error aplicando optimizaciones: {e}")
    
    def _update_monitoring_interval(self, new_interval: int):
        """Actualiza el intervalo de monitoreo adaptativamente"""
        try:
            if self.is_running and abs(new_interval - Config.MONITORING_INTERVAL) > 2:
                # Solo cambiar si la diferencia es significativa
                Config.MONITORING_INTERVAL = new_interval
                
                # Reprogramar job con nuevo intervalo
                self.scheduler.reschedule_job(
                    'monitoring_job',
                    trigger=IntervalTrigger(minutes=new_interval)
                )
                logger.info(f"📅 Intervalo de monitoreo actualizado a {new_interval} minutos")
        except Exception as e:
            logger.error(f"Error actualizando intervalo: {e}")
    
    def _update_sales_threshold(self, new_threshold: float):
        """Actualiza umbral de ventas adaptativamente"""
        try:
            Config.ALERT_THRESHOLDS["sales_threshold"] = new_threshold
            logger.info(f"💰 Umbral de ventas actualizado a ${new_threshold:,.2f}")
        except Exception as e:
            logger.error(f"Error actualizando umbral: {e}")
    
    def _update_wait_time(self, wait_type: str, new_time: float):
        """Actualiza tiempos de espera adaptativamente"""
        try:
            updates = {"wait_times": {wait_type: new_time}}
            intelligence_engine.update_adaptive_config(updates)
            logger.info(f"⏱️ Tiempo {wait_type} actualizado a {new_time}s")
        except Exception as e:
            logger.error(f"Error actualizando tiempo de espera: {e}")
    
    def get_intelligence_status(self) -> dict:
        """Obtener estado del sistema de inteligencia"""
        try:
            adaptive_config = intelligence_engine.get_adaptive_config()
            
            # Obtener predicción actual
            current_metrics = {
                'current_hour': datetime.now().hour,
                'day_of_week': datetime.now().weekday(),
                'memory_usage': psutil.virtual_memory().percent,
                'cpu_usage': psutil.cpu_percent(interval=0.1)
            }
            
            failure_prediction = intelligence_engine.predict_failure_risk(current_metrics)
            anomalies = intelligence_engine.detect_anomalies(current_metrics)
            optimizations = intelligence_engine.optimize_parameters()
            
            return {
                "intelligence_enabled": self.intelligence_enabled,
                "adaptive_config": adaptive_config,
                "failure_prediction": {
                    "probability": failure_prediction.probability,
                    "risk_level": failure_prediction.details.get("risk_level", "Desconocido"),
                    "recommendation": failure_prediction.recommendation
                },
                "anomalies_detected": len(anomalies),
                "optimizations_available": len([r for r in optimizations if r.confidence > 0.7]),
                "system_metrics": {
                    "memory_usage": current_metrics['memory_usage'],
                    "cpu_usage": current_metrics['cpu_usage']
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de inteligencia: {e}")
            return {"intelligence_enabled": False, "error": str(e)}
    
    def toggle_intelligence(self, enabled: bool):
        """Activar/desactivar sistema de inteligencia"""
        self.intelligence_enabled = enabled
        status = "activado" if enabled else "desactivado"
        logger.info(f"🧠 Sistema de inteligencia {status}")
        self._log_system_event("INFO", f"Sistema de inteligencia {status}", "intelligence")
    
    def execute_manual_iteration(self) -> dict:
        """Ejecutar una iteración manual de monitoreo"""
        try:
            logger.info("Ejecutando iteración manual...")
            self._start_progress()
            self._update_progress_step("login", "running")

            scraper = LotteryMonitorScraper(progress_callback=self._update_progress_step)
            alert_system = AlertSystem()
            
            # Ejecutar scraping
            agencies_data = scraper.scrape_all_data()
            
            if agencies_data:
                # Procesar datos y generar alertas
                self._update_progress_step("data_ready", "success")
                self._update_progress_step("generate_alerts", "running")
                db = SessionLocal()
                alerts_generated = alert_system.process_agencies_data(agencies_data, db)
                db.close()
                self._update_progress_step("generate_alerts", "success")
                
                result = {
                    "success": True,
                    "agencies_processed": len(agencies_data),
                    "alerts_generated": len(alerts_generated),
                    "alerts": alerts_generated,
                    "timestamp": datetime.now().isoformat()
                }
                
                message = f"Iteración manual completada: {len(agencies_data)} agencias, {len(alerts_generated)} alertas"
                self._log_system_event("INFO", message, "manual")
                
                self._finish_progress(True)
                return result
            
            else:
                self._update_progress_step("data_ready", "error", "Sin datos")
                self._finish_progress(False)
                return {
                    "success": False,
                    "error": "No se obtuvieron datos",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            error_msg = f"Error en iteración manual: {str(e)}"
            logger.error(error_msg)
            self._log_system_event("ERROR", error_msg, "manual")
            self._update_progress_step("complete", "error", error_msg)
            self._finish_progress(False)
            
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_status(self) -> dict:
        """Obtener estado actual del monitoreo con información de inteligencia"""
        status = {
            "is_running": self.is_running,
            "current_session_id": self.current_session_id,
            "monitoring_interval": Config.MONITORING_INTERVAL,
            "intelligence_enabled": self.intelligence_enabled
        }
        
        if self.current_session_id:
            db = SessionLocal()
            session = db.query(MonitoringSession).filter(
                MonitoringSession.id == self.current_session_id
            ).first()
            if session:
                status.update({
                    "session_start": session.start_time.isoformat(),
                    "total_iterations": session.total_iterations,
                    "total_agencies_processed": session.total_agencies_processed,
                    "total_alerts_generated": session.total_alerts_generated,
                    "session_status": session.status
                })
            db.close()
        
        # Agregar estado de inteligencia si está habilitado
        if self.intelligence_enabled:
            intelligence_status = self.get_intelligence_status()
            status["intelligence"] = intelligence_status
        # Agregar tiempo de próxima ejecución del job de monitoreo
        try:
            job = self.scheduler.get_job('monitoring_job')
            if job and job.next_run_time:
                status['next_run_time'] = job.next_run_time.isoformat()
        except Exception:
            pass
        
        return status
    
    def _log_system_event(self, level: str, message: str, module: str):
        """Registrar evento en el sistema de logs"""
        try:
            db = SessionLocal()
            log_entry = SystemLog(
                level=level,
                message=message,
                module=module,
                session_id=self.current_session_id
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error registrando log: {str(e)}")
    
    def update_settings(self, settings: dict):
        """Actualizar configuración del sistema"""
        try:
            # Actualizar intervalo de monitoreo
            if "monitoringInterval" in settings:
                Config.MONITORING_INTERVAL = settings["monitoringInterval"]
                logger.info(f"Intervalo de monitoreo actualizado: {settings['monitoringInterval']} minutos")
            
            # Actualizar modo headless
            if "browserHeadless" in settings:
                Config.HEADLESS_MODE = settings["browserHeadless"]
                logger.info(f"Modo headless actualizado: {settings['browserHeadless']}")
            
            # Actualizar umbrales de alertas
            if "salesThreshold" in settings:
                Config.ALERT_THRESHOLDS["sales_threshold"] = settings["salesThreshold"]
            
            if "balanceThreshold" in settings:
                Config.ALERT_THRESHOLDS["balance_threshold"] = settings["balanceThreshold"]
            
            if "growthVariation" in settings:
                Config.ALERT_THRESHOLDS["growth_variation"] = settings["growthVariation"]
            
            if "sustainedGrowth" in settings:
                Config.ALERT_THRESHOLDS["sustained_growth"] = settings["sustainedGrowth"]
            
            logger.info("Configuración actualizada exitosamente")
            
            # Si el monitoreo está activo, reiniciar con nueva configuración
            if self.is_running and "monitoringInterval" in settings:
                logger.info("Reiniciando monitoreo con nueva configuración...")
                self.stop_monitoring()
                self.start_monitoring()
            
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando configuración: {e}")
            return False
    
    def get_settings(self):
        """Obtener configuración actual del sistema"""
        try:
            return {
                "monitoringInterval": Config.MONITORING_INTERVAL,
                "browserHeadless": Config.HEADLESS_MODE,
                "filterSuriel": getattr(Config, 'FILTER_SURIEL', True),
                "filterTotalGeneral": getattr(Config, 'FILTER_TOTAL_GENERAL', True),
                "enableGrowthAlerts": getattr(Config, 'ENABLE_GROWTH_ALERTS', True),
                "enableThresholdAlerts": getattr(Config, 'ENABLE_THRESHOLD_ALERTS', True),
                "salesThreshold": Config.ALERT_THRESHOLDS.get("sales_threshold"),
                "balanceThreshold": Config.ALERT_THRESHOLDS.get("balance_threshold"),
                "growthVariation": Config.ALERT_THRESHOLDS.get("growth_variation"),
                "sustainedGrowth": Config.ALERT_THRESHOLDS.get("sustained_growth")
            }
        except Exception as e:
            logger.error(f"Error obteniendo configuración: {e}")
            return {}

# Instancia global del scheduler
monitoring_scheduler = MonitoringScheduler() 