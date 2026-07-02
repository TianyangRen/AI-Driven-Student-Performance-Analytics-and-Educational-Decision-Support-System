import { Form, Input, Button, Typography, message } from 'antd';
import { UserOutlined, LockOutlined, ExperimentOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useState } from 'react';
import { palette } from '../theme/tokens';

const features = [
  'Class overview · multi-dimensional snapshots',
  'AI risk prediction · SHAP explainability',
  'Trend / distribution / cohort comparison',
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('Signed in');
      const target = location.state?.from?.pathname || '/dashboard';
      navigate(target, { replace: true });
    } catch (e) {
      message.error(e.response?.data?.error?.message || e.message || 'Login failed');
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
            <h2 style={{ color: '#fff', fontSize: 24, margin: '22px 0 8px', fontWeight: 700 }}>
              Student Performance Analytics<br />& Decision Support
            </h2>
            <p style={{ color: palette.textSecondary, fontSize: 13, lineHeight: 1.7 }}>
              Turn quizzes, assignments, attendance and learning activity into clear, traceable
              and actionable teaching insights.
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
          <Typography.Title level={4} style={{ color: '#fff', marginTop: 0 }}>
            Welcome back 👋
          </Typography.Title>
          <Typography.Text style={{ color: palette.textSecondary }}>
            Sign in to enter the cockpit
          </Typography.Text>
          <Form layout="vertical" onFinish={onFinish} style={{ marginTop: 24 }} size="large">
            <Form.Item
              name="username"
              label="Username"
              rules={[{ required: true, message: 'Please enter your username' }]}
            >
              <Input prefix={<UserOutlined style={{ color: palette.textMuted }} />} placeholder="instructor01" autoFocus />
            </Form.Item>
            <Form.Item
              name="password"
              label="Password"
              rules={[{ required: true, message: 'Please enter your password' }]}
            >
              <Input.Password prefix={<LockOutlined style={{ color: palette.textMuted }} />} placeholder="••••••" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 12 }}>
              <Button block type="primary" htmlType="submit" loading={loading}>
                Sign in
              </Button>
            </Form.Item>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography.Text style={{ color: palette.textMuted, fontSize: 13 }}>
                No account yet?
              </Typography.Text>
              <Link to="/register">Create account</Link>
            </div>
          </Form>
        </div>
      </div>
    </div>
  );
}
