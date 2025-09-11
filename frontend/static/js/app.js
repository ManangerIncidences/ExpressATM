// Sistema de Monitoreo de Loterías - Frontend JavaScript

class MonitoringApp {
    constructor() {
        this.apiBase = '/api/v1';
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
        this.currentAlerts = [];
    // ==== Resumen de cambios de iteración ====
    this._lastAlertsSnapshot = new Map(); // agency_code -> snapshot
    this._iterationChangesBuffer = [];     // Cambios acumulados mientras la pestaña está oculta o hasta mostrar
    this._pendingIterationCount = 0;       // Iteraciones con cambios acumuladas
    this._lastIterationModalShownAt = 0;   // Timestamp de último modal mostrado
    this._iterationModalOpen = false;      // Estado de apertura del modal
    this.iterationModalCooldownMs = 10000; // Tiempo mínimo entre auto-shows
    this._baselineInitialized = false;     // Control de baseline inicial
    this.iterationAutoShowGraceMs = 20000;  // Gracia tras reload/navegación para no re-mostrar inmediatamente
    this._lastIterationPushAt = 0;          // Control de push notifications
    this._iterationSound = null;            // Objeto Audio
    this._iterationSoundReady = false;
    this._defaultIterationSoundSrc = '/sounds/Sonido 1.m4a';
    this._customIterationSoundB64 = null;   // Base64 almacenado
    // Web Audio API
    this._audioCtx = null;
    this._iterationAudioBuffer = null;
    this._audioSrcSignature = null; // para saber si hay que volver a decodificar
    this._audioUnlockDone = false;
    this._suspendIterationDetectionUntil = 0; // ventana temporal para ignorar cambios tras acciones locales (report)
    // Scraping progress
    this._progressPollTimer = null;
    this._progressActive = false;
    this._lastProgressData = null;
    this._progressPollIntervalMs = 900; // intervalo más rápido para el feedback visual del progreso
    this._progressDisplayedPct = 0; // porcentaje animado mostrado
    this._progressAnimTarget = 0;
    this._progressAnimRaf = null;
    this._progressStepExpected = { // estimaciones (segundos) para animación interna
        login: 18,
        navigate: 10,
        base_filters: 12,
        chance: 20,
        ruleta: 20,
        data_ready: 4,
        generate_alerts: 8
    };
    this._lastPersistProgress = null;
    this._forceProgressReset = false;
        this.sortState = { column: null, direction: 'asc' };
    // Arrancar polling continuo para detectar nuevas iteraciones
    setTimeout(()=>{ try{ this.startProgressPolling(false); }catch(e){} }, 400);
    // Inicializar estado persistido de último progreso (si reciente)
    this._initPersistedProgress();
        // Mostrar modal cuando el usuario regresa a la pestaña
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.settings?.autoShowIterationSummary && this._iterationChangesBuffer.length) {
                if (!this._iterationModalOpen && Date.now() - this._lastIterationModalShownAt > this.iterationModalCooldownMs) {
                    this.showIterationChangesModal();
                }
            }
        });
        // Cargar snapshot persistido si existe
        try {
            const savedSnap = localStorage.getItem('iterationSnapshot');
            if (savedSnap) {
                const obj = JSON.parse(savedSnap);
                if (obj && obj.agencies) {
                    Object.entries(obj.agencies).forEach(([code,val])=>{
                        this._lastAlertsSnapshot.set(code, val);
                    });
                    this._baselineInitialized = true;
                }
            }
            const storedShownAt = localStorage.getItem('iterationLastShownAt');
            if (storedShownAt) {
                this._lastIterationModalShownAt = parseInt(storedShownAt) || 0;
            }
        } catch(_) {}
        this.settings = this.loadSettings();
    this.ensureNotificationPermission();
        this.nextRunTime = null;           // Fecha ISO de próxima ejecución
        this.countdownInterval = null;     // Intervalo para actualizar cuenta regresiva
        this.countdownRefreshLock = false; // Evitar múltiples fetch al llegar a 0
        this.lastImmediateRefreshAt = 0;   // Anti-rebote para refresh inmediato
        this.lastIterationCount = null;    // Conteo de iteraciones conocido
        this.postZeroRefreshTimers = [];   // IDs de timeouts para refrescos tras 00:00
    // Tendencia global (sparkline)
    this.globalTrend = { labels: [], sales: [], balance: [], bets: [] };
    this._globalSpark = null;
    this._globalChart = null;
        
        this.init();
    this._visibilityReturnAt = 0; // timestamp de regreso de pestaña
    this._lastGlobalSalesSum = null; // para validar cambio real
    this._lastGlobalBalanceSum = null;
        // Preparar audio si está habilitado
        if (this.settings?.enableIterationSound) {
            // Inicialización temprana para que cargue en background
            setTimeout(()=> this.initIterationSound(), 50);
            // Desbloqueo por primera interacción del usuario (política autoplay)
            this._audioUnlockHandler = () => { this.unlockIterationAudio(); };
            document.addEventListener('click', this._audioUnlockHandler, { once: true });
        }
    }

    init() {
        this.applySavedTheme();
        this.setupEventListeners();
    this.setupModalStacking();
        this.loadInitialData();
        this.startAutoRefresh();
        this.startCountdown();           // Iniciar actualización de cuenta regresiva
        // Listeners de ciclo de vida de la página
        document.addEventListener('visibilitychange', () => this.onVisibilityChanged());
        window.addEventListener('focus', () => this.onFocus());
        window.addEventListener('pageshow', () => this.onFocus());
        window.addEventListener('online', () => this.onOnline());
        window.addEventListener('offline', () => this.onOffline());
    }

    onVisibilityChanged() {
        const visible = !document.hidden;
        this.autoRefreshEnabled = visible;
        if (visible) {
            this._visibilityReturnAt = Date.now();
            const now = Date.now();
            if (now - this.lastImmediateRefreshAt > 1500) {
                this.lastImmediateRefreshAt = now;
                // Refresco inmediato al volver a la pestaña
                this.refreshData();
            }
            // Reiniciar contador por si fue pausado
            this.startCountdown();
            // Reanudar auto-refresh
            this.startAutoRefresh();
        } else {
            // Pausar intervalos para ahorrar recursos
            this.stopAutoRefresh();
        }
    }

    onFocus() {
        // En algunos navegadores visibilitychange no dispara; asegurar refresh al enfocar
        const now = Date.now();
        if (now - this.lastImmediateRefreshAt > 1500) {
            this.lastImmediateRefreshAt = now;
            this.refreshData();
        }
    }

    onOnline() {
        this.showNotification('Conexión restablecida, actualizando…', 'info');
        this.refreshData();
    }

    onOffline() {
        this.showNotification('Sin conexión. Mostrando últimos datos en caché.', 'error');
    }

    applySavedTheme() {
        const saved = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', saved === 'dark' ? 'dark' : 'light');
        this.updateThemeToggleIcon();
    }

    // Helper: ¿tema oscuro activo?
    isDarkTheme() {
        return document.documentElement.getAttribute('data-theme') === 'dark';
    }

    // Ajustar colores de ejes/retícula en gráficos cuando cambia el tema
    updateChartsTheme() {
        if (this._dayChart) {
            const dark = this.isDarkTheme();
            if (this._dayChart.options && this._dayChart.options.scales) {
                const scales = this._dayChart.options.scales;
                if (scales.x && scales.x.ticks) scales.x.ticks.color = dark ? '#e5e7eb' : '#374151';
                if (scales.y && scales.y.ticks) scales.y.ticks.color = dark ? '#e5e7eb' : '#374151';
                if (scales.y && scales.y.grid) scales.y.grid.color = dark ? '#2a2f34' : '#e5e7eb';
            }
            try { this._dayChart.update(); } catch (_) {}
        }
        if (this._globalChart) {
            const dark = this.isDarkTheme();
            if (this._globalChart.options && this._globalChart.options.scales) {
                const scales = this._globalChart.options.scales;
                if (scales.x && scales.x.ticks) scales.x.ticks.color = dark ? '#e5e7eb' : '#374151';
                if (scales.y && scales.y.ticks) scales.y.ticks.color = dark ? '#e5e7eb' : '#374151';
                if (scales.y && scales.y.grid) scales.y.grid.color = dark ? '#2a2f34' : '#e5e7eb';
            }
            try { this._globalChart.update(); } catch (_) {}
        }
        if (this._globalSpark) {
            try { this._globalSpark.update('none'); } catch (_) {}
        }
    }

    setupEventListeners() {
        // Botón de tema
        const themeBtn = document.getElementById('theme-toggle');
        if (themeBtn) themeBtn.addEventListener('click', () => this.toggleTheme());
        
        // Botones de control
        const startBtn = document.getElementById('start-monitoring');
        if (startBtn) startBtn.addEventListener('click', () => this.startMonitoring());
        const stopBtn = document.getElementById('stop-monitoring');
        if (stopBtn) stopBtn.addEventListener('click', () => this.stopMonitoring());
        const manualBtn = document.getElementById('manual-iteration');
        if (manualBtn) manualBtn.addEventListener('click', () => this.executeManualIteration());
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.refreshData());
    // Botón ajustes (faltaba binding)
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) settingsBtn.addEventListener('click', (e) => { e.preventDefault(); this.showSettings(); });

        // 🧠 Controles de Inteligencia Artificial (solo si existen en la vista)
        const toggleIA = document.getElementById('toggle-intelligence');
        if (toggleIA) toggleIA.addEventListener('click', () => this.toggleIntelligence());
        const refreshIA = document.getElementById('refresh-intelligence');
        if (refreshIA) refreshIA.addEventListener('click', () => this.refreshIntelligenceData());

        // Filtros
        const alertFilter = document.getElementById('alert-type-filter');
        if (alertFilter) alertFilter.addEventListener('change', () => this.loadAlerts());

        // Modal de confirmación
        const confirmBtn = document.getElementById('confirm-action');
        if (confirmBtn) confirmBtn.addEventListener('click', () => this.executeConfirmedAction());

        // KPI clickeable - Agencias Monitoreadas (toda la tarjeta)
        const agenciesCard = document.getElementById('agencies-card');
        if (agenciesCard) {
            agenciesCard.addEventListener('click', () => this.showAllAgencies());
        }

        // KPI clickeable - Alertas Reportadas (listar agencias reportadas hoy)
        const reportedAlertsCard = document.getElementById('reported-alerts-card');
        if (reportedAlertsCard) {
            reportedAlertsCard.addEventListener('click', () => this.showReportedAgencies());
        }

        // KPI clickeable - Optimización AI (solo en ai.html)
        const optimizationsCard = document.getElementById('optimizations-card');
        if (optimizationsCard) {
            optimizationsCard.addEventListener('click', () => this.showOptimizationsRecommendations());
        }
        const soundFile = document.getElementById('iteration-sound-file');
        if (soundFile) {
            soundFile.addEventListener('change', (e)=>{
                const file = e.target.files?.[0];
                if (file) this.handleIterationSoundFile(file);
            });
        }
        // Exportar incidencias
        const exportBtn = document.getElementById('export-incidents-btn');
        if(exportBtn){
            exportBtn.addEventListener('click', ()=>{
                const modalEl = document.getElementById('exportIncidentsModal');
                if(!modalEl) return; new bootstrap.Modal(modalEl).show();
            });
        }
        const runExport = document.getElementById('export-incidents-run');
        if(runExport){
            runExport.addEventListener('click', ()=> this.runIncidentsExport());
        }
    }

    // Manejo de stacking (z-index) para múltiples modales Bootstrap
    setupModalStacking() {
        const baseModalZ = 1050;
        document.addEventListener('shown.bs.modal', (e) => {
            const openModals = document.querySelectorAll('.modal.show').length;
            const step = 10;
            const zIndex = baseModalZ + (openModals * step);
            const modalEl = e.target;
            if (modalEl && modalEl.classList) {
                modalEl.style.zIndex = zIndex;
                modalEl.classList.add('modal-stacked');
            }
            setTimeout(() => {
                const backdrops = document.querySelectorAll('.modal-backdrop');
                const backdrop = backdrops[backdrops.length - 1];
                if (backdrop) {
                    backdrop.style.zIndex = zIndex - 1;
                    backdrop.classList.add('modal-backdrop-stacked');
                    backdrop.style.opacity = String(Math.min(0.85, 0.5 + openModals * 0.12));
                }
            }, 0);
        });
        document.addEventListener('hidden.bs.modal', (e) => {
            const modalEl = e.target;
            if (modalEl && modalEl.classList && modalEl.classList.contains('modal-stacked')) {
                modalEl.style.zIndex = '';
                modalEl.classList.remove('modal-stacked');
            }
            // Mantener scroll lock si quedan modales
            const anyOpen = document.querySelectorAll('.modal.show').length > 0;
            if (anyOpen) {
                document.body.classList.add('modal-open');
            } else {
                // Limpiar overlay/backdrops residuales
                document.body.classList.remove('modal-open');
                document.querySelectorAll('.modal-backdrop').forEach(b=> b.remove());
                // Restaurar estilos inline añadidos por bootstrap
                document.body.style.removeProperty('padding-right');
            }
        });
    }

    async loadInitialData(manual=false) {
        const tasks = [
            this.loadDashboardData(),
            this.loadAlerts(),
            this.updateMonitoringStatus()
        ];
        await Promise.allSettled(tasks);
        if (document.getElementById('globalTrendSparkline')) {
            this.updateGlobalTrendFromDashboard();
            this.renderGlobalSparkline();
        }
        if (manual) this.showNotification('Datos actualizados', 'info');
    }

    async loadDashboardData() {
        try {
            const response = await fetch(`${this.apiBase}/dashboard`);
            const data = await response.json();

            this.updateDashboardStats(data);
            this.updateRecentActivity(data.latest_activity);
            this.updateAlertsSummary(data.alerts_summary);
            // Detectar cambios de iteración tras actualizar dataset principal
            this.detectIterationChanges(data);

        } catch (error) {
            console.error('Error cargando datos del dashboard:', error);
            this.showNotification('Error cargando datos del dashboard', 'error');
        }
    }

    updateDashboardStats(data) {
        // Actualizar estadísticas (sólo si existen en la vista actual)
        const totalAgenciesEl = document.getElementById('total-agencies');
        const pendingAlertsEl = document.getElementById('pending-alerts');
        const reportedAlertsEl = document.getElementById('reported-alerts');
        const statusElement = document.getElementById('monitoring-state');

        if (totalAgenciesEl) totalAgenciesEl.textContent = data.agencies_summary.total_monitored_today;
        if (pendingAlertsEl) pendingAlertsEl.textContent = data.alerts_summary.pending;
        if (reportedAlertsEl) reportedAlertsEl.textContent = data.alerts_summary.reported;

    if (statusElement) {
            const isRunning = data.monitoring_status.is_running;
            statusElement.textContent = isRunning ? 'Activo' : 'Detenido';
            statusElement.className = `badge ${isRunning ? 'bg-success' : 'bg-secondary'}`;
        }
    // Guardar snapshot para tendencia global
    this._lastDashboardData = data;
    }

    // ====== Iteration Change Detection (strict) ======
    detectIterationChanges(dashboardData) {
        if (!dashboardData) { console.debug('[detectIterationChanges] sin dashboardData'); return; }
        // Si estamos en ventana de suspensión por acciones locales y hay un flag pendiente, programar detección diferida
        if (Date.now() < this._suspendIterationDetectionUntil) {
            if (this._iterationIncrementFlag) {
                const delay = this._suspendIterationDetectionUntil - Date.now() + 80;
                if (!this._deferredIterationTimeout) {
                    console.debug('[detectIterationChanges] suspensión activa, programando detección diferida en', delay, 'ms');
                    this._deferredIterationTimeout = setTimeout(()=>{
                        this._deferredIterationTimeout = null;
                        console.debug('[detectIterationChanges] ejecutando detección diferida tras suspensión');
                        this.detectIterationChanges(this._lastDashboardData || dashboardData);
                    }, Math.max(delay, 80));
                }
            } else {
                console.debug('[detectIterationChanges] suspendido (sin flag) hasta', new Date(this._suspendIterationDetectionUntil).toLocaleTimeString());
            }
            return; // acciones locales
        }
        const activity = dashboardData.latest_activity || [];
        const now = Date.now();
        const pendingAlertsByAgency = (this.currentAlerts||[]).filter(a=>!a.reported_at).reduce((acc,a)=>{(acc[a.agency_code]||(acc[a.agency_code]=[])).push(a);return acc;},{});
        const currentSnapshot = new Map();
        activity.forEach(r=>{
            currentSnapshot.set(r.agency_code,{sales:r.sales||0,balance:r.balance||0,alertsCount:(pendingAlertsByAgency[r.agency_code]||[]).length,ts:now,agency_name:r.agency_name});
        });
        if (!this._baselineInitialized && this._lastAlertsSnapshot.size===0) {
            this._lastAlertsSnapshot = currentSnapshot; this._baselineInitialized = true; this._persistIterationSnapshot(); console.debug('[detectIterationChanges] baseline inicializada'); return;
        }
        if (!this._iterationIncrementFlag) { console.debug('[detectIterationChanges] sin flag de iteración, skip'); return; }
        this._iterationIncrementFlag = false; // consume
        console.debug('[detectIterationChanges] flag consumido, procesando diffs actividad', activity.length, 'agencias snapshot prev', this._lastAlertsSnapshot.size);
        const changes=[]; const newAlertAgencies=[];
        currentSnapshot.forEach((curr,code)=>{
            const prev=this._lastAlertsSnapshot.get(code);
            if (prev){
                const dS=curr.sales-prev.sales; const dB=curr.balance-prev.balance; const dA=curr.alertsCount-prev.alertsCount;
                if (dS!==0||dB!==0||dA!==0){
                    changes.push({agency_code:code,agency_name:curr.agency_name||prev.agency_name,deltaSales:dS,deltaBalance:dB,sales:curr.sales,balance:curr.balance,deltaAlerts:dA,alertsCount:curr.alertsCount,lastChangeAgoMs:now-prev.ts});
                }
            } else if (curr.alertsCount>0){
                newAlertAgencies.push({agency_code:code,agency_name:curr.agency_name,sales:curr.sales,balance:curr.balance,alertsCount:curr.alertsCount});
            }
        });
        this._lastAlertsSnapshot=currentSnapshot; this._persistIterationSnapshot();
    if(!changes.length && !newAlertAgencies.length) { console.debug('[detectIterationChanges] sin cambios detectables'); return; }
        const signatureBase = changes.map(c=>c.agency_code+':'+c.deltaSales+':'+c.deltaBalance+':'+c.deltaAlerts).join('|')+'|'+newAlertAgencies.map(n=>n.agency_code).join(',');
        const sig = signatureBase?this.simpleHash(signatureBase):null; if(sig && this._lastIterationSignature===sig) return; this._lastIterationSignature=sig;
    this._iterationChangesBuffer.push({at:now,changes,newAgencies:newAlertAgencies}); this._pendingIterationCount++;
    console.debug('[detectIterationChanges] cambios registrados batches=', this._iterationChangesBuffer.length, 'agencias con cambios', changes.length, 'nuevas alertas', newAlertAgencies.length);
        this.maybePlayIterationSound(); this.maybeSendIterationPush(changes,newAlertAgencies,now);
        if(this.settings?.autoShowIterationSummary && !document.hidden && !this._iterationModalOpen){ if(Date.now()-this._lastIterationModalShownAt>this.iterationModalCooldownMs){ this.showIterationChangesModal(); } }
    }

        showIterationChangesModal() {
                if (!this._iterationChangesBuffer.length) return;
                const modalEl = document.getElementById('iterationChangesModal');
                if (!modalEl) return;
                if (this._iterationModalOpen) return; // evitar doble
                const container = document.getElementById('iterationChangesContainer');
                const iterCountEl = document.getElementById('ic-iterations-count');
                const agenciesCountEl = document.getElementById('ic-agencies-count');
                const newAgenciesCountEl = document.getElementById('ic-new-agencies-count');
                const lastUpdatedEl = document.getElementById('ic-last-updated');

                // Agregación acumulada
                const aggregate = new Map();
                let totalNew = 0;
        this._iterationChangesBuffer.forEach(batch => {
            batch.changes.forEach(ch => {
                const prev = aggregate.get(ch.agency_code) || { agency_code: ch.agency_code, agency_name: ch.agency_name, deltaSales:0, deltaBalance:0, sales: ch.sales, balance: ch.balance, deltaAlerts:0, alertsCount: ch.alertsCount, lastChangeAgoMs: ch.lastChangeAgoMs };
                prev.agency_name = ch.agency_name || prev.agency_name;
                prev.deltaSales += ch.deltaSales;
                prev.deltaBalance += ch.deltaBalance;
                prev.deltaAlerts += ch.deltaAlerts;
                prev.sales = ch.sales; prev.balance = ch.balance; prev.alertsCount = ch.alertsCount; prev.lastChangeAgoMs = ch.lastChangeAgoMs;
                aggregate.set(ch.agency_code, prev);
            });
                        if (batch.newAgencies.length) totalNew += batch.newAgencies.length;
                });

                let rows = Array.from(aggregate.values()).sort((a,b)=> Math.abs(b.deltaSales) - Math.abs(a.deltaSales));
                // Filtrar: variación ventas != 0 OR variación alertas != 0 (para mostrar nuevas alertas)
                const filteredRows = rows.filter(r => r.deltaSales !== 0 || (r.deltaAlerts && r.deltaAlerts !== 0));
                const usingRows = filteredRows.length ? filteredRows : [];
                const fmtMoney = v => new Intl.NumberFormat('es-DO',{style:'currency',currency:'DOP'}).format(v||0);
                const fmtDelta = v => (v>0?'+':'') + v.toLocaleString('es-DO');
                const fmtAgo = ms => { if(ms==null)return'--'; const s=Math.floor(ms/1000); if(s<60)return s+'s'; const m=Math.floor(s/60); if(m<60)return m+'m'; return Math.floor(m/60)+'h'; };

                container.innerHTML = `
                    <div class="table-responsive">
                        <table class="table table-sm align-middle iteration-summary-table">
                            <thead class="${this.isDarkTheme() ? 'table-dark' : 'table-light'}">
                                <tr>
                                    <th>Agencia</th><th class="text-end">Δ Ventas</th><th class="text-end">Ventas</th><th class="text-end">Δ Balance</th><th class="text-end">Balance</th><th class="text-center">Alertas</th><th class="text-center">Δ Alertas</th><th class="text-center">Último Cambio</th><th></th>
                                </tr>
                            </thead>
                            <tbody>
                                ${usingRows.length ? usingRows.map(r=>`<tr>
                                    <td style="max-width:360px;">
                                        <div class="fw-bold text-truncate" title="${r.agency_code} | ${(r.agency_name||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')}">
                                            ${r.agency_code} | ${(r.agency_name||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
                                        </div>
                                    </td>
                                    <td class="text-end ${r.deltaSales>0?'text-success':(r.deltaSales<0?'text-danger':'text-muted')}">${fmtDelta(r.deltaSales)}</td>
                                    <td class="text-end">${fmtMoney(r.sales)}</td>
                                    <td class="text-end ${r.deltaBalance>0?'text-success':(r.deltaBalance<0?'text-danger':'text-muted')}">${fmtDelta(r.deltaBalance)}</td>
                                    <td class="text-end">${fmtMoney(r.balance)}</td>
                                    <td class="text-center">${r.alertsCount}</td>
                                    <td class="text-center">${r.deltaAlerts?fmtDelta(r.deltaAlerts):'-'}</td>
                                    <td class="text-center">${fmtAgo(r.lastChangeAgoMs)}</td>
                                    <td class="text-end"><button class="btn btn-sm btn-outline-primary" onclick="app.showAgencyDetails('${r.agency_code}')"><i class='fas fa-chart-line'></i></button></td>
                                </tr>`).join('') : '<tr><td colspan="9" class="text-center text-muted">Sin cambios de ventas en las iteraciones acumuladas</td></tr>'}
                            </tbody>
                        </table>
                    </div>`;

                iterCountEl.textContent = this._pendingIterationCount;
                agenciesCountEl.textContent = usingRows.length;
                newAgenciesCountEl.textContent = totalNew;
                const mostRecent = this._iterationChangesBuffer[this._iterationChangesBuffer.length-1]?.at;
                if (mostRecent) lastUpdatedEl.textContent = 'Hace ' + fmtAgo(Date.now() - mostRecent);

                // Checkbox persistente
                const autoChk = document.getElementById('auto-show-iteration-summary');
                if (autoChk) {
                        autoChk.checked = !!this.settings.autoShowIterationSummary;
                        autoChk.onchange = () => {
                                this.settings.autoShowIterationSummary = autoChk.checked;
                                localStorage.setItem('monitoringSettings', JSON.stringify(this.settings));
                        };
                }

                const modal = new bootstrap.Modal(modalEl);
                modal.show();
                this._iterationModalOpen = true;
                modalEl.addEventListener('hidden.bs.modal', () => { this._iterationModalOpen = false; }, { once: true });
                // limpiar buffer tras mostrar
                this._iterationChangesBuffer = [];
                this._pendingIterationCount = 0;
                this._lastIterationModalShownAt = Date.now();
                try { localStorage.setItem('iterationLastShownAt', String(this._lastIterationModalShownAt)); } catch(_) {}
        }

    updateRecentActivity(activities) {
        const table = document.getElementById('recent-activity-table');
        const tbody = table ? table.querySelector('tbody') : null;
        if (!tbody) return;
        
        tbody.innerHTML = '';

        activities.forEach(activity => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="agency-name" title="${activity.agency_name}">
                        ${activity.agency_code}
                    </div>
                    <small class="text-muted">${this.truncateText(activity.agency_name, 30)}</small>
                </td>
                <td class="${this.getMoneyClass(activity.sales)}">
                    ${this.formatMoney(activity.sales)}
                </td>
                <td class="${this.getMoneyClass(activity.balance)}">
                    ${this.formatMoney(activity.balance)}
                </td>
                <td class="time-ago">
                    ${this.formatTimeAgo(activity.time)}
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    // Construir serie global desde el dashboard
    updateGlobalTrendFromDashboard() {
    if (!this._lastDashboardData) return;
    if (!this.globalTrend || !this.globalTrend.labels) return; // estructura aún no lista
        const latest = this._lastDashboardData.latest_activity || [];
        // Etiqueta temporal actual
        const label = new Date().toLocaleTimeString('es-DO');
        // Agregados globales
        const sumSales = latest.reduce((a, r) => a + (r.sales || 0), 0);
        const sumBalance = latest.reduce((a, r) => a + (r.balance || 0), 0);

        // Evitar duplicación superflua sin cambios
        const lastIdx = this.globalTrend.labels.length - 1;
        if (lastIdx >= 0) {
            const sameLabel = this.globalTrend.labels[lastIdx] === label;
            const sameVals = this.globalTrend.sales[lastIdx] === sumSales && this.globalTrend.balance[lastIdx] === sumBalance;
            if (sameLabel && sameVals) return;
        }

        this.globalTrend.labels.push(label);
        this.globalTrend.sales.push(sumSales);
        this.globalTrend.balance.push(sumBalance);
        // Apuestas = Δ ventas global
        const prevSales = lastIdx >= 0 ? this.globalTrend.sales[lastIdx] : sumSales;
        this.globalTrend.bets.push(sumSales - prevSales);

        // Cap de puntos
        const cap = 200;
        ['labels','sales','balance','bets'].forEach(k => {
            if (this.globalTrend[k].length > cap) {
                this.globalTrend[k] = this.globalTrend[k].slice(-cap);
            }
        });

    const upd = document.getElementById('global-trend-updated');
    const stamp = `Actualizado: ${new Date().toLocaleTimeString('es-DO')}`;
    if (upd) upd.textContent = stamp;
    const upd2 = document.getElementById('global-trend-modal-updated');
    if (upd2) upd2.textContent = stamp;
    }

    _persistIterationSnapshot() {
        try {
            const obj = { agencies: {} };
            this._lastAlertsSnapshot.forEach((v,k)=>{ obj.agencies[k]=v; });
            localStorage.setItem('iterationSnapshot', JSON.stringify(obj));
        } catch(_) {}
    }

    ensureNotificationPermission() {
        if (!('Notification' in window)) return;
        if (!this.settings?.enableIterationPush) return;
        if (Notification.permission === 'default') {
            try { Notification.requestPermission(); } catch(_) {}
        }
    }

    maybeSendIterationPush(changes, newAlertAgencies, nowTs) {
        if (!this.settings?.enableIterationPush) return;
        if (!('Notification' in window)) return;
        if (Notification.permission !== 'granted') return;
        if (nowTs - this._lastIterationPushAt < 3000) return;
        const agenciesChanged = changes.length; // considerar cualquier cambio (ventas, balance o alertas +/-)
        if (agenciesChanged === 0 && newAlertAgencies.length === 0) {
            console.debug('[maybeSendIterationPush] no hay cambios relevantes para push');
            return;
        }
        const title = 'Iteración completada';
        const body = `${agenciesChanged} con cambios • ${newAlertAgencies.length} nuevas en alerta`;
        try {
            const n = new Notification(title, { body, icon: '/favicon.ico', badge: '/favicon.ico', tag: 'iter-summary', renotify: true, timestamp: nowTs });
            n.onclick = () => { window.focus(); try { this.showIterationChangesModal(); } catch(_) {} };
            this._lastIterationPushAt = nowTs;
        } catch(_) {}
    }

    // ==================== SONIDO DE ITERACIÓN ====================
    initIterationSound() {
        try {
            const audioEl = document.getElementById('iteration-audio');
            if (!audioEl) return;
            // Intentar cargar personalizado almacenado
            const saved = localStorage.getItem('iterationSoundCustom');
            if (saved) {
                audioEl.src = saved; // data URL
                this._customIterationSoundB64 = saved;
            } else {
                audioEl.src = this._defaultIterationSoundSrc;
            }
            audioEl.oncanplaythrough = () => { this._iterationSoundReady = true; };
            this._iterationSound = audioEl;
            // Preparar buffer Web Audio si ya está desbloqueado
            if (this._audioUnlockDone) {
                this.prepareIterationAudioBuffer();
            }
            // Si alguna iteración quiso sonar antes de estar listo
            if (this._pendingSoundPlayRequest) {
                this._pendingSoundPlayRequest = false;
                this.maybePlayIterationSound();
            }
        } catch(_) {}
    }

    maybePlayIterationSound() {
        if (!this.settings?.enableIterationSound) return;
        if (!this._iterationSound) this.initIterationSound();
    if (!this._iterationSoundReady) { this._pendingSoundPlayRequest = true; return; }
        // Intentar con Web Audio primero (más resiliente en background si ya hubo interacción)
        if (this._audioCtx && this._iterationAudioBuffer) {
            try {
                if (this._audioCtx.state === 'suspended') { this._audioCtx.resume().catch(()=>{}); }
                const src = this._audioCtx.createBufferSource();
                src.buffer = this._iterationAudioBuffer;
                src.connect(this._audioCtx.destination);
                src.start(0);
                return;
            } catch(_) {}
        }
        // Fallback al elemento audio clásico
        try {
            const playPromise = this._iterationSound.cloneNode(true).play();
            if (playPromise && typeof playPromise.then === 'function') {
                playPromise.catch(()=>{});
            }
        } catch(_) {}
    }

    handleIterationSoundFile(file) {
        if (!file) return;
        if (file.size > 1024 * 1024 * 2) { // 2MB cap
            this.showNotification('Archivo de audio demasiado grande (max 2MB)', 'warning');
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const dataUrl = e.target.result;
                localStorage.setItem('iterationSoundCustom', dataUrl);
                this._customIterationSoundB64 = dataUrl;
                const audioEl = document.getElementById('iteration-audio');
                if (audioEl) {
                    audioEl.src = dataUrl;
                    this._iterationSoundReady = false;
                    audioEl.oncanplaythrough = () => { this._iterationSoundReady = true; this.showNotification('Sonido personalizado cargado', 'success'); };
                }
            } catch(err) {
                this.showNotification('Error procesando audio', 'error');
            }
        };
        reader.readAsDataURL(file);
    }

    clearCustomIterationSound() {
        try { localStorage.removeItem('iterationSoundCustom'); } catch(_) {}
        const audioEl = document.getElementById('iteration-audio');
        if (audioEl) {
            audioEl.src = this._defaultIterationSoundSrc;
            this._iterationSoundReady = false;
            audioEl.oncanplaythrough = () => { this._iterationSoundReady = true; this.showNotification('Sonido por defecto restaurado', 'info'); if (this._audioUnlockDone) this.prepareIterationAudioBuffer(); };
        }
        this._customIterationSoundB64 = null;
    }

    unlockIterationAudio() {
        if (!this.settings?.enableIterationSound) return;
        if (!this._iterationSound) this.initIterationSound();
        const el = this._iterationSound;
        if (!el) return;
        try {
            el.muted = true;
            const p = el.play();
            if (p && typeof p.then === 'function') {
                p.then(()=>{ el.pause(); el.currentTime = 0; el.muted = false; this._audioUnlockDone = true; this.ensureAudioContext(); });
            } else {
                el.pause(); el.currentTime=0; el.muted=false; this._audioUnlockDone = true; this.ensureAudioContext();
            }
        } catch(_) {}
    }

    ensureAudioContext() {
        if (!this._audioCtx) {
            try { this._audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch(_) { return; }
        }
        if (this._audioCtx && this._audioCtx.state === 'suspended') {
            this._audioCtx.resume().catch(()=>{});
        }
        this.prepareIterationAudioBuffer();
    }

    prepareIterationAudioBuffer() {
        try {
            if (!this._audioCtx) return;
            const audioEl = this._iterationSound;
            if (!audioEl || !audioEl.src) return;
            const currentSig = audioEl.src;
            if (this._audioSrcSignature === currentSig && this._iterationAudioBuffer) return; // ya listo
            // Decodificar
            if (currentSig.startsWith('data:')) {
                const base64 = currentSig.split(',')[1];
                const binary = atob(base64);
                const len = binary.length;
                const bytes = new Uint8Array(len);
                for (let i=0;i<len;i++) bytes[i] = binary.charCodeAt(i);
                this._audioCtx.decodeAudioData(bytes.buffer.slice(0), (buf)=>{ this._iterationAudioBuffer = buf; this._audioSrcSignature = currentSig; }, ()=>{});
            } else {
                fetch(currentSig).then(r=>r.arrayBuffer()).then(ab=>{
                    this._audioCtx.decodeAudioData(ab, (buf)=>{ this._iterationAudioBuffer = buf; this._audioSrcSignature = currentSig; }, ()=>{});
                }).catch(()=>{});
            }
        } catch(_) {}
    }

    // Renderiza el sparkline global compacto
    renderGlobalSparkline() {
        const canvas = document.getElementById('globalTrendSparkline');
        if (!canvas) return;
        // Si ya existe, actualizar
        if (this._globalSpark) {
            try {
                this._globalSpark.data.labels = this.globalTrend.labels;
                this._globalSpark.data.datasets[0].data = this.globalTrend.sales;
                this._globalSpark.data.datasets[1].data = this.globalTrend.balance;
                this._globalSpark.data.datasets[2].data = this.globalTrend.bets;
                this._globalSpark.update('none');
                return;
            } catch(e) { console.debug('Spark update failed', e); }
        }

        this._globalSpark = new Chart(canvas, {
            type: 'line',
            data: {
                labels: this.globalTrend.labels,
                datasets: [
                    { label: 'Ventas', data: this.globalTrend.sales, borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,.12)', tension: .25, pointRadius: 0, fill: true },
                    { label: 'Balance', data: this.globalTrend.balance, borderColor: '#60a5fa', backgroundColor: 'rgba(96,165,250,.12)', tension: .25, pointRadius: 0, fill: true, hidden: true },
                    { label: 'Apuestas (Δ)', data: this.globalTrend.bets, borderColor: '#f6ad55', backgroundColor: 'rgba(246,173,85,.12)', tension: .25, pointRadius: 0, fill: true, hidden: true }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: { legend: { display: false }, decimation: { enabled: true, algorithm: 'lttb', samples: 60 } },
                scales: { x: { display: false }, y: { display: false } }
            }
        });

        // Toggles
        const s = document.getElementById('globalSeriesSales');
        const b = document.getElementById('globalSeriesBalance');
        const p = document.getElementById('globalSeriesBets');
        const apply = () => {
            if (!this._globalSpark) return;
            this._globalSpark.data.datasets[0].hidden = !(s && s.checked);
            this._globalSpark.data.datasets[1].hidden = !(b && b.checked);
            this._globalSpark.data.datasets[2].hidden = !(p && p.checked);
            this._globalSpark.update('none');
        };
        if (s) s.onchange = apply; if (b) b.onchange = apply; if (p) p.onchange = apply;

        // Expandir a modal
        const expandBtn = document.getElementById('global-trend-expand');
        if (expandBtn) expandBtn.onclick = () => this.showGlobalTrendModal();
    }

    showGlobalTrendModal() {
        const modalEl = document.getElementById('globalTrendModal');
        const bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();

        const canvas = document.getElementById('globalTrendChart');
        if (this._globalChart) { try { this._globalChart.destroy(); } catch(_){} }
        this._globalChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: this.globalTrend.labels,
                datasets: [
                    { label: 'Ventas', data: this.globalTrend.sales, borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,.15)', tension: .25, pointRadius: 2, fill: true },
                    { label: 'Balance', data: this.globalTrend.balance, borderColor: '#60a5fa', backgroundColor: 'rgba(96,165,250,.15)', tension: .25, pointRadius: 2, fill: true, hidden: true },
                    { label: 'Apuestas (Δ)', data: this.globalTrend.bets, borderColor: '#f6ad55', backgroundColor: 'rgba(246,173,85,.15)', tension: .25, pointRadius: 2, fill: true, hidden: true }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: this.isDarkTheme() ? '#e5e7eb' : '#374151' } },
                    y: { ticks: { color: this.isDarkTheme() ? '#e5e7eb' : '#374151' }, grid: { color: this.isDarkTheme() ? '#2a2f34' : '#e5e7eb' } }
                }
            }
        });

        // Toggle modal
        const s = document.getElementById('globalModalSeriesSales');
        const b = document.getElementById('globalModalSeriesBalance');
        const p = document.getElementById('globalModalSeriesBets');
        const apply = () => {
            if (!this._globalChart) return;
            this._globalChart.data.datasets[0].hidden = !(s && s.checked);
            this._globalChart.data.datasets[1].hidden = !(b && b.checked);
            this._globalChart.data.datasets[2].hidden = !(p && p.checked);
            this._globalChart.update();
        };
        if (s) s.onchange = apply; if (b) b.onchange = apply; if (p) p.onchange = apply;

        // Resize/update al mostrar
        const onShown = () => { try { this._globalChart.resize(); this._globalChart.update(); } catch(_){} };
        modalEl.addEventListener('shown.bs.modal', onShown, { once: true });
        modalEl.addEventListener('hidden.bs.modal', () => { try { this._globalChart.destroy(); } catch(_){} this._globalChart = null; }, { once: true });
    }

    updateAlertsSummary(alertsSummary) {
        const container = document.getElementById('alerts-summary');
        if (!container) return;
        
        const alertTypes = {
            'threshold': 'Por Umbral',
            'growth_variation': 'Crecimiento',
            'sustained_growth': 'Crecimiento Sostenido'
        };

        let html = `
            <div class="mb-3">
                <h6>Total de Alertas Hoy</h6>
                <h4 class="text-primary">${alertsSummary.total_today}</h4>
            </div>
        `;

        if (Object.keys(alertsSummary.by_type).length > 0) {
            html += '<h6>Por Tipo:</h6>';
            for (const [type, count] of Object.entries(alertsSummary.by_type)) {
                const typeName = alertTypes[type] || type;
                html += `
                    <div class="d-flex justify-content-between mb-2">
                        <span class="badge alert-type-${type} alert-type-badge">${typeName}</span>
                        <strong>${count}</strong>
                    </div>
                `;
            }
        } else {
            html += '<p class="text-muted">No hay alertas por tipo</p>';
        }

        container.innerHTML = html;
    }

    async loadAlerts() {
        try {
            const filterEl = document.getElementById('alert-type-filter');
            const alertType = filterEl ? filterEl.value : '';
            // cache-busting para evitar respuestas obsoletas que reintroduzcan filas ya reportadas
            // Control de secuencia: ignorar respuestas viejas si llegan tarde
            if (typeof this._alertsFetchSeq === 'undefined') {
                this._alertsFetchSeq = 0;
                this._alertsFetchApplied = -1;
            }
            const seq = ++this._alertsFetchSeq;
            let url = `${this.apiBase}/alerts?reported=false&_ts=${Date.now()}`;
            
            if (alertType) {
                url += `&alert_type=${alertType}`;
            }

            const response = await fetch(url);
            let alerts = await response.json();

            // Si llega una respuesta obsoleta (seq < último aplicado) se descarta silenciosamente
            if (seq < this._alertsFetchApplied) {
                console.debug('[loadAlerts] respuesta obsoleta descartada seq', seq, '<', this._alertsFetchApplied);
                return;
            }

            // Filtrar agencias en proceso de reporte o recién reportadas para evitar “rebote” visual
            if (this._reportingAgencies && this._reportingAgencies.size) {
                alerts = alerts.filter(a => !this._reportingAgencies.has(a.agency_code));
            }
            if (this._recentlyReportedAgencies && this._recentlyReportedAgencies.size) {
                alerts = alerts.filter(a => !this._recentlyReportedAgencies.has(a.agency_code));
            }

            this.currentAlerts = alerts;
            this.renderAlertsTable(alerts);
            this._alertsFetchApplied = seq;
            console.debug('[loadAlerts] aplicado seq', seq, 'alertas', alerts.length);

        } catch (error) {
            console.error('Error cargando alertas:', error);
            this.showNotification('Error cargando alertas', 'error');
        }
    }

    renderAlertsTable(alerts) {
        const tableEl = document.getElementById('alerts-table');
        const tbody = tableEl ? tableEl.querySelector('tbody') : null;
        const noAlertsDiv = document.getElementById('no-alerts');
        if (!tableEl || !tbody || !noAlertsDiv) {
            // Vista actual no contiene la tabla de alertas
            return;
        }
    // Conservar IDs previos para distinguir filas realmente nuevas
    const previousIds = new Set(Array.from(tbody.querySelectorAll('tr[data-agid]')).map(tr=>tr.getAttribute('data-agid')));
    tbody.innerHTML = '';

        if (alerts.length === 0) {
            tableEl.style.display = 'none';
            noAlertsDiv.classList.remove('d-none');
            return;
        }

        tableEl.style.display = 'table';
        noAlertsDiv.classList.add('d-none');

        // Agrupar alertas por agencia
        const groupedAlerts = this.groupAlertsByAgency(alerts);

        groupedAlerts.forEach(group => {
            const row = document.createElement('tr');
            row.dataset.agid = group.agency_code;
            if (!previousIds.has(group.agency_code)) {
                row.classList.add('new-alert'); // sólo agencias nuevas en el set de alertas
            }
            const reporting = (this._reportingAgencies && this._reportingAgencies.has(group.agency_code));
            const btnDisabledAttr = reporting ? 'disabled' : '';
            const btnExtraClass = reporting ? ' btn-reporting' : '';
            const btnLabel = reporting ? '<span class="reporting-inline-spinner"><span class="spinner-border spinner-border-sm" role="status"></span><span>Reportando...</span></span>' : '<i class="fas fa-check"></i> Reportar';
            
            // ✨ NUEVO: Crear etiquetas de tipos de lotería
            const lotteryBadges = group.lottery_types.map(type => {
                const displayName = type === 'CHANCE_EXPRESS' ? 'CHANCE' : 
                                 type === 'RULETA_EXPRESS' ? 'RULETA' : type;
                const badgeClass = type === 'CHANCE_EXPRESS' ? 'bg-primary' : 
                                 type === 'RULETA_EXPRESS' ? 'bg-danger' : 'bg-secondary';
                return `<span class="badge ${badgeClass} me-1 mb-1">
                    🎯 ${displayName}
                </span>`;
            }).join('');
            
            // Crear etiquetas de tipos de alerta
            const alertBadges = group.alert_types.map(type => 
                `<span class="badge alert-type-${type} alert-type-badge me-1 mb-1">
                    ${this.getAlertTypeName(type)}
                </span>`
            ).join('');

            // Crear mensajes formateados y legibles
            const formattedMessages = this.formatAlertMessages(group.messages, group.alert_types);

            row.innerHTML = `
                <td>
                    <div class="agency-name" title="${group.agency_name}">
                        ${group.agency_name}
                    </div>
                </td>
                <td>
                    <div class="lottery-badges mb-1">
                        ${lotteryBadges}
                    </div>
                    <div class="alert-badges">
                        ${alertBadges}
                    </div>
                </td>
                <td>
                    <div class="alert-messages-container">
                        ${formattedMessages}
                    </div>
                </td>
                <td class="${this.getMoneyClass(group.current_sales)}">
                    ${this.formatMoney(group.current_sales)}
                </td>
                <td class="${this.getMoneyClass(group.current_balance)}">
                    ${this.formatMoney(group.current_balance)}
                </td>
                <td class="time-ago">
                    ${this.formatTimeAgo(group.latest_alert_date)}
                </td>
                <td>
                    <button class="btn btn-success btn-action${btnExtraClass}" ${btnDisabledAttr} onclick="app.reportMultipleAlerts('${group.agency_code}')" title="Reportar todas las alertas de la agencia">
                        ${btnLabel}
                    </button>
                    <button class="btn btn-info btn-action ms-1" onclick="app.showAgencyDetails('${group.agency_code}')" title="Detalles de la agencia">
                        <i class="fas fa-info-circle"></i> Detalles
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    groupAlertsByAgency(alerts) {
        const grouped = {};
        
        alerts.forEach(alert => {
            const key = alert.agency_code;
            
            if (!grouped[key]) {
                grouped[key] = {
                    agency_code: alert.agency_code,
                    agency_name: alert.agency_name,
                    alert_types: [],
                    lottery_types: [],
                    messages: [],
                    current_sales: alert.current_sales,
                    current_balance: alert.current_balance,
                    latest_alert_date: alert.alert_date,
                    alert_ids: []
                };
            }
            
            // Agregar tipo de alerta si no existe
            if (!grouped[key].alert_types.includes(alert.alert_type)) {
                grouped[key].alert_types.push(alert.alert_type);
            }
            
            // Agregar tipo de lotería si no existe
            if (alert.lottery_type && !grouped[key].lottery_types.includes(alert.lottery_type)) {
                grouped[key].lottery_types.push(alert.lottery_type);
            }
            
            // Agregar mensaje si no existe
            if (!grouped[key].messages.includes(alert.alert_message)) {
                grouped[key].messages.push(alert.alert_message);
            }
            
            // Mantener la fecha más reciente
            if (new Date(alert.alert_date) > new Date(grouped[key].latest_alert_date)) {
                grouped[key].latest_alert_date = alert.alert_date;
            }
            
            // Agregar ID de alerta
            grouped[key].alert_ids.push(alert.id);
        });
        
        return Object.values(grouped);
    }

    async softRefresh() {
        // Refresco sin toasts ni estados de botones
        await Promise.allSettled([
            this.loadDashboardData(),
            this.loadAlerts(),
            this.updateMonitoringStatus()
        ]);
    }

    async updateMonitoringStatus() {
        try {
            const response = await fetch(`${this.apiBase}/monitoring/status`);
            const status = await response.json();

            // Actualizar indicador y botones con el contexto correcto
            this.updateStatusIndicator(status.is_running);
            this.updateControlButtons(status.is_running);
            // Capturar tiempo de próxima ejecución
            if (status.next_run_time) {
                this.nextRunTime = new Date(status.next_run_time);
            } else {
                this.nextRunTime = null;
            }
            
            // Detectar fin de iteración: total_iterations aumentó
            if (typeof status.total_iterations === 'number') {
                if (this.lastIterationCount === null) {
                    this.lastIterationCount = status.total_iterations;
                    console.debug('[updateMonitoringStatus] inicializando contador iteraciones =', status.total_iterations);
                } else if (status.total_iterations > this.lastIterationCount) {
                    this.lastIterationCount = status.total_iterations;
                    // Marcar incremento para el siguiente ciclo de detectIterationChanges
                    this._iterationIncrementFlag = true;
                    console.debug('[updateMonitoringStatus] incremento de iteración detectado total=', status.total_iterations);
                    // Refrescar datos inmediatamente tras concluir una iteración
                    await Promise.allSettled([
                        this.loadDashboardData(),
                        this.loadAlerts()
                    ]);
                    // Fallback: si después de 400ms el flag sigue activo (no procesado por suspensión) reintentar dashboard
                    setTimeout(()=>{ 
                        if (this._iterationIncrementFlag) { 
                            console.debug('[updateMonitoringStatus] fallback reintento loadDashboardData() por flag aún activo');
                            this.loadDashboardData(); 
                        }
                    }, 450);
                    // Segundo fallback tras ventana de suspensión típica (2.5s)
                    setTimeout(()=>{ 
                        if (this._iterationIncrementFlag) { 
                            console.debug('[updateMonitoringStatus] segundo fallback post-suspensión, reintento');
                            this.loadDashboardData(); 
                        }
                    }, 2600);
                }
            }

            // Actualizar cuenta regresiva
            this.updateCountdown();

        } catch (error) {
            console.error('Error actualizando estado del monitoreo:', error);
            this.updateStatusIndicator(false, true);
        }
    }

    simpleHash(str) {
        let h = 0, i = 0, len = str.length;
        while (i < len) {
            h = (h << 5) - h + str.charCodeAt(i++) | 0;
        }
        return h;
    }
    
    // Método para actualizar el indicador de estado del monitoreo
    updateStatusIndicator = (isRunning, hasError = false) => {
        const statusElement = document.getElementById('monitoring-state');
        if (!statusElement) return;
        
        if (hasError) {
            statusElement.textContent = 'Error';
            statusElement.className = 'badge bg-danger';
        } else {
            statusElement.textContent = isRunning ? 'Activo' : 'Detenido';
            statusElement.className = `badge ${isRunning ? 'bg-success' : 'bg-secondary'}`;
        }
    }
    
    // Método para actualizar los botones de control del monitoreo
    updateControlButtons = (isRunning) => {
        const startButton = document.getElementById('start-monitoring');
        const stopButton = document.getElementById('stop-monitoring');
        const manualButton = document.getElementById('manual-iteration');
        
        if (startButton) startButton.disabled = isRunning;
        if (stopButton) stopButton.disabled = !isRunning;
        if (manualButton) manualButton.disabled = isRunning;
    }

    startCountdown = () => {
        // Iniciar intervalo para actualizar cuenta regresiva cada segundo
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
        this.countdownInterval = setInterval(() => this.updateCountdown(), 1000);
    }
    
    updateCountdown = () => {
        const el = document.getElementById('next-run-countdown');
        if (!el) return;
        if (this.nextRunTime) {
            const now = new Date();
            let diffSec = Math.floor((this.nextRunTime - now) / 1000);
            if (diffSec < 0) diffSec = 0;
            const hours = Math.floor(diffSec / 3600);
            const minutes = Math.floor((diffSec % 3600) / 60);
            const seconds = diffSec % 60;
            let str = '';
            if (hours > 0) {
                str += String(hours).padStart(2, '0') + ':';
            }
            str += String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
            el.textContent = `Próxima iteración: ${str}`;

            // Si llega a 00:00, forzar actualización de estado/datos con pequeños reintentos
            if (diffSec === 0 && !this.countdownRefreshLock) {
                this.countdownRefreshLock = true;
                // Cancelar timers anteriores si existían
                this.postZeroRefreshTimers.forEach(id => clearTimeout(id));
                this.postZeroRefreshTimers = [];
                // Refresco inmediato silencioso
                this.softRefresh();
                // Reintentos a 2s y 5s para capturar persistencias tardías
                this.postZeroRefreshTimers.push(setTimeout(() => this.softRefresh(), 2000));
                this.postZeroRefreshTimers.push(setTimeout(() => {
                    this.softRefresh();
                    // liberar lock tras el último intento
                    this.countdownRefreshLock = false;
                }, 5000));
            }
        } else {
            el.textContent = 'Próxima iteración: --:--';
        }
    }

    async startMonitoring() {
        try {
            this.setButtonLoading('start-monitoring', true);
            
            const response = await fetch(`${this.apiBase}/monitoring/start`, {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('Monitoreo iniciado correctamente', 'success');
                await this.updateMonitoringStatus();
            } else {
                const error = await response.json();
                this.showNotification(`Error: ${error.detail}`, 'error');
            }

        } catch (error) {
            console.error('Error iniciando monitoreo:', error);
            this.showNotification('Error iniciando monitoreo', 'error');
        } finally {
            this.setButtonLoading('start-monitoring', false);
        }
    }

    async stopMonitoring() {
        try {
            this.setButtonLoading('stop-monitoring', true);
            
            const response = await fetch(`${this.apiBase}/monitoring/stop`, {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('Monitoreo detenido correctamente', 'success');
                await this.updateMonitoringStatus();
            } else {
                const error = await response.json();
                this.showNotification(`Error: ${error.detail}`, 'error');
            }

        } catch (error) {
            console.error('Error deteniendo monitoreo:', error);
            this.showNotification('Error deteniendo monitoreo', 'error');
        } finally {
            this.setButtonLoading('stop-monitoring', false);
        }
    }

    async executeManualIteration() {
        try {
            this.setButtonLoading('manual-iteration', true);
            // Iniciar visualización de progreso inmediatamente
            this.startProgressPolling(true);
            
            const response = await fetch(`${this.apiBase}/monitoring/manual-iteration`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok) {
                this.showNotification(
                    `Iteración completada: ${result.agencies_processed} agencias, ${result.alerts_generated} alertas`, 
                    'success'
                );
                console.debug('[executeManualIteration] completada -> updateMonitoringStatus primero');
                await this.updateMonitoringStatus();
                if (!this._iterationIncrementFlag) {
                    console.debug('[executeManualIteration] flag no marcado inmediatamente, programando fallback');
                    setTimeout(()=>{
                        if (!this._iterationIncrementFlag) {
                            console.debug('[executeManualIteration] fallback fuerza flag + dashboard');
                            this._iterationIncrementFlag = true;
                            this.loadDashboardData();
                        }
                    }, 650);
                }
                // Carga paralela (puede disparar detectIterationChanges si flag activo)
                await Promise.allSettled([
                    this.loadDashboardData(),
                    this.loadAlerts()
                ]);
            } else {
                this.showNotification(`Error: ${result.error}`, 'error');
            }

        } catch (error) {
            console.error('Error ejecutando iteración manual:', error);
            this.showNotification('Error ejecutando iteración manual', 'error');
        } finally {
            this.setButtonLoading('manual-iteration', false);
        }
    }

    /* =============================
       Scraping Progress (Polling)
       ============================= */
    startProgressPolling(forceShow=false){
        if(forceShow){ this.showProgressBubble(); }
        if(this._progressPollTimer) return; // ya corriendo
    const poll = async ()=>{
            try {
        const res = await fetch(`${this.apiBase}/monitoring/progress`, { cache:'no-store', headers:{'Cache-Control':'no-cache'} });
                if(!res.ok) throw new Error('HTTP '+res.status);
                const data = await res.json();
                // Si la versión no cambió pero la iteración sigue activa, actualizar igual (para avanzar fracción temporal)
                if(this._lastProgressData && data.version !== undefined && this._lastProgressData.version === data.version){
                    if(data.active){
                        this.renderProgressUI(data);
                    }
                } else {
                // Detectar nueva iteración (cambio de started_at o transición inactivo->activo)
                const prev = this._lastProgressData;
                const newRun = data.active && (!prev || !prev.active || (prev.started_at && data.started_at && prev.started_at !== data.started_at));
                if(newRun){
                    this._resetProgressAnimation();
                }
                this._lastProgressData = data;
                this.renderProgressUI(data);
                }
                if(data.active){
                    if(!this._progressActive){ this._progressActive = true; this.showProgressBubble(); }
                } else {
                    if(this._progressActive){
                        this._progressActive = false; // mantener polling para detectar próxima iteración
                        this.renderProgressUI(data);
                        this._scheduleProgressBubbleAutoHide();
                        this._persistProgressState(100, data);
                    }
                }
            } catch(err){
                // Silencioso; reintento siguiente tick
            }
        };
        poll();
        this._progressPollTimer = setInterval(poll, this._progressPollIntervalMs);
    }

    stopProgressPolling(){
        if(this._progressPollTimer){ clearInterval(this._progressPollTimer); this._progressPollTimer=null; }
    }

    showProgressBubble(){
        const bubble = document.getElementById('scraping-progress-bubble');
        if(!bubble) return;
        bubble.classList.remove('d-none');
        if(!bubble._bound){
            bubble.addEventListener('click', ()=>{
                this.openProgressModal();
            });
            bubble._bound = true;
        }
        const closeBtn = document.getElementById('sp-bubble-close');
        if(closeBtn && !closeBtn._bound){
            closeBtn.addEventListener('click',(e)=>{ e.stopPropagation(); this.hideProgressBubble(); });
            closeBtn._bound = true;
        }
    }

    hideProgressBubble(){
        const bubble=document.getElementById('scraping-progress-bubble');
        if(bubble) bubble.classList.add('d-none');
    }

    openProgressModal(){
        const modalEl = document.getElementById('scrapingProgressModal');
        if(!modalEl) return;
        const bsModal = new bootstrap.Modal(modalEl,{backdrop:'static'});
        bsModal.show();
        // Si no hay iteración activa, forzar fetch inmediato para mostrar estado "completado".
        if(!this._progressActive){
            this.startProgressPolling(false);
        }
        // Render con último dato o uno vacío
        if(!this._lastProgressData){
            this.renderProgressUI({active:false, steps:[], started_at:null, finished_at:null});
        } else {
            this.renderProgressUI(this._lastProgressData);
        }
    }

    renderProgressUI(data){
        // Estructura de pasos esperados si faltan
        const expectedOrder = [
            {key:'login', label:'Login'},
            {key:'navigate', label:'Navegación'},
            {key:'base_filters', label:'Filtros base'},
            {key:'chance', label:'CHANCE EXPRESS'},
            {key:'ruleta', label:'RULETA EXPRESS'},
            {key:'data_ready', label:'Datos listos'},
            {key:'generate_alerts', label:'Generando alertas'},
            {key:'complete', label:'Completado'}
        ];
        const stepsMap = new Map((data.steps||[]).map(s=>[s.key,s]));
        const normalized = expectedOrder.map(def=>{
            const s = stepsMap.get(def.key) || {key:def.key, status:'pending'};
            return { key:def.key, label:def.label, status:s.status, error_message:s.error_message, started_at:s.started_at, finished_at:s.finished_at };
        });
        // Progreso total calculado: peso uniforme excepto 'complete'
        const progressSteps = normalized.filter(s=>s.key!=='complete');
        const totalSegments = progressSteps.length;
        let doneSegments = 0;
        const nowTs = Date.now();
        progressSteps.forEach(s=>{
            if(['success','error'].includes(s.status)) {
                doneSegments += 1;
            } else if(s.status==='running') {
                const est = this._progressStepExpected[s.key] || 15;
                let elapsed = 0;
                if(s.started_at){
                    elapsed = (nowTs - new Date(s.started_at).getTime())/1000;
                }
                if(elapsed < 0) elapsed = 0; // clock skew safe
                // Fracción entre 0 y 0.85 del segmento basada en elapsed
                const frac = Math.max(0, Math.min(0.85, (elapsed/est)*0.85));
                // Garantizar un mínimo visual para indicar arranque
                doneSegments += Math.max(frac, 0.05);
            }
        });
    const pctRaw = Math.min(100, (doneSegments/totalSegments)*100);
    // Ajuste: evitar que se quede atascado en un porcentaje muy bajo.
    // Para saltos por finalización de pasos, preferimos un snap directo.
    this._progressDisplayedPct = pctRaw; // snap directo (se puede volver a animación fina luego)
    const pct = Math.round(pctRaw);
        // Actualizar barra mini en burbuja
        const miniFill = document.getElementById('sp-bubble-bar');
        if(miniFill){ miniFill.style.width = pct+'%'; }
        // Barra total en modal
        const totalBar = document.getElementById('scraping-progress-total');
        const totalFill = document.getElementById('scraping-progress-total-fill');
        if(totalFill){ totalFill.style.width = pct+'%'; }
        if(totalBar){
            totalBar.classList.remove('completed','error');
            if(!data.active){
                if(normalized.some(s=>s.status==='error')) totalBar.classList.add('error');
                else totalBar.classList.add('completed');
            }
        }
        const listEl = document.getElementById('scraping-progress-steps');
        if(listEl){
            listEl.innerHTML = normalized.map(s=>{
                const st = s.status;
                const badge = st==='running'?'primary':(st==='success'?'success':(st==='error'?'danger':'secondary'));
                let durationHtml = '';
                if(s.started_at && s.finished_at){
                    const durMs = (new Date(s.finished_at) - new Date(s.started_at));
                    const secs = (durMs/1000).toFixed(1);
                    durationHtml = `<span class=\"ms-2 text-muted\">${secs}s</span>`;
                }
                const times = (s.started_at||s.finished_at)?`<div class=\"sp-meta\">${s.started_at?`Inicio: ${new Date(s.started_at).toLocaleTimeString()}`:''} ${s.finished_at?`Fin: ${new Date(s.finished_at).toLocaleTimeString()}`:''} ${durationHtml}</div>`:'';
                const msg = s.error_message?`<div class=\"sp-msg\">${s.error_message}</div>`:'';
                return `<li class=\"${st}\"><div class=\"d-flex justify-content-between align-items-start\"><div class=\"sp-step-title\">${s.label}</div><span class=\"sp-step-status badge bg-${badge}\">${st}</span></div>${times}${msg}</li>`;
            }).join('');
        }
        // Bubble updates
        const bubble = document.getElementById('scraping-progress-bubble');
        if(bubble){
            const label = document.getElementById('sp-bubble-label');
            const icon = document.getElementById('sp-bubble-icon');
            if(data.active){
                const current = data.current || normalized.find(s=>s.status==='running')?.key;
                label && (label.textContent = current? `Iteración: ${this._labelForStep(current)}` : 'Iteración activa');
                icon && (icon.innerHTML = '<span class="spinner-border spinner-border-sm"></span>');
                bubble.classList.remove('done','error');
            } else {
                // Determinar si hubo error
                const anyError = normalized.some(s=>s.status==='error');
                if(anyError){
                    label && (label.textContent = 'Error en iteración');
                    icon && (icon.innerHTML = '<i class="fas fa-triangle-exclamation text-danger"></i>');
                    bubble.classList.add('error');
                    bubble.classList.remove('done');
                } else {
                    label && (label.textContent = 'Iteración completada');
                    icon && (icon.innerHTML = '<i class="fas fa-check text-success"></i>');
                    bubble.classList.add('done');
                    bubble.classList.remove('error');
                }
            }
        }
        // Resumen
        const summary = document.getElementById('scraping-progress-summary');
        if(summary){
            if(data.active){
                summary.textContent = `Iteración en curso… (${pct}%)`;
            } else {
                const finished = normalized.find(s=>s.key==='complete');
                if(finished && finished.status){
                    const success = finished.status==='success' && !normalized.some(s=>s.status==='error');
                    // Duración total si hay started_at / finished_at root
                    let durationStr = '';
                    if(data.started_at && data.finished_at){
                        const durMs = new Date(data.finished_at) - new Date(data.started_at);
                        if(durMs > 0){
                            const secs = (durMs/1000);
                            if(secs < 90) durationStr = `${secs.toFixed(1)}s`;
                            else {
                                const m = Math.floor(secs/60); const s = Math.round(secs%60);
                                durationStr = `${m}m ${s}s`;
                            }
                        }
                    }
                    summary.textContent = success ? `Última iteración: completada${durationStr?` en ${durationStr}`:''}` : (normalized.some(s=>s.status==='error')?`Última iteración terminó con errores${durationStr?` tras ${durationStr}`:''}`:'Sin iteración activa');
                } else {
                    summary.textContent = 'Sin iteración activa';
                }
            }
        }
    }

    _scheduleProgressBubbleAutoHide(){
        if(this._bubbleHideTimer) clearTimeout(this._bubbleHideTimer);
        this._bubbleHideTimer = setTimeout(()=>{
            if(!this._progressActive){ this.hideProgressBubble(); }
        }, 25000); // ocultar tras 25s si sigue inactiva
    }

    _labelForStep(key){
        switch(key){
            case 'login': return 'Login';
            case 'navigate': return 'Navegación';
            case 'base_filters': return 'Filtros';
            case 'chance': return 'Chance';
            case 'ruleta': return 'Ruleta';
            case 'data_ready': return 'Datos';
            case 'generate_alerts': return 'Alertas';
            case 'complete': return 'Fin';
            default: return key;
        }
    }

    _setAnimatedProgressTarget(target){
    // Animación desactivada (snap directo ya aplicado en renderProgressUI)
    this._progressAnimTarget = target;
    }

    _animateProgressFrame(){
    // Animación deshabilitada
    this._progressDisplayedPct = this._progressAnimTarget;
    this._progressAnimRaf = null;
    }

    _persistProgressState(pct, data){
        try {
            const payload = {
                pct: pct,
                finished_at: data.finished_at || null,
                started_at: data.started_at || null,
                status: data.steps?.find(s=>s.key==='complete')?.status || null,
                ts: Date.now()
            };
            localStorage.setItem('progressLastPct', JSON.stringify(payload));
            this._lastPersistProgress = payload;
        } catch(_){}
    }

    _initPersistedProgress(){
        try {
            const raw = localStorage.getItem('progressLastPct');
            if(!raw) return;
            const obj = JSON.parse(raw);
            if(!obj) return;
            // Mostrar burbuja reciente si terminó hace < 5 min y pct=100
            if(obj.pct === 100 && obj.ts && (Date.now() - obj.ts) < 5*60*1000){
                this.showProgressBubble();
                this._progressDisplayedPct = 100;
                const miniFill = document.getElementById('sp-bubble-bar');
                if(miniFill) miniFill.style.width = '100%';
                const label = document.getElementById('sp-bubble-label');
                const icon = document.getElementById('sp-bubble-icon');
                if(label) label.textContent = 'Iteración completada';
                if(icon) icon.innerHTML = '<i class="fas fa-check text-success"></i>';
                const bubble = document.getElementById('scraping-progress-bubble');
                if(bubble) bubble.classList.add('done');
                this._scheduleProgressBubbleAutoHide();
            }
        } catch(_){}
    }

    _resetProgressAnimation(){
        this._progressDisplayedPct = 0;
        this._progressAnimTarget = 0;
        this._forceProgressReset = true;
        // Limpiar estado visual inmediato
        const bubble = document.getElementById('scraping-progress-bubble');
        if(bubble){ bubble.classList.remove('done','error'); }
        const miniFill = document.getElementById('sp-bubble-bar');
        if(miniFill) miniFill.style.width = '0%';
        const label = document.getElementById('sp-bubble-label');
        const icon = document.getElementById('sp-bubble-icon');
        if(label) label.textContent = 'Iniciando iteración…';
        if(icon) icon.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        try { localStorage.removeItem('progressLastPct'); } catch(_){ }
    }

    async reportAlert(alertId) {
        try {
            if (!this._reportingAlerts) this._reportingAlerts = new Set();
            if (this._reportingAlerts.has(alertId)) return; // evitar doble clic rápido
            this._reportingAlerts.add(alertId);
            // Suspender detección de iteración por 2s para evitar falso positivo
            this._suspendIterationDetectionUntil = Date.now() + 2000;
            const response = await fetch(`${this.apiBase}/alerts/${alertId}/report`, {
                method: 'POST'
            });

            if (response.ok) {
                console.debug('[reportAlert] éxito backend id', alertId);
                this.currentAlerts = this.currentAlerts.filter(a => a.id !== alertId);
                this.renderAlertsTable(this.currentAlerts);
                document.querySelectorAll(`tr[data-alert-id='${alertId}']`).forEach(tr=>tr.remove());
                this.showNotification('Alerta marcada como reportada', 'success');
                // Marcar agencia asociada para supresión (buscarla en currentAlerts original si aún existía)
                const removed = this.currentAlerts.find(a=>a.id===alertId);
                if (removed && removed.agency_code){
                    if (!this._recentlyReportedAgencies) this._recentlyReportedAgencies = new Set();
                    this._recentlyReportedAgencies.add(removed.agency_code);
                    setTimeout(()=>{ if (this._recentlyReportedAgencies) this._recentlyReportedAgencies.delete(removed.agency_code); }, 3000);
                }
                setTimeout(()=>this.loadAlerts(), 280);
                setTimeout(()=>this.loadDashboardData(), 430);
            } else {
                const error = await response.json();
                this.showNotification(`Error: ${error.detail}`, 'error');
            }

        } catch (error) {
            console.error('Error reportando alerta:', error);
            this.showNotification('Error reportando alerta', 'error');
        } finally {
            if (this._reportingAlerts) this._reportingAlerts.delete(alertId);
        }
    }

    async reportMultipleAlerts(agencyCode) {
        try {
            this._suspendIterationDetectionUntil = Date.now() + 2500;
            // Encontrar todas las alertas de esta agencia
            const agencyAlerts = this.currentAlerts.filter(alert => alert.agency_code === agencyCode);
            
            if (agencyAlerts.length === 0) {
                this.showNotification('No se encontraron alertas para reportar', 'warning');
                return;
            }

            // Reportar todas las alertas
            const promises = agencyAlerts.map(alert => 
                fetch(`${this.apiBase}/alerts/${alert.id}/report`, { method: 'POST' })
            );

            // Evitar spam de clic mientras procesa
            if (!this._reportingAgencies) this._reportingAgencies = new Set();
            if (this._reportingAgencies.has(agencyCode)) return;
            this._reportingAgencies.add(agencyCode);
            // Re-render parcial: sólo actualizar botón si fila existe
            const row = document.querySelector(`tr[data-agid='${agencyCode}']`);
            if (row) {
                const btn = row.querySelector('button.btn-success');
                if (btn){
                    btn.classList.add('btn-reporting');
                    btn.disabled = true;
                    btn.innerHTML = '<span class="reporting-inline-spinner"><span class="spinner-border spinner-border-sm" role="status"></span><span>Reportando...</span></span>';
                }
            }
            // Eliminación optimista inmediata de todas las alertas de la agencia
            console.debug('[reportMultipleAlerts] click', agencyCode, 'alerts count', agencyAlerts.length);
            this.currentAlerts = this.currentAlerts.filter(a => a.agency_code !== agencyCode);
            this.renderAlertsTable(this.currentAlerts);
            if (document.querySelector(`tr[data-agid='${agencyCode}']`)) {
                console.debug('[reportMultipleAlerts] fila aún presente tras render optimista, forzando eliminación DOM');
                document.querySelectorAll(`tr[data-agid='${agencyCode}']`).forEach(tr=>tr.remove());
            }
            const results = await Promise.all(promises).finally(()=>{ this._reportingAgencies.delete(agencyCode); });
            const successAlerts = agencyAlerts.filter((_,i)=>results[i]?.ok);
            if (successAlerts.length) {
                // Eliminación optimista por agencia
                const idsToRemove = new Set(successAlerts.map(a=>a.id));
                this.currentAlerts = this.currentAlerts.filter(a => !idsToRemove.has(a.id));
                this.renderAlertsTable(this.currentAlerts);
                // Marcar agencia como recientemente reportada para suprimir reaparición breve
                if (!this._recentlyReportedAgencies) this._recentlyReportedAgencies = new Set();
                this._recentlyReportedAgencies.add(agencyCode);
                // Limpieza automática después de 3s
                setTimeout(()=>{ if (this._recentlyReportedAgencies) this._recentlyReportedAgencies.delete(agencyCode); }, 3000);
            }
            if (successAlerts.length === agencyAlerts.length) {
                this.showNotification(`${successAlerts.length} alertas marcadas como reportadas`, 'success');
            } else if (successAlerts.length > 0) {
                this.showNotification(`${successAlerts.length} de ${agencyAlerts.length} alertas reportadas`, 'warning');
            } else {
                this.showNotification(`No se pudieron reportar alertas`, 'error');
            }
            // Refrescar en background con pequeño retraso para asegurar commit y reducir carreras; el botón desaparecerá al re-render general
            setTimeout(()=>{ this.loadAlerts(); }, 320);
            setTimeout(()=>{ this.loadDashboardData(); }, 450);

        } catch (error) {
            console.error('Error reportando alertas múltiples:', error);
            this.showNotification('Error reportando alertas', 'error');
        }
    }

    // =============================
    // Exportación de Incidencias
    // =============================
    async runIncidentsExport(){
        const start = document.getElementById('export-start-day')?.value || '';
        const end = document.getElementById('export-end-day')?.value || '';
        const reportedVal = document.getElementById('export-reported')?.value || '';
        const alertType = document.getElementById('export-alert-type')?.value || '';
        const fmt = document.querySelector('input[name="export-format"]:checked')?.value || 'csv';
        const params = new URLSearchParams();
        if(start) params.append('start_day', start);
        if(end) params.append('end_day', end);
        if(reportedVal) params.append('reported', reportedVal);
        if(alertType) params.append('alert_type', alertType);
        params.append('format', fmt);
        const url = `${this.apiBase}/alerts/export?${params.toString()}`;
        // Intentar fetch para detectar vacío
        try {
            const headRes = await fetch(url, { method:'GET' });
            if(headRes.headers.get('content-type')?.includes('application/json')){
                const js = await headRes.json();
                if(js && js.message && js.message.startsWith('Sin alertas')){
                    const empty = document.getElementById('export-incidents-empty');
                    if(empty) empty.classList.remove('d-none');
                    return;
                }
            }
            // Forzar descarga creando enlace oculto
            const blob = await headRes.blob();
            const a = document.createElement('a');
            const objectUrl = URL.createObjectURL(blob);
            a.href = objectUrl;
            if(fmt==='csv') a.download = 'alertas.csv';
            else if(fmt==='excel') a.download = 'alertas.xlsx';
            else a.download = 'alertas.pdf';
            document.body.appendChild(a);
            a.click();
            setTimeout(()=>{ URL.revokeObjectURL(objectUrl); a.remove(); }, 2500);
            // Cerrar modal
            const modalEl = document.getElementById('exportIncidentsModal');
            if(modalEl){
                const m = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                m.hide();
            }
        } catch(err){
            console.error('Error exportando incidencias', err);
            this.showNotification('Error exportando incidencias', 'error');
        }
    }

    async showAllAgencies() {
        try {
            console.log('Ejecutando showAllAgencies...');
            // Asegurar que obtenemos solo agencias de hoy
            const response = await fetch(`${this.apiBase}/agencies?today_only=true`);
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const agencies = await response.json();
            console.log('Agencias obtenidas:', agencies.length);

            const modal = new bootstrap.Modal(document.getElementById('allAgenciesModal'));
            const agenciesContainer = document.getElementById('all-agencies-list');

            const today = new Date().toLocaleDateString('es-DO', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });

            let html = `
                <div class="mb-3">
                    <h5>📊 Agencias Monitoreadas Hoy</h5>
                    <div class="alert alert-info">
                        <strong>📈 Total:</strong> ${agencies.length} agencias<br>
                        <strong>📅 Fecha:</strong> ${today}<br>
                        <strong>🕐 Actualizado:</strong> ${new Date().toLocaleTimeString('es-DO')}
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="table table-striped table-hover all-agencies-table">
                        <thead class="table-dark">
                            <tr>
                                <th>Código</th>
                                <th>Nombre de Agencia</th>
                                <th>Últimas Ventas (Hoy)</th>
                                <th>Último Balance (Hoy)</th>
                                <th>Última Actualización</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            if (agencies.length === 0) {
                html += `
                    <tr>
                        <td colspan="6" class="text-center text-muted py-4">
                            <i class="fas fa-info-circle fa-2x mb-2"></i><br>
                            No hay agencias monitoreadas hoy.<br>
                            <small>Inicia el monitoreo para comenzar a recopilar datos.</small>
                        </td>
                    </tr>
                `;
            } else {
                agencies.forEach(agency => {
                    const lastUpdate = agency.latest_update ? this.formatTimeAgo(agency.latest_update) : 'Sin datos hoy';
                    const sales = agency.latest_sales !== null ? this.formatMoney(agency.latest_sales) : 'N/A';
                    const balance = agency.latest_balance !== null ? this.formatMoney(agency.latest_balance) : 'N/A';
                
                    html += `
                        <tr>
                            <td><strong>${agency.code}</strong></td>
                            <td>
                                <div class="agency-name" title="${agency.name}">
                                    ${agency.name}
                                </div>
                            </td>
                            <td class="${agency.latest_sales !== null ? this.getMoneyClass(agency.latest_sales) : ''}">${sales}</td>
                            <td class="${agency.latest_balance !== null ? this.getMoneyClass(agency.latest_balance) : ''}">${balance}</td>
                            <td class="time-ago">${lastUpdate}</td>
                            <td>
                                <button class="btn btn-info btn-sm" onclick="app.showAgencyDetails('${agency.code}')">
                                    <i class="fas fa-chart-line"></i> Ver Historial
                                </button>
                            </td>
                        </tr>
                    `;
                });
            }

            html += `
                        </tbody>
                    </table>
                </div>
            `;

            agenciesContainer.innerHTML = html;
            modal.show();

        } catch (error) {
            console.error('Error cargando todas las agencias:', error);
            this.showNotification('Error cargando agencias', 'error');
        }
    }

    // Listar agencias con alertas reportadas hoy y la hora de reporte
    async showReportedAgencies() {
        try {
            const resp = await fetch(`${this.apiBase}/alerts?today_only=true&reported=true`);
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            const alerts = await resp.json();

            // Agrupar por agencia y tomar la última hora de reporte del día
            const byAgency = {};
            alerts.forEach(a => {
                const key = a.agency_code;
                if (!byAgency[key]) {
                    byAgency[key] = {
                        code: a.agency_code,
                        name: a.agency_name,
                        first_reported_at: a.reported_at ? new Date(a.reported_at) : (a.alert_date ? new Date(a.alert_date) : null),
                        last_reported_at: a.reported_at ? new Date(a.reported_at) : (a.alert_date ? new Date(a.alert_date) : null),
                        count: 1
                    };
                } else {
                    const currFirst = byAgency[key].first_reported_at;
                    const currLast = byAgency[key].last_reported_at;
                    const thisTime = a.reported_at ? new Date(a.reported_at) : (a.alert_date ? new Date(a.alert_date) : null);
                    if (thisTime) {
                        if (!currFirst || thisTime < currFirst) byAgency[key].first_reported_at = thisTime;
                        if (!currLast || thisTime > currLast) byAgency[key].last_reported_at = thisTime;
                    }
                    byAgency[key].count += 1;
                }
            });

            const agencies = Object.values(byAgency).sort((a,b)=>{
                const ta = a.last_reported_at ? a.last_reported_at.getTime() : 0;
                const tb = b.last_reported_at ? b.last_reported_at.getTime() : 0;
                return tb - ta;
            });
            const modal = new bootstrap.Modal(document.getElementById('reportedAgenciesModal'));
            const container = document.getElementById('reported-agencies-list');

            const today = new Date().toLocaleDateString('es-DO', {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
            });

            let html = `
                <div class="mb-3">
                    <h5>✅ Agencias Reportadas Hoy</h5>
                    <div class="alert alert-success">
                        <strong>🏢 Total:</strong> ${agencies.length} agencias<br>
                        <strong>📅 Fecha:</strong> ${today}<br>
                        <strong>🕐 Actualizado:</strong> ${new Date().toLocaleTimeString('es-DO')}
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="table table-striped table-hover all-agencies-table">
                        <thead class="table-dark">
                            <tr>
                                <th>Código</th>
                                <th>Agencia</th>
                                <th>Hora reportada</th>
                                <th>Alertas</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            if (agencies.length === 0) {
                html += `
                    <tr>
                        <td colspan="5" class="text-center text-muted py-4">
                            <i class="fas fa-info-circle fa-2x mb-2"></i><br>
                            No hay agencias reportadas hoy.
                        </td>
                    </tr>
                `;
            } else {
                agencies.forEach(ag => {
                    const time = ag.last_reported_at ? ag.last_reported_at.toLocaleTimeString() : (ag.first_reported_at ? ag.first_reported_at.toLocaleTimeString() : '--');
                    html += `
                        <tr>
                            <td><strong>${ag.code}</strong></td>
                            <td><div class="agency-name" title="${ag.name}">${ag.name}</div></td>
                            <td class="time-ago">${time}</td>
                            <td>${ag.count}</td>
                            <td>
                                    <button class="btn btn-warning btn-sm me-1" onclick="app.unreportAgencyAlerts('${ag.code}')" title="Revertir reportado">
                                        <i class="fas fa-undo"></i> Desmarcar
                                    </button>
                                    <button class="btn btn-info btn-sm" onclick="app.showAgencyDetails('${ag.code}')">
                                    <i class="fas fa-chart-line"></i> Ver Historial
                                </button>
                            </td>
                        </tr>
                    `;
                });
            }

            html += `
                        </tbody>
                    </table>
                </div>
            `;

            container.innerHTML = html;
            modal.show();
        } catch (error) {
            console.error('Error cargando agencias reportadas:', error);
            this.showNotification('Error cargando agencias reportadas', 'error');
        }
    }

    async unreportAgencyAlerts(agencyCode) {
        try {
            // Obtener alertas reportadas de la agencia para hoy
            const resp = await fetch(`${this.apiBase}/alerts?today_only=true&reported=true`);
            if (!resp.ok) return;
            const alerts = await resp.json();
            const toRevert = alerts.filter(a=>a.agency_code===agencyCode);
            if (!toRevert.length) {
                this.showNotification('Sin alertas para revertir', 'warning');
                return;
            }
            // Llamadas secuenciales (evitar saturar backend)
            for (const a of toRevert) {
                try { await fetch(`${this.apiBase}/alerts/${a.id}/unreport`, { method:'POST' }); } catch(_) {}
            }
            this.showNotification(`${toRevert.length} alertas revertidas`, 'info');
            // Refrescar vistas relevantes
            this.loadAlerts();
            this.showReportedAgencies();
            this.loadDashboardData();
        } catch(e) {
            console.error('Error revirtiendo alertas', e);
            this.showNotification('Error revirtiendo alertas', 'error');
        }
    }

    async showAgencyDetails(agencyCode) {
        try {
            const response = await fetch(`${this.apiBase}/agencies/${agencyCode}/history`);
            const data = await response.json();

            // Buscar el nombre completo de la agencia en las alertas actuales o en actividad reciente
            let fullAgencyName = agencyCode;
            
            // Buscar en alertas actuales
            const currentAlert = this.currentAlerts.find(alert => alert.agency_code === agencyCode);
            if (currentAlert) {
                fullAgencyName = currentAlert.agency_name;
            } else {
                // Buscar en la actividad reciente del dashboard
                try {
                    const dashboardResponse = await fetch(`${this.apiBase}/dashboard`);
                    const dashboardData = await dashboardResponse.json();
                    const recentActivity = dashboardData.latest_activity.find(activity => activity.agency_code === agencyCode);
                    if (recentActivity) {
                        fullAgencyName = recentActivity.agency_name;
                    }
                } catch (e) {
                    console.log('No se pudo obtener datos del dashboard para el nombre completo');
                }
            }

            const modal = new bootstrap.Modal(document.getElementById('agencyModal'));
            const detailsContainer = document.getElementById('agency-details');

        let html = `
                <div class="mb-3">
                    <h5>📊 Detalles de Agencia</h5>
                    <div class="alert alert-info">
                        <strong>🏢 Agencia:</strong> ${fullAgencyName}<br>
                        <strong>🔢 Código:</strong> ${agencyCode}<br>
                        <strong>📅 Período de análisis:</strong> ${data.period_days} días
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Fecha</th>
                                <th>Ventas Promedio</th>
                                <th>Balance Promedio</th>
                                <th>Crecimiento Diario</th>
                                <th>Iteraciones</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

        data.growth_history.forEach(day => {
                html += `
                    <tr class="day-row" style="cursor:pointer" onclick="app.showAgencyDayDetails('${agencyCode}','${day.date}','${fullAgencyName}')" title="Ver iteraciones del ${day.date}">
                        <td>${day.date}</td>
                        <td class="${this.getMoneyClass(day.avg_sales)}">${this.formatMoney(day.avg_sales)}</td>
                        <td class="${this.getMoneyClass(day.avg_balance)}">${this.formatMoney(day.avg_balance)}</td>
                        <td class="${this.getMoneyClass(day.daily_growth)}">${this.formatMoney(day.daily_growth)}</td>
                        <td>${day.iterations}</td>
                    </tr>
                `;
            });

            html += `
                        </tbody>
                    </table>
                </div>
            `;

            detailsContainer.innerHTML = html;
            modal.show();

        } catch (error) {
            console.error('Error cargando detalles de agencia:', error);
            this.showNotification('Error cargando detalles de agencia', 'error');
        }
    }

    // Drill-down: mostrar iteraciones de un día específico
    async showAgencyDayDetails(agencyCode, day, agencyName) {
        try {
            // Preparar modal fullscreen
            const modalEl = document.getElementById('dayDetailsModal');
            const titleEl = document.getElementById('dayDetailsTitle');
            if (titleEl) titleEl.innerHTML = `<i class="fas fa-calendar-day me-2"></i> Movimientos del ${day} — <span class="text-muted">${agencyName || agencyCode}</span>`;
            const bsModal = new bootstrap.Modal(modalEl);
            bsModal.show();

            // Placeholders mientras carga
            const summaryEl = document.getElementById('day-summary');
            const tableBody = document.querySelector('#day-iterations-table tbody');
            const alertsEl = document.getElementById('day-alerts');
            if (summaryEl) summaryEl.innerHTML = '';
            if (tableBody) tableBody.innerHTML = '<tr><td colspan="8" class="text-muted">Cargando...</td></tr>';
            if (alertsEl) alertsEl.innerHTML = '';

            const resp = await fetch(`${this.apiBase}/agencies/${agencyCode}/day/${day}/iterations`);
            if (!resp.ok) {
                if (tableBody) tableBody.innerHTML = '<tr><td colspan="8" class="text-danger">No hay datos para este día.</td></tr>';
                return;
            }
            const data = await resp.json();

            // Resumen
            const first = data.iterations[0];
            const last = data.iterations[data.iterations.length - 1];
            const totalDeltaSales = last.sales - first.sales;
            const totalDeltaBalance = last.balance - first.balance;
            if (summaryEl) {
                summaryEl.innerHTML = `
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-icon bg-primary"><i class="fas fa-receipt"></i></div>
                            <div class="stat-info">
                                <h6>Iteraciones</h6>
                                <h4>${data.total_iterations}</h4>
                                <small class="text-muted">${new Date(data.first_time).toLocaleTimeString()} → ${new Date(data.last_time).toLocaleTimeString()}</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-icon bg-success"><i class="fas fa-arrow-trend-up"></i></div>
                            <div class="stat-info">
                                <h6>Δ Ventas (día)</h6>
                                <h4 class="${this.getMoneyClass(totalDeltaSales)}">${this.formatMoney(totalDeltaSales)}</h4>
                                <small class="text-muted">${this.formatMoney(first.sales)} → ${this.formatMoney(last.sales)}</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-icon bg-info"><i class="fas fa-scale-balanced"></i></div>
                            <div class="stat-info">
                                <h6>Δ Balance (día)</h6>
                                <h4 class="${this.getMoneyClass(totalDeltaBalance)}">${this.formatMoney(totalDeltaBalance)}</h4>
                                <small class="text-muted">${this.formatMoney(first.balance)} → ${this.formatMoney(last.balance)}</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-icon bg-warning"><i class="fas fa-bell"></i></div>
                            <div class="stat-info">
                                <h6>Alertas del día</h6>
                                <h4>${data.alerts?.length || 0}</h4>
                                <small class="text-muted">Registros detectados</small>
                            </div>
                        </div>
                    </div>
                `;
            }

            // Tabla usando HORA EXACTA
            if (tableBody) {
                tableBody.innerHTML = data.iterations.map(it => `
                    <tr>
                        <td class="time-cell" title="${new Date(it.time).toLocaleString()}">${new Date(it.time).toLocaleTimeString()}</td>
                        <td class="${this.getMoneyClass(it.sales)}">${this.formatMoney(it.sales)}</td>
                        <td class="${this.getMoneyClass(it.delta_sales)}">${this.formatMoney(it.delta_sales)}</td>
                        <td class="${this.getMoneyClass(it.balance)}">${this.formatMoney(it.balance)}</td>
                        <td class="${this.getMoneyClass(it.delta_balance)}">${this.formatMoney(it.delta_balance)}</td>
                        <td class="${this.getMoneyClass(it.prizes)}">${this.formatMoney(it.prizes)}</td>
                        <td class="${this.getMoneyClass(it.prizes_paid)}">${this.formatMoney(it.prizes_paid)}</td>
                        <td><span class="badge ${it.lottery_type==='CHANCE_EXPRESS' ? 'bg-primary' : 'bg-danger'}">${it.lottery_type || '-'}</span></td>
                    </tr>
                `).join('');
            }

            // Sparkline intradía (Chart.js)
            const ctx = document.getElementById('daySparkline');
            if (ctx) {
                const labels = data.iterations.map(it => new Date(it.time).toLocaleTimeString());
                const salesSeries = data.iterations.map(it => it.sales);
                const balanceSeries = data.iterations.map(it => it.balance);
                // Serie "Apuestas": variación de ventas por iteración
                const betsSeries = data.iterations.map((it, idx, arr) => idx === 0 ? 0 : (it.sales - arr[idx - 1].sales));
                // Destruir chart previo si existe
                if (this._dayChart) {
                    try { this._dayChart.destroy(); } catch (_) {}
                }
                this._dayChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [{
                            label: 'Ventas',
                            data: salesSeries,
                            borderColor: '#4ade80',
                            backgroundColor: 'rgba(74, 222, 128, 0.15)',
                            tension: 0.25,
                            pointRadius: 2,
                            fill: true
                        },{
                            label: 'Balance',
                            data: balanceSeries,
                            borderColor: '#60a5fa',
                            backgroundColor: 'rgba(96, 165, 250, 0.15)',
                            tension: 0.25,
                            pointRadius: 2,
                            fill: true,
                            hidden: true
                        },{
                            label: 'Apuestas (Δ Ventas)',
                            data: betsSeries,
                            borderColor: '#f6ad55',
                            backgroundColor: 'rgba(246, 173, 85, 0.15)',
                            tension: 0.25,
                            pointRadius: 2,
                            fill: true,
                            hidden: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { color: this.isDarkTheme() ? '#e5e7eb' : '#374151' } },
                            y: { ticks: { color: this.isDarkTheme() ? '#e5e7eb' : '#374151' }, grid: { color: this.isDarkTheme() ? '#2a2f34' : '#e5e7eb' } }
                        }
                    }
                });

                // Forzar resize tras mostrar modal (evita gráficas invisibles al crearse en oculto)
                const onShown = () => { try { this._dayChart.resize(); this._dayChart.update(); } catch (_) {} };
                modalEl.addEventListener('shown.bs.modal', onShown, { once: true });
                // Limpiar al cerrar
                modalEl.addEventListener('hidden.bs.modal', () => { try { this._dayChart.destroy(); } catch (_) {} this._dayChart = null; }, { once: true });

                // Toggle series con botones
                const salesBtn = document.getElementById('seriesSales');
                const balBtn = document.getElementById('seriesBalance');
                const betsBtn = document.getElementById('seriesBets');
                const updateVisibility = () => {
                    if (!this._dayChart) return;
                    this._dayChart.data.datasets[0].hidden = !(salesBtn && salesBtn.checked);
                    this._dayChart.data.datasets[1].hidden = !(balBtn && balBtn.checked);
                    this._dayChart.data.datasets[2].hidden = !(betsBtn && betsBtn.checked);
                    this._dayChart.update();
                };
                if (salesBtn) salesBtn.onchange = updateVisibility;
                if (balBtn) balBtn.onchange = updateVisibility;
                if (betsBtn) betsBtn.onchange = updateVisibility;
            }

            // Alertas del día
            if (alertsEl) {
                if (data.alerts && data.alerts.length) {
                    alertsEl.innerHTML = `
                        <div class="card">
                            <div class="card-header"><i class="fas fa-bell me-2"></i>Alertas del día</div>
                            <div class="card-body">
                                ${data.alerts.map(a => `
                                    <div class="alert-message-item ${this.getAlertColorClass(a.type)} mb-2">
                                        <i class="${this.getAlertIcon(a.type)} me-1"></i>
                                        <span class="alert-message-text">${this.cleanAlertMessage(a.message)}</span>
                                        <span class="badge ms-2 ${a.type==='threshold' ? 'bg-danger' : a.type==='growth_variation' ? 'bg-warning text-dark' : 'bg-info'}">${this.getAlertTypeName(a.type)}</span>
                                        <small class="text-muted ms-2">${new Date(a.created_at).toLocaleTimeString()}</small>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                } else {
                    alertsEl.innerHTML = '';
                }
            }
        } catch (e) {
            console.error('Error cargando iteraciones del día:', e);
            this.showNotification('No se pudieron cargar los movimientos del día', 'error');
        }
    }

    // Mostrar recomendaciones de optimización en modal
    async showOptimizationsRecommendations() {
        try {
            const response = await fetch(`${this.apiBase}/intelligence/optimizations`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const recommendations = await response.json();
            const container = document.getElementById('optimizations-modal-body');
            if (!recommendations.length) {
                container.innerHTML = `
                    <div class="text-center text-muted p-4">
                        <i class="fas fa-check-circle fa-2x mb-2 text-success"></i>
                        <p>No hay recomendaciones disponibles</p>
                    </div>
                `;
            } else {
                let html = '';
                recommendations.forEach(rec => {
                    html += `
                        <div class="card mb-2">
                            <div class="card-body">
                                <h6>${rec.parameter.replace('_', ' ').toUpperCase()}</h6>
                                <p class="mb-1"><strong>Actual:</strong> ${rec.current_value} &rarr; <strong>Recomendado:</strong> ${rec.recommended_value}</p>
                                <p class="mb-1"><strong>Confianza:</strong> ${(rec.confidence * 100).toFixed(1)}%</p>
                                <p class="mb-1"><strong>Motivo:</strong> ${rec.reason}</p>
                                <p class="mb-0"><strong>Mejora esperada:</strong> ${rec.expected_improvement}</p>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            }
            // Mostrar modal
            const modalEl = document.getElementById('optimizationsModal');
            const bsModal = new bootstrap.Modal(modalEl);
            bsModal.show();
        } catch (error) {
            console.error('Error cargando recomendaciones de optimización:', error);
            this.showNotification('No se pudieron cargar las recomendaciones', 'error');
        }
    }

    async refreshData() {
        this.setButtonLoading('refresh-btn', true);
        await this.loadInitialData(true); // manual=true para mostrar toast explícito
        this.setButtonLoading('refresh-btn', false);
        this.countdownRefreshLock = false;
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.refreshInterval = setInterval(() => {
            if (this.autoRefreshEnabled) {
                this.loadInitialData(false);
            }
        }, 30000); // Actualizar cada 30 segundos
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    setButtonLoading(buttonId, isLoading) {
        const button = document.getElementById(buttonId);
        const icon = button.querySelector('i');
        
        if (isLoading) {
            button.disabled = true;
            icon.className = 'fas fa-spinner fa-spin';
        } else {
            button.disabled = false;
            // Restaurar icono original basado en el ID del botón
            const iconMap = {
                'start-monitoring': 'fas fa-play',
                'stop-monitoring': 'fas fa-stop',
                'manual-iteration': 'fas fa-sync',
                'refresh-btn': 'fas fa-sync-alt'
            };
            icon.className = iconMap[buttonId] || 'fas fa-cog';
        }
    }

    showNotification(message, type = 'info') {
        const toast = document.getElementById('notification-toast');
        const messageElement = document.getElementById('toast-message');
        
        messageElement.textContent = message;
        
        // Cambiar color según el tipo
        toast.className = 'toast';
        switch (type) {
            case 'success':
                toast.classList.add('bg-success', 'text-white');
                break;
            case 'error':
                toast.classList.add('bg-danger', 'text-white');
                break;
            case 'warning':
                toast.classList.add('bg-warning');
                break;
            default:
                toast.classList.add('bg-info', 'text-white');
        }

        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    // Utilidades de formateo
    formatMoney(amount) {
        if (amount === null || amount === undefined) return '$0.00';
        return new Intl.NumberFormat('es-DO', {
            style: 'currency',
            currency: 'DOP'
        }).format(amount);
    }

    getMoneyClass(amount) {
        if (amount > 0) return 'money-positive';
        if (amount < 0) return 'money-negative';
        return 'money-neutral';
    }

    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Ahora';
        if (diffMins < 60) return `${diffMins}m`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d`;
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    getAlertTypeName(type) {
        const typeNames = {
            'threshold': 'Por Umbral',
            'growth_variation': 'Crecimiento',
            'sustained_growth': 'Crecimiento Sostenido'
        };
        return typeNames[type] || type;
    }

    formatAlertMessages(messages, alertTypes) {
        /**
         * Formatear mensajes de alerta para mejor legibilidad
         * Convierte mensajes largos en formato legible con iconos y estructura
         */
        if (!messages || messages.length === 0) {
            return '<span class="text-muted">Sin mensajes</span>';
        }

        return messages.map((message, index) => {
            // Determinar el tipo de alerta para el icono
            const alertType = alertTypes[index] || 'threshold';
            const icon = this.getAlertIcon(alertType);
            const colorClass = this.getAlertColorClass(alertType);
            
            // Limpiar y formatear el mensaje
            const cleanMessage = this.cleanAlertMessage(message);
            
            return `
                <div class="alert-message-item ${colorClass} mb-1" title="${message}">
                    <i class="${icon} me-1"></i>
                    <span class="alert-message-text">${cleanMessage}</span>
                </div>
            `;
        }).join('');
    }

    getAlertIcon(alertType) {
        const icons = {
            'threshold': 'fas fa-exclamation-triangle',
            'growth_variation': 'fas fa-chart-line',
            'sustained_growth': 'fas fa-trending-up'
        };
        return icons[alertType] || 'fas fa-bell';
    }

    getAlertColorClass(alertType) {
        const colors = {
            'threshold': 'alert-threshold',
            'growth_variation': 'alert-growth',
            'sustained_growth': 'alert-sustained'
        };
        return colors[alertType] || 'alert-default';
    }

    cleanAlertMessage(message) {
        /**
         * Limpiar y formatear el mensaje para mejor legibilidad
         * Extraer información clave y presentarla de forma clara
         */
        if (!message) return 'Mensaje no disponible';

        // Si el mensaje contiene información de ventas/balance, formatearlo mejor
        if (message.includes('$')) {
            // Buscar patrones de dinero y formatearlos
            return message.replace(/\$([0-9,]+\.?\d*)/g, (match, amount) => {
                return `<strong class="money-highlight">$${amount}</strong>`;
            });
        }

        // Si el mensaje contiene porcentajes, resaltarlos
        if (message.includes('%')) {
            return message.replace(/(\d+\.?\d*)%/g, '<strong class="percentage-highlight">$1%</strong>');
        }

        // Si el mensaje es muy largo, truncarlo inteligentemente
        if (message.length > 80) {
            // Buscar un punto de corte natural (después de una coma o punto)
            const cutPoint = message.lastIndexOf(',', 80) || message.lastIndexOf('.', 80) || 80;
            return message.substring(0, cutPoint) + '...';
        }

        return message;
    }

    // ==================== SISTEMA DE CONFIGURACIÓN ====================

    loadSettings() {
        const defaultSettings = {
            monitoringInterval: 15,
            browserHeadless: true,
            filterSuriel: true,
            filterTotalGeneral: true,
            enableGrowthAlerts: true,
            enableThresholdAlerts: true,
            salesThreshold: 20000,
            balanceThreshold: 6000,
            growthVariation: 1500,
            sustainedGrowth: 500,
            autoShowIterationSummary: true,
            enableIterationPush: true,
            enableIterationSound: true
        };

        const savedSettings = localStorage.getItem('monitoringSettings');
        return savedSettings ? { ...defaultSettings, ...JSON.parse(savedSettings) } : defaultSettings;
    }

    showSettings() {
        // Cargar valores actuales en el modal
        document.getElementById('monitoring-interval').value = this.settings.monitoringInterval;
        document.getElementById('browser-headless').checked = this.settings.browserHeadless;
        document.getElementById('filter-suriel').checked = this.settings.filterSuriel;
        document.getElementById('filter-total-general').checked = this.settings.filterTotalGeneral;
        document.getElementById('enable-growth-alerts').checked = this.settings.enableGrowthAlerts;
        document.getElementById('enable-threshold-alerts').checked = this.settings.enableThresholdAlerts;
        document.getElementById('sales-threshold').value = this.settings.salesThreshold;
        document.getElementById('balance-threshold').value = this.settings.balanceThreshold;
        document.getElementById('growth-variation').value = this.settings.growthVariation;
        document.getElementById('sustained-growth').value = this.settings.sustainedGrowth;
    const soundChk = document.getElementById('enable-iteration-sound');
    if (soundChk) soundChk.checked = !!this.settings.enableIterationSound;

        // Listeners (única vez por sesión)
        if (!this._settingsListenersBound) {
            const saveBtn = document.getElementById('save-settings');
            if (saveBtn) saveBtn.addEventListener('click', async () => {
                await this.saveSettings();
                // Cierre explícito si el modal sigue abierto
                const modalEl = document.getElementById('settingsModal');
                try {
                    const inst = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                    inst.hide();
                } catch(_){}
            });
            const resetBtn = document.getElementById('reset-settings');
            if (resetBtn) resetBtn.addEventListener('click', () => this.resetSettings());
            this._settingsListenersBound = true;
        }

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
        modal.show();
        
        // 🚀 Actualizar información del intervalo después de mostrar el modal
        setTimeout(() => {
            this.updateIntervalDisplay();
            const autoChk = document.getElementById('auto-show-iteration-summary');
            if (autoChk) autoChk.checked = !!this.settings.autoShowIterationSummary;
            const pushChk = document.getElementById('enable-iteration-push');
            if (pushChk) pushChk.checked = !!this.settings.enableIterationPush;
        }, 100);
    }

    async saveSettings() {
        try {
            // Recopilar valores del formulario
            const newSettings = {
                monitoringInterval: parseInt(document.getElementById('monitoring-interval').value),
                browserHeadless: document.getElementById('browser-headless').checked,
                filterSuriel: document.getElementById('filter-suriel').checked,
                filterTotalGeneral: document.getElementById('filter-total-general').checked,
                enableGrowthAlerts: document.getElementById('enable-growth-alerts').checked,
                enableThresholdAlerts: document.getElementById('enable-threshold-alerts').checked,
                salesThreshold: parseInt(document.getElementById('sales-threshold').value),
                balanceThreshold: parseInt(document.getElementById('balance-threshold').value),
                growthVariation: parseInt(document.getElementById('growth-variation').value),
                sustainedGrowth: parseInt(document.getElementById('sustained-growth').value),
                autoShowIterationSummary: this.settings?.autoShowIterationSummary !== undefined ? this.settings.autoShowIterationSummary : true,
                enableIterationPush: document.getElementById('enable-iteration-push')?.checked ?? true,
                enableIterationSound: document.getElementById('enable-iteration-sound')?.checked ?? true
            };

            // Validaciones
            if (newSettings.monitoringInterval < 1) {
                this.showNotification('El intervalo mínimo es de 1 minuto', 'warning');
                return;
            }

            // Advertencia para intervalos muy cortos
            if (newSettings.monitoringInterval < 5) {
                const proceed = confirm(`⚠️ ADVERTENCIA: Configuraste un intervalo de ${newSettings.monitoringInterval} minuto(s).\n\nEsto ejecutará el monitoreo muy frecuentemente y puede sobrecargar el sistema.\n\n¿Estás seguro de que quieres continuar?`);
                if (!proceed) {
                    return;
                }
            }

            // Guardar en localStorage
            localStorage.setItem('monitoringSettings', JSON.stringify(newSettings));
            this.settings = newSettings;

            // Enviar configuración al backend
            const response = await fetch(`${this.apiBase}/settings/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newSettings)
            });

            if (response.ok) {
                this.showNotification('Configuración guardada correctamente', 'success');
                // Cierre ya se maneja en el listener de guardado; aquí por redundancia segura
                try { const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal')); if (modal) modal.hide(); } catch(_){}
                // Actualizar interfaz si es necesario
                this.updateUIFromSettings();
                const autoChk = document.getElementById('auto-show-iteration-summary');
                if (autoChk) autoChk.checked = !!this.settings.autoShowIterationSummary;
                const pushChk = document.getElementById('enable-iteration-push');
                if (pushChk) pushChk.checked = !!this.settings.enableIterationPush;
                const soundChk = document.getElementById('enable-iteration-sound');
                if (soundChk) soundChk.checked = !!this.settings.enableIterationSound;
            } else {
                // Parsear mensaje de error del servidor
                let errorMsg = 'Error al guardar configuración en el servidor';
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.detail || errorData.message || errorMsg;
                } catch (_) {}
                this.showNotification(errorMsg, 'error');
            }

        } catch (error) {
            console.error('Error guardando configuración:', error);
            this.showNotification('Error guardando configuración', 'error');
        }
    }

    resetSettings() {
        const defaultSettings = {
            monitoringInterval: 15,
            browserHeadless: true,
            filterSuriel: true,
            filterTotalGeneral: true,
            enableGrowthAlerts: true,
            enableThresholdAlerts: true,
            salesThreshold: 20000,
            balanceThreshold: 6000,
            growthVariation: 1500,
            sustainedGrowth: 500,
            autoShowIterationSummary: true,
            enableIterationPush: true,
            enableIterationSound: true
        };

        // Actualizar formulario
        document.getElementById('monitoring-interval').value = defaultSettings.monitoringInterval;
        document.getElementById('browser-headless').checked = defaultSettings.browserHeadless;
        document.getElementById('filter-suriel').checked = defaultSettings.filterSuriel;
        document.getElementById('filter-total-general').checked = defaultSettings.filterTotalGeneral;
        document.getElementById('enable-growth-alerts').checked = defaultSettings.enableGrowthAlerts;
        document.getElementById('enable-threshold-alerts').checked = defaultSettings.enableThresholdAlerts;
        document.getElementById('sales-threshold').value = defaultSettings.salesThreshold;
        document.getElementById('balance-threshold').value = defaultSettings.balanceThreshold;
        document.getElementById('growth-variation').value = defaultSettings.growthVariation;
        document.getElementById('sustained-growth').value = defaultSettings.sustainedGrowth;

        this.showNotification('Configuración restaurada a valores por defecto', 'info');
    // Sincronizar checkbox de resumen de iteración si abierto
    const autoChk = document.getElementById('auto-show-iteration-summary');
    if (autoChk) autoChk.checked = defaultSettings.autoShowIterationSummary;
    const pushChk = document.getElementById('enable-iteration-push');
    if (pushChk) pushChk.checked = defaultSettings.enableIterationPush;
    const soundChk = document.getElementById('enable-iteration-sound');
    if (soundChk) soundChk.checked = defaultSettings.enableIterationSound;
    }

    updateUIFromSettings() {
        // Actualizar intervalo de auto-refresh si cambió
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.startAutoRefresh();
        }
        // Inicializar audio si se activó
        if (this.settings.enableIterationSound) {
            this.initIterationSound();
        }
    }

    // (Nota) Los listeners de sonido se agregan dinámicamente después de init en initIterationSoundCall()

    // ==================== ORDENAMIENTO DE TABLA ====================

    sortAlertsTable(column) {
        if (this.sortState.column === column) {
            // Cambiar dirección si es la misma columna
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            // Nueva columna, empezar con ascendente
            this.sortState.column = column;
            this.sortState.direction = 'asc';
        }

        // Actualizar iconos
        this.updateSortIcons();

        // Ordenar alertas
        const sortedAlerts = [...this.currentAlerts].sort((a, b) => {
            let valueA, valueB;

            if (column === 'sales') {
                valueA = a.current_sales || 0;
                valueB = b.current_sales || 0;
            } else if (column === 'balance') {
                valueA = a.current_balance || 0;
                valueB = b.current_balance || 0;
            }

            if (this.sortState.direction === 'asc') {
                return valueA - valueB;
            } else {
                return valueB - valueA;
            }
        });

        // Re-renderizar tabla
        this.renderAlertsTable(sortedAlerts);
    }

    updateSortIcons() {
        document.querySelectorAll('.sortable i').forEach(icon => {
            icon.className = 'fas fa-sort ms-1';
        });

        if (this.sortState.column) {
            const currentHeader = document.querySelector(`[data-sort="${this.sortState.column}"] i`);
            if (currentHeader) {
                currentHeader.className = `fas fa-sort-${this.sortState.direction === 'asc' ? 'up' : 'down'} ms-1`;
            }
        }
    }

    // 🧠 SISTEMA DE INTELIGENCIA ARTIFICIAL

    async loadIntelligenceData() {
        try {
            const response = await fetch(`${this.apiBase}/intelligence/status`);
            if (response.ok) {
                const data = await response.json();
                this.updateIntelligenceUI(data);
            } else {
                console.log('Sistema de IA no disponible aún');
                this.updateIntelligenceUI({ intelligence_enabled: false });
            }
        } catch (error) {
            console.log('Sistema de IA no disponible:', error);
            this.updateIntelligenceUI({ intelligence_enabled: false });
        }
    }

    async refreshIntelligenceData() {
        this.setButtonLoading('refresh-intelligence', true);
        await this.loadIntelligenceData();
        this.setButtonLoading('refresh-intelligence', false);
    }

    async toggleIntelligence() {
        try {
            this.setButtonLoading('toggle-intelligence', true);

            // Obtener el estado actual de IA desde el DOM (asegúrate de booleano)
            const statusBadge = document.getElementById('ai-status');
            const isEnabled = statusBadge && statusBadge.textContent.trim() === 'Habilitado';

            // Enviar el valor contrario como booleano
            const response = await fetch(`${this.apiBase}/intelligence/toggle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: !isEnabled })
            });

            if (response.ok) {
                const result = await response.json();
                // Usa el campo correcto según la respuesta del backend
                const enabled = result.enabled !== undefined ? result.enabled : result.intelligence_enabled;
                this.showNotification(
                    `Sistema de IA ${enabled ? 'habilitado' : 'deshabilitado'}`,
                    'success'
                );
                await this.loadIntelligenceData();
            } else {
                const error = await response.json();
                this.showNotification(`Error: ${error.detail || JSON.stringify(error)}`, 'error');
            }

        } catch (error) {
            console.error('Error toggling intelligence:', error);
            this.showNotification('Error al cambiar estado de IA', 'error');
        } finally {
            this.setButtonLoading('toggle-intelligence', false);
        }
    }

    updateIntelligenceUI(data) {
        const isEnabled = data.intelligence_enabled;
        
        // Actualizar botón toggle
        const toggleBtn = document.getElementById('toggle-intelligence');
        const toggleText = document.getElementById('intelligence-toggle-text');
        
        if (isEnabled) {
            toggleBtn.className = 'btn btn-warning btn-sm me-2';
            toggleText.textContent = 'Deshabilitar IA';
        } else {
            toggleBtn.className = 'btn btn-light btn-sm me-2';
            toggleText.textContent = 'Habilitar IA';
        }

        // Actualizar estado
        const statusBadge = document.getElementById('ai-status');
        statusBadge.textContent = isEnabled ? 'Habilitado' : 'Deshabilitado';
        statusBadge.className = `badge ${isEnabled ? 'bg-success' : 'bg-secondary'}`;

        // Actualizar métricas
        document.getElementById('anomalies-count').textContent = data.anomalies_detected || 0;
        document.getElementById('optimizations-count').textContent = data.optimizations_available || 0;
        document.getElementById('prediction-accuracy').textContent = 
            data.system_metrics?.prediction_accuracy ? 
            `${(data.system_metrics.prediction_accuracy * 100).toFixed(1)}%` : '--';

        // Actualizar predicciones y optimizaciones
        this.updateFailurePredictions(data.failure_prediction);
        this.updateOptimizationRecommendations(data.adaptive_config);
    }

    updateFailurePredictions(predictions) {
        const container = document.getElementById('failure-predictions');
        
        if (!predictions || !predictions.high_risk_components) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-shield-alt fa-2x mb-2 text-success"></i>
                    <p>No se detectan riesgos inmediatos</p>
                </div>
            `;
            return;
        }

        let html = '';
        predictions.high_risk_components.forEach(component => {
            const riskLevel = component.risk_score > 0.8 ? 'danger' : 
                            component.risk_score > 0.6 ? 'warning' : 'info';
            
            html += `
                <div class="alert alert-${riskLevel} mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong><i class="fas fa-exclamation-triangle me-1"></i>${component.component}</strong>
                            <p class="mb-0 small">${component.prediction}</p>
                        </div>
                        <span class="badge bg-${riskLevel}">
                            ${(component.risk_score * 100).toFixed(0)}%
                        </span>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    updateOptimizationRecommendations(adaptiveConfig) {
        const container = document.getElementById('optimization-recommendations');
        
        if (!adaptiveConfig || Object.keys(adaptiveConfig).length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-check-circle fa-2x mb-2 text-success"></i>
                    <p>Sistema optimizado</p>
                </div>
            `;
            return;
        }

        let html = '';
        Object.entries(adaptiveConfig).forEach(([param, config]) => {
            const improvementIcon = config.confidence > 0.8 ? 'fas fa-star text-warning' : 
                                  config.confidence > 0.6 ? 'fas fa-thumbs-up text-info' : 
                                  'fas fa-info-circle text-secondary';
            
            html += `
                <div class="card mb-2">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong class="small">${param.replace('_', ' ').toUpperCase()}</strong>
                            <i class="${improvementIcon}"></i>
                        </div>
                        <div class="small text-muted mb-1">
                            <span class="text-danger">${config.current_value}</span> → 
                            <span class="text-success">${config.recommended_value}</span>
                        </div>
                        <div class="small">${config.reason}</div>
                        <div class="progress mt-1" style="height: 4px;">
                            <div class="progress-bar bg-info" style="width: ${config.confidence * 100}%"></div>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    // 🔍 SISTEMA DOM INTELLIGENCE

    async loadDOMIntelligenceData() {
        try {
            const response = await fetch(`${this.apiBase}/dom-intelligence/status`);
            if (response.ok) {
                const data = await response.json();
                this.updateDOMIntelligenceUI(data);
            } else {
                console.log('Sistema DOM Intelligence no disponible aún');
            }
        } catch (error) {
            console.log('Sistema DOM Intelligence no disponible:', error);
        }
    }

    updateDOMIntelligenceUI(data) {
        // Verificar si existe el panel DOM Intelligence en el HTML
        const domPanel = document.getElementById('dom-intelligence-panel');
        if (!domPanel) {
            // Si no existe, crearlo dinámicamente
            this.createDOMIntelligencePanel();
        }

        // Actualizar métricas básicas
        if (data.learning_active !== undefined) {
            const learningStatus = document.getElementById('dom-learning-status');
            if (learningStatus) {
                learningStatus.textContent = data.learning_active ? 'Activo' : 'Inactivo';
                learningStatus.className = `badge ${data.learning_active ? 'bg-success' : 'bg-secondary'}`;
            }
        }

        if (data.interactions_recorded !== undefined) {
            const interactionsCount = document.getElementById('dom-interactions-count');
            if (interactionsCount) {
                interactionsCount.textContent = data.interactions_recorded;
            }
        }

        if (data.current_optimizations !== undefined) {
            const optimizationsCount = document.getElementById('dom-optimizations-count');
            if (optimizationsCount) {
                optimizationsCount.textContent = data.current_optimizations;
            }
        }

        if (data.recommendations_available !== undefined) {
            const recommendationsCount = document.getElementById('dom-recommendations-count');
            if (recommendationsCount) {
                recommendationsCount.textContent = data.recommendations_available;
            }
        }

        // Actualizar estadísticas de rendimiento
        if (data.performance_stats) {
            this.updateDOMPerformanceStats(data.performance_stats);
        }

        // Actualizar elementos problemáticos
        if (data.problem_elements) {
            this.updateProblemElements(data.problem_elements);
        }
    }

    createDOMIntelligencePanel() {
        // Crear panel DOM Intelligence dinámicamente
        const intelligenceSection = document.querySelector('.row .card.border-info');
        if (intelligenceSection) {
            const domPanel = document.createElement('div');
            domPanel.className = 'card mt-3';
            domPanel.innerHTML = `
                <div class="card-header bg-secondary text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-search me-2"></i>Observación Inteligente DOM
                    </h6>
                </div>
                <div class="card-body" id="dom-intelligence-panel">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon bg-secondary">
                                    <i class="fas fa-microscope"></i>
                                </div>
                                <div class="stat-info">
                                    <h6>Aprendizaje DOM</h6>
                                    <span id="dom-learning-status" class="badge bg-secondary">Inactivo</span>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon bg-info">
                                    <i class="fas fa-mouse-pointer"></i>
                                </div>
                                <div class="stat-info">
                                    <h6>Interacciones</h6>
                                    <h4 id="dom-interactions-count">0</h4>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon bg-warning">
                                    <i class="fas fa-cogs"></i>
                                </div>
                                <div class="stat-info">
                                    <h6>Optimizaciones</h6>
                                    <h4 id="dom-optimizations-count">0</h4>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-card">
                                <div class="stat-icon bg-success">
                                    <i class="fas fa-lightbulb"></i>
                                </div>
                                <div class="stat-info">
                                    <h6>Recomendaciones</h6>
                                    <h4 id="dom-recommendations-count">0</h4>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6 class="mb-0">
                                        <i class="fas fa-chart-bar me-2"></i>Rendimiento DOM
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div id="dom-performance-stats">
                                        <div class="text-center text-muted py-3">
                                            <i class="fas fa-chart-line fa-2x mb-2"></i>
                                            <p>Recopilando datos...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6 class="mb-0">
                                        <i class="fas fa-exclamation-triangle me-2"></i>Elementos Problemáticos
                                    </h6>
                                </div>
                                <div class="card-body">
                                    <div id="problem-elements">
                                        <div class="text-center text-muted py-3">
                                            <i class="fas fa-check-circle fa-2x mb-2 text-success"></i>
                                            <p>No hay problemas detectados</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            intelligenceSection.parentNode.insertBefore(domPanel, intelligenceSection.nextSibling);
        }
    }

    updateDOMPerformanceStats(stats) {
        const container = document.getElementById('dom-performance-stats');
        if (!container) return;

        if (!stats || Object.keys(stats).length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-hourglass-start fa-2x mb-2"></i>
                    <p>Esperando datos de rendimiento...</p>
                </div>
            `;
            return;
        }

        const successRate = stats.success_rate ? (stats.success_rate * 100).toFixed(1) : '0.0';
        const avgDuration = stats.avg_duration ? stats.avg_duration.toFixed(2) : '0.00';

        container.innerHTML = `
            <div class="row">
                <div class="col-6">
                    <div class="text-center mb-2">
                        <div class="h5 mb-0 text-primary">${stats.total_interactions || 0}</div>
                        <small class="text-muted">Interacciones</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="text-center mb-2">
                        <div class="h5 mb-0 text-success">${successRate}%</div>
                        <small class="text-muted">Tasa de Éxito</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="text-center mb-2">
                        <div class="h5 mb-0 text-info">${avgDuration}s</div>
                        <small class="text-muted">Duración Promedio</small>
                    </div>
                </div>
                <div class="col-6">
                    <div class="text-center mb-2">
                        <div class="h5 mb-0 text-warning">${stats.unique_selectors || 0}</div>
                        <small class="text-muted">Elementos</small>
                    </div>
                </div>
            </div>
        `;
    }

    updateProblemElements(problemElements) {
        const container = document.getElementById('problem-elements');
        if (!container) return;

        if (!problemElements || problemElements.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-check-circle fa-2x mb-2 text-success"></i>
                    <p>No hay problemas detectados</p>
                </div>
            `;
            return;
        }

        let html = '';
        problemElements.slice(0, 3).forEach(element => {
            const successRate = (element.success_rate * 100).toFixed(1);
            const avgDuration = element.avg_duration.toFixed(2);
            const alertClass = element.success_rate < 0.5 ? 'danger' : 'warning';

            html += `
                <div class="alert alert-${alertClass} mb-2 p-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong class="small">${this.truncateText(element.selector, 25)}</strong>
                            <div class="small">${element.interactions} interacciones</div>
                        </div>
                        <div class="text-end">
                            <div class="small">${successRate}%</div>
                            <div class="small text-muted">${avgDuration}s</div>
                        </div>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async showDOMIntelligenceDetails() {
        try {
            // Obtener datos detallados
            const [statsResponse, optimizationsResponse] = await Promise.all([
                fetch(`${this.apiBase}/dom-intelligence/stats`),
                fetch(`${this.apiBase}/dom-intelligence/optimizations`)
            ]);

            const stats = await statsResponse.json();
            const optimizations = await optimizationsResponse.json();

            // Crear modal con detalles
            const modalHTML = `
                <div class="modal fade" id="domIntelligenceModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header bg-secondary text-white">
                                <h5 class="modal-title">
                                    <i class="fas fa-search me-2"></i>Detalles de DOM Intelligence
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${this.generateDOMStatsHTML(stats)}
                                ${this.generateDOMOptimizationsHTML(optimizations)}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-warning" onclick="app.toggleDOMLearning()">
                                    <i class="fas fa-power-off me-1"></i>Toggle Aprendizaje
                                </button>
                                <button type="button" class="btn btn-info" onclick="app.refreshDOMIntelligence()">
                                    <i class="fas fa-sync-alt me-1"></i>Actualizar
                                </button>
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                    <i class="fas fa-times me-1"></i>Cerrar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Agregar modal al DOM
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // Mostrar modal
            const modal = new bootstrap.Modal(document.getElementById('domIntelligenceModal'));
            modal.show();

            // Limpiar modal al cerrar
            document.getElementById('domIntelligenceModal').addEventListener('hidden.bs.modal', function() {
                this.remove();
            });

        } catch (error) {
            console.error('Error mostrando detalles DOM Intelligence:', error);
            this.showNotification('Error cargando detalles de DOM Intelligence', 'error');
        }
    }

    generateDOMStatsHTML(stats) {
        if (!stats || !stats.general_stats) return '<p>No hay estadísticas disponibles</p>';

        return `
            <div class="row mb-4">
                <div class="col-12">
                    <h6>📊 Estadísticas Generales (${stats.period})</h6>
                    <div class="row">
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h4>${stats.general_stats.total_interactions}</h4>
                                    <small>Total Interacciones</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h4>${stats.general_stats.success_rate}%</h4>
                                    <small>Tasa de Éxito</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h4>${stats.general_stats.avg_duration}s</h4>
                                    <small>Duración Promedio</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-light">
                                <div class="card-body text-center">
                                    <h4>${stats.general_stats.unique_selectors}</h4>
                                    <small>Elementos Únicos</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    generateDOMOptimizationsHTML(optimizations) {
        if (!optimizations || !optimizations.recommendations || optimizations.recommendations.length === 0) {
            return '<div class="alert alert-success">✅ No hay optimizaciones pendientes</div>';
        }

        let html = `
            <div class="row">
                <div class="col-12">
                    <h6>💡 Optimizaciones Recomendadas</h6>
                </div>
            </div>
        `;

        optimizations.recommendations.forEach((opt, index) => {
            const confidenceColor = opt.confidence > 0.8 ? 'success' : opt.confidence > 0.6 ? 'warning' : 'info';
            
            html += `
                <div class="card mb-2">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-md-8">
                                <h6 class="mb-1">${opt.optimization_type.replace('_', ' ').toUpperCase()}</h6>
                                <p class="mb-1 small">${opt.reason}</p>
                                <div class="small text-muted">
                                    <strong>Actual:</strong> ${opt.current_value} → 
                                    <strong>Recomendado:</strong> ${opt.recommended_value}
                                </div>
                            </div>
                            <div class="col-md-4 text-end">
                                <span class="badge bg-${confidenceColor}">${(opt.confidence * 100).toFixed(0)}% confianza</span>
                                <div class="small text-muted mt-1">${opt.expected_improvement}</div>
                                <button class="btn btn-sm btn-primary mt-1" 
                                        onclick="app.applyDOMOptimization('${opt.optimization_type}', '${opt.affected_elements[0]}', '${opt.recommended_value}')">
                                    Aplicar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        return html;
    }

    async toggleDOMLearning() {
        try {
            const response = await fetch(`${this.apiBase}/dom-intelligence/toggle-learning`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification(result.message, 'success');
                await this.loadDOMIntelligenceData();
            } else {
                this.showNotification('Error cambiando estado de aprendizaje DOM', 'error');
            }
        } catch (error) {
            console.error('Error toggling DOM learning:', error);
            this.showNotification('Error cambiando estado de aprendizaje DOM', 'error');
        }
    }

    async applyDOMOptimization(optimizationType, targetElement, newValue) {
        try {
            const response = await fetch(`${this.apiBase}/dom-intelligence/apply-optimization`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    optimization_type: optimizationType,
                    target_element: targetElement,
                    new_value: newValue
                })
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification(result.message, 'success');
                await this.loadDOMIntelligenceData();
            } else {
                const error = await response.json();
                this.showNotification(`Error aplicando optimización: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Error applying DOM optimization:', error);
            this.showNotification('Error aplicando optimización DOM', 'error');
        }
    }

    async refreshDOMIntelligence() {
        try {
            this.setButtonLoading('refresh-dom-intelligence', true);
            await this.loadDOMIntelligenceData();
            this.showNotification('Datos de DOM Intelligence actualizados', 'success');
        } catch (error) {
            this.showNotification('Error actualizando DOM Intelligence', 'error');
        } finally {
            this.setButtonLoading('refresh-dom-intelligence', false);
        }
    }

    // 🚀 FUNCIONES PARA CONTROL RÁPIDO DE INTERVALOS
    async setQuickInterval(minutes) {
        const intervalInput = document.getElementById('monitoring-interval');
        const infoSpan = document.getElementById('interval-info');
        
        // Actualizar el input
        intervalInput.value = minutes;
        
        // Actualizar información visual
        const modeInfo = {
            1: { text: 'SÚPER INTENSIVO - 60 ejecuciones/hora', color: 'text-danger' },
            2: { text: 'INTENSIVO - 30 ejecuciones/hora', color: 'text-warning' },
            5: { text: 'PRUEBAS - 12 ejecuciones/hora', color: 'text-info' },
            15: { text: 'NORMAL - 4 ejecuciones/hora', color: 'text-success' }
        };
        
        const mode = modeInfo[minutes] || { text: `${minutes} minutos - ${Math.round(60/minutes)} ejecuciones/hora`, color: 'text-primary' };
        infoSpan.innerHTML = `<span class="${mode.color}">${mode.text}</span>`;
        
        // Mostrar confirmación para intervalos muy cortos
        if (minutes < 5) {
            const proceed = confirm(`⚠️ MODO ${minutes === 1 ? 'SÚPER ' : ''}INTENSIVO\n\nEsto ejecutará el monitoreo cada ${minutes} minuto${minutes > 1 ? 's' : ''}.\n\n¿Aplicar este cambio inmediatamente?`);
            if (!proceed) {
                intervalInput.value = this.settings.monitoringInterval;
                infoSpan.innerHTML = 'Clicks rápidos para tests intensivos';
                return;
            }
        }
        
        // Aplicar el cambio inmediatamente
        try {
            await this.saveSettings();
            this.showNotification(`Intervalo actualizado a ${minutes} minuto${minutes > 1 ? 's' : ''}`, 'success');
        } catch (error) {
            console.error('Error aplicando intervalo rápido:', error);
            this.showNotification('Error aplicando el cambio de intervalo', 'error');
        }
    }

    // Función para mostrar el estado actual del intervalo
    updateIntervalDisplay() {
        const intervalInput = document.getElementById('monitoring-interval');
        const infoSpan = document.getElementById('interval-info');
        
        if (intervalInput && infoSpan) {
            const currentInterval = parseInt(intervalInput.value);
            const execsPerHour = Math.round(60 / currentInterval);
            
            if (currentInterval <= 1) {
                infoSpan.innerHTML = `<span class="text-danger">SÚPER INTENSIVO - ${execsPerHour} ejecuciones/hora</span>`;
            } else if (currentInterval <= 2) {
                infoSpan.innerHTML = `<span class="text-warning">INTENSIVO - ${execsPerHour} ejecuciones/hora</span>`;
            } else if (currentInterval <= 5) {
                infoSpan.innerHTML = `<span class="text-info">PRUEBAS - ${execsPerHour} ejecuciones/hora</span>`;
            } else if (currentInterval <= 15) {
                infoSpan.innerHTML = `<span class="text-success">NORMAL - ${execsPerHour} ejecuciones/hora</span>`;
            } else {
                infoSpan.innerHTML = `<span class="text-primary">${currentInterval} minutos - ${execsPerHour} ejecuciones/hora</span>`;
            }
        }
    }

    toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        this.updateThemeToggleIcon();
    // Sincronizar tema en gráficos activos
    this.updateChartsTheme();
    }

    updateThemeToggleIcon() {
        const themeBtn = document.getElementById('theme-toggle');
        if (!themeBtn) return;
        const icon = themeBtn.querySelector('i');
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (icon) {
            icon.classList.toggle('fa-moon', !isDark);
            icon.classList.toggle('fa-sun', isDark);
        }
    }
}

// Inicializar la aplicación cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MonitoringApp();
});

// 🚀 FUNCIONES GLOBALES PARA BOTONES RÁPIDOS DE INTERVALO
function setQuickInterval(minutes) {
    if (window.app) {
        window.app.setQuickInterval(minutes);
    }
}

// Función para actualizar la información cuando se cambia manualmente el intervalo
function updateIntervalInfo() {
    if (window.app) {
        window.app.updateIntervalDisplay();
    }
}