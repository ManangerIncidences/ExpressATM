# 🏦 ExpressATM - Sistema de Monitoreo de Loterías

## 📝 Descripción
Sistema automatizado de monitoreo para loterías Express (CHANCE EXPRESS y RULETA EXPRESS) con análisis inteligente y alertas en tiempo real.

## ✨ Características
- 🎯 Monitoreo dual automático (CHANCE y RULETA EXPRESS)
- 🧠 Sistema de inteligencia artificial integrado
- 📊 Dashboard web interactivo
- 📈 Análisis de tendencias y patrones
- 🔔 Sistema de alertas automáticas
- 📄 Reportes en PDF
- ⚡ Procesamiento en tiempo real

---

## 🚀 Instalación en Nueva PC

### � **Método Unificado (Recomendado) - Un Solo Script**

#### **Paso 1: Descargar Proyecto**
1. Ve a: **https://github.com/ManangerIncidences/ExpressATM**
2. Clic en **"Code"** > **"Download ZIP"**  
3. Extraer en carpeta deseada (ej: `C:\ExpressATM`)

#### **Paso 2: Ejecutar Instalador Universal**
```bash
# UN SOLO COMANDO - TODO AUTOMÁTICO
install_complete.bat

# O usar el inicio inteligente (detecta qué necesitas)
smart_start.bat
```

✅ **Este script hace TODO automáticamente:**
- Verifica Python y dependencias
- Crea entorno virtual limpio  
- Instala todas las dependencias
- Configura ChromeDriver
- Crea acceso directo en escritorio
- Ofrece ejecutar inmediatamente

### 🔧 **Con Git (Usuarios Avanzados)**
```bash
# Clonar y ejecutar todo en uno
git clone https://github.com/ManangerIncidences/ExpressATM.git
cd ExpressATM
install_complete.bat
```

### 🎛️ **Centro de Control (Opciones Avanzadas)**
```bash
# Menú interactivo con todas las opciones
express_control.bat
```

### ⚙️ **Instalación Manual (Solo si es necesario)**
```bash
# 1. Descargar ZIP desde GitHub y extraer
# 2. Instalar Python 3.8+ desde python.org
# 3. Abrir terminal en carpeta del proyecto
pip install -r requirements.txt
python run.py
```

---

## 💻 Para PC con Proyecto Existente

### **Instalación/Actualización Normal**
```bash
# Instalar/actualizar dependencias
install.bat

# Ejecutar aplicación
run.bat
```

### **Comandos Manuales**
```bash
# Actualizar dependencias
pip install -r requirements.txt

# Ejecutar con puerto personalizado
python run.py --port 8001
```

---

## 🌐 Acceso a la Aplicación

Una vez ejecutando, accede en tu navegador:

- **🏠 Panel Principal**: http://localhost:8000
- **📊 Dashboard**: http://localhost:8000/dashboard  
- **🧠 Análisis IA**: http://localhost:8000/ai
- **📚 API Docs**: http://localhost:8000/docs

---

## 👥 Colaboración en Equipo (Uso Interno)

### 🗄️ **Base de Datos Compartida**
- **`monitoring.db`**: Datos principales de monitoreo
- **`dom_intelligence.db`**: Patrones de inteligencia DOM  
- **`vision_learning.db`**: Datos de aprendizaje visual

### 🔄 **Flujo de Trabajo Diario**

#### **Antes de Trabajar:**
```bash
# Sincronizar datos del equipo
sync_data.bat
```

#### **Después del Trabajo:**
```bash
# Subir datos actualizados
update_data.bat
```

#### **Comandos Git Manuales:**
```bash
# Obtener últimos datos
git pull origin main

# Subir cambios de base de datos
git add *.db
git commit -m "Update DB $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git push origin main
```

---

## 📁 Estructura del Proyecto

```
ExpressATM/
├── 🖥️ backend/              # API y lógica de negocio
├── 🌐 frontend/             # Interfaz web
├── 🗃️ data/                 # Archivos de datos
├── 🤖 drivers/              # ChromeDriver
├── 📊 intelligence_models/  # Modelos de IA
├── 📝 logs/                 # Archivos de log
├── � install_complete.bat  # ⭐ INSTALADOR UNIVERSAL (TODO EN UNO)
├── 🎯 smart_start.bat       # ⭐ INICIO INTELIGENTE (DETECTA QUÉ NECESITAS)
├── 🎛️ express_control.bat   # ⭐ CENTRO DE CONTROL (MENÚ COMPLETO)
├── ▶️ run.bat               # Ejecutor rápido
├── 🔄 update.bat            # Actualización automática
├── 🔄 sync_data.bat         # Sincronizar equipo
├── ⬆️ update_data.bat       # Subir datos equipo
└── 📋 requirements.txt      # Dependencias Python
```

---

## ⚠️ Resolución de Problemas

### **Error: "Python no encontrado"**
1. Instalar Python desde: https://python.org/downloads
2. ✅ **Importante**: Marcar "Add Python to PATH"
3. Reiniciar PC y ejecutar `setup_new_pc.bat`

### **Error: "Fatal error in launcher" o rutas de pip incorrectas**
**Causa**: Entorno virtual con rutas de otra PC
```bash
# Reparación automática
repair_installation.bat

# O reparación manual:
deactivate
rmdir /S venv
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

### **Error: "Unable to obtain driver for chrome" (ChromeDriver)**
**Causa**: ChromeDriver faltante o incompatible con versión de Chrome
```bash
# Solución automática
update_chromedriver.bat

# O con PowerShell (más robusta)
powershell -ExecutionPolicy Bypass -File update_chromedriver.ps1

# Verificar instalación
check_system.bat
```

### **Error: "Puerto ocupado"**
```bash
# Usar puerto diferente
python run.py --port 8001
```

### **Error: "No se conecta a la base de datos"**
```bash
# Reinstalar dependencias
install.bat
```

---

## 🛠️ Comandos Útiles

### **Mantenimiento**
```bash
# Limpiar archivos temporales
cleanup_repository.py

# Actualizar ChromeDriver
update_chromedriver.bat

# Ver logs en tiempo real
tail -f logs/app.log
```

### **Desarrollo**
```bash
# Modo desarrollo con recarga automática
python run.py --dev

# Ejecutar tests
python -m pytest

# Verificar dependencias
pip check
```

---

## 📖 Documentación Adicional

- 📋 **Para Nuevos Usuarios**: `INSTALACION_EQUIPO.md`
- 📚 **Documentación Técnica**: `DOCUMENTACION_TECNICA.md`  
- 👤 **Guía de Usuario**: `GUIA_USUARIOS.md`

---

## 📞 Soporte

### **Problemas Comunes:**
1. Ejecutar `install.bat` para reinstalar dependencias
2. Revisar logs en la consola o `logs/app.log`
3. Verificar que Chrome esté actualizado

### **Contacto:**
- **Repositorio**: https://github.com/ManangerIncidences/ExpressATM
- **Issues**: Reportar problemas en GitHub Issues

---

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

## 🔄 **Actualización del Sistema**

### **📋 Verificar Actualizaciones**
```bash
# Verificar actualizaciones disponibles
check_updates.bat

# Ver versión actual
python run.py --version
```

### **⚡ Actualizar Automáticamente**
```bash
# Actualización completa con respaldos automáticos
update.bat
```

### **🔧 Actualización Manual**
```bash
# Paso a paso
git pull origin main
python -m pip install -r requirements.txt --upgrade
```

### **📚 Documentación de Actualización**
- **Guía Completa**: `ACTUALIZACION.md`
- **Resolución de Problemas**: Ver sección de errores comunes

---

## 🎯 **Scripts Principales - TODO SIMPLIFICADO**

### 🌟 **Scripts Unificados (Usa Estos):**
- **`install_complete.bat`** - 🚀 Instalación completa automática (nuevos usuarios)  
- **`smart_start.bat`** - 🎯 Inicio inteligente (detecta qué necesitas y lo hace)
- **`express_control.bat`** - 🎛️ Centro de control (menú con todas las opciones)

### 📊 **Scripts Específicos (Opcionales):**
- `update.bat` - Actualizar desde GitHub
- `check_updates.bat` - Ver actualizaciones disponibles
- `update_chromedriver.bat` - Solo instalar ChromeDriver
- `check_system.bat` - Diagnóstico del sistema
- `repair_installation.bat` - Reparar problemas

---

## 🎯 Inicio Rápido - Resumen

### 🆕 **NUEVA PC (Súper Fácil):**
1. **📥 Descargar**: https://github.com/ManangerIncidences/ExpressATM
2. **🚀 UN COMANDO**: `install_complete.bat`  
3. **🌐 Usar**: http://localhost:8000

### 🔄 **PC EXISTENTE:**
1. **🎯 Ejecutar**: `smart_start.bat` (detecta automáticamente qué hacer)
2. **🌐 Usar**: http://localhost:8000

### 🎛️ **OPCIONES AVANZADAS:**
1. **� Menú Completo**: `express_control.bat`

¡Listo para monitorear ExpressATM! 🎉
