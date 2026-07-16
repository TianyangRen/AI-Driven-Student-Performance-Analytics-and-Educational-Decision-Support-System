import { Row, Col, Avatar, Tag, Descriptions } from 'antd';
import { UserOutlined, IdcardOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext.jsx';
import { PageHeader, Panel } from '../components/ui';
import { palette } from '../theme/tokens';

export default function Profile() {
  const { user } = useAuth();
  if (!user) return null;

  const roleLabel = user.role === 'ADMIN' ? 'Administrator' : 'Instructor';

  return (
    <div>
      <PageHeader title="Profile" subtitle="Current account and role permissions" />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Panel hover bodyStyle={{ padding: 28, textAlign: 'center' }}>
            <Avatar
              size={88}
              icon={<UserOutlined />}
              style={{ background: 'linear-gradient(135deg,#38bdf8,#6366f1)', boxShadow: '0 10px 30px -8px rgba(56,189,248,0.6)' }}
            />
            <div style={{ color: palette.textStrong, fontSize: 20, fontWeight: 700, marginTop: 16 }}>
              {user.full_name || user.username}
            </div>
            <div style={{ color: palette.textSecondary, marginTop: 4 }}>@{user.username}</div>
            <div style={{ marginTop: 14 }}>
              <Tag color={user.role === 'ADMIN' ? 'purple' : 'blue'} style={{ borderRadius: 999, padding: '2px 14px' }}>
                {roleLabel}
              </Tag>
            </div>
          </Panel>
        </Col>
        <Col xs={24} lg={16}>
          <Panel title="Account details" icon={<IdcardOutlined />} style={{ height: '100%' }}>
            <Descriptions column={1} bordered size="middle">
              <Descriptions.Item label="User ID">{user.id}</Descriptions.Item>
              <Descriptions.Item label="Username">{user.username}</Descriptions.Item>
              <Descriptions.Item label="Full name">{user.full_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="Email">{user.email || '-'}</Descriptions.Item>
              <Descriptions.Item label="Role">
                <Tag color={user.role === 'ADMIN' ? 'purple' : 'blue'}>{roleLabel}</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Panel>
        </Col>
      </Row>
    </div>
  );
}
