import { useState, useEffect } from 'react';
import { Card, Select, DatePicker, Button, Table, Space, Spin, Tag, Statistic, Row, Col } from 'antd';
import dayjs from 'dayjs';
import { getAgencies, getAgencyDayDetail } from '../api/reportsApi';
import { formatMoney } from '../utils/formatters';

export default function AgencyDayDetail() {
  const [agencies, setAgencies] = useState([]);
  const [selectedAgency, setSelectedAgency] = useState(null);
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getAgencies().then(list => setAgencies(list.map(a => ({ label: a.name, value: a.code }))));
  }, []);

  const handleSearch = async () => {
    if (!selectedAgency || !selectedDate) return;
    setLoading(true);
    try {
      const result = await getAgencyDayDetail(selectedAgency, selectedDate.format('YYYY-MM-DD'));
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'Hora', dataIndex: 'time', key: 'time', width: 180,
      render: v => dayjs(v).format('hh:mm:ss A') },
    { title: 'Sorteo', dataIndex: 'lottery_type', key: 'lottery_type', width: 160,
      render: v => <Tag color="blue">{(v || '').replace(/_/g, ' ')}</Tag> },
    { title: 'Ventas', dataIndex: 'sales', key: 'sales', width: 140, align: 'right',
      render: v => formatMoney(v) },
    { title: 'Balance', dataIndex: 'balance', key: 'balance', width: 140, align: 'right',
      render: v => formatMoney(v) },
    { title: 'Premios', dataIndex: 'prizes', key: 'prizes', width: 140, align: 'right',
      render: v => formatMoney(v) },
    { title: 'Δ Ventas', dataIndex: 'delta_sales', key: 'delta_sales', width: 120, align: 'right',
      render: v => <span style={{ color: v > 0 ? '#52c41a' : v < 0 ? '#ff4d4f' : '#8c8c8c' }}>
        {v > 0 ? '+' : ''}{formatMoney(v)}
      </span> },
    { title: 'Δ Balance', dataIndex: 'delta_balance', key: 'delta_balance', width: 120, align: 'right',
      render: v => <span style={{ color: v > 0 ? '#52c41a' : v < 0 ? '#ff4d4f' : '#8c8c8c' }}>
        {v > 0 ? '+' : ''}{formatMoney(v)}
      </span> },
  ];

  const alertColumns = [
    { title: 'Hora', dataIndex: 'created_at', key: 'created_at', width: 120,
      render: v => dayjs(v).format('hh:mm A') },
    { title: 'Tipo', dataIndex: 'type', key: 'type', width: 150,
      render: v => <Tag color="red">{v}</Tag> },
    { title: 'Sorteo', dataIndex: 'lottery_type', key: 'lottery_type', width: 160,
      render: v => (v || '').replace(/_/g, ' ') },
    { title: 'Mensaje', dataIndex: 'message', key: 'message' },
  ];

  return (
    <Card title="Movimiento Diario de Agencia">
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          showSearch optionFilterProp="label"
          placeholder="Seleccionar agencia" style={{ minWidth: 300 }}
          options={agencies} value={selectedAgency} onChange={setSelectedAgency}
        />
        <DatePicker value={selectedDate} onChange={setSelectedDate} />
        <Button type="primary" onClick={handleSearch} loading={loading}>Consultar</Button>
      </Space>

      <Spin spinning={loading}>
        {data && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}><Statistic title="Agencia" value={data.agency_name || data.agency_code} /></Col>
              <Col span={6}><Statistic title="Iteraciones" value={data.total_iterations} /></Col>
              <Col span={6}><Statistic title="Primera captura" value={data.first_time ? dayjs(data.first_time).format('hh:mm A') : '-'} /></Col>
              <Col span={6}><Statistic title="Última captura" value={data.last_time ? dayjs(data.last_time).format('hh:mm A') : '-'} /></Col>
            </Row>

            <Table
              dataSource={(data.iterations || []).map((r, i) => ({ ...r, key: i }))}
              columns={columns} size="small" scroll={{ x: 1000 }}
              pagination={false}
            />

            {data.alerts?.length > 0 && (
              <Card title="Alertas del día" size="small" style={{ marginTop: 16 }}>
                <Table
                  dataSource={data.alerts.map((a, i) => ({ ...a, key: i }))}
                  columns={alertColumns} size="small" pagination={false}
                />
              </Card>
            )}
          </>
        )}
      </Spin>
    </Card>
  );
}
