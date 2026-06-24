import { Button, Card, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../api/client';

const RISK_COLOR = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' };

export default function Predictions() {
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [running, setRunning] = useState(false);

  const load = () => client.get(`/sections/${sectionId}/predictions`).then((r) => setData(r.data?.data || []));
  useEffect(load, [sectionId]);

  const run = async () => {
    setRunning(true);
    try {
      await client.post(`/sections/${sectionId}/predictions/run`, { force: false });
      message.success('Prediction run completed');
      load();
    } finally { setRunning(false); }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', display: 'flex' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>Risk prediction · Section #{sectionId}</Typography.Title>
        <Button type="primary" loading={running} onClick={run}>Run prediction</Button>
      </Space>
      <Card>
        <Table
          rowKey="prediction_id"
          dataSource={data}
          columns={[
            { title: 'Student', dataIndex: 'anonymized_code' },
            { title: 'Risk probability', dataIndex: 'probability', render: (v) => `${(v * 100).toFixed(1)}%` },
            { title: 'Risk level', dataIndex: 'risk_level', render: (v) => <Tag color={RISK_COLOR[v]}>{v}</Tag> },
            {
              title: 'Actions',
              render: (_, r) => <a onClick={() => navigate(`/sections/${sectionId}/students/${r.student_id}`)}>View details</a>,
            },
          ]}
        />
      </Card>
    </div>
  );
}
