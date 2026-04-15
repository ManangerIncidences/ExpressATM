import { useState } from 'react';
import { Card, DatePicker, Button, Table, Space, Spin, Segmented } from 'antd';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import dayjs from 'dayjs';
import { getLotteryComparison } from '../api/reportsApi';
import { formatMoney, getLotteryColor } from '../utils/formatters';

const { RangePicker } = DatePicker;

export default function LotteryComparison() {
  const [dateRange, setDateRange] = useState([dayjs().subtract(7, 'day'), dayjs()]);
  const [groupBy, setGroupBy] = useState('day');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!dateRange) return;
    setLoading(true);
    try {
      const result = await getLotteryComparison({
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        groupBy,
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  const lotteryTypes = data?.lottery_types || [];

  const columns = [
    { title: 'Periodo', dataIndex: 'period', key: 'period', width: 120, fixed: 'left' },
    ...lotteryTypes.map(lt => ({
      title: lt.replace(/_/g, ' '),
      dataIndex: lt,
      key: lt,
      width: 160,
      align: 'right',
      render: v => formatMoney(v),
    })),
    { title: 'Total', dataIndex: 'total', key: 'total', width: 160, align: 'right',
      render: v => <strong>{formatMoney(v)}</strong> },
  ];

  return (
    <Card title="Comparativo entre Sorteos">
      <Space wrap style={{ marginBottom: 16 }}>
        <RangePicker value={dateRange} onChange={setDateRange} />
        <Segmented options={[
          { label: 'Día', value: 'day' },
          { label: 'Semana', value: 'week' },
        ]} value={groupBy} onChange={setGroupBy} />
        <Button type="primary" onClick={handleSearch} loading={loading}>Generar</Button>
      </Space>

      <Spin spinning={loading}>
        {data?.rows?.length > 0 && (
          <>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={data.rows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis tickFormatter={v => `$${(v / 1e6).toFixed(1)}M`} />
                <Tooltip formatter={v => formatMoney(v)} />
                <Legend />
                {lotteryTypes.map(lt => (
                  <Line key={lt} type="monotone" dataKey={lt} name={lt.replace(/_/g, ' ')}
                    stroke={getLotteryColor(lt)} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
            <Table
              dataSource={data.rows.map((r, i) => ({ ...r, key: i }))}
              columns={columns} size="small" scroll={{ x: 800 }}
              pagination={false}
            />
          </>
        )}
      </Spin>
    </Card>
  );
}
