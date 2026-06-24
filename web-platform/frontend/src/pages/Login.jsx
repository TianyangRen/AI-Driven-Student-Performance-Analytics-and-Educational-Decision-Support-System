import { Card, Form, Input, Button, Typography, message, Space } from 'antd';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useState } from 'react';

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
    <div style={{ minHeight: '100vh', background: '#f0f2f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card style={{ width: 380 }} title={<Typography.Title level={4} style={{ margin: 0 }}>Sign in</Typography.Title>}>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="username" label="Username" rules={[{ required: true, message: 'Please enter your username' }]}>
            <Input autoFocus placeholder="instructor01" />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true, message: 'Please enter your password' }]}>
            <Input.Password placeholder="••••••" />
          </Form.Item>
          <Form.Item>
            <Button block type="primary" htmlType="submit" loading={loading}>Sign in</Button>
          </Form.Item>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Typography.Text type="secondary">No account yet?</Typography.Text>
            <Link to="/register">Create account</Link>
          </Space>
        </Form>
      </Card>
    </div>
  );
}
