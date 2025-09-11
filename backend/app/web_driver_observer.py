"""
🔍 WebDriver Observer - ExpressATM
Observer inteligente que intercepta todas las interacciones con Selenium
y alimenta el sistema de inteligencia DOM con datos en tiempo real
"""

import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    WebDriverException, StaleElementReferenceException
)

from .dom_intelligence import DOMInteraction, dom_intelligence

logger = logging.getLogger(__name__)

class IntelligentWebDriverWait(WebDriverWait):
    """WebDriverWait inteligente que registra todas las interacciones"""
    
    def __init__(self, driver, timeout: float, poll_frequency: float = 0.5, context: str = "unknown"):
        super().__init__(driver, timeout, poll_frequency)
        self.context = context
        self.start_time = None
        
    def until(self, method, message: str = ""):
        """Override del método until para capturar métricas"""
        self.start_time = time.time()
        
        try:
            result = super().until(method, message)
            duration = time.time() - self.start_time
            
            # Registrar interacción exitosa
            self._record_interaction(
                action_type="wait_until",
                selector=str(method),
                duration=duration,
                success=True
            )
            
            return result
            
        except TimeoutException as e:
            duration = time.time() - self.start_time
            
            # Registrar interacción fallida
            self._record_interaction(
                action_type="wait_until",
                selector=str(method),
                duration=duration,
                success=False,
                error_message=str(e)
            )
            raise
    
    def _record_interaction(self, action_type: str, selector: str, duration: float, 
                          success: bool, error_message: Optional[str] = None):
        """Registrar interacción en el sistema de inteligencia"""
        try:
            interaction = DOMInteraction(
                timestamp=datetime.now(),
                action_type=action_type,
                selector=selector,
                selector_type="condition",
                duration=duration,
                success=success,
                element_found=success,
                page_url=self._driver.current_url,
                context=self.context,
                error_message=error_message
            )
            
            dom_intelligence.record_interaction(interaction)
            
        except Exception as e:
            logger.warning(f"Error registrando interacción: {e}")

class IntelligentWebElement:
    """Wrapper inteligente para WebElement que observa todas las interacciones"""
    
    def __init__(self, element: WebElement, selector: str, selector_type: str, 
                 driver, context: str = "unknown"):
        self._element = element
        self._selector = selector
        self._selector_type = selector_type
        self._driver = driver
        self._context = context
    
    def click(self):
        """Click inteligente con observación"""
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            # Aplicar optimización si existe
            optimization = dom_intelligence.get_optimization_for_element(self._selector)
            if optimization and optimization['type'] == 'pre_click_wait':
                time.sleep(optimization['value'])
            
            self._element.click()
            success = True
            
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time
            self._record_interaction("click", duration, success, error_message)
        
        return self
    
    def send_keys(self, *value):
        """Send keys inteligente con observación"""
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            # Aplicar optimización si existe
            optimization = dom_intelligence.get_optimization_for_element(self._selector)
            if optimization and optimization['type'] == 'typing_delay':
                # Escribir más lentamente si se detectaron problemas
                for char in str(value[0]):
                    self._element.send_keys(char)
                    time.sleep(optimization['value'])
            else:
                self._element.send_keys(*value)
            
            success = True
            
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time
            self._record_interaction("send_keys", duration, success, error_message)
        
        return self
    
    def clear(self):
        """Clear inteligente con observación"""
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            self._element.clear()
            success = True
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time
            self._record_interaction("clear", duration, success, error_message)
        
        return self
    
    def get_attribute(self, name: str):
        """Get attribute con observación"""
        start_time = time.time()
        success = False
        error_message = None
        result = None
        
        try:
            result = self._element.get_attribute(name)
            success = True
            return result
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time
            self._record_interaction("get_attribute", duration, success, error_message)
    
    @property
    def text(self):
        """Text property con observación"""
        start_time = time.time()
        success = False
        error_message = None
        result = None
        
        try:
            result = self._element.text
            success = True
            return result
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            duration = time.time() - start_time
            self._record_interaction("get_text", duration, success, error_message)
    
    def _record_interaction(self, action_type: str, duration: float, success: bool, 
                          error_message: Optional[str] = None):
        """Registrar interacción en el sistema de inteligencia"""
        try:
            # Obtener propiedades del elemento para análisis
            element_properties = {}
            try:
                element_properties = {
                    'tag_name': self._element.tag_name,
                    'is_displayed': self._element.is_displayed(),
                    'is_enabled': self._element.is_enabled(),
                    'size': self._element.size,
                    'location': self._element.location
                }
            except:
                pass  # Si no se pueden obtener propiedades, continuamos
            
            interaction = DOMInteraction(
                timestamp=datetime.now(),
                action_type=action_type,
                selector=self._selector,
                selector_type=self._selector_type,
                duration=duration,
                success=success,
                element_found=True,  # Si llegamos aquí, el elemento fue encontrado
                page_url=self._driver.current_url,
                context=self._context,
                error_message=error_message,
                element_properties=element_properties
            )
            
            dom_intelligence.record_interaction(interaction)
            
        except Exception as e:
            logger.warning(f"Error registrando interacción de elemento: {e}")
    
    def __getattr__(self, name):
        """Delegar otros métodos al elemento original"""
        return getattr(self._element, name)

class WebDriverObserver:
    """Observer principal que intercepta todas las interacciones con WebDriver"""
    
    def __init__(self, driver, context: str = "unknown"):
        self.driver = driver
        self.context = context
        self.interaction_count = 0
        self.retry_count = 0
        
    def find_element_intelligent(self, by: By, value: str, timeout: float = None, 
                               retry_count: int = 3) -> IntelligentWebElement:
        """Buscar elemento con inteligencia y optimización automática"""
        
        # Obtener optimización de timeout si existe
        optimization = dom_intelligence.get_optimization_for_element(value)
        if optimization and optimization['type'] == 'timeout':
            timeout = optimization['value']
        elif timeout is None:
            timeout = 10  # Default timeout
        
        start_time = time.time()
        success = False
        element_found = False
        error_message = None
        element = None
        
        for attempt in range(retry_count + 1):
            try:
                # Usar wait inteligente
                wait = IntelligentWebDriverWait(self.driver, timeout, context=self.context)
                element = wait.until(EC.presence_of_element_located((by, value)))
                
                success = True
                element_found = True
                break
                
            except TimeoutException as e:
                error_message = f"Timeout después de {timeout}s (intento {attempt + 1})"
                if attempt < retry_count:
                    # Aumentar timeout para el siguiente intento
                    timeout *= 1.5
                    logger.info(f"Reintentando con timeout aumentado: {timeout:.2f}s")
                continue
                
            except Exception as e:
                error_message = str(e)
                break
        
        duration = time.time() - start_time
        
        # Registrar la interacción
        interaction = DOMInteraction(
            timestamp=datetime.now(),
            action_type="find_element",
            selector=value,
            selector_type=by,
            duration=duration,
            success=success,
            element_found=element_found,
            page_url=self.driver.current_url,
            context=self.context,
            retry_count=retry_count if not success else 0,
            error_message=error_message
        )
        
        dom_intelligence.record_interaction(interaction)
        
        if not success:
            raise TimeoutException(f"No se pudo encontrar elemento: {value}")
        
        # Retornar elemento inteligente
        return IntelligentWebElement(element, value, by, self.driver, self.context)
    
    def find_elements_intelligent(self, by: By, value: str, timeout: float = 10) -> List[IntelligentWebElement]:
        """Buscar múltiples elementos con inteligencia"""
        start_time = time.time()
        success = False
        elements_found = False
        error_message = None
        elements = []
        
        try:
            wait = IntelligentWebDriverWait(self.driver, timeout, context=self.context)
            elements = wait.until(EC.presence_of_all_elements_located((by, value)))
            
            success = True
            elements_found = len(elements) > 0
            
        except TimeoutException as e:
            error_message = f"Timeout encontrando elementos: {value}"
        except Exception as e:
            error_message = str(e)
        
        duration = time.time() - start_time
        
        # Registrar la interacción
        interaction = DOMInteraction(
            timestamp=datetime.now(),
            action_type="find_elements",
            selector=value,
            selector_type=by,
            duration=duration,
            success=success,
            element_found=elements_found,
            page_url=self.driver.current_url,
            context=self.context,
            error_message=error_message
        )
        
        dom_intelligence.record_interaction(interaction)
        
        if not success:
            raise TimeoutException(f"No se pudieron encontrar elementos: {value}")
        
        # Retornar elementos inteligentes
        return [
            IntelligentWebElement(elem, value, by, self.driver, self.context) 
            for elem in elements
        ]
    
    def wait_for_page_load(self, timeout: float = 30):
        """Esperar carga completa de página con observación"""
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            wait = IntelligentWebDriverWait(self.driver, timeout, context=self.context)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            success = True
            
        except TimeoutException as e:
            error_message = "Timeout esperando carga de página"
        except Exception as e:
            error_message = str(e)
        
        duration = time.time() - start_time
        
        # Registrar la interacción
        interaction = DOMInteraction(
            timestamp=datetime.now(),
            action_type="page_load_wait",
            selector="document.readyState",
            selector_type="javascript",
            duration=duration,
            success=success,
            element_found=success,
            page_url=self.driver.current_url,
            context=self.context,
            error_message=error_message
        )
        
        dom_intelligence.record_interaction(interaction)
        
        if not success:
            raise TimeoutException("Página no cargó completamente")
    
    def intelligent_sleep(self, base_duration: float):
        """Sleep inteligente que se adapta basado en el rendimiento del sistema"""
        # Analizar rendimiento reciente
        optimization = dom_intelligence.get_optimization_for_element("system_sleep")
        
        if optimization and optimization['type'] == 'adaptive_sleep':
            # Ajustar duración basada en el análisis de rendimiento
            adjusted_duration = base_duration * optimization['value']
            logger.debug(f"Sleep adaptativo: {base_duration}s -> {adjusted_duration:.2f}s")
            time.sleep(adjusted_duration)
        else:
            time.sleep(base_duration)
    
    def set_context(self, context: str):
        """Cambiar el contexto actual para las observaciones"""
        self.context = context
        logger.debug(f"Contexto DOM cambiado a: {context}")
    
    def get_performance_summary(self) -> Dict:
        """Obtener resumen de rendimiento de la sesión actual"""
        return {
            'interaction_count': self.interaction_count,
            'context': self.context,
            'current_url': self.driver.current_url
        } 