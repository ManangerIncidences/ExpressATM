import { useState } from 'react';
import { Card, DatePicker, Button, Space, Spin, Statistic, Row, Col, Table, Tag } from 'antd';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
         BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import dayjs from 'dayjs';
import { getConfirmationRate } from '../api/reportsApi';

const { RangePicker } = DatePicker;

const STATUS_COLORS = {
  pendiente: '#faad14',
  reportada: '#1890ff',
  confirmada: '#52c41a',
};

export default function ConfirmationRate() {
  const [dateRange, setDateRange] = useState([dayjs().subtract(30, 'day'), dayjs()]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!dateRange) return;
    setLoading(true);
    try {
      const result = await getConfirmationRate({
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const pieData = data ? [
    { name: 'Pendientes', value: data.pending, color: STATUS_COLORS.pendiente },
    { name: 'Reportadas', value: data.reported, color: STATUS_COLORS.reportada },
    { name: 'Confirmadas', value: data.confirmed, color: STATUS_COLORS.confirmada },
  ].filter(d => d.value > 0) : [];

  const SPANISH_LABELS = {
    alert_type: 'Tipo de Alerta',
    total: 'Total',
    reported: 'Reportadas',
    confirmed: 'Confirmadas',
    report_rate: '% Reportadas',
    confirm_rate: '% Confirmadas',
    threshold: 'Umbral',
    growth_variation: 'Variación de Crecimiento',
    sustained_growth: 'Crecimiento Sostenido',
  };

  const byTypeColumns = [
    { title: 'Tipo de Alerta', dataIndex: 'alert_type', key: 'type', width: 180,
      render: v => <Tag>{SPANISH_LABELS[v] || v}</Tag> },
    { title: 'Total', dataIndex: 'total', key: 'total', width: 100, align: 'center' },
    { title: 'Reportadas', dataIndex: 'reported', key: 'reported', width: 110, align: 'center' },
    { title: 'Confirmadas', dataIndex: 'confirmed', key: 'confirmed', width: 110, align: 'center' },
    { title: 'Tasa Reporte', dataIndex: 'report_rate', key: 'rr', width: 120, align: 'center',
      render: v => <span style={{ color: v >= 80 ? '#52c41a' : v >= 50 ? '#faad14' : '#ff4d4f' }}>
        {v?.toFixed(1)}%
      </span> },
    { title: 'Tasa Confirmación', dataIndex: 'confirm_rate', key: 'cr', width: 130, align: 'center',
      render: v => <span style={{ color: v >= 80 ? '#52c41a' : v >= 50 ? '#faad14' : '#ff4d4f' }}>
        {v?.toFixed(1)}%
      </span> },
  ];

  return (
    <Card title="Tasa de Confirmación de Alertas">
      <Space wrap style={{ marginBottom: 16 }}>
        <RangePicker value={dateRange} onChange={setDateRange} />
        <Button type="primary" onClick={handleSearch} loading={loading}>Consultar</Button>
      </Space>

      <Spin spinning={loading}>
        {data && (
          <>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={4}><Statistic title="Total Generadas" value={data.total} /></Col>
              <Col span={4}><Statistic title="Pendientes" value={data.pending} valueStyle={{ color: STATUS_COLORS.pendiente }} /></Col>
              <Col span={4}><Statistic title="Reportadas" value={data.reported} valueStyle={{ color: STATUS_COLORS.reportada }} /></Col>
              <Col span={4}><Statistic title="Confirmadas" value={data.confirmed} valueStyle={{ color: STATUS_COLORS.confirmada }} /></Col>
              <Col span={4}><Statistic title="Tasa de Reporte" value={data.report_rate} precision={1} suffix="%" /></Col>
              <Col span={4}><Statistic title="Tasa de Confirmación" value={data.confirm_rate} precision={1} suffix="%" /></Col>
            </Row>

            {data.avg_response_minutes != null && (
              <Row style={{ marginBottom: 16 }}>
                <Col span={8}>
                  <Statistic
                    title="Tiempo Promedio de Respuesta"
                    value={data.avg_response_minutes < 60
                      ? data.avg_response_minutes
                      : (data.avg_response_minutes / 60).toFixed(1)}
                    suffix={data.avg_response_minutes < 60 ? 'min' : 'hrs'}
                    valueStyle={{ color: data.avg_response_minutes < 30 ? '#52c41a' : data.avg_response_minutes < 120 ? '#faad14' : '#ff4d4f' }}
                  />
                </Col>
              </Row>
            )}

            <Row gutter={24}>
              <Col span={10}>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                      outerRadius={100} innerRadius={50} label>
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </Col>
              <Col span={14}>
                <Table
                  dataSource={(data.by_type || []).map((r, i) => ({ ...r, key: i }))}
                  columns={byTypeColumns} size="small" pagination={false}
                />
              </Col>
            </Row>

            {/* Tendencia diaria */}
            {data.daily_trend?.length > 1 && (
              <Card title="Tendencia Diaria de Alertas" size="small" style={{ marginTop: 16 }}>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={data.daily_trend.map(d => ({
                    ...d,
                    day: dayjs(d.day).format('dd DD/MM'),
                    no_reportadas: d.total - d.reported,
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="reported" name="Reportadas" stackId="a" fill={STATUS_COLORS.reportada} />
                    <Bar dataKey="confirmed" name="Confirmadas" stackId="a" fill={STATUS_COLORS.confirmada} />
                    <Bar dataKey="no_reportadas" name="Sin Reportar" stackId="a" fill={STATUS_COLORS.pendiente} />
                    <Legend />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            )}
          </>
        )}
      </Spin>
    </Card>
  );
}
