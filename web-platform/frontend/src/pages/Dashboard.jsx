import { Card, Col, Row, Statistic, Typography, Alert, List, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  return (
    <div>
      <Typography.Title level={3}>Welcome, {user?.full_name || user?.username}</Typography.Title>
      <Alert
        showIcon
        type="info"
        message="Prototype notice"
        description="This is the V1.1 design prototype. Aside from sign-in / sign-up, all displayed metrics are sample data. Click any section to open its overview."
        style={{ marginBottom: 16 }}
      />
      <Row gutter={16}>
        <Col span={6}><Card><Statistic title="My courses" value={2} /></Card></Col>
        <Col span={6}><Card><Statistic title="Sections" value={3} /></Card></Col>
        <Col span={6}><Card><Statistic title="High-risk students" value={12} valueStyle={{ color: '#cf1322' }} /></Card></Col>
        <Col span={6}><Card><Statistic title="Pending reports" value={1} /></Card></Col>
      </Row>
      <Card title="Quick access to sections" style={{ marginTop: 16 }}>
        <List
          dataSource={[
            { id: 1001, name: 'COMP8567 · Section 01', risk: 5 },
            { id: 1002, name: 'COMP8567 · Section 02', risk: 3 },
            { id: 1003, name: 'COMP8001 · Section 01', risk: 4 },
          ]}
          renderItem={(item) => (
            <List.Item
              actions={[
                <a onClick={() => navigate(`/sections/${item.id}/overview`)}>Overview</a>,
                <a onClick={() => navigate(`/sections/${item.id}/import`)}>Import data</a>,
                <a onClick={() => navigate(`/sections/${item.id}/predictions`)}>Risk prediction</a>,
              ]}
            >
              <List.Item.Meta
                title={item.name}
                description={<Tag color="red">{item.risk} high-risk</Tag>}
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
