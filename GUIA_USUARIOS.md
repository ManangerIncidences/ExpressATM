# Guía de Usuario – ExpressATM

Bienvenido a ExpressATM. Esta guía explica, en un lenguaje no técnico, qué hace el sistema, de dónde salen los números que ves y cómo usar cada parte de la interfaz.

---
## 1. ¿Qué es ExpressATM?
Es una herramienta que observa periódicamente (cada cierto número de minutos) la actividad de las agencias de juego/lotería y te muestra:
- Ventas acumuladas
- Premios y pagos de premios
- Balance (resultado económico)
- Alertas cuando algo se sale de lo normal

También te permite exportar reportes (CSV, Excel, PDF) de las alertas para análisis o envío a otras áreas.

---
## 2. ¿De dónde salen los datos?
El sistema realiza “iteraciones” automáticas (consultas) a las fuentes de información de cada agencia. Cada iteración guarda una foto de:
- Ventas hasta ese momento
- Premios generados
- Premios pagados
- Tipo de juego/lotería (por ejemplo: CHANCE_EXPRESS o RULETA_EXPRESS)

Con esas fotos se construyen las tablas y gráficos. Si algo crece muy rápido o supera un umbral definido, se genera una alerta.

---
## 3. Conceptos Clave
- Iteración: Una pasada de recolección de datos para todas las agencias.
- Venta: Monto total vendido acumulado hasta la hora de la iteración.
- Premios Pagados: Lo que ya se pagó a ganadores.
- Balance: Ventas menos Premios Pagados. (Si es negativo, se resalta en rojo.)
- Alerta: Aviso de situación fuera de lo habitual. Tipos principales:
  - Umbral: Se superó un límite predefinido.
  - Var. Crecimiento: Cambio fuerte frente a la iteración anterior.
  - Crec. Sostenido: Aumentos consecutivos durante varias iteraciones.
- Reportar una alerta: Marcarla como gestionada (ya atendida) para que deje de aparecer como pendiente.

---
## 4. Pantalla Principal (Panel)
Elementos principales en la parte superior:
- Estado del Monitoreo: Activo o Detenido.
- Agencias Monitoreadas: Número total de agencias en seguimiento (puedes hacer clic para ver el detalle).
- Alertas Pendientes: Cuántas necesitan atención.
- Alertas Reportadas: Cuántas ya se marcaron como gestionadas hoy.

Botones:
- Iniciar Monitoreo: Arranca las iteraciones automáticas.
- Detener Monitoreo: Pausa el proceso.
- Ejecutar Manual: Fuerza una nueva iteración en ese momento.
- Exportar Incidencias: Abre opciones para descargar un reporte de alertas.
- Ajustes: (Si está habilitado) Configura parámetros avanzados.
- Actualizar: Refresca la vista inmediatamente.

---
## 5. Tabla de Alertas Pendientes
Columnas típicas:
- Agencia: Nombre de la agencia.
- Tipo de Alerta: Umbral / Var. Crecimiento / Crec. Sostenido.
- Mensaje: Explica el motivo.
- Ventas Actuales / Balance Actual: Valores en el momento de la alerta.
- Fecha/Hora: Cuándo se detectó.
- Acciones: Botones para marcar como “Reportada” u otras acciones disponibles.

Si no hay alertas, verás un mensaje de felicitación.

Filtro: Puedes filtrar por tipo de alerta con el menú desplegable.

---
## 6. Actividad Reciente
Una tabla compacta que muestra para las últimas iteraciones:
- Agencia
- Ventas
- Balance
- Hora de la iteración
Sirve para ver rápidamente cómo están evolucionando las cifras.

---
## 7. Modales / Ventanas Emergentes
- Todas las Agencias: Lista completa de agencias supervisadas.
- Detalles de Agencia: Información más profunda de una agencia (evolución intradía, variaciones, etc.).
- Tendencia Global: Gráfico de las métricas en el día (Ventas, Balance y otros si se activan).
- Movimientos del Día: Tabla completa de cada iteración con columnas como Hora, Ventas, Δ (cambio) de Ventas, Balance, Δ Balance, Premios, Premios Pagados y Lotería.

Δ significa “diferencia respecto a la iteración anterior”.

---
## 8. Exportar Alertas
Al pulsar “Exportar Incidencias” puedes elegir formato:
- CSV: Texto simple, útil para abrir en casi cualquier programa.
- Excel: Formato con colores, columnas ajustadas y números formateados.
- PDF: Documento listo para compartir o imprimir.

Columnas del reporte (pueden variar ligeramente según evolución):
- Hora: Hora de la alerta.
- Agencia: Nombre.
- Sorteo: Tipo de juego (CHANCE_EXPRESS, RULETA_EXPRESS, etc.).
- Tipo: Clase de alerta (en español).
- Ventas: Monto en el momento.
- Balance: Monto en el momento (negativo en rojo en PDF/Excel).
- Hora Reportada: Hora en que se marcó como atendida (o null si no se ha reportado).

Rango de Fechas: Si eliges un intervalo, el reporte solo incluirá alertas de esos días.

---
## 9. Cómo Interpretar las Alertas
- Umbral ("Umbral"): Señala que una métrica pasó un valor límite (por ejemplo, ventas demasiado altas o balance muy bajo).
- Var. Crecimiento ("Var. Crecimiento"): Indica un salto brusco comparado con la iteración previa.
- Crec. Sostenido ("Crec. Sostenido"): Muestra un crecimiento continuo en varias iteraciones consecutivas.

Prioriza primero alertas con gran impacto (por ejemplo balance muy negativo o crecimientos inusualmente altos).

---
## 10. Buenas Prácticas de Uso
- Revisa el panel al iniciar el día y antes de cerrar la jornada.
- Marca las alertas una vez hayas verificado su causa (para mantener el panel limpio).
- Exporta reportes a PDF para enviar resúmenes diarios.
- Usa el filtro de tipo de alerta para enfocarte en un problema específico.

---
## 11. Preguntas Frecuentes (FAQ)
1. ¿Por qué una alerta sigue apareciendo? → Aún no la has marcado como reportada.
2. ¿Por qué el balance está en rojo? → El resultado es negativo (más pagos que ventas o estructura definida así).
3. ¿Puedo cambiar el intervalo de monitoreo? → Sí, a través de Ajustes (si tu rol lo permite) o pidiendo al administrador.
4. ¿Por qué algunas agencias no muestran datos nuevos? → Puede que no haya cambios desde la última iteración o la fuente no devolvió datos (revisar logs si persiste).
5. ¿Qué pasa si cierro el navegador? → El monitoreo sigue en el servidor; al volver verás el estado actualizado.

---
## 12. Errores Comunes
- PDF no se descarga: Conexión interrumpida o no hay datos en el rango. Intenta sin filtro.
- Excel abre sin formato: Usar una versión moderna de Excel o LibreOffice.
- Números muy grandes: Utiliza exportes para análisis detallado o considera segmentar por fechas.

---
## 13. Seguridad / Acceso
Actualmente el sistema puede no requerir inicio de sesión (según configuración). Si se añade autenticación, necesitarás credenciales para acceder. No compartas reportes sensibles sin autorización interna.

---
## 14. Próximas Mejoras (Plan)
- Notificaciones por email/Telegram para alertas críticas.
- Métricas históricas multi-día.
- Indicadores adicionales (porcentaje de pago, desviaciones vs promedio histórico).
- Roles de usuario (operador, analista, administrador).

---
## 15. Glosario Rápido
| Término | Significado |
|--------|-------------|
| Iteración | Recolección de datos en un momento dado |
| Δ (Delta) | Diferencia respecto a la iteración anterior |
| Balance | Ventas - Premios Pagados |
| Alertar | Generar aviso por condición especial |
| Reportar (alerta) | Marcar como gestionada |
| Sorteo | Tipo de juego monitoreado |

---
## 16. Soporte
Si encuentras un comportamiento extraño o datos que no cuadran:
1. Refresca la página.
2. Intenta una nueva iteración manual.
3. Revisa si hay alertas recientes relacionadas.
4. Contacta al responsable técnico con hora y detalle del problema.

---
¡Gracias por usar ExpressATM! Esta guía se actualizará a medida que el sistema evolucione.
