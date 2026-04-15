import { useState, useEffect } from 'react';
import { Card, Select, DatePicker, Button, Space, Spin, Tooltip as AntTooltip } from 'antd';
import dayjs from 'dayjs';
import { getAgencies, getActivityHeatmap } from '../api/reportsApi';
import { formatMoney } from '../utils/formatters';

const { RangePicker } = DatePicker;

const HOURS = Array.from({ length: 14 }, (_, i) => i + 8); // 8 AM to 9 PM

function getHeatColor(value, max) {
  if (!value || !max) return '#f0f0f0';
  const intensity = Math.min(value / max, 1);
  const r = Math.round(255 * intensity);
  const g = Math.round(255 * (1 - intensity * 0.7));
  const b = Math.round(100 * (1 - intensity));
  return `rgb(${r}, ${g}, ${b})`;
}

export default function ActivityHeatmap() {
  const [agencies, setAgencies] = useState([]);
  const [selectedAgency, setSelectedAgency] = useState(null);
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAgencies().then(list => setAgencies(list.map(a => ({ label: a.name, value: a.code }))));
  }, []);

  const handleSearch = async () => {
    if (!dateRange) return;
    setLoading(true);
    try {
      const result = await getActivityHeatmap({
        agencyCode: selectedAgency || undefined,
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const days = data?.days || [];
  const matrix = data?.matrix || {};
  const maxValue = data?.max_value || 1;

  return (
    <Card title="Heatmap de Actividad por Hora">
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          showSearch allowClear optionFilterProp="label"
          placeholder="Agencia (opcional — global)" style={{ minWidth: 300 }}
          options={agencies} value={selectedAgency} onChange={setSelectedAgency}
        />
        <RangePicker value={dateRange} onChange={setDateRange} />
        <Button type="primary" onClick={handleSearch} loading={loading}>Generar</Button>
      </Space>

      <Spin spinning={loading}>
        {days.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 600 }}>
              <thead>
                <tr>
                  <th style={{ padding: '6px 10px', textAlign: 'left', fontSize: 12 }}>Hora</th>
                  {days.map(d => (
                    <th key={d} style={{ padding: '6px 8px', textAlign: 'center', fontSize: 11 }}>
                      {dayjs(d).format('ddd DD')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {HOURS.map(hour => (
                  <tr key={hour}>
                    <td style={{ padding: '4px 10px', fontSize: 12, fontWeight: 500 }}>
                      {hour > 12 ? `${hour - 12}PM` : hour === 12 ? '12PM' : `${hour}AM`}
                    </td>
                    {days.map(d => {
                      const val = matrix[d]?.[hour] || 0;
                      return (
                        <AntTooltip key={d} title={`${dayjs(d).format('ddd DD MMM')} ${hour}:00 — ${formatMoney(val)}`}>
                          <td style={{
                            padding: 4, textAlign: 'center', fontSize: 10,
                            backgroundColor: getHeatColor(val, maxValue),
                            border: '1px solid #e8e8e8', cursor: 'default',
                            minWidth: 48, borderRadius: 2,
                          }}>
                            {val > 0 ? formatMoney(val) : ''}
                          </td>
                        </AntTooltip>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Spin>
    </Card>
  );
}
