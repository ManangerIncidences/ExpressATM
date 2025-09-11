#!/bin/bash
# ExpressATM - Script de Instalación para Linux/macOS
# ===================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 ExpressATM - Instalación Linux/macOS${NC}"
echo -e "${BLUE}========================================${NC}"

# Verificar Python
echo -e "${BLUE}🐍 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 no encontrado. Por favor instala Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✅ Python $PYTHON_VERSION encontrado${NC}"

# Crear entorno virtual
echo -e "${BLUE}📦 Creando entorno virtual...${NC}"
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
echo -e "${BLUE}📥 Instalando dependencias...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Crear directorios
echo -e "${BLUE}📁 Creando directorios...${NC}"
mkdir -p logs drivers data frontend/logos

# Configurar .env
echo -e "${BLUE}⚙️ Configurando variables de entorno...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Archivo .env creado${NC}"
else
    echo -e "${YELLOW}⚠️ Archivo .env ya existe${NC}"
fi

# Configurar ChromeDriver según el sistema
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${BLUE}🌐 Configurando ChromeDriver para Linux...${NC}"
    echo -e "${YELLOW}💡 Ejecuta: sudo apt update && sudo apt install chromium-chromedriver${NC}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${BLUE}🌐 Configurando ChromeDriver para macOS...${NC}"
    if command -v brew &> /dev/null; then
        brew install chromedriver
        echo -e "${GREEN}✅ ChromeDriver instalado con Homebrew${NC}"
    else
        echo -e "${YELLOW}💡 Instala Homebrew y ejecuta: brew install chromedriver${NC}"
    fi
fi

# Inicializar base de datos
echo -e "${BLUE}🗄️ Inicializando base de datos...${NC}"
python3 -c "
import sys
sys.path.append('.')
from backend.app.database import engine
from backend.app.models import Base
Base.metadata.create_all(bind=engine)
print('✅ Base de datos inicializada')
" 2>/dev/null || echo -e "${YELLOW}⚠️ Base de datos se creará al primer uso${NC}"

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 ¡Instalación completada!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "${BLUE}📋 Próximos pasos:${NC}"
echo -e "${YELLOW}1. Activar entorno: source venv/bin/activate${NC}"
echo -e "${YELLOW}2. Ejecutar: python run.py${NC}"
echo -e "${YELLOW}3. Abrir: http://localhost:8000${NC}"
echo
echo -e "${BLUE}🔧 Configuración adicional:${NC}"
echo -e "${YELLOW}- Edita .env para personalizar configuración${NC}"
echo -e "${YELLOW}- Revisa DataAgencias.xlsx para configurar agencias${NC}"
echo
echo -e "${GREEN}¡Disfruta usando ExpressATM! 🎯${NC}"
