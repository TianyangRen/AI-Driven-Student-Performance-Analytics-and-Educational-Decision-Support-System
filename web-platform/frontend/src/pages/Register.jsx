import { Form, Input, Button, Typography, message, Select } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, IdcardOutlined, ExperimentOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useState } from 'react';
import { palette } from '../theme/tokens';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      await register(values);
      message.success('Account created and signed in');
      navigate('/dashboard', { replace: true });
    } catch (e) {
      const details = e.response?.data?.error?.details;
      message.error(details?.[0]?.reason || e.response?.data?.error?.message || 'Registration failed');
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
            <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>
              Create account
            </Typography.Title>
            <Typography.Text style={{ color: palette.textSecondary, fontSize: 12 }}>
              The first user can register as instructor / admin
            </Typography.Text>
          </div>
        </div>

        <Form layout="vertical" onFinish={onFinish} initialValues={{ role: 'INSTRUCTOR' }} size="large">
          <Form.Item name="username" label="Username" rules={[{ required: true, message: 'Please enter a username' }]}>
            <Input prefix={<UserOutlined style={{ color: palette.textMuted }} />} placeholder="instructor01" />
          </Form.Item>
          <Form.Item name="full_name" label="Full name">
            <Input prefix={<IdcardOutlined style={{ color: palette.textMuted }} />} placeholder="Demo Instructor" />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ type: 'email', message: 'Please enter a valid email' }]}>
            <Input prefix={<MailOutlined style={{ color: palette.textMuted }} />} placeholder="you@example.com" />
          </Form.Item>
          <Form.Item name="role" label="Role">
            <Select
              options={[
                { value: 'INSTRUCTOR', label: 'Instructor' },
                { value: 'ADMIN', label: 'Administrator' },
              ]}
            />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true, min: 6, message: 'At least 6 characters' }]}>
            <Input.Password prefix={<LockOutlined style={{ color: palette.textMuted }} />} placeholder="At least 6 characters" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 12 }}>
            <Button block type="primary" htmlType="submit" loading={loading}>
              Sign up & sign in
            </Button>
          </Form.Item>
          <Typography.Text style={{ color: palette.textMuted, fontSize: 13 }}>
            Already have an account? <Link to="/login">Back to sign in</Link>
          </Typography.Text>
        </Form>
      </div>
    </div>
  );
}
