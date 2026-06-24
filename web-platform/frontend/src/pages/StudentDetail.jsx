import { Card, Col, Row, Typography, Descriptions, Tag, Table, Alert } from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import client from '../api/client';

const RISK_COLOR = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' };

export default function StudentDetail() {
  const { sectionId, studentId } = useParams();
  const [profile, setProfile] = useState(null);
  const [explanation, setExplanation] = useState(null);

  useEffect(() => {
    client.get(`/sections/${sectionId}/students/${studentId}/profile`).then((r) => setProfile(r.data?.data));
    client.get(`/predictions/${90000 + parseInt(studentId, 10)}/explanation`).then((r) => setExplanation(r.data?.data));
  }, [sectionId, studentId]);

  if (!profile) return null;

  const radarOption = {
    radar: {
      indicator: [
        { name: 'Mastery', max: 1 },
        { name: 'Stability', max: 1 },
        { name: 'Engagement', max: 1 },
        { name: 'Improvement', max: 0.5, min: -0.3 },
      ],
    },
    series: [{
      type: 'radar',
      data: [{
        value: [profile.indicators.mastery, profile.indicators.stability, profile.indicators.engagement, profile.indicators.improvement],
        name: 'Current indicators',
      }],
    }],
  };
  const trendOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: profile.trend.map((t) => `W${t.week}`) },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, data: profile.trend.map((t) => t.score) }],
  };

  return (
    <div>
      <Typography.Title level={3}>Student detail · {profile.student.anonymized_code}</Typography.Title>
      <Descriptions bordered column={3}>
        <Descriptions.Item label="Anonymized code">{profile.student.anonymized_code}</Descriptions.Item>
        <Descriptions.Item label="Risk level"><Tag color={RISK_COLOR[profile.risk.level]}>{profile.risk.level}</Tag></Descriptions.Item>
        <Descriptions.Item label="Risk probability">{(profile.risk.probability * 100).toFixed(1)}%</Descriptions.Item>
      </Descriptions>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}><Card title="Multi-dimensional indicators"><ReactECharts option={radarOption} style={{ height: 320 }} /></Card></Col>
        <Col span={12}><Card title="Weekly score trend"><ReactECharts option={trendOption} style={{ height: 320 }} /></Card></Col>
      </Row>
      <Card title="Assessment details" style={{ marginTop: 16 }}>
        <Table
          rowKey="name"
          dataSource={profile.assessments}
          pagination={false}
          columns={[
            { title: 'Assessment', dataIndex: 'name' },
            { title: 'Type', dataIndex: 'type' },
            { title: 'Score', dataIndex: 'score' },
            { title: 'Weight (%)', dataIndex: 'weight' },
          ]}
        />
      </Card>
      {explanation && (
        <Card title="Risk explanation (SHAP)" style={{ marginTop: 16 }}>
          <Alert type="warning" showIcon message={explanation.disclaimer} style={{ marginBottom: 12 }} />
          <Table
            rowKey="feature"
            pagination={false}
            dataSource={explanation.top_factors}
            columns={[
              { title: 'Feature', dataIndex: 'display_name' },
              { title: 'Contribution', dataIndex: 'contribution', render: (v) => v.toFixed(3) },
              { title: 'Direction', dataIndex: 'direction', render: (v) => v === 'increase_risk' ? <Tag color="red">↑ raises risk</Tag> : <Tag color="green">↓ reduces risk</Tag> },
            ]}
          />
          <div style={{ marginTop: 12 }}><b>Suggestion: </b>{explanation.suggestion}</div>
        </Card>
      )}
    </div>
  );
}
