import { useState } from 'react';
import { Card, DatePicker, Button, Table, Select, Space, Spin, Tag } from 'antd';
import dayjs from 'dayjs';
import { getAgencyRanking } from '../api/reportsApi';
import { formatMoney, formatPercent } from '../utils/formatters';

const { RangePicker } = DatePicker;

const LOTTERY_OPTIONS = [
  { label: 'Todos', value: '' },
  { label: 'Chance Express', value: 'CHANCE_EXPRESS' },
  { label: 'Ruleta Express', value: 'RULETA_EXPRESS' },
  { label: 'Chance Extraordinario', value: 'CHANCE_EXTRAORDINARIO' },
  { label: 'Pega 3', value: 'PEGA_3' },
];

export default function AgencyRanking() {
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);
  const [metric, setMetric] = useState('sales');
  const [lotteryType, setLotteryType] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!dateRange) return;
    setLoading(true);
    try {
      const result = await getAgencyRanking({
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        metric,
        lotteryType: lotteryType || undefined,
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: '#', dataIndex: 'rank', key: 'rank', width: 50, align: 'center',
      render: (_, __, i) => i + 1 },
    { title: 'Agencia', dataIndex: 'agency_name', key: 'agency_name', width: 250 },
    { title: 'Código', dataIndex: 'agency_code', key: 'agency_code', width: 100 },
    { title: metric === 'sales' ? 'Ventas Total' : 'Balance Prom.',
      dataIndex: 'value', key: 'value', width: 160, align: 'right',
      render: v => formatMoney(v), sorter: (a, b) => a.value - b.value, defaultSortOrder: 'descend' },
    { title: 'Periodo Anterior', dataIndex: 'prev_value', key: 'prev_value', width: 160, align: 'right',
      render: v => v != null ? formatMoney(v) : '-' },
    { title: 'Variación', dataIndex: 'variation_pct', key: 'variation_pct', width: 120, align: 'right',
      render: v => v != null
        ? <Tag color={v > 0 ? 'green' : v < 0 ? 'red' : 'default'}>{formatPercent(v)}</Tag>
        : '-',
      sorter: (a, b) => (a.variation_pct || 0) - (b.variation_pct || 0),
    },
  ];

  return (
    <Card title="Ranking de Agencias">
      <Space wrap style={{ marginBottom: 16 }}>
        <RangePicker value={dateRange} onChange={setDateRange} />
        <Select value={metric} onChange={setMetric} style={{ width: 140 }}
          options={[
            { label: 'Ventas', value: 'sales' },
            { label: 'Balance', value: 'balance' },
          ]}
        />
        <Select value={lotteryType} onChange={setLotteryType} style={{ width: 200 }}
          options={LOTTERY_OPTIONS} placeholder="Sorteo" />
        <Button type="primary" onClick={handleSearch} loading={loading}>Generar</Button>
      </Space>

      <Spin spinning={loading}>
        {data?.ranking && (
          <Table
            dataSource={data.ranking.map((r, i) => ({ ...r, key: i }))}
            columns={columns} size="small" scroll={{ x: 800 }}
            pagination={{ pageSize: 25 }}
          />
        )}
      </Spin>
    </Card>
  );
}
