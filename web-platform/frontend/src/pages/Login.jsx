import { Form, Input, Button, Typography, message } from 'antd';
import { UserOutlined, LockOutlined, ExperimentOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useI18n } from '../contexts/PreferencesContext.jsx';
import { useState } from 'react';
import { palette } from '../theme/tokens';

export default function Login() {
  const { login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const features = [t('auth.feature1'), t('auth.feature2'), t('auth.feature3')];

  const onFinish = async (values) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success(t('auth.signedIn'));
      const target = location.state?.from?.pathname || '/dashboard';
      navigate(target, { replace: true });
    } catch (e) {
      message.error(e.response?.data?.error?.message || e.message || t('auth.loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-grid" />
      <div
        className="cockpit-panel fade-up"
        style={{
          display: 'flex',
          width: 'min(880px, 100%)',
          overflow: 'hidden',
          padding: 0,
        }}
      >
        {/* Left brand intro */}
        <div
          style={{
            flex: 1,
            padding: '44px 40px',
            background:
              'linear-gradient(155deg, rgba(56,189,248,0.16), rgba(99,102,241,0.12) 60%, transparent)',
            borderRight: '1px solid rgba(94,124,196,0.16)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
          className="auth-hero"
        >
          <div>
            <div className="cockpit-brand__logo" style={{ width: 48, height: 48, fontSize: 24 }}>
              <ExperimentOutlined />
            </div>
            <h2 style={{ color: palette.textStrong, fontSize: 24, margin: '22px 0 8px', fontWeight: 700 }}>
              {t('auth.appName')}
            </h2>
            <p style={{ color: palette.textSecondary, fontSize: 13, lineHeight: 1.7 }}>
              {t('auth.intro')}
            </p>
          </div>
          <div style={{ marginTop: 28 }}>
            {features.map((f) => (
              <div
                key={f}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  color: palette.textSecondary,
                  fontSize: 13,
                  marginBottom: 12,
                }}
              >
                <span style={{ color: palette.cyan }}>
                  <ArrowRightOutlined />
                </span>
                {f}
              </div>
            ))}
          </div>
        </div>

        {/* Right form */}
        <div style={{ width: 380, maxWidth: '100%', padding: '44px 36px' }}>
          <Typography.Title level={4} style={{ color: palette.textStrong, marginTop: 0 }}>
            {t('auth.welcomeBack')}
          </Typography.Title>
          <Typography.Text style={{ color: palette.textSecondary }}>
            {t('auth.signInHint')}
          </Typography.Text>
          <Form layout="vertical" onFinish={onFinish} style={{ marginTop: 24 }} size="large">
            <Form.Item
              name="username"
              label={t('auth.username')}
              rules={[{ required: true, message: t('auth.usernameRequired') }]}
            >
              <Input prefix={<UserOutlined style={{ color: palette.textMuted }} />} placeholder="instructor01" autoFocus />
            </Form.Item>
            <Form.Item
              name="password"
              label={t('auth.password')}
              rules={[{ required: true, message: t('auth.passwordRequired') }]}
            >
              <Input.Password prefix={<LockOutlined style={{ color: palette.textMuted }} />} placeholder="••••••" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 12 }}>
              <Button block type="primary" htmlType="submit" loading={loading}>
                {t('auth.signIn')}
              </Button>
            </Form.Item>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography.Text style={{ color: palette.textMuted, fontSize: 13 }}>
                {t('auth.noAccount')}
              </Typography.Text>
              <Link to="/register">{t('auth.createAccount')}</Link>
            </div>
          </Form>
        </div>
      </div>
    </div>
  );
}
