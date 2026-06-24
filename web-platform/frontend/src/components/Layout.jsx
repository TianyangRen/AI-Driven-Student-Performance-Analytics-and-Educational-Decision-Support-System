import { Layout as AntLayout, Menu, Dropdown, Avatar, Space, Typography } from 'antd';
import {
  DashboardOutlined,
  BookOutlined,
  ApartmentOutlined,
  BarChartOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';

const { Header, Sider, Content } = AntLayout;

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/courses', icon: <BookOutlined />, label: 'Courses' },
  { key: '/sections', icon: <ApartmentOutlined />, label: 'Sections' },
  { key: '/comparisons', icon: <BarChartOutlined />, label: 'Comparisons' },
  { key: '/reports', icon: <FileTextOutlined />, label: 'Reports' },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const selectedKey =
    menuItems.find((m) => location.pathname.startsWith(m.key))?.key || '/dashboard';

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: 'Profile', onClick: () => navigate('/profile') },
      { type: 'divider' },
      { key: 'logout', icon: <LogoutOutlined />, label: 'Sign out', onClick: async () => { await logout(); navigate('/login'); } },
    ],
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsible style={{ background: '#001529' }}>
        <div style={{ color: '#fff', padding: 16, fontWeight: 600, fontSize: 14 }}>
          <ExperimentOutlined /> Student Analytics
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography.Text type="secondary">AI-Driven Student Performance Analytics & Educational Decision Support · V1.1 Prototype</Typography.Text>
          <Dropdown menu={userMenu}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} />
              <span>{user?.full_name || user?.username} · {user?.role}</span>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, background: '#fff', padding: 24, borderRadius: 6 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
