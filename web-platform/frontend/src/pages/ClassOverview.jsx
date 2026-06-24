import { Card, Col, Row, Statistic, Typography, Table, Tag, Button, message } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import client from '../api/client';

const RISK_COLOR = { HIGH: 'red', MEDIUM: 'orange', LOW: 'green' };

export default function ClassOverview() {
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [students, setStudents] = useState([]);

  const load = () => {
    client.get(`/sections/${sectionId}/overview`).then((r) => setOverview(r.data?.data));
    client.get(`/sections/${sectionId}/students`).then((r) => setStudents(r.data?.data || []));
  };
  useEffect(load, [sectionId]);

  const recalc = async () => {
    await client.post(`/sections/${sectionId}/analytics/recalculate`);
    message.success('Recalculation triggered');
    load();
  };

  if (!overview) return null;

  const distOption = {
    tooltip: {},
    xAxis: { type: 'category', data: overview.score_distribution.map((d) => d.range) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: overview.score_distribution.map((d) => d.count) }],
  };
  const trendOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: overview.trend.map((t) => `W${t.week}`) },
    yAxis: { type: 'value', min: 50, max: 100 },
    series: [{ type: 'line', smooth: true, data: overview.trend.map((t) => t.average) }],
  };

  return (
    <div>
      <Typography.Title level={3}>
        Class overview · {overview.section.course_code} · {overview.section.section_code}
        <Button style={{ float: 'right' }} onClick={recalc}>Recalculate</Button>
      </Typography.Title>
      <Row gutter={16}>
        <Col span={6}><Card><Statistic title="Students" value={overview.kpis.student_count} /></Card></Col>
        <Col span={6}><Card><Statistic title="Average score" value={overview.kpis.average_score} /></Card></Col>
        <Col span={6}><Card><Statistic title="Median" value={overview.kpis.median_score} /></Card></Col>
        <Col span={6}><Card><Statistic title="Pass rate" value={overview.kpis.pass_rate * 100} suffix="%" /></Card></Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="Score distribution"><ReactECharts option={distOption} style={{ height: 280 }} /></Card>
        </Col>
        <Col span={12}>
          <Card title="Weekly average trend"><ReactECharts option={trendOption} style={{ height: 280 }} /></Card>
        </Col>
      </Row>
      <Card title="Risk summary" style={{ marginTop: 16 }}>
        <Row>
          <Col span={8}><Statistic title="High risk" value={overview.risk_summary.high} valueStyle={{ color: '#cf1322' }} /></Col>
          <Col span={8}><Statistic title="Medium risk" value={overview.risk_summary.medium} valueStyle={{ color: '#d48806' }} /></Col>
          <Col span={8}><Statistic title="Low risk" value={overview.risk_summary.low} valueStyle={{ color: '#389e0d' }} /></Col>
        </Row>
      </Card>
      <Card title="Students" style={{ marginTop: 16 }}>
        <Table
          rowKey="student_id"
          dataSource={students}
          columns={[
            { title: 'Anonymized code', dataIndex: 'anonymized_code' },
            { title: 'Average score', dataIndex: 'average_score' },
            { title: 'Attendance', dataIndex: 'attendance_rate', render: (v) => `${(v * 100).toFixed(0)}%` },
            { title: 'Risk', dataIndex: 'risk_level', render: (v) => <Tag color={RISK_COLOR[v]}>{v}</Tag> },
            {
              title: 'Actions',
              render: (_, r) => <a onClick={() => navigate(`/sections/${sectionId}/students/${r.student_id}`)}>Details</a>,
            },
          ]}
        />
      </Card>
    </div>
  );
}
