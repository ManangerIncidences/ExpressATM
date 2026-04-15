import { useState, useEffect } from 'react';
import { Card, Select, DatePicker, Button, Table, Space, Spin, Tag, Statistic, Row, Col } from 'antd';
import dayjs from 'dayjs';
import { getAgencies, getAlertHistory } from '../api/reportsApi';

const { RangePicker } = DatePicker;

const LOTTERY_OPTIONS = [
  { label: 'Todos', value: '' },
  { label: 'Chance Express', value: 'CHANCE_EXPRESS' },
  { label: 'Ruleta Express', value: 'RULETA_EXPRESS' },
  { label: 'Chance Extraordinario', value: 'CHANCE_EXTRAORDINARIO' },
];

const TYPE_COLORS = {
  threshold: 'volcano',
  growth_variation: 'orange',
  sustained_growth: 'red',
};

export default function AlertHistory() {
  const [agencies, setAgencies] = useState([]);
  const [selectedAgency, setSelectedAgency] = useState(null);
  const [dateRange, setDateRange] = useState([dayjs().subtract(30, 'day'), dayjs()]);
  const [lotteryType, setLotteryType] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAgencies().then(list => setAgencies(list.map(a => ({ label: a.name, value: a.code }))));
  }, []);

  const handleSearch = async () => {
    if (!dateRange) return;
    setLoading(true);
    try {
      const result = await getAlertHistory({
        agencyCode: selectedAgency || undefined,
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        lotteryType: lotteryType || undefined,
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'Agencia', dataIndex: 'agency_name', key: 'agency_name', width: 250 },
    { title: 'Código', dataIndex: 'agency_code', key: 'agency_code', width: 100 },
    { title: 'Total Alertas', dataIndex: 'total_alerts', key: 'total_alerts', width: 110, align: 'center',
      sorter: (a, b) => a.total_alerts - b.total_alerts, defaultSortOrder: 'descend' },
    { title: 'Umbral', dataIndex: 'threshold_count', key: 'threshold', width: 90, align: 'center',
      render: v => v > 0 ? <Tag color="volcano">{v}</Tag> : '-' },
    { title: 'Var. Crec.', dataIndex: 'growth_variation_count', key: 'growth', width: 100, align: 'center',
      render: v => v > 0 ? <Tag color="orange">{v}</Tag> : '-' },
    { title: 'Crec. Sost.', dataIndex: 'sustained_growth_count', key: 'sustained', width: 100, align: 'center',
      render: v => v > 0 ? <Tag color="red">{v}</Tag> : '-' },
    { title: 'Sorteos', dataIndex: 'lottery_types', key: 'lottery_types',
      render: types => (types || []).map(t => (
        <Tag key={t} color="blue" style={{ marginBottom: 2 }}>{t.replace(/_/g, ' ')}</Tag>
      )),
    },
    { title: 'Días con Alerta', dataIndex: 'days_with_alerts', key: 'days', width: 120, align: 'center' },
  ];

  return (
    <Card title="Historial de Alertas">
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          showSearch allowClear optionFilterProp="label"
          placeholder="Agencia (opcional)" style={{ minWidth: 300 }}
          options={agencies} value={selectedAgency} onChange={setSelectedAgency}
        />
        <RangePicker value={dateRange} onChange={setDateRange} />
        <Select value={lotteryType} onChange={setLotteryType} style={{ width: 200 }}
          options={LOTTERY_OPTIONS} />
        <Button type="primary" onClick={handleSearch} loading={loading}>Consultar</Button>
      </Space>

      <Spin spinning={loading}>
        {data && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}><Statistic title="Total Alertas" value={data.total_alerts} /></Col>
              <Col span={6}><Statistic title="Agencias Afectadas" value={data.agencies_count} /></Col>
              <Col span={6}><Statistic title="Días con Alertas" value={data.days_with_alerts} /></Col>
              <Col span={6}><Statistic title="Promedio/Día" value={data.avg_per_day} precision={1} /></Col>
            </Row>
            <Table
              dataSource={(data.by_agency || []).map((r, i) => ({ ...r, key: i }))}
              columns={columns} size="small" scroll={{ x: 1000 }}
              pagination={{ pageSize: 20 }}
            />
          </>
        )}
      </Spin>
    </Card>
  );
}
