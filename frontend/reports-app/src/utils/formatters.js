export function formatMoney(value) {
  if (value == null) return '-';
  return new Intl.NumberFormat('es-DO', {
    style: 'currency',
    currency: 'DOP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value) {
  if (value == null) return '-';
  return new Intl.NumberFormat('es-DO').format(Math.round(value));
}

export function formatPercent(value) {
  if (value == null) return '-';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

export function getVariationColor(value) {
  if (value > 0) return '#52c41a';
  if (value < 0) return '#ff4d4f';
  return '#8c8c8c';
}

export const LOTTERY_COLORS = {
  CHANCE_EXPRESS: '#1890ff',
  RULETA_EXPRESS: '#ff4d4f',
  CHANCE_EXTRAORDINARIO: '#faad14',
  PEGA_3: '#52c41a',
  DEFAULT: '#722ed1',
};

export function getLotteryColor(type) {
  return LOTTERY_COLORS[type] || LOTTERY_COLORS.DEFAULT;
}
