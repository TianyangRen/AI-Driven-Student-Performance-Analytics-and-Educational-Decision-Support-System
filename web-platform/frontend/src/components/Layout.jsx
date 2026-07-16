import { useState } from 'react';
import { Layout as AntLayout, Menu, Dropdown, Avatar, Grid, Button, Tag, Tooltip } from 'antd';
import {
  DashboardOutlined,
  BookOutlined,
  ApartmentOutlined,
  BarChartOutlined,
  ClusterOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  ExperimentOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  SunOutlined,
  MoonOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useI18n } from '../contexts/PreferencesContext.jsx';
import { palette } from '../theme/tokens';

const { Header, Sider, Content } = AntLayout;
const { useBreakpoint } = Grid;

function Brand({ collapsed, t }) {
  return (
    <div className="cockpit-brand" style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}>
      <div className="cockpit-brand__logo">
        <ExperimentOutlined />
      </div>
      {!collapsed && (
        <div>
          <div className="cockpit-brand__title">{t('brand.title')}</div>
          <div className="cockpit-brand__subtitle">{t('brand.subtitle')}</div>
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { t, isLight, toggleMode, lang, toggleLang } = useI18n();
  const screens = useBreakpoint();
  const isMobile = !screens.lg;
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: t('nav.dashboard') },
    { key: '/courses', icon: <BookOutlined />, label: t('nav.courses') },
    { key: '/sections', icon: <ApartmentOutlined />, label: t('nav.sections') },
    { key: '/comparisons', icon: <BarChartOutlined />, label: t('nav.comparisons') },
    { key: '/cohort-insights', icon: <ClusterOutlined />, label: t('nav.cohortInsights') },
    { key: '/reports', icon: <FileTextOutlined />, label: t('nav.reports') },
  ];

  const selectedKey =
    menuItems.find((m) => location.pathname.startsWith(m.key))?.key || '/dashboard';

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: t('user.profile'), onClick: () => navigate('/profile') },
      { type: 'divider' },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: t('user.signOut'),
        danger: true,
        onClick: async () => {
          await logout();
          navigate('/login');
        },
      },
    ],
  };

  const siderContent = (
    <>
      <Brand collapsed={collapsed && !isMobile} t={t} />
      <Menu
        theme={isLight ? 'light' : 'dark'}
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ borderInlineEnd: 'none', background: 'transparent', padding: '6px 4px' }}
      />
      {!(collapsed && !isMobile) && (
        <div style={{ position: 'absolute', bottom: 16, left: 16, right: 16 }}>
          <div
            className="cockpit-panel"
            style={{ padding: 14, fontSize: 12, color: palette.textSecondary }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span className="live-dot" />
              <span style={{ color: palette.textStrong, fontWeight: 600 }}>{t('system.online')}</span>
            </div>
            {t('system.inference')}&nbsp;
            <Tag color="processing" style={{ marginInlineEnd: 0 }}>
              {t('system.sampleData')}
            </Tag>
          </div>
        </div>
      )}
    </>
  );

  const controls = (
    <>
      <Tooltip title={isLight ? t('ctrl.toDark') : t('ctrl.toLight')}>
        <Button
          className="cockpit-ctrl-btn"
          type="text"
          icon={isLight ? <MoonOutlined /> : <SunOutlined />}
          onClick={toggleMode}
        />
      </Tooltip>
      <Tooltip title={lang === 'en' ? t('ctrl.toFr') : t('ctrl.toEn')}>
        <Button
          className="cockpit-ctrl-btn"
          type="text"
          onClick={toggleLang}
          icon={<TranslationOutlined />}
          style={{ paddingInline: 10 }}
        >
          {t('ctrl.langShort')}
        </Button>
      </Tooltip>
    </>
  );

  return (
    <AntLayout style={{ minHeight: '100vh', background: 'transparent' }}>
      {!isMobile && (
        <Sider
          width={236}
          collapsedWidth={80}
          collapsed={collapsed}
          trigger={null}
          style={{
            position: 'relative',
            borderRight: '1px solid var(--cockpit-border-soft)',
            background: 'var(--sider-grad)',
            backdropFilter: 'blur(10px)',
          }}
        >
          {siderContent}
        </Sider>
      )}

      <AntLayout style={{ background: 'transparent' }}>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            padding: '0 20px',
            height: 64,
            borderBottom: '1px solid var(--cockpit-border-soft)',
            background: 'var(--header-bg)',
            backdropFilter: 'blur(10px)',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed((c) => !c)}
              style={{ color: palette.textSecondary }}
            />
            <div style={{ minWidth: 0, overflow: 'hidden' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: palette.textStrong, whiteSpace: 'nowrap' }}>
                {t('header.appTitle')}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: palette.textMuted,
                  whiteSpace: 'nowrap',
                  display: isMobile ? 'none' : 'block',
                }}
              >
                {t('header.appSubtitle')}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {controls}
            <Dropdown menu={userMenu} trigger={['click']}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  cursor: 'pointer',
                  padding: '6px 10px',
                  borderRadius: 12,
                  border: '1px solid var(--cockpit-border)',
                  background: 'var(--chip-bg)',
                }}
              >
                <Avatar
                  size={32}
                  style={{ background: 'linear-gradient(135deg,#38bdf8,#6366f1)' }}
                  icon={<UserOutlined />}
                />
                {!isMobile && (
                  <div style={{ lineHeight: 1.2 }}>
                    <div style={{ fontSize: 13, color: palette.textStrong, fontWeight: 600 }}>
                      {user?.full_name || user?.username}
                    </div>
                    <div style={{ fontSize: 11, color: palette.textSecondary }}>
                      {user?.role === 'ADMIN' ? t('user.administrator') : t('user.instructor')}
                    </div>
                  </div>
                )}
              </div>
            </Dropdown>
          </div>
        </Header>

        {isMobile && (
          <div style={{ padding: '10px 14px 0' }}>
            <Menu
              theme={isLight ? 'light' : 'dark'}
              mode="horizontal"
              selectedKeys={[selectedKey]}
              items={menuItems}
              onClick={({ key }) => navigate(key)}
              style={{ background: 'transparent', borderBottom: 'none', justifyContent: 'center' }}
            />
          </div>
        )}

        <Content
          style={{
            margin: isMobile ? 14 : 24,
            padding: 0,
            minHeight: 280,
          }}
        >
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
