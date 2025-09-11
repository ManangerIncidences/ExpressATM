# 🚀 ExpressATM - Guía de Instalación para Equipo

## 📱 Instalación Rápida (5 minutos)

### Paso 1: Descargar
1. Ve a: https://github.com/ManangerIncidences/ExpressATM
2. Clic en **"Code"** > **"Download ZIP"**
3. Extraer en: `C:\ExpressATM`

### Paso 2: Instalar
1. Abrir carpeta `C:\ExpressATM`
2. Doble clic en **`install.bat`**
3. Esperar que termine la instalación

### Paso 3: Ejecutar
1. Doble clic en **`run.bat`**
2. Abrir navegador en: http://localhost:8000

---

## 🔧 Instalación Alternativa (Con Git)

```bash
# Terminal/PowerShell como Administrador
git clone https://github.com/ManangerIncidences/ExpressATM.git
cd ExpressATM
install.bat
run.bat
```

---

## 📊 Sincronización de Datos del Equipo

### Primera vez:
- La base de datos se descarga automáticamente con el proyecto

### Actualizaciones diarias:
```bash
# Antes de trabajar (obtener datos del equipo)
sync_data.bat

# Después de trabajar (subir tus datos)
update_data.bat
```

---

## ⚠️ Resolución de Problemas

### Error: "Python no encontrado"
1. Instalar Python desde: https://python.org
2. ✅ Marcar "Add Python to PATH"
3. Reiniciar PC
4. Ejecutar `install.bat` de nuevo

### Error: "Fatal error in launcher" o rutas incorrectas en pip
**Problema**: Entorno virtual con rutas de otra PC
```bash
# Paso 1: Desactivar entorno virtual
deactivate

# Paso 2: Eliminar carpeta venv corrupta
rmdir /S venv

# Paso 3: Usar script de reparación
repair_installation.bat

# O crear entorno virtual nuevo manualmente:
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

### Error: "ChromeDriver no encontrado"
1. Ejecutar `update_chromedriver.bat`
2. O instalar Chrome si no está instalado

### Error: "No se pueden instalar dependencias"
1. Abrir PowerShell como Administrador
2. Ejecutar: `pip install --upgrade pip`
3. Ejecutar: `pip install -r requirements.txt`

### Error: "Puerto ocupado"
```bash
# Usar puerto diferente
python run.py --port 8001
```

---

## 📱 Uso Diario

### Flujo de Trabajo:
1. **`sync_data.bat`** - Sincronizar datos del equipo
2. **`run.bat`** - Ejecutar aplicación  
3. Usar aplicación normalmente
4. **`update_data.bat`** - Subir datos actualizados

### URLs de Acceso:
- **Panel Principal**: http://localhost:8000
- **Dashboard**: http://localhost:8000/dashboard  
- **Análisis IA**: http://localhost:8000/ai
- **API Docs**: http://localhost:8000/docs

---

## 💡 Consejos para el Equipo

### ✅ Buenas Prácticas:
- Siempre ejecutar `sync_data.bat` antes de trabajar
- Subir datos con `update_data.bat` al terminar
- Mantener Chrome actualizado
- No modificar archivos de configuración

### 🚫 Evitar:
- Ejecutar múltiples instancias al mismo tiempo
- Modificar archivos .db manualmente
- Cerrar la aplicación bruscamente

---

## 📞 Soporte

**Contacto**: [Tu información de contacto]
**Repositorio**: https://github.com/ManangerIncidences/ExpressATM
**Documentación**: README.md en el repositorio
