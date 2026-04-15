import { useState } from 'react';
import { Card, DatePicker, Button, Table, Space, Spin, Statistic, Row, Col, Select, Tag, Segmented } from 'antd';
import { PieChart, Pie, Cell, Tooltip as ReTooltip, Legend, ResponsiveContainer,
         AreaChart, Area, XAxis, YAxis, CartesianGrid } from 'recharts';
import dayjs from 'dayjs';
import { getGlobalSummary } from '../api/reportsApi';
import { formatMoney, getLotteryColor } from '../utils/formatters';

const { RangePicker } = DatePicker;

const PIE_COLORS = ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96'];

export default function GlobalSummary() {
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);
  const [topN, setTopN] = useState(20);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!dateRange) return;
    setLoading(true);
    try {
      const result = await getGlobalSummary({
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        topN,
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const kpis = data?.kpis || {};

  const columns = [
    { title: '#', dataIndex: 'rank', key: 'rank', width: 50, align: 'center' },
    { title: 'Agencia', dataIndex: 'agency_name', key: 'agency_name', width: 280 },
    { title: 'Código', dataIndex: 'agency_code', key: 'agency_code', width: 100 },
    { title: 'Ventas Total', dataIndex: 'total_sales', key: 'total_sales', width: 150, align: 'right',
      render: v => formatMoney(v), sorter: (a, b) => a.total_sales - b.total_sales, defaultSortOrder: 'descend' },
    { title: 'Balance Prom.', dataIndex: 'avg_balance', key: 'avg_balance', width: 140, align: 'right',
      render: v => formatMoney(v) },
    { title: 'Premios', dataIndex: 'total_prizes', key: 'total_prizes', width: 130, align: 'right',
      render: v => formatMoney(v) },
    { title: 'Iteraciones', dataIndex: 'iterations', key: 'iterations', width: 100, align: 'center' },
    { title: 'Alertas', dataIndex: 'alerts', key: 'alerts', width: 80, align: 'center',
      render: v => v > 0 ? <Tag color="red">{v}</Tag> : <span style={{ color: '#8c8c8c' }}>0</span> },
    { title: '% del Total', dataIndex: 'pct_of_total', key: 'pct', width: 100, align: 'center',
      render: v => <span style={{ fontWeight: 500 }}>{v}%</span> },
  ];

  const pieData = (data?.lottery_distribution || []).map((d, i) => ({
    name: (d.lottery_type || '').replace(/_/g, ' '),
    value: d.total_sales,
    pct: d.pct,
    fill: PIE_COLORS[i % PIE_COLORS.length],
  }));

  const trendData = (data?.daily_trend || []).map(d => ({
    ...d,
    day: dayjs(d.day).format('dd DD'),
  }));

  return (
    <Card title="Resumen Global de Rendimiento">
      <Space wrap style={{ marginBottom: 16 }}>
        <RangePicker value={dateRange} onChange={setDateRange} />
        <Select value={topN} onChange={setTopN} style={{ width: 120 }}
          options={[
            { label: 'Top 10', value: 10 },
            { label: 'Top 20', value: 20 },
            { label: 'Top 50', value: 50 },
            { label: 'Todas', value: 999 },
          ]}
        />
        <Button type="primary" onClick={handleSearch} loading={loading}>Generar</Button>
      </Space>

      <Spin spinning={loading}>
        {data && (
          <>
            {/* KPI Cards */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={12} sm={8} md={4}>
                <Card size="small" bordered>
                  <Statistic title="Ventas Totales" value={kpis.total_sales} formatter={v => formatMoney(v)} />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small" bordered>
                  <Statistic title="Agencias Activas" value={kpis.total_agencies} />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small" bordered>
                  <Statistic title="Alertas Generadas" value={kpis.total_alerts}
                    valueStyle={{ color: kpis.total_alerts > 0 ? '#ff4d4f' : undefined }} />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small" bordered>
                  <Statistic title="Prom. Ventas/Agencia" value={kpis.avg_sales_per_agency}
                    formatter={v => formatMoney(v)} />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small" bordered>
                  <Statistic title="Días en Periodo" value={kpis.days_in_period} />
                </Card>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Card size="small" bordered>
                  <Statistic title="Sorteos Activos" value={kpis.lottery_types_count} />
                </Card>
              </Col>
            </Row>

            {/* Charts row */}
            <Row gutter={24} style={{ marginBottom: 24 }}>
              <Col xs={24} md={10}>
                <Card title="Distribución por Sorteo" size="small">
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        outerRadius={90} innerRadius={40} label={({ pct }) => `${pct}%`}>
                        {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                      </Pie>
                      <ReTooltip formatter={v => formatMoney(v)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
              <Col xs={24} md={14}>
                <Card title="Tendencia Diaria de Ventas" size="small">
                  <ResponsiveContainer width="100%" height={260}>
                    <AreaChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                      <YAxis tickFormatter={v => `$${(v / 1e6).toFixed(1)}M`} />
                      <ReTooltip formatter={v => formatMoney(v)} />
                      <Area type="monotone" dataKey="total_sales" name="Ventas" stroke="#1890ff" fill="#1890ff" fillOpacity={0.15} />
                    </AreaChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
            </Row>

            {/* Top agencies table */}
            <Card title={`Top ${data.top_agencies?.length || 0} Agencias`} size="small">
              <Table
                dataSource={(data.top_agencies || []).map(r => ({ ...r, key: r.rank }))}
                columns={columns} size="small" scroll={{ x: 1000 }}
                pagination={{ pageSize: 25 }}
              />
            </Card>
          </>
        )}
      </Spin>
    </Card>
  );
}
