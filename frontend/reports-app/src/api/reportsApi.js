const API_BASE = '/api/v1';

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

export function getAgencies() {
  return fetchJson(`${API_BASE}/agencies?today_only=false`);
}

export function getAgencyPerformance({ agencyCodes, startDate, endDate, groupBy }) {
  const params = new URLSearchParams();
  if (agencyCodes?.length) params.set('agency_codes', agencyCodes.join(','));
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  params.set('group_by', groupBy || 'day');
  return fetchJson(`${API_BASE}/reports/agency-performance?${params}`);
}

export function getAgencyDayDetail(agencyCode, day) {
  return fetchJson(`${API_BASE}/agencies/${agencyCode}/day/${day}/iterations`);
}

export function getAgencyRanking({ startDate, endDate, metric, lotteryType }) {
  const params = new URLSearchParams();
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  params.set('metric', metric || 'sales');
  if (lotteryType) params.set('lottery_type', lotteryType);
  return fetchJson(`${API_BASE}/reports/agency-ranking?${params}`);
}

export function getLotteryComparison({ startDate, endDate, groupBy }) {
  const params = new URLSearchParams();
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  params.set('group_by', groupBy || 'day');
  return fetchJson(`${API_BASE}/reports/lottery-comparison?${params}`);
}

export function getAlertHistory({ agencyCode, startDate, endDate, lotteryType }) {
  const params = new URLSearchParams();
  if (agencyCode) params.set('agency_code', agencyCode);
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  if (lotteryType) params.set('lottery_type', lotteryType);
  return fetchJson(`${API_BASE}/reports/alert-history?${params}`);
}

export function getActivityHeatmap({ agencyCode, startDate, endDate }) {
  const params = new URLSearchParams();
  if (agencyCode) params.set('agency_code', agencyCode);
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  return fetchJson(`${API_BASE}/reports/activity-heatmap?${params}`);
}

export function getConfirmationRate({ startDate, endDate }) {
  const params = new URLSearchParams();
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  return fetchJson(`${API_BASE}/reports/confirmation-rate?${params}`);
}

export function getGlobalSummary({ startDate, endDate, topN }) {
  const params = new URLSearchParams();
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  params.set('top_n', topN || 20);
  return fetchJson(`${API_BASE}/reports/global-summary?${params}`);
}
