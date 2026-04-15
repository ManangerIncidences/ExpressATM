import { useState, useEffect } from 'react';
import { ConfigProvider, theme, Layout, Menu, Button } from 'antd';
import {
  LineChartOutlined,
  CalendarOutlined,
  TrophyOutlined,
  SwapOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import GlobalSummary from './components/GlobalSummary';
import AgencyPerformance from './components/AgencyPerformance';
import AgencyDayDetail from './components/AgencyDayDetail';
import AgencyRanking from './components/AgencyRanking';
import LotteryComparison from './components/LotteryComparison';
import AlertHistory from './components/AlertHistory';
import ConfirmationRate from './components/ConfirmationRate';

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: 'global', icon: <DashboardOutlined />, label: 'Resumen Global' },
  { key: 'performance', icon: <LineChartOutlined />, label: 'Rendimiento Agencias' },
  { key: 'day-detail', icon: <CalendarOutlined />, label: 'Movimiento Diario' },
  { key: 'ranking', icon: <TrophyOutlined />, label: 'Ranking Agencias' },
  { key: 'lottery', icon: <SwapOutlined />, label: 'Comparativo Sorteos' },
  { key: 'alerts', icon: <AlertOutlined />, label: 'Historial Alertas' },
  { key: 'confirmation', icon: <CheckCircleOutlined />, label: 'Tasa Confirmación' },
];

const components = {
  'global': GlobalSummary,
  'performance': AgencyPerformance,
  'day-detail': AgencyDayDetail,
  'ranking': AgencyRanking,
  'lottery': LotteryComparison,
  'alerts': AlertHistory,
  'confirmation': ConfirmationRate,
};

export default function App() {
  const [activeKey, setActiveKey] = useState('global');
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('theme') === 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  const toggleTheme = () => {
    const next = !darkMode;
    setDarkMode(next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };

  const ActiveComponent = components[activeKey];

  return (
    <ConfigProvider
      theme={{
        algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: { colorPrimary: '#1890ff', borderRadius: 6 },
      }}
    >
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 24px', background: '#1890ff',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <a href="/" style={{ color: '#fff', fontSize: 16, textDecoration: 'none' }}>
              <ArrowLeftOutlined /> Volver
            </a>
            <span style={{ color: '#fff', fontSize: 20, fontWeight: 600 }}>
              ExpressATM — Reportes
            </span>
          </div>
          <Button ghost size="small" onClick={toggleTheme}>
            {darkMode ? '☀️ Claro' : '🌙 Oscuro'}
          </Button>
        </Header>
        <Layout>
          <Sider width={240} breakpoint="lg" collapsedWidth={60}
            style={{ background: darkMode ? '#141414' : '#fff' }}>
            <Menu
              mode="inline"
              selectedKeys={[activeKey]}
              items={menuItems}
              onClick={({ key }) => setActiveKey(key)}
              style={{ height: '100%', borderRight: 0, paddingTop: 8 }}
            />
          </Sider>
          <Content style={{ padding: 24, minHeight: 280 }}>
            <ActiveComponent />
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
