# 🔄 Guía de Actualización ExpressATM

## 📋 **Métodos de Actualización**

### 🚀 **Método 1: Actualización Automática (Recomendado)**

```bash
# Verificar actualizaciones disponibles
check_updates.bat

# Actualizar automáticamente
update.bat
```

**✅ Ventajas:**
- Respaldos automáticos de cambios locales
- Verificación de integridad
- Actualización de dependencias
- Manejo de conflictos automático

---

### 🔧 **Método 2: Actualización Manual**

```bash
# 1. Verificar estado
git status

# 2. Respaldar cambios locales (si los hay)
git stash push -m "Respaldo antes de actualizar"

# 3. Descargar actualizaciones
git pull origin main

# 4. Actualizar dependencias
python -m pip install -r requirements.txt --upgrade

# 5. Restaurar cambios (si es necesario)
git stash pop
```

---

### 📥 **Método 3: Descarga Completa (Para Problemas Graves)**

```bash
# 1. Respaldar datos importantes
copy *.db backup\
copy logs\*.log backup\

# 2. Descargar versión completa
git clone https://github.com/ManangerIncidences/ExpressATM.git ExpressATM_new

# 3. Migrar datos
copy backup\*.db ExpressATM_new\
copy backup\*.log ExpressATM_new\logs\

# 4. Reemplazar carpeta
rmdir /S ExpressATM_old
move ExpressATM ExpressATM_old
move ExpressATM_new ExpressATM
```

---

## 🔍 **Verificación de Actualizaciones**

### **Verificar Versión Actual:**
```bash
python run.py --version
```

### **Verificar Actualizaciones Disponibles:**
```bash
check_updates.bat
```

### **Ver Historial de Cambios:**
```bash
git log --oneline -10
```

---

## ⚠️ **Solución de Problemas de Actualización**

### **Error: "Your local changes would be overwritten"**
```bash
# Opción 1: Respaldar cambios
git stash push -m "Respaldo temporal"
git pull origin main
git stash pop

# Opción 2: Descartar cambios locales
git reset --hard HEAD
git pull origin main
```

### **Error: "Fatal: not a git repository"**
```bash
# Reconectar con GitHub
git init
git remote add origin https://github.com/ManangerIncidences/ExpressATM.git
git fetch origin main
git reset --hard origin/main
```

### **Error: Conflictos de merge**
```bash
# Ver archivos en conflicto
git status

# Resolver conflictos manualmente o usar herramienta
git mergetool

# Después de resolver
git add .
git commit -m "Resolver conflictos de actualización"
```

### **Error: Dependencias faltantes después de actualizar**
```bash
# Reparar instalación
repair_installation.bat

# O manualmente
python -m pip install -r requirements.txt --force-reinstall
```

---

## 🔄 **Flujo de Actualización para Equipos**

### **Para Administradores:**
1. **Antes de publicar actualizaciones:**
   ```bash
   # Actualizar número de versión
   edit version.py
   
   # Commit cambios
   git add .
   git commit -m "v2.1.0: Nuevas funcionalidades"
   git push origin main
   ```

2. **Notificar al equipo:**
   - Enviar mensaje con novedades
   - Indicar si requiere pasos especiales

### **Para Usuarios del Equipo:**
1. **Verificar actualizaciones:**
   ```bash
   check_updates.bat
   ```

2. **Actualizar cuando esté disponible:**
   ```bash
   update.bat
   ```

3. **Sincronizar datos del equipo:**
   ```bash
   sync_data.bat  # Después de actualizar
   ```

---

## 📊 **Control de Versiones**

### **Estructura de Versiones:**
- **Major.Minor.Patch** (ej: 2.1.0)
- **Major**: Cambios importantes/incompatibles
- **Minor**: Nuevas funcionalidades
- **Patch**: Corrección de errores

### **Información de Versión:**
```bash
# Ver versión actual
python run.py --version

# Ver información detallada
python -c "from version import get_version_info; print(get_version_info())"
```

---

## 🛡️ **Respaldos Automáticos**

### **El script `update.bat` automáticamente:**
- ✅ Detecta cambios locales
- 💾 Crea respaldos con `git stash`
- 🔄 Aplica actualizaciones
- 📦 Actualiza dependencias
- 🔍 Verifica integridad

### **Restaurar Respaldo:**
```bash
# Ver respaldos disponibles
git stash list

# Restaurar último respaldo
git stash pop

# Restaurar respaldo específico
git stash apply stash@{1}
```

---

## 💡 **Consejos de Actualización**

### **✅ Buenas Prácticas:**
- Siempre usar `check_updates.bat` antes de actualizar
- Cerrar ExpressATM antes de actualizar
- Permitir respaldos automáticos de cambios locales
- Verificar funcionamiento después de actualizar

### **🚫 Evitar:**
- Actualizar con ExpressATM ejecutándose
- Modificar archivos principales del sistema
- Ignorar mensajes de conflictos
- Descartar respaldos sin verificar

---

## 📞 **Soporte de Actualización**

### **Si encuentras problemas:**
1. **Revisar logs:** `logs/app.log`
2. **Ejecutar diagnóstico:** `check_system.bat`
3. **Reparar instalación:** `repair_installation.bat`
4. **Contactar soporte:** Issues en GitHub

### **Recursos:**
- **Repositorio**: https://github.com/ManangerIncidences/ExpressATM
- **Documentación**: README.md
- **Guía de instalación**: INSTALACION_EQUIPO.md
