import { Form, Input, Button, Typography, message, Select } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, IdcardOutlined, ExperimentOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useI18n } from '../contexts/PreferencesContext.jsx';
import { useState } from 'react';
import { palette } from '../theme/tokens';

export default function Register() {
  const { register } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      await register(values);
      message.success(t('auth.registeredSignedIn'));
      navigate('/dashboard', { replace: true });
    } catch (e) {
      const details = e.response?.data?.error?.details;
      message.error(details?.[0]?.reason || e.response?.data?.error?.message || t('auth.registerFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-grid" />
      <div
        className="cockpit-panel fade-up"
        style={{ width: 'min(440px, 100%)', padding: '40px 36px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <div className="cockpit-brand__logo">
            <ExperimentOutlined />
          </div>
          <div>
            <Typography.Title level={4} style={{ color: palette.textStrong, margin: 0 }}>
              {t('auth.registerTitle')}
            </Typography.Title>
            <Typography.Text style={{ color: palette.textSecondary, fontSize: 12 }}>
              {t('auth.registerHint')}
            </Typography.Text>
          </div>
        </div>

        <Form layout="vertical" onFinish={onFinish} initialValues={{ role: 'INSTRUCTOR' }} size="large">
          <Form.Item name="username" label={t('auth.username')} rules={[{ required: true, message: t('auth.usernameRequired2') }]}>
            <Input prefix={<UserOutlined style={{ color: palette.textMuted }} />} placeholder="instructor01" />
          </Form.Item>
          <Form.Item name="full_name" label={t('auth.fullName')}>
            <Input prefix={<IdcardOutlined style={{ color: palette.textMuted }} />} placeholder="Demo Instructor" />
          </Form.Item>
          <Form.Item name="email" label={t('auth.email')} rules={[{ type: 'email', message: t('auth.emailInvalid') }]}>
            <Input prefix={<MailOutlined style={{ color: palette.textMuted }} />} placeholder="you@example.com" />
          </Form.Item>
          <Form.Item name="role" label={t('auth.role')}>
            <Select
              options={[
                { value: 'INSTRUCTOR', label: t('user.instructor') },
                { value: 'ADMIN', label: t('user.administrator') },
              ]}
            />
          </Form.Item>
          <Form.Item name="password" label={t('auth.password')} rules={[{ required: true, min: 6, message: t('auth.passwordMin') }]}>
            <Input.Password prefix={<LockOutlined style={{ color: palette.textMuted }} />} placeholder={t('auth.passwordMin')} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 12 }}>
            <Button block type="primary" htmlType="submit" loading={loading}>
              {t('auth.signUpSignIn')}
            </Button>
          </Form.Item>
          <Typography.Text style={{ color: palette.textMuted, fontSize: 13 }}>
            {t('auth.alreadyHave')} <Link to="/login">{t('auth.backSignIn')}</Link>
          </Typography.Text>
        </Form>
      </div>
    </div>
  );
}
