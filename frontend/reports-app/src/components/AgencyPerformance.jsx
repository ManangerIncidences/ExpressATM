import { useState, useEffect } from 'react';
import { Card, Select, DatePicker, Button, Table, Space, Spin, Segmented } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import dayjs from 'dayjs';
import { getAgencies, getAgencyPerformance } from '../api/reportsApi';
import { formatMoney, getLotteryColor } from '../utils/formatters';

const { RangePicker } = DatePicker;

export default function AgencyPerformance() {
  const [agencies, setAgencies] = useState([]);
  const [selectedAgencies, setSelectedAgencies] = useState([]);
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);
  const [groupBy, setGroupBy] = useState('day');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAgencies().then(list => setAgencies(list.map(a => ({ label: a.name, value: a.code }))));
  }, []);

  const handleSearch = async () => {
    if (!selectedAgencies.length || !dateRange) return;
    setLoading(true);
    try {
      const result = await getAgencyPerformance({
        agencyCodes: selectedAgencies,
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        groupBy,
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'Periodo', dataIndex: 'period', key: 'period', fixed: 'left', width: 120 },
    { title: 'Agencia', dataIndex: 'agency_name', key: 'agency_name', width: 200 },
    { title: 'Sorteo', dataIndex: 'lottery_type', key: 'lottery_type', width: 160,
      render: v => <span style={{ color: getLotteryColor(v) }}>{(v || '').replace(/_/g, ' ')}</span> },
    { title: 'Ventas', dataIndex: 'total_sales', key: 'total_sales', width: 140, align: 'right',
      render: v => formatMoney(v), sorter: (a, b) => (a.total_sales || 0) - (b.total_sales || 0) },
    { title: 'Balance', dataIndex: 'avg_balance', key: 'avg_balance', width: 140, align: 'right',
      render: v => formatMoney(v), sorter: (a, b) => (a.avg_balance || 0) - (b.avg_balance || 0) },
    { title: 'Premios', dataIndex: 'total_prizes', key: 'total_prizes', width: 140, align: 'right',
      render: v => formatMoney(v) },
    { title: 'Iteraciones', dataIndex: 'iterations', key: 'iterations', width: 100, align: 'center' },
  ];

  // Build chart data from table rows grouped by period
  const chartData = data?.rows
    ? Object.values(data.rows.reduce((acc, r) => {
        if (!acc[r.period]) acc[r.period] = { period: r.period };
        const key = `${r.agency_name} (${(r.lottery_type || '').replace(/_/g, ' ')})`;
        acc[r.period][key] = r.total_sales;
        return acc;
      }, {}))
    : [];

  const chartKeys = data?.rows
    ? [...new Set(data.rows.map(r => `${r.agency_name} (${(r.lottery_type || '').replace(/_/g, ' ')})`))]
    : [];

  return (
    <Card title="Rendimiento de Agencias por Periodo">
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          mode="multiple" allowClear showSearch optionFilterProp="label"
          placeholder="Seleccionar agencias" style={{ minWidth: 300 }}
          options={agencies} value={selectedAgencies} onChange={setSelectedAgencies}
        />
        <RangePicker value={dateRange} onChange={setDateRange} />
        <Segmented options={[
          { label: 'Día', value: 'day' },
          { label: 'Semana', value: 'week' },
          { label: 'Mes', value: 'month' },
        ]} value={groupBy} onChange={setGroupBy} />
        <Button type="primary" onClick={handleSearch} loading={loading}>Generar</Button>
      </Space>

      <Spin spinning={loading}>
        {data?.rows?.length > 0 && (
          <>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis tickFormatter={v => `$${(v / 1e6).toFixed(1)}M`} />
                <Tooltip formatter={v => formatMoney(v)} />
                <Legend />
                {chartKeys.map((key, i) => (
                  <Line key={key} type="monotone" dataKey={key} stroke={Object.values(getLotteryColor)[i % 7] || `hsl(${i * 50}, 70%, 50%)`} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
            <Table
              dataSource={data.rows.map((r, i) => ({ ...r, key: i }))}
              columns={columns} size="small" scroll={{ x: 1000 }}
              pagination={{ pageSize: 20 }}
            />
          </>
        )}
      </Spin>
    </Card>
  );
}
