import { Card, Form, Input, Button, Typography, message, Select } from 'antd';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { useState } from 'react';

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
    <div style={{ minHeight: '100vh', background: '#f0f2f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card style={{ width: 420 }} title={<Typography.Title level={4} style={{ margin: 0 }}>Create account</Typography.Title>}>
        <Form layout="vertical" onFinish={onFinish} initialValues={{ role: 'INSTRUCTOR' }}>
          <Form.Item name="username" label="Username" rules={[{ required: true }]}>
            <Input placeholder="instructor01" />
          </Form.Item>
          <Form.Item name="full_name" label="Full name">
            <Input placeholder="Demo Instructor" />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ type: 'email', message: 'Please enter a valid email' }]}>
            <Input placeholder="you@example.com" />
          </Form.Item>
          <Form.Item name="role" label="Role">
            <Select
              options={[
                { value: 'INSTRUCTOR', label: 'Instructor' },
                { value: 'ADMIN', label: 'Administrator' },
              ]}
            />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button block type="primary" htmlType="submit" loading={loading}>Sign up & sign in</Button>
          </Form.Item>
          <Typography.Text type="secondary">Already have an account? <Link to="/login">Back to sign in</Link></Typography.Text>
        </Form>
      </Card>
    </div>
  );
}
