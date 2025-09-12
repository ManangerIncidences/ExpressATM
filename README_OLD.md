"# ?? ExpressATM - Sistema de Monitoreo de Loter�as## ?? Descripci�nSistema automatizado de monitoreo para loter�as Express (CHANCE EXPRESS y RULETA EXPRESS) con an�lisis inteligente y alertas en tiempo real.## ? Caracter�sticas- ?? Monitoreo dual autom�tico (CHANCE y RULETA EXPRESS)- ?? Sistema de inteligencia artificial integrado- ?? Dashboard web interactivo- ?? An�lisis de tendencias y patrones- ?? Sistema de alertas autom�ticas- ?? Reportes en PDF- ?? Procesamiento en tiempo real## ??? Instalaci�n R�pida### Windows1. Descarga el proyecto2. Ejecuta \`install.bat\` (instalaci�n completa con entorno virtual)3. Ejecuta \`run.bat\` para iniciar### Instalaci�n Manual\`\`\`bash# Clonar repositoriogit clone https://github.com/tu-usuario/ExpressATM.gitcd ExpressATM# Instalar dependenciaspip install -r requirements.txt# Configurar variables de entornocp .env.example .env# Editar .env con tus credenciales# Iniciar aplicaci�npython run.py\`\`\`## ?? Acceso a la Aplicaci�n- **Panel Principal:** http://localhost:8000- **Dashboard:** http://localhost:8000/dashboard- **An�lisis IA:** http://localhost:8000/ai- **API Docs:** http://localhost:8000/docs## ?? Estructura del Proyecto\`\`\`ExpressATM/��� backend/          # API y l�gica de negocio��� frontend/         # Interfaz web��� install.bat       # Instalador Windows��� run.bat          # Ejecutor r�pido��� requirements.txt  # Dependencias Python��� README.md        # Este archivo\`\`\`## ?? Configuraci�n1. Edita el archivo \`.env\` con tus credenciales2. Ajusta \`backend/config.py\` seg�n tus necesidades3. Configura ChromeDriver para tu versi�n de Chrome## ?? Uso1. Ejecuta \`run.bat\` o \`python run.py\`2. Abre http://localhost:8000 en tu navegador3. El sistema comenzar� el monitoreo autom�tico## ?? Contribuir1. Fork el proyecto2. Crea una rama para tu feature3. Commit tus cambios4. Push a la rama5. Abre un Pull Request## ?? LicenciaMIT License - ver [LICENSE](LICENSE) para detalles## ?? SoporteSi encuentras problemas:1. Ejecuta \`start.bat\` para reinstalar dependencias2. Revisa los logs en la consola3. Crea un Issue en GitHub con detalles del error## 🗄️ Base de Datos Compartida (Uso Interno)

### 📊 Contenido de Base de Datos
- **`monitoring.db`**: Datos principales de monitoreo y alertas
- **`dom_intelligence.db`**: Datos de inteligencia DOM y patrones  
- **`vision_learning.db`**: Datos de aprendizaje visual y ML

### 🔄 Flujo de Trabajo para el Equipo

#### Para Nuevos Miembros:
```bash
# 1. Clonar repositorio
git clone https://github.com/ManangerIncidences/ExpressATM.git
cd ExpressATM

# 2. Instalar dependencias
install.bat

# 3. Ejecutar aplicación
run.bat
```

#### Para Uso Diario:
1. **Antes de trabajar**: `sync_data.bat` (obtener datos actualizados del equipo)
2. **Ejecutar aplicación**: `run.bat` 
3. **Después del trabajo**: `update_data.bat` (subir datos nuevos al equipo)

### 💡 Comandos Rápidos
```bash
# Sincronizar datos del equipo
git pull origin main

# Subir cambios de base de datos
git add *.db && git commit -m "Update DB $(date)" && git push
```

### 🔐 Configuración de Acceso
- **Repositorio**: `https://github.com/ManangerIncidences/ExpressATM`
- **Acceso**: Privado (solo miembros autorizados del equipo)
- **Sincronización**: Automática con scripts .bat incluidos

---? �Dale una estrella si te resulta �til!" 
