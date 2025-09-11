# ExpressATM - Información de Versión

VERSION = "2.2.0"
BUILD_DATE = "2025-09-11"
RELEASE_NOTES = {
    "2.2.0": [
        "🚀 Instalador universal - TODO en un solo script",
        "🎯 Inicio inteligente - detecta automáticamente qué necesitas",
        "🎛️ Centro de control unificado - menú con todas las opciones",
        "🌐 ChromeDriver mejorado - instalación automática robusta",
        "📋 Scripts simplificados - menos archivos, más funcionalidad"
    ],
    "2.1.0": [
        "✅ Corregidos errores de instalación en nuevas PCs",
        "🛠️ Agregados scripts de reparación automática",
        "🔍 Sistema de diagnóstico de problemas mejorado",
        "📚 Documentación actualizada con soluciones comunes",
        "🔄 Sistema de actualización automática implementado"
    ],
    "2.0.0": [
        "🧠 Sistema de inteligencia artificial integrado",
        "📊 Dashboard interactivo mejorado",
        "🔔 Sistema de alertas automáticas",
        "🎯 Monitoreo dual (CHANCE y RULETA EXPRESS)",
        "📈 Análisis de tendencias y patrones"
    ]
}

def get_version_info():
    """Retorna información completa de la versión actual"""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "release_notes": RELEASE_NOTES.get(VERSION, [])
    }

def print_version():
    """Imprime información de versión en consola"""
    print(f"ExpressATM v{VERSION} ({BUILD_DATE})")
    if VERSION in RELEASE_NOTES:
        print("\nNovedades de esta versión:")
        for note in RELEASE_NOTES[VERSION]:
            print(f"  {note}")
