(function(){
    const apiBase = '/api/v1';
    let chart, heatmap, hist;

    const els = {
        granularity: () => document.getElementById('granularity'),
        baselineDays: () => document.getElementById('baselineDays'),
        alignDow: () => document.getElementById('alignDow'),
        lottery: () => document.getElementById('lottery'),
        updated: () => document.getElementById('updatedAt'),
        kpis: () => document.getElementById('kpis-compare'),
        seriesSales: () => document.getElementById('seriesSales'),
        seriesBalance: () => document.getElementById('seriesBalance'),
        seriesBets: () => document.getElementById('seriesBets'),
    };

    function isDark(){ return document.documentElement.getAttribute('data-theme')==='dark'; }

    function applySavedTheme(){
        const saved = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', saved === 'dark' ? 'dark' : 'light');
        updateThemeToggleIcon();
    }

    function toggleTheme(){
        const current = isDark() ? 'dark' : 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeToggleIcon();
        // Re-render para ajustar colores de ejes y fondos
        setTimeout(refresh, 10);
    }

    function updateThemeToggleIcon(){
        const btn = document.getElementById('theme-toggle');
        if (!btn) return;
        btn.innerHTML = isDark() ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        btn.setAttribute('title', isDark()? 'Tema claro' : 'Tema oscuro');
    }

    async function fetchGlobal(){
        const g = els.granularity().value;
        const d = els.baselineDays().value;
        const a = els.alignDow().value === 'true';
        const l = els.lottery().value;
        const params = new URLSearchParams({ granularity: g, days: d, align_dow: String(a) });
        if (l) params.append('lottery', l);
        const resp = await fetch(`${apiBase}/stats/global?${params.toString()}`);
        if (!resp.ok) throw new Error('HTTP '+resp.status);
        return await resp.json();
    }

    function renderTrend(data){
        const ctx = document.getElementById('globalTrend');
        const labels = data.labels;
        const sales = data.today.sales;
        const balance = data.today.balance;
        const bets = data.today.bets;
        const mean = data.baseline.mean_sales;
        const std = data.baseline.std_sales;
        const upper = mean.map((m,i)=> (m!=null && std[i]!=null) ? m+std[i] : null);
        const lower = mean.map((m,i)=> (m!=null && std[i]!=null) ? m-std[i] : null);
        if (chart) { try { chart.destroy(); } catch(_){} }
        const initialSalesOn = (els.seriesSales() ? els.seriesSales().checked : true);
        const initialBalanceOn = (els.seriesBalance() ? els.seriesBalance().checked : false);
        const initialBetsOn = (els.seriesBets() ? els.seriesBets().checked : false);
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Ventas', data: sales, borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,.15)', tension: .25, pointRadius: 2, fill: true, hidden: !initialSalesOn },
                    { label: 'Balance', data: balance, borderColor: '#60a5fa', backgroundColor: 'rgba(96,165,250,.15)', tension: .25, pointRadius: 2, fill: true, hidden: !initialBalanceOn },
                    { label: 'Apuestas (Δ)', data: bets, borderColor: '#f6ad55', backgroundColor: 'rgba(246,173,85,.15)', tension: .25, pointRadius: 2, fill: true, hidden: !initialBetsOn },
                    { label: 'Promedio', data: mean, borderColor: '#d1d5db', borderDash: [6,4], tension: .2, pointRadius: 0, fill: false, yAxisID: 'y' },
                    { label: 'Banda +1σ', data: upper, borderColor: 'rgba(209,213,219,.0)', backgroundColor: 'rgba(209,213,219,.15)', tension: .2, pointRadius: 0, fill: '-1' },
                    { label: 'Banda -1σ', data: lower, borderColor: 'rgba(209,213,219,.0)', backgroundColor: 'rgba(209,213,219,.15)', tension: .2, pointRadius: 0, fill: 1 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: isDark()? '#e5e7eb':'#374151' } },
                    y: { ticks: { color: isDark()? '#e5e7eb':'#374151' }, grid: { color: isDark()? '#2a2f34':'#e5e7eb' } }
                }
            }
        });

        const s = els.seriesSales();
        const b = els.seriesBalance();
        const p = els.seriesBets();
        const apply = () => {
            if (s) chart.data.datasets[0].hidden = !s.checked;
            if (b) chart.data.datasets[1].hidden = !b.checked;
            if (p) chart.data.datasets[2].hidden = !p.checked;
            chart.update('none');
        };
        if (s) s.onchange = apply; if (b) b.onchange = apply; if (p) p.onchange = apply;
        // asegurar estado inicial correcto tras construir
        apply();
        const upd = document.getElementById('updatedAt');
        if (upd) upd.textContent = `Actualizado: ${new Date().toLocaleTimeString('es-DO')}`;
    }

        function renderKPIs(data){
                const s = data.summary || {};
                const cont = els.kpis();
                cont.innerHTML = `
                    <div class="kpi-card">
                        <div class="kpi-icon"><i class="fas fa-coins"></i></div>
                        <div>
                            <p class="kpi-title mb-1">Ventas Hoy</p>
                            <p class="kpi-value mb-0">${fmtMoney(s.total_today_sales||0)}</p>
                            <p class="kpi-sub mb-0">Actualizado en tiempo real</p>
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-icon" style="background: rgba(6,182,212,.15); color: var(--brand2-neo)"><i class="fas fa-chart-line"></i></div>
                        <div>
                            <p class="kpi-title mb-1">Normal (Prom.)</p>
                            <p class="kpi-value mb-0">${fmtMoney(s.total_baseline_sales||0)}</p>
                            <p class="kpi-sub mb-0">Basado en baseline</p>
                        </div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-icon" style="background: rgba(34,197,94,.14); color: var(--ok-neo)"><i class="fas fa-percent"></i></div>
                        <div>
                            <p class="kpi-title mb-1">Desviación vs Normal</p>
                            <p class="kpi-value mb-0">${fmtPct(s.deviation_sales_pct)}</p>
                            <p class="kpi-sub mb-0">Iteraciones: ${s.iterations_today||0} / ${s.iterations_expected||0}</p>
                        </div>
                    </div>`;
        }

    function renderHeatmap(data){
        // Simplificado: barras apiladas que colorean por desviación
        const ctx = document.getElementById('deviationHeatmap');
        const labels = data.labels;
        const mean = data.baseline.mean_sales;
        const today = data.today.sales;
        const devPct = labels.map((_,i)=> (mean[i] ? (today[i]-mean[i]) / mean[i] * 100 : 0));
        if (heatmap) { try { heatmap.destroy(); } catch(_){} }
        heatmap = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: '% Desviación',
                    data: devPct,
                    backgroundColor: devPct.map(v => v>10? '#ef4444': v<-10? '#22c55e':'#f59e0b')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: isDark()? '#e5e7eb':'#374151' } },
                    y: { ticks: { color: isDark()? '#e5e7eb':'#374151' }, grid: { color: isDark()? '#2a2f34':'#e5e7eb' } }
                }
            }
        });
    }

    function renderHistogram(data){
        const ctx = document.getElementById('betsHistogram');
        const deltas = (data.today.bets||[]).filter(v=>typeof v==='number');
        if (!deltas.length){ if (hist) {try{hist.destroy()}catch(_){}}; return; }
        // bins simples
        const min = Math.min(...deltas), max = Math.max(...deltas);
        const bins = 20;
        const step = (max-min)/bins || 1;
        const counts = new Array(bins).fill(0);
        deltas.forEach(v=>{ const idx = Math.min(bins-1, Math.max(0, Math.floor((v-min)/step))); counts[idx]++; });
        const labels = counts.map((_,i)=> fmtMoney(min+i*step));
        if (hist) { try{ hist.destroy(); } catch(_){} }
        hist = new Chart(ctx, { type: 'bar', data: { labels, datasets: [{ data: counts, backgroundColor: '#60a5fa' }] }, options: { responsive:true, maintainAspectRatio:false, plugins:{ legend:{display:false} }, scales:{ x:{ ticks:{ color:isDark()? '#e5e7eb':'#374151' } }, y:{ ticks:{ color:isDark()? '#e5e7eb':'#374151' }, grid:{ color:isDark()? '#2a2f34':'#e5e7eb' } } } } });
    }

    function fmtMoney(v){ return new Intl.NumberFormat('es-DO',{style:'currency', currency:'DOP'}).format(v||0); }
    function fmtPct(v){ if(v===null||v===undefined) return '--'; return `${v.toFixed(1)}%`; }
    function getDeltaColor(p){ if (p==null) return 'bg-secondary'; if (p>5) return 'bg-success'; if(p<-5) return 'bg-danger'; return 'bg-warning'; }

    async function refresh(){
        const data = await fetchGlobal();
        renderTrend(data);
        renderKPIs(data);
        renderHeatmap(data);
        renderHistogram(data);
    }

    function bindControls(){
        ['granularity','baselineDays','alignDow','lottery'].forEach(id=>{
            document.getElementById(id).addEventListener('change', refresh);
        });
        // Toggle de tema propio de esta vista (persistente)
        const themeBtn = document.getElementById('theme-toggle');
        if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
    }

    document.addEventListener('DOMContentLoaded', async ()=>{
        applySavedTheme();
        bindControls();
        await refresh();
        // Auto actualiza cada 30s
        setInterval(refresh, 30000);
    });
})();
