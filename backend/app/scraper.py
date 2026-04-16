from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, WebDriverException
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.config import Config, SiteConfig, SITE_EXPRESS
from backend.driver_manager import get_chromedriver_path, get_chrome_binary_path, get_chrome_and_driver_info
import logging
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from configuracion_especifica_chance import apply_lottery_specific_config, monitor_lottery_performance, chance_optimizer

# 🧠 Importar sistema de inteligencia DOM
from .web_driver_observer import WebDriverObserver
from .dom_intelligence import dom_intelligence
logger = logging.getLogger(__name__)

# Agregar importación del sistema de visión
try:
    from .vision_learning_engine import vision_learner
    VISION_SYSTEM_AVAILABLE = True
    logger.info("Sistema de vision + ML disponible")
except ImportError as e:
    VISION_SYSTEM_AVAILABLE = False
    logger.warning(f"Sistema de vision no disponible: {e}")
except Exception as e:
    VISION_SYSTEM_AVAILABLE = False
    logger.warning(f"Error inicializando sistema de vision: {e}")

class LotteryMonitorScraper:
    def __init__(self, progress_callback=None, site_config: SiteConfig = None):
        """Inicializar scraper de monitoreo

        progress_callback: callable(key, status, message?) para reportar progreso de pasos clave.
        site_config: SiteConfig con credenciales y lista de loterías. Si None, usa Config.* (legacy express).
        """
        self.driver = None
        self.session_start_time = None
        self.agencies_data = []
        self._progress_cb = progress_callback or (lambda *a, **k: None)
        
        # Configuración del sitio
        self.site_config = site_config
        if site_config:
            self._login_url = site_config.login_url
            self._username = site_config.username
            self._password = site_config.password
            self._site_lotteries = site_config.lotteries
            self._site_id = site_config.site_id
        else:
            self._login_url = Config.LOGIN_URL
            self._username = Config.USERNAME
            self._password = Config.PASSWORD
            self._site_lotteries = SITE_EXPRESS.lotteries
            self._site_id = "express"
        
        # ⚡ Configuración de reintentos y timeout
        self.max_retries = 3
        self.session_timeout = 3600  # 1 hora
        self.last_activity = None
        
        # Configuracion de navegacion
        self.lotteries = [
            {"name": "CHANCE EXPRESS", "url": "https://www.chanceexpress.com.co/gana-millones-todos-los-dias"},
            {"name": "RULETA EXPRESS", "url": "https://ruletaexpress.com/juegos/"}
        ]
        
        # Sistema de vision + ML disponible
        if VISION_SYSTEM_AVAILABLE:
            logger.info("Sistema de vision + ML disponible")
            self.vision_engine = vision_learner
        else:
            logger.warning("Sistema de vision no disponible")
            self.vision_engine = None
    
    def setup_driver(self):
        """Configurar el driver de Chrome con configuración optimizada para velocidad y pantalla"""
        try:
            chrome_options = Options()
            
            # CONFIGURACIÓN MÍNIMA Y RÁPIDA (inspirada en script que funciona rápido)
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-client-side-phishing-detection")
            chrome_options.add_argument("--disable-hang-monitor")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--metrics-recording-only")
            chrome_options.add_argument("--password-store=basic")
            chrome_options.add_argument("--use-mock-keychain")
            
            # CACHE: perfil temporal único por sesión (evita conflictos de lock)
            import tempfile
            import shutil
            self._profile_dir = tempfile.mkdtemp(prefix=f"expressatm_{self._site_id}_")
            chrome_options.add_argument(f"--user-data-dir={self._profile_dir}")
            chrome_options.add_argument("--disk-cache-size=52428800")
            
            # CONFIGURACIÓN DE PANTALLA PARA MÚLTIPLES MONITORES
            chrome_options.add_argument("--window-size=1920,1080")  # Tamaño estándar
            chrome_options.add_argument("--window-position=0,0")     # Posición en monitor principal
            chrome_options.add_argument("--start-maximized")         # Maximizar en monitor actual
            
            # Solo las opciones esenciales para estabilidad
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")
            
            # Configurar headless si es necesario
            if getattr(Config, 'HEADLESS_MODE', False):
                # Headless moderno
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--window-size=1920,1080")
            
            # Intentar fijar el binario de Chrome si está disponible (mejora portabilidad)
            try:
                chrome_binary = get_chrome_binary_path()
                if chrome_binary:
                    chrome_options.binary_location = chrome_binary
                    logger.info(f"Chrome binary: {chrome_binary}")
            except Exception as _e:
                logger.debug(f"No se pudo determinar CHROME_BINARY: {_e}")

            # Crear servicio del driver (usa variable de entorno si existe o detección automática)
            driver_binary = Config.CHROMEDRIVER_PATH or get_chromedriver_path()
            self.service = Service(driver_binary)
            
            # Crear driver con configuración mínima
            self.driver = webdriver.Chrome(service=self.service, options=chrome_options)

            # Log de diagnóstico de versiones y rutas
            try:
                caps = self.driver.capabilities or {}
                browser_ver = caps.get('browserVersion') or caps.get('version')
                cd_ver = caps.get('chrome', {}).get('chromedriverVersion') if isinstance(caps.get('chrome'), dict) else None
                diag = get_chrome_and_driver_info()
                logger.info(f"Selenium: browser={browser_ver} chromedriver={cd_ver} service={driver_binary} opts.binary={getattr(chrome_options,'binary_location',None)} diag={diag}")
            except Exception as _e:
                logger.debug(f"Diag capabilities error: {_e}")
            
            # CONFIGURACIÓN ADICIONAL DE VENTANA DESPUÉS DE CREAR EL DRIVER
            try:
                # Asegurar que la ventana esté en el monitor principal (0,0) y maximizada
                self.driver.set_window_position(0, 0)
                self.driver.maximize_window()
                logger.info("🖥️ Ventana posicionada en monitor principal y maximizada")
            except Exception as window_error:
                logger.warning(f"No se pudo ajustar posición de ventana: {window_error}")
            
            # TIMEOUTS OPTIMIZADOS (como el script rápido)
            self.driver.set_page_load_timeout(30)  # 30s en lugar de 60s
            self.driver.implicitly_wait(5)  # 5s en lugar de 10s
            
            # WebDriverWait con timeout razonable
            self.wait = WebDriverWait(self.driver, 30)  # 30s en lugar de 45s
            
            # Registrar actividad inicial
            self.last_activity = datetime.now()
            
            # Sistema de vision - Configurar driver solo si tiene el metodo
            if self.vision_engine and hasattr(self.vision_engine, 'set_current_driver'):
                try:
                    self.vision_engine.set_current_driver(self.driver)
                    logger.info("Driver registrado en sistema de vision")
                except Exception as e:
                    logger.warning(f"No se pudo registrar driver en sistema de vision: {e}")
            
            logger.info("Driver de Chrome configurado con configuración optimizada para velocidad y pantalla")
            
        except Exception as e:
            error_msg = str(e)
            # Si Chrome crasheó por profile corrupto, matar zombies y limpiar profile
            if 'DevToolsActivePort' in error_msg or 'Chrome failed to start: crashed' in error_msg:
                # Primero matar procesos Chrome zombie que bloquean el profile
                self._kill_chrome_processes()
                if hasattr(self, '_profile_dir') and self._profile_dir:
                    try:
                        import shutil
                        logger.warning(f"🧹 Limpiando profile corrupto: {self._profile_dir}")
                        shutil.rmtree(self._profile_dir, ignore_errors=True)
                        os.makedirs(self._profile_dir, exist_ok=True)
                    except Exception as cleanup_err:
                        logger.warning(f"No se pudo limpiar profile: {cleanup_err}")
            logger.error(f"Error configurando driver: {error_msg}")
            raise
    
    def is_driver_alive(self) -> bool:
        """Verificar si el driver está activo y funcional"""
        try:
            if not self.driver:
                return False
            
            # Intentar obtener el título de la página
            _ = self.driver.title
            
            # Verificar timeout de sesión
            if self.last_activity:
                time_since_activity = (datetime.now() - self.last_activity).total_seconds()
                if time_since_activity > self.session_timeout:
                    logger.warning(f"Sesión expirada ({time_since_activity:.0f}s > {self.session_timeout}s)")
                    return False
            
            return True
            
        except (WebDriverException, Exception) as e:
            logger.warning(f"Driver no está activo: {e}")
            return False
    
    def refresh_driver(self):
        """Reinicializar el driver si está desconectado"""
        try:
            logger.info("Reinicializando driver...")
            
            # Cerrar driver actual si existe
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    # quit() falló — matar a nivel OS
                    self._kill_chrome_processes()
                finally:
                    self.driver = None
            
            # Recrear driver
            self.setup_driver()
            logger.info("Driver reinicializado exitosamente")
            
        except Exception as e:
            logger.error(f"Error reinicializando driver: {e}")
            raise
    
    def execute_with_retry(self, func, *args, **kwargs):
        """Ejecutar función con reintentos automáticos en caso de fallo de conexión"""
        for attempt in range(self.max_retries):
            try:
                # Verificar si el driver está activo
                if not self.is_driver_alive():
                    logger.warning(f"Driver inactivo en intento {attempt + 1}, reinicializando...")
                    self.refresh_driver()
                
                # Actualizar actividad
                self.last_activity = datetime.now()
                
                # Ejecutar función
                result = func(*args, **kwargs)
                return result
                
            except (WebDriverException, Exception) as e:
                error_message = str(e)
                
                # Detectar errores críticos del WebDriver que no deben retry
                critical_errors = [
                    "chrome not reachable",
                    "session deleted because of page crash",
                    "unknown error: session deleted",
                    "GetHandleVerifier"  # Stack trace específico que estamos viendo
                ]
                
                is_critical = any(critical in error_message for critical in critical_errors)
                
                if is_critical:
                    logger.error(f"Error crítico detectado, no reintentando: {error_message[:200]}...")
                    # Para errores críticos, limpiar el driver sin retry
                    try:
                        self.cleanup_safe()
                    except Exception:
                        pass
                    raise e
                
                logger.warning(f"Intento {attempt + 1} falló: {error_message[:200]}...")
                
                if attempt < self.max_retries - 1:
                    # Esperar antes del siguiente intento
                    wait_time = (attempt + 1) * 2  # 2, 4, 6 segundos
                    logger.info(f"Esperando {wait_time}s antes del siguiente intento...")
                    time.sleep(wait_time)
                    
                    # Reinicializar driver solo para errores no críticos
                    try:
                        self.refresh_driver()
                    except Exception:
                        pass
                else:
                    logger.error(f"Todos los intentos fallaron para {func.__name__}")
                    raise e
    
    def wait_for_page_load(self, quick_check=False):
        """Esperar a que la página termine de cargar completamente"""
        try:
            # Actualizar actividad
            self.last_activity = datetime.now()
            
            # Si es verificación rápida, usar timeout más corto
            timeout = 5 if quick_check else 15
            wait = WebDriverWait(self.driver, timeout)
            
            # Esperar a que el estado de la página sea 'complete'
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Esperar a que no haya loaders activos (solo si no es verificación rápida)
            if not quick_check:
                try:
                    wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading, .loader, .spinner, .el-loading-mask")))
                except TimeoutException:
                    pass  # Si no hay loaders, continuar
                
        except Exception as e:
            if not quick_check:
                logger.warning(f"Error esperando carga de página: {e}")
            # En verificación rápida, no loggear errores
    
    def wait_for_element_stable(self, element):
        """Esperar a que un elemento esté estable (no se mueva)"""
        try:
            last_position = None
            stable_count = 0
            
            for _ in range(10):  # Máximo 10 intentos
                current_position = element.location
                if current_position == last_position:
                    stable_count += 1
                    if stable_count >= 3:  # 3 posiciones iguales consecutivas
                        break
                else:
                    stable_count = 0
                last_position = current_position
                time.sleep(0.1)
                
        except Exception:
            pass  # Si hay error, continuar
    
    def safe_click(self, element):
        """Hacer clic de forma segura en un elemento"""
        try:
            # Actualizar actividad
            self.last_activity = datetime.now()
            
            # Scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            
            # Esperar a que sea clickeable
            self.wait.until(EC.element_to_be_clickable(element))
            
            # Esperar a que esté estable
            self.wait_for_element_stable(element)
            
            # Intentar clic normal
            try:
                element.click()
                return True
            except ElementClickInterceptedException:
                # Si está interceptado, usar JavaScript
                self.driver.execute_script("arguments[0].click();", element)
                return True
                
        except Exception as e:
            logger.error(f"Error haciendo clic: {e}")
            return False
    
    def wait_for_dropdown_options(self, dropdown_selector):
        """Esperar a que aparezcan las opciones del dropdown con detección rápida"""
        try:
            # Usar timeout más corto para detección rápida
            quick_wait = WebDriverWait(self.driver, 3)
            
            # Esperar a que aparezca la lista de opciones
            quick_wait.until(EC.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'el-select-dropdown__list')]")))
            
            # Esperar brevemente a que haya opciones con texto
            quick_wait.until(lambda driver: len([
                opt for opt in driver.find_elements(By.XPATH, "//li[contains(@class, 'el-select-dropdown__item')]")
                if opt.text.strip()
            ]) > 0)
            
            return True
        except TimeoutException:
            # Intentar una segunda vez con timeout estándar
            try:
                self.wait.until(EC.presence_of_element_located((By.XPATH, "//ul[contains(@class, 'el-select-dropdown__list')]")))
                return True
            except TimeoutException:
                logger.warning("Timeout esperando opciones del dropdown")
                return False
    
    def wait_for_table_load(self):
        """Esperar a que la tabla termine de cargar completamente"""
        try:
            logger.info("Esperando a que la tabla termine de cargar...")
            
            # 1. Esperar a que aparezca la tabla
            table = self.wait.until(EC.presence_of_element_located((By.XPATH, "//table | //div[contains(@class, 'table')] | //div[contains(@class, 'el-table')]")))
            logger.info("Tabla encontrada, esperando contenido...")
            
            # 2. Esperar a que desaparezcan los loaders
            try:
                self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".el-loading-mask, .loading, .spinner, svg.circular")))
                logger.info("Loaders desaparecidos")
            except TimeoutException:
                logger.info("No se encontraron loaders o ya desaparecieron")
            
            # 3. Esperar a que haya filas con datos
            try:
                self.wait.until(lambda driver: len(driver.find_elements(By.XPATH, "//tbody//tr[td[text()]]")) > 0)
                logger.info("Filas con datos encontradas")
            except TimeoutException:
                logger.info("Timeout esperando filas con datos, verificando si hay mensaje de 'sin datos'")
                
                # Verificar si hay mensaje de "sin datos"
                try:
                    no_data = self.driver.find_element(By.XPATH, "//*[contains(text(), 'No hay datos') or contains(text(), 'Sin resultados') or contains(text(), 'No se encontraron')]")
                    logger.info("Mensaje de 'sin datos' encontrado")
                    return True
                except NoSuchElementException:
                    pass
            
            # 4. Esperar un poco más para asegurar estabilidad
            time.sleep(2)
            
            # 5. Verificar que la tabla esté estable (no cambiando)
            row_count = len(self.driver.find_elements(By.XPATH, "//tbody//tr"))
            time.sleep(1)
            new_row_count = len(self.driver.find_elements(By.XPATH, "//tbody//tr"))
            
            if row_count == new_row_count:
                logger.info(f"Tabla estable con {row_count} filas")
                return True
            else:
                logger.info("Tabla aún cargando, esperando más...")
                time.sleep(3)
                return True
                
        except TimeoutException:
            logger.warning("Timeout esperando carga de tabla")
            return False
        except Exception as e:
            logger.error(f"Error esperando carga de tabla: {e}")
            return False
    
    def login(self) -> bool:
        """Realizar login en el sitio web con estabilidad mejorada para ejecuciones automáticas"""
        try:
            logger.info("Iniciando proceso de login...")
            try:
                self._progress_cb("login", "running")
            except Exception:
                pass
            self.driver.get(self._login_url)
            
            # ESPERA ADICIONAL para asegurar carga completa de la página
            time.sleep(3)  # Pausa crítica para ejecuciones automáticas
            
            # Esperar a que desaparezcan posibles overlays o loaders
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading, .overlay, .modal-backdrop"))
                )
            except TimeoutException:
                pass  # No hay overlays, continuar
            
            # Login con verificación de interceptación
            try:
                # Campo usuario
                user_field = self.wait.until(EC.element_to_be_clickable((By.ID, "txtUser")))
                user_field.clear()
                user_field.send_keys(self._username)
                logger.info("✓ Usuario ingresado")
                
                # Campo contraseña  
                pwd_field = self.wait.until(EC.element_to_be_clickable((By.ID, "txtPwd")))
                pwd_field.clear()
                pwd_field.send_keys(self._password)
                logger.info("✓ Contraseña ingresada")
                
                # Botón login con manejo de interceptación
                login_button = self.wait.until(EC.element_to_be_clickable((By.ID, "icmdLogin")))
                
                # Intentar click normal primero
                try:
                    login_button.click()
                    logger.info("✓ Click normal en botón login")
                except Exception as click_error:
                    logger.warning(f"Click normal falló: {click_error}")
                    # Fallback: JavaScript click
                    try:
                        self.driver.execute_script("arguments[0].click();", login_button)
                        logger.info("✓ Click JavaScript en botón login")
                    except Exception as js_error:
                        logger.error(f"Ambos clicks fallaron: {js_error}")
                        return False
                
            except Exception as login_error:
                logger.error(f"Error en campos de login: {login_error}")
                return False
            
            # Verificar login exitoso con timeout extendido para ejecuciones automáticas
            try:
                # Esperar más tiempo para carga del menú en ejecuciones automáticas
                extended_wait = WebDriverWait(self.driver, 45)  # 45 segundos vs 30 normal
                extended_wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#js-primary-nav")))
                logger.info("Login exitoso - Menú lateral cargado")
                try:
                    self._progress_cb("login", "success")
                except Exception:
                    pass
                
                # Pausa adicional para estabilización en ejecuciones automáticas
                time.sleep(2)
                return True
                
            except TimeoutException:
                logger.error("Login falló - no se encontró el menú lateral después de 45s")
                try:
                    self._progress_cb("login", "error", "timeout")
                except Exception:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"Error durante login: {str(e)}")
            try:
                self._progress_cb("login", "error", str(e)[:120])
            except Exception:
                pass
            return False
    
    # MÉTODOS OBSOLETOS ELIMINADOS: debug_menu_structure(), expand_monitoring_menu(), 
    # navigate_to_monitor_robust(), verify_menu_expanded(), robust_click()
    # Estos métodos causaban lentitud innecesaria en la navegación
    
    # SECCIÓN DE NAVEGACIÓN ULTRA-OPTIMIZADA
    # Métodos obsoletos eliminados para máxima velocidad
    
    def navigate_to_monitor(self) -> bool:
        """Navegar al Monitor de Ventas - VERSIÓN OPTIMIZADA SIN MÉTODOS OBSOLETOS"""
        try:
            logger.info("Navegando a Monitor de Ventas...")
            try:
                self._progress_cb("navigate", "running")
            except Exception:
                pass
            
            # Verificar que el menú está cargado
            self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "#js-primary-nav")))
            
            # NAVEGACIÓN DIRECTA: Solo lo necesario con mejor manejo de clicks
            try:
                # Scroll al top para evitar elementos superpuestos
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
                
                # Buscar directamente el botón Monitoreo (sin debug)
                monitoreo_button = self.driver.find_element(
                    By.XPATH, 
                    "//span[@class='nav-link-text'][text()='Monitoreo']/parent::a"
                )
                
                logger.info("🎯 Botón Monitoreo encontrado, expandiendo...")
                
                # Intentar click con múltiples métodos
                try:
                    # Método 1: Click normal
                    monitoreo_button.click()
                    logger.info("✅ Click normal exitoso en Monitoreo")
                except Exception as click_error:
                    logger.warning(f"Click normal falló: {click_error}")
                    try:
                        # Método 2: JavaScript click
                        self.driver.execute_script("arguments[0].click();", monitoreo_button)
                        logger.info("✅ Click JavaScript exitoso en Monitoreo")
                    except Exception as js_error:
                        logger.warning(f"Click JS falló: {js_error}")
                        # Método 3: ActionChains
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.driver).move_to_element(monitoreo_button).click().perform()
                        logger.info("✅ Click ActionChains exitoso en Monitoreo")
                
                time.sleep(1.5)  # Pausa para expansión del menú
                logger.info("✅ Menú Monitoreo expandido")
                
                # Buscar enlace Monitor de Ventas directamente
                monitor_link = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "a[href='Monitor.aspx'][title='Monitor de Ventas']"
                )
                
                logger.info("✅ Enlace Monitor de Ventas encontrado")
                
                # Click en Monitor de Ventas con el mismo manejo robusto
                try:
                    monitor_link.click()
                    logger.info("✅ Click normal exitoso en Monitor de Ventas")
                except Exception as click_error:
                    logger.warning(f"Click normal en monitor falló: {click_error}")
                    try:
                        self.driver.execute_script("arguments[0].click();", monitor_link)
                        logger.info("✅ Click JavaScript exitoso en Monitor de Ventas")
                    except Exception as js_error:
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.driver).move_to_element(monitor_link).click().perform()
                        logger.info("✅ Click ActionChains exitoso en Monitor de Ventas")
                
                # Verificar que la página cargó con timeout reducido
                logger.info("🔍 Verificando carga de página del Monitor...")
                result = self.verify_monitor_page_loaded()
                if result:
                    try: self._progress_cb("navigate", "success")
                    except Exception: pass
                return result
                
            except Exception as e:
                logger.error(f"❌ Navegación directa falló: {e}")
                # FALLBACK MÍNIMO: Intentar con selectors alternativos
                return self.navigate_fallback_minimal()
            
        except Exception as e:
            logger.error(f"❌ Error crítico en navegación: {e}")
            try:
                self._progress_cb("navigate", "error", str(e)[:120])
            except Exception:
                pass
            return False

    def navigate_fallback_minimal(self) -> bool:
        """Fallback mínimo para navegación cuando falla el método principal"""
        try:
            logger.info("🔄 Intentando navegación fallback...")
            
            # Scroll al top nuevamente
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
            # Intentar con selector CSS más general para Monitoreo
            try:
                monitoreo_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Monitoreo')]")
                if monitoreo_link.is_displayed():
                    # Intentar múltiples métodos de click
                    try:
                        monitoreo_link.click()
                        logger.info("✅ Fallback click normal exitoso")
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", monitoreo_link)
                            logger.info("✅ Fallback click JavaScript exitoso")
                        except Exception:
                            from selenium.webdriver.common.action_chains import ActionChains
                            ActionChains(self.driver).move_to_element(monitoreo_link).click().perform()
                            logger.info("✅ Fallback click ActionChains exitoso")
                    
                    time.sleep(1.5)
                    
                    # Buscar Monitor de Ventas con selector más general
                    monitor_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'Monitor.aspx')]")
                    if monitor_link.is_displayed():
                        # Aplicar el mismo manejo robusto de clicks
                        try:
                            monitor_link.click()
                            logger.info("✅ Fallback monitor click normal exitoso")
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].click();", monitor_link)
                                logger.info("✅ Fallback monitor click JavaScript exitoso")
                            except Exception:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(self.driver).move_to_element(monitor_link).click().perform()
                                logger.info("✅ Fallback monitor click ActionChains exitoso")
                        
                        return self.verify_monitor_page_loaded()
                        
            except Exception as e:
                logger.error(f"Fallback también falló: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error en fallback: {e}")
            return False

    def verify_monitor_page_loaded(self) -> bool:
        """Verificar que la página del Monitor se cargó correctamente - VERSIÓN ESTABLE"""
        try:
            logger.info("🔍 Verificando carga de página del Monitor...")
            
            # Timeout reducido para verificación rápida
            short_wait = WebDriverWait(self.driver, 8)  # 8 segundos máximo
            
            try:
                # Buscar el dropdown de lotería que confirma que estamos en la página correcta
                dropdown_element = short_wait.until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_ddlLottery"))
                )
                logger.info("✅ Página de Monitor cargada correctamente")
                return True
                
            except TimeoutException:
                logger.warning("⏱️ Timeout esperando elementos, verificando URL...")
                # Verificar URL como fallback rápido
                current_url = self.driver.current_url
                if "Monitor.aspx" in current_url:
                    logger.info("✅ Estamos en Monitor.aspx - navegación exitosa por URL")
                    return True
                else:
                    logger.error(f"❌ No estamos en Monitor.aspx. URL: {current_url}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error verificando carga de página: {e}")
            return False
    
    def set_filters(self) -> bool:
        """Configurar los filtros usando JavaScript directo (método rápido)"""
        try:
            logger.info("Configurando filtros con JavaScript directo...")
            
            # Nuevo orden optimizado: Tipo Lotería → Filtro → Monto → Lotería (con esperas inteligentes)
            js_script = """
            // Función para configurar filtros con esperas inteligentes y nuevo orden
            function configurarFiltrosInteligente() {
                try {
                    console.log('🚀 Iniciando configuración optimizada - Nuevo orden');
                    
                    // 1. Configurar Tipo Lotería: No tradicionales
                    var tipoLoteria = document.querySelector('#ctl00_ContentPlaceHolder1_lblTipoLot');
                    if (tipoLoteria) {
                        var selectWrapper = tipoLoteria.nextElementSibling.querySelector('.el-select__wrapper');
                        if (selectWrapper) {
                            selectWrapper.click();
                            
                            // Espera inteligente para opciones (optimizada)
                            esperarYConfigurar(function() {
                                var opciones = document.querySelectorAll('.el-select-dropdown:not([aria-hidden="true"]) li.el-select-dropdown__item');
                                return seleccionarOpcionRapida(opciones, 'Loterias No Tradicionales', function() {
                                    console.log('✅ 1. Tipo Lotería: No tradicionales');
                                    // 2. Configurar Filtro SEGUNDO (nuevo orden)
                                    setTimeout(configurarFiltro, 200);
                                });
                            }, 100, 5);
                        }
                    }
                } catch(e) {
                    console.error('❌ Error configurando Tipo Lotería:', e);
                }
            }
            
            function configurarFiltro() {
                try {
                    var spans = document.querySelectorAll('span');
                    var filtroSpan = null;
                    
                    for (var i = 0; i < spans.length; i++) {
                        if (spans[i].textContent.trim() === 'Filtro:') {
                            filtroSpan = spans[i];
                            break;
                        }
                    }
                    
                    if (filtroSpan) {
                        var parent = filtroSpan.closest('.el-form-item');
                        if (parent) {
                            var selectWrapper = parent.querySelector('.el-select__wrapper');
                            if (selectWrapper) {
                                selectWrapper.click();
                                
                                // Espera inteligente para opciones de filtro (OPTIMIZADA)
                                esperarYConfigurar(function() {
                                    var opciones = document.querySelectorAll('.el-select-dropdown:not([aria-hidden="true"]) li.el-select-dropdown__item');
                                    return seleccionarOpcionRapida(opciones, 'Ventas Mayor o Igual a', function() {
                                        console.log('✅ 2. Filtro: Ventas Mayor o Igual a');
                                        // 3. Configurar Monto TERCERO
                                        setTimeout(configurarMonto, 80);
                                    });
                                }, 60, 5);
                            }
                        }
                    }
                } catch(e) {
                    console.error('❌ Error configurando Filtro:', e);
                }
            }
            
            function configurarMonto() {
                try {
                    var spans = document.querySelectorAll('span');
                    var montoSpan = null;
                    
                    for (var i = 0; i < spans.length; i++) {
                        if (spans[i].textContent.trim() === 'Monto:') {
                            montoSpan = spans[i];
                            break;
                        }
                    }
                    
                    if (montoSpan) {
                        var parent = montoSpan.closest('.el-form-item');
                        if (parent) {
                            var input = parent.querySelector('input[type="text"]');
                            if (input) {
                                input.value = '10000';
                                input.dispatchEvent(new Event('input', {bubbles: true}));
                                input.dispatchEvent(new Event('change', {bubbles: true}));
                                console.log('✅ 3. Monto: 10000');
                                
                                // 4. Configurar Lotería CUARTO (nuevo orden)
                                setTimeout(configurarLoteria, 50);
                            }
                        }
                    }
                } catch(e) {
                    console.error('❌ Error configurando Monto:', e);
                }
            }
            
            function configurarLoteria() {
                try {
                    console.log('🎯 Configurando Lotería (paso final)...');
                    var spans = document.querySelectorAll('span');
                    var loteriaSpan = null;
                    
                    // Buscar específicamente "Lotería:" (no "Tipo Lotería:")
                    for (var i = 0; i < spans.length; i++) {
                        var texto = spans[i].textContent.trim();
                        if (texto === 'Lotería:') {
                            loteriaSpan = spans[i];
                            break;
                        }
                    }
                    
                    if (loteriaSpan) {
                        var parent = loteriaSpan.closest('.el-form-item');
                        if (parent) {
                            // PRIMERO: Hacer clic en el icono de flecha (caret) para abrir el dropdown
                            var caretIcon = parent.querySelector('.el-select__caret');
                            if (caretIcon) {
                                caretIcon.click();
                                console.log('🎯 Clic en icono de flecha');
                            } else {
                                // Fallback: usar select wrapper
                                var selectWrapper = parent.querySelector('.el-select__wrapper');
                                if (selectWrapper) {
                                    selectWrapper.click();
                                    console.log('🎯 Clic en wrapper (fallback)');
                                }
                            }
                            
                            // Espera inteligente para opciones de lotería (OPTIMIZADA)
                            esperarYConfigurar(function() {
                                var opciones = document.querySelectorAll('.el-select-dropdown:not([aria-hidden="true"]) li.el-select-dropdown__item');
                                
                                // Intentar RULETA EXPRESS primero (MODO PRUEBA)
                                if (seleccionarOpcionRapida(opciones, 'RULETA EXPRESS', function() {
                                    console.log('✅ 4. Lotería: RULETA EXPRESS');
                                    window.filtrosConfigurados = true;
                                })) {
                                    return true;
                                }
                                
                                // Si no hay RULETA EXPRESS, usar "Todos"
                                return seleccionarOpcionRapida(opciones, 'Todos', function() {
                                    console.log('✅ 4. Lotería: Todos (fallback)');
                                    window.filtrosConfigurados = true;
                                });
                            }, 60, 5);
                        }
                    } else {
                        console.log('ℹ️ Campo Lotería no encontrado, marcando como completado');
                        window.filtrosConfigurados = true;
                    }
                } catch(e) {
                    console.error('❌ Error configurando Lotería:', e);
                    window.filtrosConfigurados = true; // Completar aunque haya error
                }
            }
            
            // Función de espera inteligente optimizada para navegación rápida de opciones
            function esperarYConfigurar(callback, intervalo, maxIntentos) {
                var intentos = 0;
                
                function intentar() {
                    if (intentos >= maxIntentos) {
                        console.warn('⚠️ Máximo de intentos alcanzado');
                        return;
                    }
                    
                    try {
                        if (callback()) {
                            return; // Éxito, salir
                        }
                    } catch(e) {
                        console.warn('⚠️ Error en intento:', e);
                    }
                    
                    intentos++;
                    setTimeout(intentar, intervalo);
                }
                
                // Primer intento inmediato (las opciones aparecen al instante)
                setTimeout(intentar, 50);
            }
            
            // Función optimizada para selección rápida de opciones
            function seleccionarOpcionRapida(opciones, textoObjetivo, callback) {
                console.log('🔍 Buscando opción:', textoObjetivo);
                console.log('📋 Opciones disponibles:', opciones.length);
                
                // Búsqueda directa e inmediata
                for (var i = 0; i < opciones.length; i++) {
                    var texto = opciones[i].textContent.trim();
                    console.log('   Opción ' + i + ':', texto);
                    
                    if (texto.includes(textoObjetivo) || texto === textoObjetivo) {
                        console.log('✅ Opción encontrada, haciendo clic inmediato');
                        opciones[i].click();
                        if (callback) callback();
                        return true;
                    }
                }
                
                console.log('❌ Opción no encontrada');
                return false;
            }
            
            // Iniciar configuración con nuevo orden optimizado
            configurarFiltrosInteligente();
            """
            
            # Ejecutar JavaScript
            self.driver.execute_script(js_script)
            
            # Espera inteligente reducida con nuevo orden optimizado
            time.sleep(1.5)  # Reducido significativamente de 3 a 1.5 segundos
            
            # Verificar si se configuró correctamente
            try:
                result = self.driver.execute_script("return window.filtrosConfigurados || false;")
                if result:
                    logger.info("✅ Filtros configurados con JavaScript directo")
                    return True
                else:
                    logger.warning("JavaScript no confirmó la configuración, intentando método fallback")
                    # Fallback al método anterior si JavaScript falla
                    return self.set_filters_fallback()
            except Exception:
                logger.warning("No se pudo verificar resultado JavaScript")
                return self.set_filters_fallback()
                
        except Exception as e:
            logger.error(f"Error configurando filtros: {str(e)}")
            return False
    
    def set_filters_fallback(self) -> bool:
        """Método fallback para configurar filtros usando Selenium directo (optimizado)"""
        try:
            logger.info("🔄 Usando método fallback con NUEVO ORDEN optimizado...")
            
            # 1. Configurar Tipo Lotería: No tradicionales
            try:
                tipo_loteria_label = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_lblTipoLot"))
                )
                
                # Buscar el dropdown asociado
                parent = tipo_loteria_label.find_element(By.XPATH, "..")
                select_wrapper = parent.find_element(By.CSS_SELECTOR, ".el-select__wrapper")
                select_wrapper.click()
                
                # Espera inteligente reducida para navegación rápida
                time.sleep(0.05)  # Reducido drásticamente de 0.2s
                
                opciones = WebDriverWait(self.driver, 2).until(  # Reducido de 3s
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".el-select-dropdown:not([aria-hidden='true']) li.el-select-dropdown__item"))
                )
                
                # Navegación rápida de opciones
                for opcion in opciones:
                    if "Loterias No Tradicionales" in opcion.text:
                        opcion.click()
                        logger.info("✅ 1. Tipo Lotería: No tradicionales")
                        break;
                        
            except Exception as e:
                logger.error(f"Error configurando Tipo Lotería: {str(e)}")
                return False
            
            # Espera inteligente antes de configurar filtro
            time.sleep(0.4)  # Reducido significativamente
            
            # 2. Configurar Filtro: Ventas Mayor o Igual a (SEGUNDO en nuevo orden)
            try:
                spans = self.driver.find_elements(By.TAG_NAME, "span")
                filtro_span = None
                
                for span in spans:
                    if span.text.strip() == "Filtro:":
                        filtro_span = span
                        break
                
                if filtro_span:
                    # SELECTORES MEJORADOS: Buscar wrapper en múltiples niveles
                    wrapper_encontrado = False
                    niveles = [
                        filtro_span.find_element(By.XPATH, ".."),  # Parent
                        filtro_span.find_element(By.XPATH, "../.."),  # Grandparent
                        filtro_span.find_element(By.XPATH, "../../..")  # Great-grandparent
                    ]
                    
                    for nivel in niveles:
                        try:
                            wrapper = nivel.find_element(By.CSS_SELECTOR, ".el-select__wrapper")
                            wrapper.click()
                            wrapper_encontrado = True
                            break
                        except Exception:
                            continue
                    
                    if not wrapper_encontrado:
                        logger.error("No se encontró wrapper válido para Filtro")
                        raise Exception("Wrapper no encontrado")
                    
                    time.sleep(0.15)  # Espera inteligente reducida
                    
                    opciones = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".el-select-dropdown:not([aria-hidden='true']) li.el-select-dropdown__item"))
                    )
                    
                    for opcion in opciones:
                        if "Ventas Mayor o Igual a" in opcion.text:
                            opcion.click()
                            logger.info("✅ 2. Filtro: Ventas Mayor o Igual a")
                            break
                            
            except Exception as e:
                logger.error(f"Error configurando Filtro: {str(e)}")
                return False
            
            # Espera inteligente antes de monto
            time.sleep(0.1)
            
            # 3. Configurar Monto: 10000 (TERCERO en nuevo orden)
            try:
                spans = self.driver.find_elements(By.TAG_NAME, "span")
                monto_span = None
                
                for span in spans:
                    if span.text.strip() == "Monto:":
                        monto_span = span
                        break
                
                if monto_span:
                    # SELECTORES MEJORADOS: Buscar input en múltiples niveles
                    input_encontrado = False
                    niveles = [
                        monto_span.find_element(By.XPATH, ".."),  # Parent
                        monto_span.find_element(By.XPATH, "../.."),  # Grandparent
                        monto_span.find_element(By.XPATH, "../../..")  # Great-grandparent
                    ]
                    
                    for nivel in niveles:
                        try:
                            input_field = nivel.find_element(By.CSS_SELECTOR, "input[type='text']")
                            
                            # Limpiar y configurar valor
                            input_field.clear()
                            input_field.send_keys("10000")
                            logger.info("✅ 3. Monto: 10000")
                            input_encontrado = True
                            break
                        except Exception:
                            continue
                    
                    if not input_encontrado:
                        logger.error("No se encontró input válido para Monto")
                        raise Exception("Input no encontrado")
                    
            except Exception as e:
                logger.error(f"Error configurando Monto: {str(e)}")
                return False
            
            # Espera inteligente antes de lotería
            time.sleep(0.1)
            
            # 4. Configurar Lotería: RULETA EXPRESS (CUARTO en nuevo orden)
            try:
                # Buscar campo "Lotería:" específicamente
                spans = self.driver.find_elements(By.TAG_NAME, "span")
                loteria_span = None
                
                for span in spans:
                    if span.text.strip() == "Lotería:":
                        loteria_span = span
                        break
                
                if loteria_span:
                    # SELECTORES MEJORADOS: Buscar wrapper en múltiples niveles
                    wrapper_encontrado = False
                    niveles = [
                        loteria_span.find_element(By.XPATH, ".."),  # Parent
                        loteria_span.find_element(By.XPATH, "../.."),  # Grandparent
                        loteria_span.find_element(By.XPATH, "../../..")  # Great-grandparent
                    ]
                    
                    for nivel in niveles:
                        try:
                            # Buscar wrapper Element UI
                            wrapper = nivel.find_element(By.CSS_SELECTOR, ".el-select__wrapper")
                            
                            # PRIMERO: Intentar hacer clic en el icono de flecha (caret)
                            try:
                                caret_icon = wrapper.find_element(By.CSS_SELECTOR, ".el-select__caret")
                                caret_icon.click()
                                logger.info("🎯 Clic en icono de flecha de Lotería")
                                wrapper_encontrado = True
                                break
                            except Exception:
                                # Fallback: usar select wrapper
                                wrapper.click()
                                logger.info("🎯 Clic en select wrapper de Lotería (fallback)")
                                wrapper_encontrado = True
                                break
                        except Exception:
                            continue
                    
                    if not wrapper_encontrado:
                        logger.error("No se encontró wrapper válido para Lotería")
                        raise Exception("Wrapper no encontrado")
                    
                    # Espera inteligente para opciones
                    time.sleep(0.2)  # Espera inteligente reducida
                    
                    opciones = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".el-select-dropdown:not([aria-hidden='true']) li.el-select-dropdown__item"))
                    )
                    
                    # Buscar RULETA EXPRESS (MODO PRUEBA)
                    for opcion in opciones:
                        if opcion.text.strip() == "RULETA EXPRESS":
                            opcion.click()
                            logger.info("✅ 4. Lotería: RULETA EXPRESS")
                            break
                    else:
                        # Si no hay RULETA EXPRESS, usar "Todos"
                        for opcion in opciones:
                            if opcion.text.strip() == "Todos":
                                opcion.click()
                                logger.info("✅ 4. Lotería: Todos (fallback)")
                                break
                else:
                    logger.info("ℹ️ Campo Lotería no encontrado, continuando...")
                    
            except Exception as e:
                logger.warning(f"Error configurando Lotería: {str(e)}")
                # No fallar aquí, la lotería es opcional
            
            logger.info("✅ Filtros configurados con NUEVO ORDEN optimizado (fallback)")
            return True
            
        except Exception as e:
            logger.error(f"Error en método fallback: {str(e)}")
            return False
    
    def execute_search(self) -> bool:
        """Ejecutar la búsqueda después de configurar filtros (optimizado para evitar doble clic)"""
        try:
            logger.info("Ejecutando búsqueda...")
            
            # Buscar el botón de búsqueda con timeout reducido
            search_button = None
            selectors = [
                "//a[contains(@class, 'btn-primary') and contains(text(), 'Buscar')]",
                "//button[contains(@class, 'btn-primary') and contains(text(), 'Buscar')]",
                "//input[@type='submit' and @value='Buscar']",
                "//a[contains(@class, 'btn') and contains(text(), 'Buscar')]"
            ]
            
            quick_wait = WebDriverWait(self.driver, 10)
            for selector in selectors:
                try:
                    search_button = quick_wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    logger.info(f"Botón encontrado con selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not search_button:
                logger.error("No se encontró el botón de búsqueda")
                return False
            
            # Verificar que el botón no esté ya presionado/deshabilitado
            if search_button.get_attribute("disabled") or "disabled" in search_button.get_attribute("class"):
                logger.warning("El botón de búsqueda está deshabilitado, esperando...")
                time.sleep(2)
            
            # Hacer clic único y controlado
            logger.info("Haciendo clic en botón de búsqueda...")
            try:
                # Scroll al botón
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
                
                # Clic directo con JavaScript para evitar interceptación
                self.driver.execute_script("arguments[0].click();", search_button)
                logger.info("✓ Clic ejecutado en botón de búsqueda")
                
                # Esperar brevemente para verificar que se inició la búsqueda
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error con JavaScript, intentando clic normal: {e}")
                search_button.click()
            
            # Esperar a que la tabla termine de cargar con timeout optimizado
            logger.info("Esperando resultados de búsqueda...")
            if not self.wait_for_table_load_optimized():
                logger.warning("Timeout esperando carga de tabla, pero continuando...")
            
            logger.info("Búsqueda ejecutada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando búsqueda: {str(e)}")
            
            # Tomar captura de pantalla para debug
            try:
                self.driver.save_screenshot("error_busqueda.png")
                logger.info("Captura de pantalla guardada: error_busqueda.png")
            except Exception:
                pass
                
            return False
    
    def wait_for_table_load_optimized(self):
        """Versión optimizada de espera de tabla con detección más rápida"""
        try:
            logger.info("Esperando carga de tabla (optimizado)...")
            
            # 1. Esperar a que aparezca la tabla con timeout corto
            quick_wait = WebDriverWait(self.driver, 15)
            table = quick_wait.until(EC.presence_of_element_located((By.XPATH, "//table | //div[contains(@class, 'table')] | //div[contains(@class, 'el-table')]")))
            logger.info("Tabla encontrada")
            
            # 2. Esperar a que desaparezcan los loaders (timeout corto)
            try:
                WebDriverWait(self.driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".el-loading-mask, .loading, .spinner, svg.circular")))
                logger.info("Loaders desaparecidos")
            except TimeoutException:
                logger.info("No se encontraron loaders")
            
            # 3. Esperar a que haya filas con datos (detección rápida)
            try:
                WebDriverWait(self.driver, 10).until(lambda driver: len(driver.find_elements(By.XPATH, "//tbody//tr[td[text()]]")) > 0)
                logger.info("Filas con datos encontradas")
            except TimeoutException:
                logger.info("Timeout esperando filas, verificando si hay mensaje de 'sin datos'")
                
                # Verificar mensaje de "sin datos"
                try:
                    no_data = self.driver.find_element(By.XPATH, "//*[contains(text(), 'No hay datos') or contains(text(), 'Sin resultados') or contains(text(), 'No se encontraron')]")
                    logger.info("Mensaje de 'sin datos' encontrado")
                    return True
                except NoSuchElementException:
                    pass
            
            # 4. Verificación rápida de estabilidad (solo 1 segundo)
            row_count = len(self.driver.find_elements(By.XPATH, "//tbody//tr"))
            time.sleep(1)
            new_row_count = len(self.driver.find_elements(By.XPATH, "//tbody//tr"))
            
            if row_count == new_row_count:
                logger.info(f"Tabla estable con {row_count} filas")
                return True
            else:
                logger.info("Tabla aún cargando, esperando 2s más...")
                time.sleep(2)
                return True
                
        except TimeoutException:
            logger.warning("Timeout esperando carga de tabla")
            return False
        except Exception as e:
            logger.error(f"Error esperando carga de tabla: {e}")
            return False
    
    def wait_for_table_load_complete(self):
        """Esperar a que la tabla cargue completamente con verificación extendida"""
        try:
            logger.info("🔄 Esperando carga completa de tabla...")
            
            # Esperar inicial
            time.sleep(3)
            
            # Verificación extendida para asegurar carga completa
            stable_count = 0
            required_stable_checks = 3  # Necesitamos 3 verificaciones estables consecutivas
            
            for attempt in range(20):  # Máximo 20 intentos (60 segundos)
                try:
                    # 1. Verificar que no hay indicadores de carga
                    loading_selectors = [
                        ".el-loading-spinner",
                        ".loading",
                        "[class*='loading']",
                        ".el-table__empty-text",
                        ".el-loading-mask",
                        "[aria-label*='loading']"
                    ]
                    
                    loading_visible = False
                    for selector in loading_selectors:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            try:
                                if elem.is_displayed() and elem.text.strip() not in ["Sin datos", "No data", ""]:
                                    loading_visible = True
                                    break
                            except Exception:
                                continue
                        if loading_visible:
                            break
                    
                    if loading_visible:
                        logger.info(f"Intento {attempt + 1}: Aún cargando...")
                        stable_count = 0
                        time.sleep(3)
                        continue
                    
                    # 2. Verificar que hay filas con datos
                    table_rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    if len(table_rows) == 0:
                        logger.info(f"Intento {attempt + 1}: Sin filas de datos")
                        stable_count = 0
                        time.sleep(3)
                        continue
                    
                    # 3. Verificar contenido de las filas
                    valid_rows = 0
                    for row in table_rows[:10]:  # Verificar las primeras 10 filas
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 3:  # Al menos 3 columnas
                                cell_texts = [cell.text.strip() for cell in cells[:3]]
                                if any(text and text != "-" and text != "..." for text in cell_texts):
                                    valid_rows += 1
                        except Exception:
                            continue
                    
                    if valid_rows == 0:
                        logger.info(f"Intento {attempt + 1}: Sin datos válidos en filas")
                        stable_count = 0
                        time.sleep(3)
                        continue
                    
                    # 4. Verificar estabilidad del número de filas
                    current_row_count = len(table_rows)
                    if hasattr(self, '_previous_row_count'):
                        if self._previous_row_count == current_row_count:
                            stable_count += 1
                            logger.info(f"Intento {attempt + 1}: Tabla estable ({stable_count}/{required_stable_checks}) - {current_row_count} filas, {valid_rows} válidas")
                        else:
                            stable_count = 0
                            logger.info(f"Intento {attempt + 1}: Tabla cambiando - {current_row_count} filas, {valid_rows} válidas")
                    else:
                        stable_count = 1
                        logger.info(f"Intento {attempt + 1}: Primera verificación - {current_row_count} filas, {valid_rows} válidas")
                    
                    self._previous_row_count = current_row_count
                    
                    # Si hemos tenido suficientes verificaciones estables, consideramos que terminó
                    if stable_count >= required_stable_checks:
                        logger.info(f"✅ Tabla completamente cargada: {current_row_count} filas, {valid_rows} con datos válidos")
                        return True
                    
                    time.sleep(3)
                    
                except Exception as e:
                    logger.warning(f"Error en verificación completa (intento {attempt + 1}): {e}")
                    stable_count = 0
                    time.sleep(3)
                    continue
            
            logger.warning("⚠️ Timeout esperando carga completa de tabla")
            return False
            
        except Exception as e:
            logger.error(f"Error esperando carga completa de tabla: {e}")
            return False
    
    def extract_data(self) -> List[Dict[str, Any]]:
        """Extraer datos de la tabla de resultados con confirmación visual de ML"""
        try:
            logger.info("Extrayendo datos de la tabla...")
            
            # Sistema de vision - Solo si tiene el metodo necesario
            if VISION_SYSTEM_AVAILABLE and self.vision_engine and hasattr(self.vision_engine, 'visual_wait_for_table_ready'):
                logger.info("Solicitando confirmacion visual de ML para carga completa...")
                
                try:
                    # Usar parametros correctos para el sistema de vision
                    table_ready_confirmation = self.vision_engine.visual_wait_for_table_ready(
                        driver=self.driver,
                        timeout=45  # Parametro correcto
                    )
                    
                    if table_ready_confirmation:
                        logger.info("ML CONFIRMA: Tabla completamente cargada con datos reales")
                        logger.info("   El sistema visual verifico que no hay placeholders")
                    else:
                        logger.warning("ML ADVIERTE: Tabla puede no estar completamente lista")
                        logger.warning("   Sistema visual detecto posibles placeholders o carga incompleta")
                        
                        # Espera adicional y re-verificacion
                        time.sleep(5)
                        
                        # Segunda verificacion con el sistema visual
                        if hasattr(self.vision_engine, 'visual_wait_for_table_ready'):
                            second_confirmation = self.vision_engine.visual_wait_for_table_ready(
                                driver=self.driver,
                                timeout=20
                            )
                            
                            if second_confirmation:
                                logger.info("SEGUNDA VERIFICACION EXITOSA: ML confirma datos reales")
                            else:
                                logger.error("ML CONFIRMA PROBLEMA: Tabla con placeholders o incompleta")
                except Exception as vision_error:
                    logger.warning(f"Error en confirmacion ML: {vision_error}")
            else:
                # Fallback al metodo clasico si no hay sistema de vision
                logger.info("Usando metodo clasico de espera (sin ML)")
                if not self.wait_for_table_load():
                    logger.warning("Tabla no termino de cargar completamente (metodo clasico)")
            
            # Buscar la tabla con diferentes selectores
            table_selectors = [
                "//table[contains(@class, 'table')]",
                "//div[contains(@class, 'el-table')]//table",
                "//table",
                "//div[contains(@class, 'table-responsive')]//table"
            ]
            
            table = None
            for selector in table_selectors:
                try:
                    table = self.driver.find_element(By.XPATH, selector)
                    logger.info(f"📊 Tabla encontrada con selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not table:
                logger.error("❌ No se encontró la tabla de resultados")
                return []
            
            # 🔍 VALIDACIÓN ADICIONAL DE ML: Verificar que los datos no son placeholders
            if VISION_SYSTEM_AVAILABLE and self.vision_engine:
                logger.info("🔍 ML realizando validación final de contenido...")
                
                # Capturar estado visual actual para análisis
                try:
                    visual_state = self.vision_engine.capture_visual_state(self.driver)
                    
                    # Evaluar completitud de datos con ML
                    data_completeness = self.vision_engine._evaluate_data_completeness(self.driver)
                    
                    logger.info(f"📊 ML - Completitud de datos: {data_completeness:.1%}")
                    
                    if data_completeness > 0.7:  # 70% o más de completitud
                        logger.info("✅ 🎯 ML CONFIRMA: Datos con alta completitud detectados")
                    elif data_completeness > 0.3:  # 30-70% completitud
                        logger.warning("⚠️ 📊 ML ADVIERTE: Completitud media detectada")
                        logger.warning("   💡 Posibles datos parciales o en carga")
                    else:  # <30% completitud
                        logger.error("❌ 🚨 ML ALERTA: Completitud baja - Probable placeholders")
                        logger.error("   💡 Recomendación: Reintentar o verificar conectividad")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error en validación ML final: {e}")
            
            # Extraer encabezados
            headers = []
            try:
                header_elements = table.find_elements(By.XPATH, ".//thead//th | .//tr[1]//td")
                headers = [header.text.strip() for header in header_elements if header.text.strip()]
                logger.info(f"📋 Encabezados encontrados: {headers}")
            except Exception as e:
                logger.warning(f"⚠️ Error extrayendo encabezados: {e}")
                headers = ["Agencia", "Ventas", "Premios", "Premios Pagados", "Balance"]  # Headers por defecto
            
            # Extraer filas de datos
            data = []
            try:
                # Buscar filas con datos
                rows = table.find_elements(By.XPATH, ".//tbody//tr[td] | .//tr[td and position()>1]")
                logger.info(f"📊 Encontradas {len(rows)} filas de datos")
                
                # 🧠 ANÁLISIS ML DE PATRONES: Detectar placeholders típicos
                placeholder_patterns = ["$0.00", "0.00", "Total General", "Cargando...", "---", "N/A"]
                real_data_found = 0
                placeholder_data_found = 0
                
                for i, row in enumerate(rows):
                    try:
                        cells = row.find_elements(By.XPATH, ".//td")
                        if len(cells) >= 4:  # Asegurar que tiene al menos las columnas principales
                            row_data = {}
                            
                            # Mapear datos a los encabezados
                            for j, cell in enumerate(cells):
                                header = headers[j] if j < len(headers) else f"Columna_{j+1}"
                                value = cell.text.strip()
                                row_data[header] = value
                                
                                # 🔍 Detectar placeholders en el contenido
                                if any(pattern in value for pattern in placeholder_patterns):
                                    placeholder_data_found += 1
                                elif value and value not in ["0", "0.0", ""]:
                                    real_data_found += 1
                            
                            # Asegurar que tenemos los campos principales
                            if not row_data.get("Agencia"):
                                row_data["Agencia"] = cells[0].text.strip() if len(cells) > 0 else ""
                            if not row_data.get("Ventas"):
                                row_data["Ventas"] = cells[1].text.strip() if len(cells) > 1 else "0"
                            if not row_data.get("Balance"):
                                row_data["Balance"] = cells[-1].text.strip() if len(cells) > 0 else "0"
                            
                            # Limpiar valores numéricos
                            for key in ["Ventas", "Premios", "Premios Pagados", "Balance"]:
                                if key in row_data:
                                    # Remover caracteres no numéricos excepto punto y coma
                                    cleaned_value = re.sub(r'[^\d.,\-]', '', row_data[key])
                                    cleaned_value = cleaned_value.replace(',', '')
                                    try:
                                        row_data[key] = float(cleaned_value) if cleaned_value else 0.0
                                    except ValueError:
                                        row_data[key] = 0.0
                            
                            # Transformar datos al formato esperado por el sistema de alertas
                            agency_text = row_data.get("Agencia", "")
                            
                            # Extraer código de agencia (parte antes del |)
                            agency_code = ""
                            agency_name = agency_text
                            
                            if "|" in agency_text:
                                parts = agency_text.split("|", 1)
                                agency_code = parts[0].strip()
                                agency_name = parts[1].strip() if len(parts) > 1 else agency_text
                            else:
                                # Si no hay |, usar el texto completo como nombre y generar código
                                agency_code = agency_text[:10] if agency_text else "UNKNOWN"
                                agency_name = agency_text
                            
                            # Transformar al formato esperado
                            transformed_data = {
                                "agency_code": agency_code,
                                "agency_name": agency_name,
                                "sales": row_data.get("Ventas", 0.0),
                                "prizes": row_data.get("Premios", 0.0),
                                "prizes_paid": row_data.get("Premios Pagados", 0.0),
                                "balance": row_data.get("Balance", 0.0),
                                "capture_time": datetime.now()  # Usar objeto datetime en lugar de string ISO
                            }
                            
                            data.append(transformed_data)
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Error procesando fila {i+1}: {e}")
                        continue
                
                # 🧠 REPORTE FINAL DE ML: Análisis de calidad de datos
                total_data_points = real_data_found + placeholder_data_found
                if total_data_points > 0:
                    real_data_percentage = (real_data_found / total_data_points) * 100
                    
                    logger.info(f"🧠 ML - ANÁLISIS FINAL DE DATOS:")
                    logger.info(f"   📊 Datos reales detectados: {real_data_found}")
                    logger.info(f"   🔲 Placeholders detectados: {placeholder_data_found}")
                    logger.info(f"   📈 Calidad de datos: {real_data_percentage:.1f}%")
                    
                    if real_data_percentage >= 80:
                        logger.info("✅ 🎉 ML CONFIRMA: Datos de alta calidad extraídos")
                    elif real_data_percentage >= 50:
                        logger.warning("⚠️ 📊 ML ADVIERTE: Calidad media - algunos placeholders")
                    else:
                        logger.error("❌ 🚨 ML ALERTA: Calidad baja - mayoría placeholders")
                        logger.error("   💡 Esto confirma el problema original detectado")
                
            except Exception as e:
                logger.error(f"❌ Error extrayendo filas: {e}")
                return []
            
            logger.info(f"📈 Extraídos {len(data)} registros de datos")
            
            # Log de muestra de los primeros registros para debug
            if data:
                logger.info(f"📋 Muestra de datos extraídos: {data[:2]}")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo datos: {str(e)}")
            
            # Tomar captura de pantalla para debug
            try:
                self.driver.save_screenshot("error_extraccion.png")
                logger.info("📸 Captura de pantalla guardada: error_extraccion.png")
            except Exception:
                pass
                
            return []
    
    def scrape_all_data(self) -> List[Dict[str, Any]]:
        """Ejecutar el proceso completo de scraping con reintentos automáticos"""
        return self.execute_with_retry(self._scrape_all_data_internal)
    
    def _scrape_all_data_internal(self) -> List[Dict[str, Any]]:
        """Método interno para el proceso completo de scraping (reutilizando sesión).
        Itera dinámicamente sobre self._site_lotteries."""
        all_data = []
        
        try:
            n_lotteries = len(self._site_lotteries)
            lottery_names = [l["name"] for l in self._site_lotteries]
            logger.info(f"🎯 Iniciando proceso de MONITOREO [{self._site_id.upper()}] ({n_lotteries} loterías, sesión única)...")
            for i, lot in enumerate(self._site_lotteries, 1):
                logger.info(f"   📊 Lotería {i}: {lot['name']}")
            try: self._progress_cb("login","running")
            except Exception: pass
            
            # PASO 1: Login y navegación (UNA SOLA VEZ)
            if not self.execute_with_retry(self.login):
                logger.error("✗ Error en login")
                return []
            
            logger.info("✓ Login exitoso")
            try: self._progress_cb("login","success")
            except Exception: pass
            try: self._progress_cb("navigate","running")
            except Exception: pass
            
            if not self.execute_with_retry(self.navigate_to_monitor):
                logger.error("✗ Error navegando al monitor")
                return []
            
            logger.info("✓ Navegación exitosa")
            try: self._progress_cb("navigate","success")
            except Exception: pass
            try: self._progress_cb("base_filters","running")
            except Exception: pass
            
            # PASO 2: Configurar filtros base (SIN especificar lotería)
            if not self.execute_with_retry(self.set_base_filters):
                logger.error("✗ Error configurando filtros base")
                return []
            
            logger.info("✓ Filtros base configurados")
            try: self._progress_cb("base_filters","success")
            except Exception: pass
            
            # PASOS DINÁMICOS: Procesar cada lotería del site
            for lot_cfg in self._site_lotteries:
                lot_name = lot_cfg["name"]
                lot_type = lot_cfg["lottery_type"]
                step_key = lot_cfg["step_key"]
                
                logger.info(f"🔄 Procesando {lot_name}...")
                try: self._progress_cb(step_key, "running")
                except Exception: pass
                
                lot_data = self._process_lottery_in_session(lot_name)
                if lot_data:
                    for record in lot_data:
                        record['lottery_type'] = lot_type
                    all_data.extend(lot_data)
                    logger.info(f"✅ {lot_name}: {len(lot_data)} registros obtenidos")
                else:
                    logger.warning(f"⚠️ {lot_name}: No se obtuvieron datos")
                
                try: self._progress_cb(step_key, "success" if lot_data else "error", None if lot_data else "sin datos")
                except Exception: pass
            
            logger.info(f"🎉 MONITOREO [{self._site_id.upper()}] COMPLETADO:")
            try: self._progress_cb("data_ready","running")
            except Exception: pass
            for lot_cfg in self._site_lotteries:
                count = len([r for r in all_data if r.get('lottery_type') == lot_cfg["lottery_type"]])
                logger.info(f"   📊 {lot_cfg['name']}: {count} registros")
            logger.info(f"   📈 TOTAL: {len(all_data)} registros")
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error en proceso de scraping dual: {str(e)}")
            return []
        
        finally:
            # Limpieza automática del driver después de completar el scraping
            logger.info("🧹 Iniciando limpieza automática del driver...")
            try:
                # Dar tiempo al sistema de visión para procesar si es necesario
                time.sleep(3)
                
                # Verificar si el sistema de visión está activo
                vision_active = False
                if hasattr(self, 'vision_engine') and self.vision_engine:
                    try:
                        # Verificar si hay monitoreo preventivo activo
                        vision_active = getattr(self.vision_engine, 'monitoring_active', False)
                        logger.info(f"Sistema de vision activo: {vision_active}")
                    except Exception:
                        pass
                
                # Siempre cerrar el driver al terminar la iteración
                self.cleanup_safe()
                logger.info("Driver cerrado automaticamente")
            except Exception as e:
                logger.warning(f"Error en limpieza automática: {e}")
                # Forzar limpieza en caso de error
                try:
                    self.cleanup_safe()
                except Exception:
                    pass
    
    def set_base_filters(self) -> bool:
        """Configurar filtros base (Tipo Lotería, Filtro, Monto) SIN especificar lotería específica"""
        try:
            logger.info("Configurando filtros base...")
            try:
                self._progress_cb("base_filters", "running")
            except Exception:
                pass
            
            # Usar el método fallback que ya funcionaba, pero sin configurar lotería específica
            return self.set_base_filters_fallback()
                
        except Exception as e:
            logger.error(f"Error configurando filtros base: {str(e)}")
            try:
                self._progress_cb("base_filters", "error", str(e)[:120])
            except Exception:
                pass
            return False
    
    def set_base_filters_fallback(self) -> bool:
        """Método fallback para configurar filtros base usando Selenium directo"""
        try:
            logger.info("🔄 Configurando filtros base con Selenium...")
            
            # 1. Configurar Tipo Lotería: No tradicionales
            try:
                tipo_loteria_label = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_lblTipoLot"))
                )
                
                # Buscar el dropdown asociado
                parent = tipo_loteria_label.find_element(By.XPATH, "..")
                select_wrapper = parent.find_element(By.CSS_SELECTOR, ".el-select__wrapper")
                select_wrapper.click()
                
                time.sleep(0.3)
                
                opciones = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".el-select-dropdown:not([aria-hidden='true']) li.el-select-dropdown__item"))
                )
                
                for opcion in opciones:
                    if "Loterias No Tradicionales" in opcion.text:
                        opcion.click()
                        logger.info("✅ 1. Tipo Lotería: No tradicionales")
                        break
                        
            except Exception as e:
                logger.error(f"Error configurando Tipo Lotería: {str(e)}")
                return False
            
            time.sleep(0.5)
            
            # 2. Configurar Filtro: Ventas Mayor o Igual a
            try:
                spans = self.driver.find_elements(By.TAG_NAME, "span")
                filtro_span = None
                
                for span in spans:
                    if span.text.strip() == "Filtro:":
                        filtro_span = span
                        break
                
                if filtro_span:
                    # Buscar wrapper en múltiples niveles
                    wrapper_encontrado = False
                    niveles = [
                        filtro_span.find_element(By.XPATH, ".."),
                        filtro_span.find_element(By.XPATH, "../.."),
                        filtro_span.find_element(By.XPATH, "../../..")
                    ]
                    
                    for nivel in niveles:
                        try:
                            wrapper = nivel.find_element(By.CSS_SELECTOR, ".el-select__wrapper")
                            wrapper.click()
                            wrapper_encontrado = True
                            break
                        except Exception:
                            continue
                    
                    if not wrapper_encontrado:
                        logger.error("No se encontró wrapper válido para Filtro")
                        raise Exception("Wrapper no encontrado")
                    
                    time.sleep(0.3)
                    
                    opciones = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".el-select-dropdown:not([aria-hidden='true']) li.el-select-dropdown__item"))
                    )
                    
                    for opcion in opciones:
                        if "Ventas Mayor o Igual a" in opcion.text:
                            opcion.click()
                            logger.info("✅ 2. Filtro: Ventas Mayor o Igual a")
                            break
                            
            except Exception as e:
                logger.error(f"Error configurando Filtro: {str(e)}")
                return False
            
            time.sleep(0.3)
            
            # 3. Configurar Monto: 10000
            try:
                spans = self.driver.find_elements(By.TAG_NAME, "span")
                monto_span = None
                
                for span in spans:
                    if span.text.strip() == "Monto:":
                        monto_span = span
                        break
                
                if monto_span:
                    # Buscar input en múltiples niveles
                    input_encontrado = False
                    niveles = [
                        monto_span.find_element(By.XPATH, ".."),
                        monto_span.find_element(By.XPATH, "../.."),
                        monto_span.find_element(By.XPATH, "../../..")
                    ]
                    
                    for nivel in niveles:
                        try:
                            input_field = nivel.find_element(By.CSS_SELECTOR, "input[type='text']")
                            
                            # Limpiar y configurar valor
                            input_field.clear()
                            input_field.send_keys("10000")
                            logger.info("✅ 3. Monto: 10000")
                            input_encontrado = True
                            break
                        except Exception:
                            continue
                    
                    if not input_encontrado:
                        logger.error("No se encontró input válido para Monto")
                        raise Exception("Input no encontrado")
                    
            except Exception as e:
                logger.error(f"Error configurando Monto: {str(e)}")
                return False
            
            logger.info("✅ Filtros base configurados con Selenium")
            try:
                self._progress_cb("base_filters", "success")
            except Exception:
                pass
            return True
            
        except Exception as e:
            logger.error(f"Error en método fallback base: {str(e)}")
            return False
    
    def _process_lottery_in_session(self, lottery_type: str) -> List[Dict[str, Any]]:
        """Procesar una lotería específica en la sesión actual (solo cambiar dropdown)"""
        try:
            logger.info(f"🎯 Seleccionando {lottery_type} en dropdown...")
            # Determinar step_key desde site_lotteries si está disponible
            step_key = None
            for lot_cfg in self._site_lotteries:
                if lot_cfg["name"] == lottery_type:
                    step_key = lot_cfg["step_key"]
                    break
            if not step_key:
                # Fallback legacy
                step_key = "chance_extra" if "EXTRAORDINARIO" in lottery_type.upper() else ("chance" if "CHANCE" in lottery_type.upper() else ("ruleta" if "RULETA" in lottery_type.upper() else lottery_type.lower()))
            try:
                self._progress_cb(step_key, "running")
            except Exception:
                pass
            
            # Cambiar solo el campo "Lotería" sin reconfigurar todo
            if not self._change_lottery_dropdown(lottery_type):
                logger.error(f"✗ Error cambiando dropdown a {lottery_type}")
                return []
            
            logger.info(f"✓ Dropdown cambiado a {lottery_type}")
            
            # Ejecutar búsqueda
            if not self.execute_with_retry(self.execute_search):
                logger.error(f"✗ Error ejecutando búsqueda para {lottery_type}")
                try:
                    self._progress_cb(step_key, "error", "búsqueda falló")
                except Exception:
                    pass
                return []
            
            logger.info(f"✓ Búsqueda ejecutada para {lottery_type}")
            
            # USAR SOLO LA VALIDACIÓN OPTIMIZADA (MÁS RÁPIDA)
            logger.info(f"⏳ Esperando carga de tabla para {lottery_type}...")
            if not self.wait_for_table_load_optimized():
                logger.warning(f"⚠️ Timeout esperando carga de tabla para {lottery_type}")
            else:
                logger.info(f"✅ Tabla cargada para {lottery_type}")
            
            # Pausa adicional corta para asegurar estabilidad
            time.sleep(2)
            
            # Extraer datos
            data = self.execute_with_retry(self.extract_data)
            if data:
                logger.info(f"✓ Datos extraídos para {lottery_type}: {len(data)} registros")
                try:
                    self._progress_cb(step_key, "success")
                except Exception:
                    pass
                return data
            else:
                logger.warning(f"⚠️ No se obtuvieron datos para {lottery_type}")
                try:
                    self._progress_cb(step_key, "error", "sin datos")
                except Exception:
                    pass
                return []
                
        except Exception as e:
            logger.error(f"Error procesando {lottery_type}: {str(e)}")
            try:
                self._progress_cb(step_key, "error", str(e)[:120])
            except Exception:
                pass
            return []
    
    def _change_lottery_dropdown(self, lottery_type: str) -> bool:
        """Cambiar solo el dropdown de lotería (reutilizando sesión)"""
        try:
            logger.info(f"Cambiando dropdown Lotería a {lottery_type}...")
            
            # Buscar el campo "Lotería:" usando Selenium
            spans = self.driver.find_elements(By.TAG_NAME, "span")
            loteria_span = None
            
            for span in spans:
                if span.text.strip() == "Lotería:":
                    loteria_span = span
                    break
            
            if not loteria_span:
                logger.error("Campo 'Lotería:' no encontrado")
                return False
            
            # Buscar wrapper en múltiples niveles
            wrapper_encontrado = False
            niveles = [
                loteria_span.find_element(By.XPATH, ".."),
                loteria_span.find_element(By.XPATH, "../.."),
                loteria_span.find_element(By.XPATH, "../../..")
            ]
            
            for nivel in niveles:
                try:
                    # Intentar encontrar el wrapper o el icono de flecha
                    wrapper = None
                    try:
                        wrapper = nivel.find_element(By.CSS_SELECTOR, ".el-select__caret")
                        logger.info("Usando icono de flecha")
                    except Exception:
                        wrapper = nivel.find_element(By.CSS_SELECTOR, ".el-select__wrapper")
                        logger.info("Usando wrapper")
                    
                    wrapper.click()
                    wrapper_encontrado = True
                    break
                except Exception:
                    continue
            
            if not wrapper_encontrado:
                logger.error("No se encontró wrapper válido para Lotería")
                return False
            
            time.sleep(0.5)
            
            # Buscar y seleccionar la opción
            try:
                opciones = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".el-select-dropdown:not([aria-hidden='true']) li.el-select-dropdown__item"))
                )
                
                logger.info(f"Encontradas {len(opciones)} opciones de lotería")
                
                # Filtrar solo opciones con texto válido para evitar spam en logs
                opciones_validas = []
                for opcion in opciones:
                    texto = opcion.text.strip()
                    if texto and texto != "":
                        opciones_validas.append((opcion, texto))
                
                logger.info(f"Opciones válidas encontradas: {len(opciones_validas)}")
                
                # Buscar la opción específica
                for opcion, texto in opciones_validas:
                    logger.info(f"Evaluando: '{texto}'")
                    
                    # Buscar coincidencias más flexibles
                    if lottery_type == "CHANCE EXPRESS EXTRAORDINARIO" and "CHANCE" in texto and "EXTRAORDINARIO" in texto:
                        logger.info(f"✅ Seleccionando CHANCE EXPRESS EXTRAORDINARIO: {texto}")
                        opcion.click()
                        time.sleep(0.3)
                        logger.info(f"✅ Lotería cambiada a {lottery_type}")
                        return True
                    elif lottery_type == "CHANCE EXPRESS" and "CHANCE" in texto and "EXPRESS" in texto:
                        if "EXTRAORDINARIO" not in texto:
                            logger.info(f"✅ Seleccionando CHANCE EXPRESS: {texto}")
                            opcion.click()
                            time.sleep(0.3)
                            logger.info(f"✅ Lotería cambiada a {lottery_type}")
                            return True
                    elif lottery_type == "RULETA EXPRESS" and "RULETA" in texto and "EXPRESS" in texto:
                        if "EXTRAORDINARIO" not in texto:
                            logger.info(f"✅ Seleccionando RULETA EXPRESS: {texto}")
                            opcion.click()
                            time.sleep(0.3)
                            logger.info(f"✅ Lotería cambiada a {lottery_type}")
                            return True
                    elif texto.strip().upper() == lottery_type.strip().upper():
                        # Coincidencia exacta genérica (para todos los sorteos REAL y futuros)
                        logger.info(f"✅ Seleccionando (exacta): {texto}")
                        opcion.click()
                        time.sleep(0.3)
                        logger.info(f"✅ Lotería cambiada a {lottery_type}")
                        return True
                
                logger.error(f"No se encontró opción para {lottery_type}")
                return False
                
            except Exception as e:
                logger.error(f"Error buscando opciones de lotería: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error cambiando dropdown a {lottery_type}: {str(e)}")
            return False
    
    def cleanup(self):
        """Limpiar recursos"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Driver cerrado correctamente")
                self.driver = None
        except Exception as e:
            logger.error(f"Error cerrando driver: {str(e)}")
    
    def _kill_chrome_processes(self):
        """Matar procesos Chrome/ChromeDriver huérfanos asociados a este scraper"""
        try:
            import subprocess
            # Intentar matar por PID del service (chromedriver) y sus hijos (chrome)
            if hasattr(self, 'service') and self.service and hasattr(self.service, 'process') and self.service.process:
                pid = self.service.process.pid
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(pid)],
                    capture_output=True, timeout=10
                )
                logger.info(f"Proceso ChromeDriver (PID {pid}) y children terminados")
        except Exception as e:
            logger.debug(f"Kill by service PID: {e}")
        # Limpiar directorio temporal de perfil Chrome
        self._cleanup_profile_dir()

    def _cleanup_profile_dir(self):
        """Eliminar directorio temporal de perfil Chrome si existe"""
        if hasattr(self, '_profile_dir') and self._profile_dir:
            try:
                import shutil
                shutil.rmtree(self._profile_dir, ignore_errors=True)
                logger.debug(f"Perfil temporal eliminado: {self._profile_dir}")
            except Exception:
                pass
            self._profile_dir = None

    def cleanup_safe(self):
        """Limpiar recursos de forma segura sin fallar"""
        try:
            logger.info("🧹 Iniciando limpieza segura del driver...")
            
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                    logger.info("✅ Driver cerrado correctamente")
                except Exception:
                    # driver.quit() falló — matar a nivel OS
                    logger.warning("driver.quit() falló, matando procesos a nivel OS")
                    self._kill_chrome_processes()
                finally:
                    self.driver = None
            else:
                logger.info("✓ No hay driver activo para cerrar")
            
            # Limpiar profile temporal
            if hasattr(self, '_profile_dir') and self._profile_dir:
                try:
                    import shutil
                    shutil.rmtree(self._profile_dir, ignore_errors=True)
                except Exception:
                    pass
                self._profile_dir = None
                
        except Exception as e:
            logger.warning(f"Advertencia durante cleanup seguro: {str(e)}")
            self._kill_chrome_processes()
            try:
                self.driver = None
            except Exception:
                pass
    
    def __del__(self):
        """Destructor para asegurar limpieza"""
        self.cleanup_safe()
    
    def navigate_dropdown_with_keys(self, dropdown_element, target_text, max_attempts=50):
        """Navegar dropdown usando teclas de flecha y seleccionar opción"""
        try:
            logger.info(f"Navegando dropdown con teclas para encontrar: '{target_text}'")
            
            # Hacer clic en el dropdown para abrirlo
            self.safe_click(dropdown_element)
            
            # Esperar a que se abra el dropdown
            self.wait_for_dropdown_options("dropdown")
            
            # Presionar flecha hacia abajo para empezar a navegar
            dropdown_element.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.5)
            
            # Navegar por las opciones
            for i in range(max_attempts):
                try:
                    # Obtener el elemento actualmente seleccionado/resaltado
                    # Intentar múltiples selectores para Element UI
                    active_option = None
                    selectors = [
                        "//li[contains(@class, 'el-select-dropdown__item') and contains(@class, 'is-hovering')]",
                        "//li[contains(@class, 'el-select-dropdown__item') and contains(@class, 'hover')]", 
                        "//li[contains(@class, 'el-select-dropdown__item') and contains(@class, 'active')]",
                        "//li[contains(@class, 'el-select-dropdown__item') and contains(@class, 'selected')]"
                    ]
                    
                    for selector in selectors:
                        try:
                            active_option = self.driver.find_element(By.XPATH, selector)
                            break
                        except NoSuchElementException:
                            continue
                    
                    if active_option:
                        current_text = active_option.text.strip()
                        logger.info(f"Navegación {i+1}: '{current_text}'")
                        
                        # Verificar si encontramos la opción buscada
                        if target_text.upper() in current_text.upper() and current_text:
                            # Verificar que no sea "EXTRAORDINARIO" si buscamos "RULETA EXPRESS"
                            if target_text.upper() == "RULETA EXPRESS" and "EXTRAORDINARIO" in current_text.upper():
                                logger.info(f"Saltando '{current_text}' (contiene EXTRAORDINARIO)")
                            else:
                                logger.info(f"¡Opción encontrada! Presionando Enter en: '{current_text}'")
                                dropdown_element.send_keys(Keys.ENTER)
                                time.sleep(1)
                                return True
                    
                    # Si no es la opción correcta, continuar navegando
                    dropdown_element.send_keys(Keys.ARROW_DOWN)
                    time.sleep(0.3)  # Pausa entre navegaciones
                    
                except Exception as e:
                    # Si hay error, continuar navegando
                    dropdown_element.send_keys(Keys.ARROW_DOWN)
                    time.sleep(0.3)
                    continue
            
            logger.error(f"No se encontró '{target_text}' después de {max_attempts} intentos")
            return False
            
        except Exception as e:
            logger.error(f"Error navegando dropdown con teclas: {e}")
            return False
    
    def select_option_with_javascript(self, dropdown_xpath, target_text, field_name):
        """Seleccionar opción usando JavaScript directamente"""
        try:
            logger.info(f"Configurando {field_name} con JavaScript...")
            
            # Buscar el dropdown
            dropdown_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
            )
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", dropdown_element)
            self.wait_for_element_stable(dropdown_element)
            
            # Hacer clic para abrir el dropdown
            dropdown_element.click()
            time.sleep(2)  # Esperar a que se abra completamente
            
            # Usar JavaScript mejorado para encontrar y hacer clic en la opción
            js_script = f"""
            // Esperar un momento para que el dropdown se renderice
            setTimeout(function() {{
                // Buscar el dropdown que está visible y activo
                var visibleDropdowns = document.querySelectorAll('.el-select__popper:not([aria-hidden="true"])');
                var targetDropdown = null;
                
                // Encontrar el dropdown visible
                for (var d = 0; d < visibleDropdowns.length; d++) {{
                    var dropdown = visibleDropdowns[d];
                    if (dropdown.style.display !== 'none' && dropdown.offsetHeight > 0) {{
                        targetDropdown = dropdown;
                        break;
                    }}
                }}
                
                if (!targetDropdown) {{
                    // Fallback: buscar cualquier lista visible
                    var lists = document.querySelectorAll('ul.el-select-dropdown__list');
                    for (var i = 0; i < lists.length; i++) {{
                        if (lists[i].offsetHeight > 0 && lists[i].offsetWidth > 0) {{
                            targetDropdown = lists[i].closest('.el-select__popper') || lists[i];
                            break;
                        }}
                    }}
                }}
                
                if (targetDropdown) {{
                    var options = targetDropdown.querySelectorAll('li.el-select-dropdown__item');
                    console.log('Dropdown encontrado con ' + options.length + ' opciones');
                    
                    for (var i = 0; i < options.length; i++) {{
                        var option = options[i];
                        var text = option.textContent || option.innerText || '';
                        text = text.trim();
                        
                        console.log('Opción ' + (i+1) + ': "' + text + '"');
                        
                        if (text.includes('{target_text}')) {{
                            // Verificar si es RULETA EXPRESS y no EXTRAORDINARIO
                            if ('{target_text}' === 'RULETA EXPRESS' && text.includes('EXTRAORDINARIO')) {{
                                console.log('Saltando EXTRAORDINARIO: ' + text);
                                continue;
                            }}
                            
                            console.log('Haciendo clic en: ' + text);
                            
                            // Simular hover primero
                            option.classList.add('is-hovering');
                            
                            // Hacer clic
                            option.click();
                            
                            // También disparar evento change si es necesario
                            var event = new Event('change', {{ bubbles: true }});
                            option.dispatchEvent(event);
                            
                            window.selectionResult = true;
                            return;
                        }}
                    }}
                    
                    console.log('No se encontró la opción: {target_text}');
                    window.selectionResult = false;
                }} else {{
                    console.log('No se encontró dropdown visible');
                    window.selectionResult = false;
                }}
            }}, 100);
            """
            
            # Ejecutar el script
            self.driver.execute_script(js_script)
            
            # Esperar a que se complete la selección
            time.sleep(3)
            
            # Verificar el resultado
            try:
                result = self.driver.execute_script("return window.selectionResult;")
                if result:
                    logger.info(f"✓ {field_name} configurado con JavaScript: '{target_text}'")
                    self.wait_for_page_load()
                    return True
                else:
                    logger.error(f"✗ JavaScript no pudo seleccionar '{target_text}' en {field_name}")
                    return False
            except Exception:
                logger.warning(f"No se pudo verificar resultado de JavaScript para {field_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error configurando {field_name} con JavaScript: {e}")
            return False
    
    def select_option_by_typing(self, dropdown_xpath, target_text, field_name):
        """Seleccionar opción escribiendo el texto directamente"""
        try:
            logger.info(f"Configurando {field_name} escribiendo texto...")
            
            # Buscar el dropdown
            dropdown_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
            )
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", dropdown_element)
            self.wait_for_element_stable(dropdown_element)
            
            # Hacer clic para enfocar el dropdown
            dropdown_element.click()
            time.sleep(1)
            
            # Limpiar cualquier texto existente
            dropdown_element.send_keys(Keys.CONTROL + "a")
            time.sleep(0.5)
            
            # Escribir el texto de la opción
            if target_text == "Loterias No Tradicionales":
                dropdown_element.send_keys("No Tradicionales")
            elif target_text == "RULETA EXPRESS":
                dropdown_element.send_keys("RULETA EXPRESS")
            elif target_text == "Ventas Mayor o Igual a":
                dropdown_element.send_keys("Ventas Mayor")
            else:
                dropdown_element.send_keys(target_text)
            
            time.sleep(2)
            
            # Presionar Enter para seleccionar
            dropdown_element.send_keys(Keys.ENTER)
            time.sleep(1)
            
            logger.info(f"✓ {field_name} configurado escribiendo: '{target_text}'")
            self.wait_for_page_load()
            return True
            
        except Exception as e:
            logger.error(f"Error configurando {field_name} escribiendo: {e}")
            return False
    
    def debug_dropdown_options(self, dropdown_xpath, field_name):
        """Debug: mostrar todas las opciones disponibles en un dropdown"""
        try:
            logger.info(f"=== DEBUG: Inspeccionando opciones de {field_name} ===")
            
            # Buscar el dropdown
            dropdown_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
            )
            
            # Abrir el dropdown
            dropdown_element.click()
            time.sleep(3)
            
            # Usar JavaScript para obtener solo las opciones del dropdown activo
            js_script = """
            // Buscar el dropdown que está visible y activo
            var visibleDropdowns = document.querySelectorAll('.el-select__popper:not([aria-hidden="true"])');
            var targetDropdown = null;
            
            // Encontrar el dropdown visible
            for (var d = 0; d < visibleDropdowns.length; d++) {
                var dropdown = visibleDropdowns[d];
                if (dropdown.style.display !== 'none' && dropdown.offsetHeight > 0) {
                    targetDropdown = dropdown;
                    break;
                }
            }
            
            if (!targetDropdown) {
                // Fallback: buscar cualquier lista visible
                var lists = document.querySelectorAll('ul.el-select-dropdown__list');
                for (var i = 0; i < lists.length; i++) {
                    if (lists[i].offsetHeight > 0 && lists[i].offsetWidth > 0) {
                        targetDropdown = lists[i].closest('.el-select__popper') || lists[i];
                        break;
                    }
                }
            }
            
            var results = [];
            
            if (targetDropdown) {
                var options = targetDropdown.querySelectorAll('li.el-select-dropdown__item');
                
                for (var i = 0; i < options.length; i++) {
                    var option = options[i];
                    var text = option.textContent || option.innerText || '';
                    var classes = option.className || '';
                    var visible = option.offsetHeight > 0 && option.offsetWidth > 0;
                    
                    results.push({
                        index: i,
                        text: text.trim(),
                        classes: classes,
                        visible: visible,
                        html: option.outerHTML.substring(0, 200)
                    });
                }
            }
            
            return {
                found: targetDropdown !== null,
                count: results.length,
                options: results
            };
            """
            
            debug_data = self.driver.execute_script(js_script)
            
            if debug_data['found']:
                logger.info(f"Dropdown activo encontrado con {debug_data['count']} opciones en {field_name}:")
                
                for i, option in enumerate(debug_data['options'][:15]):  # Mostrar solo las primeras 15
                    logger.info(f"  {i+1}: '{option['text']}' (visible: {option['visible']})")
                    if option['text'] and ('RULETA' in option['text'].upper() or 'TRADICIONAL' in option['text'].upper() or 'VENTAS' in option['text'].upper()):
                        logger.info(f"    *** OPCIÓN RELEVANTE: '{option['text']}' ***")
            else:
                logger.warning(f"No se encontró dropdown activo para {field_name}")
            
            # Cerrar el dropdown
            dropdown_element.send_keys(Keys.ESCAPE)
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error inspeccionando {field_name}: {e}")
    
    def select_dropdown_option_robust(self, dropdown_xpath, target_text, field_name, timeout=10):
        """Método ultra-optimizado para selección rápida de opciones"""
        try:
            logger.info(f"Configurando {field_name}...")
            
            # Estrategia NUEVA: Usar selectores CSS directos basados en el HTML real
            if self.select_option_with_css_selector(target_text, field_name):
                return True
            
            # Fallback: JavaScript directo
            if self.select_option_with_javascript_fast(dropdown_xpath, target_text, field_name):
                return True
            
            logger.error(f"✗ Error configurando {field_name}")
            return False
                
        except Exception as e:
            logger.error(f"Error configurando {field_name}: {e}")
            return False
    
    def select_option_with_css_selector(self, target_text, field_name):
        """Método optimizado usando selectores CSS basados en el HTML real"""
        try:
            # Mapeo de campos a sus selectores específicos basados en el HTML real
            field_selectors = {
                "Tipo Lotería": {
                    "wrapper": "#ctl00_ContentPlaceHolder1_lblTipoLot + .input-group .el-select__wrapper",
                    "placeholder": "Todos"
                },
                "Lotería": {
                    "wrapper": "span:contains('Lotería:') + .input-group .el-select__wrapper",
                    "placeholder": "Todos"
                },
                "Filtro": {
                    "wrapper": "span:contains('Filtro:') + .input-group .el-select__wrapper", 
                    "placeholder": "Todos"
                }
            }
            
            if field_name not in field_selectors:
                return False
            
            selector_info = field_selectors[field_name]
            
            # JavaScript optimizado para cada campo específico
            js_script = f"""
            (function() {{
                // Para {field_name}, buscar el wrapper específico
                var wrapper = null;
                
                if ('{field_name}' === 'Tipo Lotería') {{
                    // Buscar por ID específico del label
                    var label = document.getElementById('ctl00_ContentPlaceHolder1_lblTipoLot');
                    if (label) {{
                        var inputGroup = label.nextElementSibling;
                        if (inputGroup && inputGroup.classList.contains('input-group')) {{
                            wrapper = inputGroup.querySelector('.el-select__wrapper');
                        }}
                    }}
                }} else {{
                    // Para otros campos, buscar por texto del span
                    var spans = document.querySelectorAll('span');
                    for (var i = 0; i < spans.length; i++) {{
                        if (spans[i].textContent.trim() === '{field_name}:') {{
                            var inputGroup = spans[i].nextElementSibling;
                            if (inputGroup && inputGroup.classList.contains('input-group')) {{
                                wrapper = inputGroup.querySelector('.el-select__wrapper');
                                break;
                            }}
                        }}
                    }}
                }}
                
                if (!wrapper) {{
                    console.log('No se encontró wrapper para {field_name}');
                    return false;
                }}
                
                // Hacer clic en el wrapper para abrir dropdown
                wrapper.click();
                
                // Esperar brevemente y buscar opciones
                setTimeout(function() {{
                    var dropdowns = document.querySelectorAll('.el-select-dropdown:not([aria-hidden="true"])');
                    var activeDropdown = null;
                    
                    for (var d = 0; d < dropdowns.length; d++) {{
                        if (dropdowns[d].offsetHeight > 0) {{
                            activeDropdown = dropdowns[d];
                            break;
                        }}
                    }}
                    
                    if (activeDropdown) {{
                        var options = activeDropdown.querySelectorAll('li.el-select-dropdown__item');
                        for (var i = 0; i < options.length; i++) {{
                            var text = (options[i].textContent || '').trim();
                            if (text.includes('{target_text}')) {{
                                // Verificar EXTRAORDINARIO para evitar confusiones
                                if ((text === 'RULETA EXPRESS' || text === 'CHANCE EXPRESS') && text.includes('EXTRAORDINARIO')) {{
                                    console.log('Saltando EXTRAORDINARIO: ' + text);
                                    continue;
                                }}
                                
                                console.log('✅ Opción encontrada, haciendo clic inmediato');
                                options[i].click();
                                if (callback) callback();
                                return true;
                            }}
                        }}
                        console.log('No se encontró la opción: {target_text}');
                    }} else {{
                        console.log('No se encontró dropdown activo');
                    }}
                    window.selectionSuccess = false;
                }}, 1000);
            }})();
            """
            
            # Ejecutar JavaScript
            self.driver.execute_script(js_script)
            
            # Esperar resultado
            time.sleep(2)
            
            try:
                result = self.driver.execute_script("return window.selectionSuccess;")
                if result:
                    logger.info(f"✓ {field_name}: '{target_text}' seleccionado con CSS")
                    self.wait_for_page_load()
                    return True
                else:
                    logger.warning(f"CSS selector falló para {field_name}")
                    return False
            except Exception:
                logger.warning(f"No se pudo verificar resultado CSS para {field_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error con CSS selector para {field_name}: {e}")
            return False
    
    def select_option_with_javascript_fast(self, dropdown_xpath, target_text, field_name):
        """Método ultra-rápido sin debug ni esperas innecesarias"""
        try:
            # Buscar dropdown inmediatamente (timeout corto)
            dropdown_element = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
            )
            
            # Clic inmediato sin scroll
            dropdown_element.click()
            
            # JavaScript ultra-optimizado - ejecuta inmediatamente
            js_script = f"""
            (function() {{
                // Buscar dropdown activo inmediatamente
                var dropdown = document.querySelector('.el-select__popper:not([aria-hidden="true"])');
                if (!dropdown) {{
                    var lists = document.querySelectorAll('ul.el-select-dropdown__list');
                    for (var i = 0; i < lists.length; i++) {{
                        if (lists[i].offsetHeight > 0) {{
                            dropdown = lists[i];
                            break;
                        }}
                    }}
                }}
                
                if (dropdown) {{
                    var options = dropdown.querySelectorAll('li.el-select-dropdown__item');
                    for (var i = 0; i < options.length; i++) {{
                        var text = (options[i].textContent || '').trim();
                        if (text.includes('{target_text}')) {{
                            // Verificar EXTRAORDINARIO solo para RULETA EXPRESS
                            if ('{target_text}' === 'RULETA EXPRESS' && text.includes('EXTRAORDINARIO')) {{
                                continue;
                            }}
                            options[i].click();
                            return true;
                        }}
                    }}
                }}
                return false;
            }})();
            """
            
            # Espera mínima y ejecución inmediata
            time.sleep(0.5)  # Solo 0.5 segundos
            result = self.driver.execute_script(f"return {js_script}")
            
            if result:
                logger.info(f"✓ {field_name}: '{target_text}'")
                return True
            else:
                return False
                
        except Exception as e:
            logger.warning(f"Error rápido en {field_name}: {e}")
            return False
    
    def process_lottery_with_optimization(self, lottery: Dict[str, str]) -> List[Dict[str, Any]]:
        """Procesar lotería con optimización específica basada en su rendimiento histórico"""
        lottery_name = lottery["name"]
        start_time = time.time()
        data = []
        success = False
        
        try:
            logger.info(f"🎯 Procesando {lottery_name} con optimización específica...")
            
            # 1. APLICAR CONFIGURACIÓN ESPECÍFICA DE LA LOTERÍA
            strategy = apply_lottery_specific_config(lottery_name, self)
            
            # 2. PROCESAR CON ESTRATEGIA ADAPTATIVA
            if strategy["wait_strategy"] == "enhanced":
                logger.info(f"🔧 Usando estrategia mejorada para {lottery_name}")
                data = self.process_lottery_enhanced(lottery, strategy)
            else:
                logger.info(f"⚡ Usando estrategia estándar para {lottery_name}")
                data = self.process_lottery_standard(lottery, strategy)
            
            success = len(data) > strategy.get("expected_min_rows", 1)
            
            # 3. MONITOREAR Y ANALIZAR RENDIMIENTO
            performance_report = monitor_lottery_performance(
                lottery_name, start_time, len(data), success
            )
            
            # 4. APLICAR ACCIONES CORRECTIVAS SI ES NECESARIO
            if performance_report["issues"]["has_issues"]:
                logger.warning(f"🚨 Aplicando corrección automática para {lottery_name}...")
                data = self.apply_automatic_correction(lottery, strategy, performance_report)
                success = len(data) > strategy.get("expected_min_rows", 1)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Error procesando {lottery_name} con optimización: {e}")
            # Reportar fallo para estadísticas
            monitor_lottery_performance(lottery_name, start_time, 0, False)
            return []
    
    def process_lottery_enhanced(self, lottery: Dict[str, str], strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Estrategia mejorada para loterías problemáticas como CHANCE EXPRESS"""
        lottery_name = lottery["name"]
        logger.info(f"🔧 ESTRATEGIA MEJORADA PARA {lottery_name}")
        
        try:
            # 1. Navegar con timeout extendido
            logger.info(f"🌐 Navegando a {lottery['url']} (timeout: {strategy['timeout']}s)")
            self.driver.set_page_load_timeout(strategy['timeout'])
            self.driver.get(lottery["url"])
            
            # 2. Cambiar filtro con confirmación visual
            self.change_lottery_filter(lottery_name)
            
            # 3. Ejecutar búsqueda con estabilidad extra
            self.execute_search()
            
            # 4. ESPERA ESPECÍFICA PARA CHANCE EXPRESS
            if lottery_name == "CHANCE EXPRESS":
                logger.info("⏰ Aplicando espera específica para CHANCE EXPRESS...")
                
                # Espera inicial más larga
                time.sleep(5)
                
                # Verificaciones de estabilidad múltiples
                for attempt in range(strategy['stability_checks']):
                    logger.info(f"🔍 Verificación de estabilidad {attempt + 1}/{strategy['stability_checks']}")
                    
                    if self.wait_for_table_load_enhanced(strategy['timeout']):
                        logger.info("✅ Tabla estable detectada")
                        break
                    else:
                        logger.warning(f"⚠️ Intento {attempt + 1} fallido, reintentando...")
                        time.sleep(3)
                else:
                    logger.error("❌ No se logró estabilidad de tabla tras múltiples intentos")
            else:
                # Espera estándar para otras loterías
                self.wait_for_table_load_enhanced(strategy['timeout'])
            
            # 5. Extraer datos con confirmación ML
            if strategy['use_visual_ml']:
                data = self.extract_data_with_ml_confirmation(lottery_name, strategy)
            else:
                data = self.extract_data()
            
            logger.info(f"✅ {lottery_name}: {len(data)} registros extraídos con estrategia mejorada")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error en estrategia mejorada para {lottery_name}: {e}")
            return []
    
    def process_lottery_standard(self, lottery: Dict[str, str], strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Estrategia estándar para loterías que funcionan bien"""
        lottery_name = lottery["name"]
        
        try:
            # Proceso estándar optimizado
            self.driver.get(lottery["url"])
            self.change_lottery_filter(lottery_name)
            self.execute_search()
            self.wait_for_table_load(strategy['timeout'])
            data = self.extract_data()
            
            logger.info(f"✅ {lottery_name}: {len(data)} registros extraídos con estrategia estándar")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error en estrategia estándar para {lottery_name}: {e}")
            return []
    
    def wait_for_table_load_enhanced(self, timeout: int = 45) -> bool:
        """🎯 ESPERA MEJORADA - Usa botón Buscar + ML para detectar cuando tabla está lista"""
        try:
            logger.info(f"🎯 Esperando carga de tabla (BOTÓN BUSCAR + ML, timeout: {timeout}s)...")
            
            # Verificar si tenemos sistema de visión disponible
            if hasattr(self, 'vision_engine') and self.vision_engine:
                # MÉTODO NUEVO: Usar detección de botón Buscar + ML
                logger.info("🔍 Usando detección de botón 'Buscar' + análisis ML...")
                
                # Establecer driver actual para el sistema de visión
                self.vision_engine.set_current_driver(self.driver)
                
                # Usar el nuevo método mejorado que combina botón + ML
                success = self.vision_engine.enhanced_table_wait(self.driver, timeout)
                
                if success:
                    logger.info("✅ Tabla lista confirmada por botón 'Buscar' + ML")
                    return True
                else:
                    logger.warning("⚠️ Método de botón falló - usando fallback")
            
            # FALLBACK: Método tradicional mejorado si no hay sistema de visión
            logger.info("🔄 Usando método de espera tradicional mejorado...")
            
            start_time = time.time()
            last_row_count = 0
            stable_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    # 1. Verificar que no hay loaders activos (incluye botón Buscar)
                    loading_check = self.driver.execute_script("""
                        // Buscar botón Buscar y verificar si está cargando
                        const buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                        let searchButtonLoading = false;
                        
                        for (let btn of buttons) {
                            const text = (btn.textContent || btn.value || '').toLowerCase();
                            if (text.includes('buscar') || text.includes('search')) {
                                const isDisabled = btn.disabled || btn.hasAttribute('disabled');
                                const hasLoadingClass = btn.className.includes('loading') || btn.className.includes('disabled');
                                const hasLoadingText = text.includes('cargando') || text.includes('loading');
                                
                                if (isDisabled || hasLoadingClass || hasLoadingText) {
                                    searchButtonLoading = true;
                                    break;
                                }
                            }
                        }
                        
                        // Verificar otros loaders
                        const loaders = document.querySelectorAll('.spinner, .loading, [class*="load"], [class*="spin"]');
                        const activeLoaders = Array.from(loaders).filter(l => {
                            const style = window.getComputedStyle(l);
                            return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                        });
                        
                        return {
                            search_button_loading: searchButtonLoading,
                            general_loaders: activeLoaders.length,
                            is_loading: searchButtonLoading || activeLoaders.length > 0
                        };
                    """)
                    
                    if loading_check.get('is_loading'):
                        logger.debug(f"🔄 Carga activa detectada: botón={loading_check.get('search_button_loading')}, "
                                   f"loaders={loading_check.get('general_loaders')}")
                        stable_count = 0  # Reset contador
                        time.sleep(2)
                        continue
                    
                    # 2. Buscar tabla y verificar contenido
                    table = self.driver.find_element(By.XPATH, "//table[contains(@class, 'table')]")
                    
                    # 3. Verificar calidad de datos (no solo cantidad)
                    data_quality = self.driver.execute_script("""
                        const table = document.querySelector('table tbody');
                        if (!table) return {rows: 0, quality: 0, has_real_data: false};
                        
                        const rows = table.querySelectorAll('tr');
                        let realDataRows = 0;
                        let totalRows = rows.length;
                        
                        for (let row of rows) {
                            const cells = row.querySelectorAll('td');
                            let hasRealData = false;
                            
                            for (let cell of cells) {
                                const text = cell.textContent.trim();
                                // Verificar que no es placeholder y tiene datos significativos
                                if (text && text !== '0' && text !== '$0.00' && 
                                    !text.includes('Total General') &&
                                    !text.includes('cargando') &&
                                    !text.includes('...')) {
                                    hasRealData = true;
                                    break;
                                }
                            }
                            
                            if (hasRealData) realDataRows++;
                        }
                        
                        const quality = totalRows > 0 ? realDataRows / totalRows : 0;
                        
                        return {
                            rows: totalRows,
                            real_data_rows: realDataRows,
                            quality: quality,
                            has_real_data: realDataRows > 0 && quality > 0.3
                        };
                    """)
                    
                    current_row_count = data_quality.get('real_data_rows', 0)
                    has_quality_data = data_quality.get('has_real_data', False)
                    
                    # 4. Verificar estabilidad mejorada
                    if (current_row_count == last_row_count and 
                        current_row_count > 1 and 
                        has_quality_data):
                        
                        stable_count += 1
                        logger.debug(f"✅ Estabilidad {stable_count}/3: {current_row_count} filas reales, "
                                   f"calidad: {data_quality.get('quality', 0):.1%}")
                        
                        if stable_count >= 3:  # 3 verificaciones estables
                            logger.info(f"🎯 ¡TABLA COMPLETAMENTE LISTA! {current_row_count} filas con datos reales")
                            return True
                    else:
                        stable_count = 0
                        last_row_count = current_row_count
                        logger.debug(f"🔄 Tabla cambiando: {current_row_count} filas reales")
                    
                    time.sleep(1)
                    
                except NoSuchElementException:
                    logger.debug("📋 Esperando aparición de tabla...")
                    time.sleep(2)
                    continue
            
            # Timeout alcanzado
            elapsed = time.time() - start_time
            logger.warning(f"⏰ Timeout alcanzado después de {elapsed:.1f}s")
            logger.warning(f"   Último conteo: {last_row_count} filas reales")
            logger.warning(f"   Estabilidad: {stable_count}/3 verificaciones")
            
            # Retornar True si al menos tenemos algo de datos, False si está completamente vacío
            return last_row_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error en espera mejorada: {e}")
            return False
    
    def extract_data_with_ml_confirmation(self, lottery_name: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extraer datos con confirmación ML específica para CHANCE EXPRESS"""
        try:
            logger.info(f"🧠 Extrayendo datos con confirmación ML para {lottery_name}...")
            
            # Verificar patrones de placeholders específicos
            placeholder_patterns = strategy['placeholder_patterns']
            
            # Obtener datos iniciales
            initial_data = self.extract_data()
            
            # Analizar calidad de datos
            real_data_count = 0
            placeholder_count = 0
            
            for record in initial_data:
                agency_name = record.get('agency_name', '')
                sales = record.get('sales', 0)
                
                # Detectar placeholders específicos de CHANCE EXPRESS
                is_placeholder = False
                for pattern in placeholder_patterns:
                    if pattern in agency_name or sales == 0:
                        is_placeholder = True
                        break
                
                if is_placeholder:
                    placeholder_count += 1
                else:
                    real_data_count += 1
            
            data_quality = real_data_count / max(len(initial_data), 1)
            
            logger.info(f"📊 Análisis ML {lottery_name}:")
            logger.info(f"   📈 Datos reales: {real_data_count}")
            logger.info(f"   🔲 Placeholders: {placeholder_count}")
            logger.info(f"   🎯 Calidad: {data_quality:.1%}")
            
            # Decidir si los datos son aceptables
            expected_min_rows = strategy['expected_min_rows']
            
            if real_data_count >= expected_min_rows and data_quality > 0.5:
                logger.info(f"✅ ML CONFIRMA: Datos de calidad aceptable para {lottery_name}")
                return initial_data
            else:
                logger.warning(f"⚠️ ML RECHAZA: Calidad insuficiente para {lottery_name}")
                logger.warning(f"   Esperado: {expected_min_rows}+ registros, obtenido: {real_data_count}")
                logger.warning(f"   Calidad esperada: >50%, obtenida: {data_quality:.1%}")
                
                # Aplicar corrección automática
                return self.apply_data_quality_correction(lottery_name, strategy)
        
        except Exception as e:
            logger.error(f"❌ Error en confirmación ML: {e}")
            return self.extract_data()  # Fallback a método estándar
    
    def apply_automatic_correction(self, lottery: Dict[str, str], strategy: Dict[str, Any], 
                                 performance_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Aplicar corrección automática basada en problemas detectados"""
        lottery_name = lottery["name"]
        issues = performance_report["issues"]
        
        logger.warning(f"🔧 APLICANDO CORRECCIÓN AUTOMÁTICA PARA {lottery_name}")
        logger.warning(f"   Severidad: {issues['severity']}")
        logger.warning(f"   Recomendación: {issues['recommendation']}")
        
        try:
            if issues["severity"] == "critical":
                # Reiniciar proceso completo
                logger.warning("🔄 Reiniciando proceso completo...")
                self.driver.refresh()
                time.sleep(10)
                return self.process_lottery_enhanced(lottery, strategy)
            
            elif issues["severity"] == "high":
                # Aumentar timeout y reintentar
                logger.warning("⏰ Aumentando timeout y reintentando...")
                enhanced_strategy = strategy.copy()
                enhanced_strategy['timeout'] = int(strategy['timeout'] * 1.5)
                enhanced_strategy['use_visual_ml'] = True
                
                return self.process_lottery_enhanced(lottery, enhanced_strategy)
            
            else:
                # Aplicar optimización menor
                logger.info("💡 Aplicando optimización menor...")
                time.sleep(5)
                return self.extract_data()
        
        except Exception as e:
            logger.error(f"❌ Error en corrección automática: {e}")
            return []
    
    def apply_data_quality_correction(self, lottery_name: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Aplicar corrección específica por calidad de datos"""
        logger.warning(f"🔧 CORRECCIÓN DE CALIDAD PARA {lottery_name}")
        
        try:
            # Esperar más tiempo para que termine la carga
            logger.info("⏰ Esperando carga completa adicional...")
            time.sleep(10)
            
            # Verificar nuevamente
            if self.wait_for_table_load_enhanced(30):
                new_data = self.extract_data()
                logger.info(f"🔄 Segunda extracción: {len(new_data)} registros")
                return new_data
            else:
                logger.warning("⚠️ Corrección de calidad fallida")
                return []
        
        except Exception as e:
            logger.error(f"❌ Error en corrección de calidad: {e}")
            return []

# Alias para compatibilidad
LotteryScraper = LotteryMonitorScraper