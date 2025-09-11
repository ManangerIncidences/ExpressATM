# ExpressATM – Documentación Técnica Completa

## 1. Visión General
ExpressATM es un sistema de monitoreo y análisis en tiempo (casi) real de agencias de juego/lotería. Automatiza iteraciones de scraping/ingesta, persiste métricas operativas (ventas, premios, balance), detecta anomalías/gatillos de alerta y expone endpoints y una interfaz web para supervisión, exportes y análisis.

Arquitectura base:
- Frontend: HTML + Bootstrap 5 + JS (polling REST) – vistas `index.html`, `dashboard.html`, `ai.html`.
- Backend: FastAPI (Python) – API REST + orquestación de scraping y lógica de alertas.
- Persistencia: SQLite (archivos `monitoring.db`, `dom_intelligence.db`).
- Automatización / Scheduling: Scheduler híbrido (threads / APScheduler) para iteraciones periódicas y tareas de mantenimiento.
- Exports: CSV / Excel (openpyxl) / PDF (fpdf2) para alertas.
- Inteligencia DOM / aprendizaje: Módulo `dom_intelligence` registra interacciones y evalúa desempeño de selectores, con capacidad de optimización incremental.

## 2. Componentes Principales
### 2.1 Backend (carpeta `backend/app`)
- `main.py`: Inicialización FastAPI, inclusión de routers.
- `api/routes.py`: Endpoints de estadísticas, alertas, exportaciones, estado de inteligencia DOM y otros.
- `scraper.py`: Lógica de scraping / extracción (usa configuraciones específicas y observador de webdriver).
- `scheduler.py` / `scheduler_hybrid.py`: Planificación de iteraciones y tareas (limpieza, backoff, modo híbrido).
- `alerts.py`: Generación de alertas (tipos threshold, growth_variation, sustained_growth).
- `agency_matcher.py`: Resolución y normalización de agencias (usa `DataAgencias.xlsx`).
- `agency_behavior_analyzer.py`: Análisis histórico de comportamiento para inferencias.
- `intelligence.py`: Motor de consolidación y métricas globales (ventas, balance, variaciones).
- `dom_intelligence.py` + `dom_learning_engine.py`: Registro de interacciones, evaluación de elementos, aprendizaje y optimización de selectores.
- `web_driver_observer.py`: Observador para eventos del navegador / DOM.
- `models.py`: Definición de modelos SQLAlchemy (agencias, ventas, alertas, sesiones, logs).
- `database.py`: Sesión y manejo de conexión (SQLAlchemy / SQLite).
- `config.py`: Configuración base (DATABASE_URL, flags futuros, etc.).

### 2.2 Frontend (carpeta `frontend/`)
- `index.html`: Panel operativo (estado de monitoreo, alertas pendientes, actividad reciente, modales de detalle, exportaciones).
- `dashboard.html`: Visualizaciones agregadas / gráficas históricas (balance/ventas/agencias).
- `ai.html`: Vista de análisis avanzado / IA (interacción con dom_intelligence u otros modelos).
- `static/js/*.js`: Lógica de polling, renderizado de tablas, filtros, export trigger, UI feedback.
- `static/css/style.css`: Estilos personalizados.

### 2.3 Persistencia
- `monitoring.db`: Métricas operativas (ventas, premios, balance, alertas, sesiones, logs).
- `dom_intelligence.db`: Métricas y estados de aprendizaje de la capa DOM (rendimiento de selectores, interacciones, optimizaciones propuestas/aplicadas).

## 3. Modelo de Datos
Ver `models.py`.

Entidades clave:
- Agency(code, name)
- SalesRecord(agency_code, agency_name, sales, prizes, prizes_paid, balance, lottery_type, capture_day, iteration_time)
- Alert(alert_type, alert_message, lottery_type, current_sales, current_balance, previous_sales, growth_amount, is_reported, reported_at, alert_day)
- MonitoringSession(status, total_iterations, total_agencies_processed, total_alerts_generated)
- SystemLog(level, message, module, timestamp)

### 3.1 Relaciones Lógicas (implícitas)
- SalesRecord se agrupa por (agency_code, capture_day) para construir series intradía.
- Alert referencia la agencia y el contexto numérico que provocó su disparo; `is_reported` marca cierre manual / gestionado.
- MonitoringSession agrega métricas globales de ejecución de un día o ventana.

## 4. Flujo de Monitoreo
1. Scheduler dispara iteración.
2. Scraper obtiene datos de cada agencia (ventas, premios, premios pagados) para cada `lottery_type` (p.ej. CHANCE_EXPRESS, RULETA_EXPRESS).
3. Se calcula balance = ventas - premios_pagados (o fórmula específica definida en scraping si difiere). Se inserta `SalesRecord`.
4. Motor de alertas evalúa reglas:
   - threshold: supera umbral absoluto (ej. ventas > X, balance < Y, etc.).
   - growth_variation: cambio abrupto entre iteraciones (ventas actuales vs previas).
   - sustained_growth: crecimiento consecutivo durante N iteraciones.
5. Alertas generadas se registran en tabla `alerts` con snapshot de valores.
6. Frontend realiza polling para mostrar alertas pendientes y métricas agregadas.
7. Usuario puede marcar reportadas (is_reported=True, reported_at=timestamp).

## 5. Cálculo de Métricas
- Ventas (sales): Valor bruto obtenido del origen (scraping / API externa).
- Premios (prizes) y Premios Pagados (prizes_paid): Provienen de la misma fuente; pueden alimentar análisis de payout.
- Balance: Generalmente Ventas - Premios Pagados (confirmar en scraper). En exportes se formatea con separador miles punto y signo antes si negativo ("-$ 123.456").
- Crecimiento (growth_amount): sales_actual - sales_previa.
- Variación de crecimiento (growth_variation): Puede normalizarse comparando contra media móvil o simplemente delta absoluta; en el modelo se guarda growth_amount; la clasificación de tipo growth_variation depende de lógica en `alerts.py`.
- Alertas sostenidas (sustained_growth): Condición de crecimiento repetido N veces; se evalúa secuencia de deltas positivos para la misma agencia.
- Hora Reportada: Extraída de `reported_at` si existe; caso contrario 'null' en exportes.

## 6. Exportaciones de Alertas
Endpoint (en `routes.py`) soporta formato: csv | excel | pdf.
- Columnas actuales: Hora, Agencia, Sorteo (lottery_type), Tipo, Ventas, Balance, Hora Reportada.
- Mapeos de Tipo: sustained_growth -> "Crec. Sostenido"; growth_variation -> "Var. Crecimiento"; threshold -> "Umbral".
- PDF: fpdf2, anchos calibrados, truncación segura con '...' ASCII, reemplazo de caracteres no Latin-1.
- Excel: openpyxl, estilos (bordes, encabezados grises, negativo en rojo, formato monetario "$ #,##0").
- CSV: Orden de campos consistente y sin formato adicional.

## 7. Inteligencia DOM
- Registra interacciones de elementos (selectores) durante scraping o navegación automatizada.
- Evalúa performance: tiempos, errores, estabilidad de selectores.
- Genera optimizaciones (p.ej. cambiar XPATH por CSS más estable) basadas en heurísticas.
- Persistencia en `dom_intelligence.db` para histórico y aprendizaje incremental.
- Endpoints de estado / reportes en `routes.py` (consultas agregadas, anomalías, performance por selector).

## 8. Scheduler Híbrido
- Combina un loop propio + APScheduler para granularidad fina y resiliencia.
- Control de intervalos configurables (frontend puede exponer ajustes).
- Modo manual: trigger directo desde UI (botón "Ejecutar Manual").
- Estado expuesto en `monitoring-state` y `next-run-countdown` en frontend.

## 9. Manejo de Errores y Logs
- `SystemLog` captura eventos (INFO/WARNING/ERROR) con módulo origen.
- Excepciones críticas se reflejan en `MonitoringSession.status`.
- Logs en archivo `logs/app.log` para auditoría (rotación futura recomendada).

## 10. Consideraciones de Rendimiento
- SQLite: Adecuado para volumen moderado. Para escalado migrar a Postgres/MySQL (ajustar `DATABASE_URL`).
- Indexes: Campos clave ya indexados (agency_code, alert_day, capture_day, lottery_type). Revisar consultas en endpoints críticos para añadir índices compuestos si crece el volumen.
- Límite PDF: Top N (800) filas para prevenir PDFs gigantes (ajustable).

## 11. Seguridad / Hardening
- CORS: Configurar según dominio productivo (no descrito aquí – revisar `main.py`).
- Autenticación: No implementada (pendiente) – para producción añadir OAuth2 API key o JWT.
- Sanitización PDF: Reemplazo de caracteres no mapeables evita errores de codificación.

## 12. Extensibilidad
- Añadir nuevos tipos de alerta: Extender enumeración en `alerts.py` + mapear a etiquetas en exportes.
- Métricas derivadas: Crear campos calculados (ej. payout ratio = premios_pagados / ventas).
- Integrar un bus de eventos: Publicar alertas a un canal (Kafka / Redis) para consumo externo.

## 13. Variables de Entorno Propuestas
| Variable | Uso | Default |
|----------|-----|---------|
| EXPRESSATM_DB_URL | Override DB principal | sqlite:///./monitoring.db |
| EXPRESSATM_DOM_DB | Ruta DB dom_intelligence | dom_intelligence.db |
| EXPRESSATM_INTERVAL_MIN | Minutos entre iteraciones | 15 |
| EXPRESSATM_MAX_PDF_ROWS | Límite filas export PDF | 800 |

(Implementar lectura en `config.py` para completar la parametrización.)

## 14. Procedimiento de Despliegue (Resumido)
1. Crear entorno virtual.
2. `pip install -r requirements.txt`.
3. Ejecutar migración/creación de tablas (al iniciar la app se crean si no existen).
4. Iniciar: `python run.py` o `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`.
5. Acceder a UI: http://localhost:8000 (según configuración de montaje estático).

## 15. Pruebas / QA (Situación Actual)
- No hay suite formal activa (scripts de robustez antiguos removidos). Recomendado introducir PyTest para validar:
  - Generación de alerta para cada tipo con data sintética.
  - Exportes (cabeceras, conteo filas, encoding PDF).
  - Scheduler: intervalo y ejecución manual.

## 16. Riesgos Actuales
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Falta de auth | Acceso no controlado | Añadir auth antes de exponer públicamente |
| SQLite locking | Demoras bajo concurrencia | Migrar a Postgres para alto volumen |
| Sin límites de retención | Crecimiento indefinido DB | Tarea de purga histórica (cron) |
| Exportes grandes | Memoria/tiempo PDF | Límite configurable y paginación |
| Dependencia DataAgencias.xlsx | Falla si falta archivo | Migrar a tabla Agencies o seed inicial |

## 17. Roadmap Sugerido
- Autenticación + roles.
- Métricas avanzadas (payout ratio, variabilidad intradía).
- API para marcar alertas masivamente.
- Dashboard de tendencias históricas multi-día.
- Integración mensajería externa (Telegram/Email) para alertas críticas.
- Batch ETL nocturno para agregados históricos.

## 18. Estilo de Código / Contribución
- PEP8 salvo optimizaciones locales.
- Usar tipado gradual (añadir hints en módulos críticos).
- Centralizar formatos monetarios y de fecha en utilidades comunes.
- Commits pequeños y descriptivos (Convención: feat:, fix:, refactor:, docs:, chore:).

## 19. Troubleshooting Rápido
| Síntoma | Posible Causa | Acción |
|---------|---------------|--------|
| PDF 500 | Caracter no Latin-1 | Revisar sanitización / truncación |
| Export Excel vacío | Filtro fecha sin datos | Verificar rango o logs |
| Alertas no incrementan | Scheduler detenido | Revisar estado sesión/logs |
| Balance negativo inesperado | Premios mal parseados | Inspeccionar scraper / fuente |

## 20. Licenciamiento / Propiedad
(Completar según políticas internas; actualmente no definido en repo.)

---
Esta documentación debe mantenerse sincronizada con cambios estructurales (nuevas columnas, endpoints o motores de aprendizaje).
