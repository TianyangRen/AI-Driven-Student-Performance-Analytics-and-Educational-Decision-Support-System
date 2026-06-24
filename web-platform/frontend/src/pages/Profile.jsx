import { Card, Descriptions, Typography, Tag } from 'antd';
import { useAuth } from '../contexts/AuthContext.jsx';

export default function Profile() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <div>
      <Typography.Title level={3}>Profile</Typography.Title>
      <Card>
        <Descriptions bordered column={1}>
          <Descriptions.Item label="User ID">{user.id}</Descriptions.Item>
          <Descriptions.Item label="Username">{user.username}</Descriptions.Item>
          <Descriptions.Item label="Full name">{user.full_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="Email">{user.email || '-'}</Descriptions.Item>
          <Descriptions.Item label="Role"><Tag color={user.role === 'ADMIN' ? 'purple' : 'blue'}>{user.role}</Tag></Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
