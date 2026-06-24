import { Button, Card, Form, Select, Typography, message } from 'antd';
import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import client from '../api/client';

export default function Comparisons() {
  const [result, setResult] = useState(null);

  const onRun = async (values) => {
    try {
      const r = await client.post('/analytics/comparisons', values);
      setResult(r.data?.data);
    } catch (e) {
      message.error('Comparison failed');
    }
  };

  const option = result && {
    tooltip: { trigger: 'axis' },
    legend: { data: result.series.map((s) => s.name) },
    xAxis: { type: 'category', data: result.labels },
    yAxis: { type: 'value' },
    series: result.series.map((s) => ({ name: s.name, type: 'bar', data: s.data })),
  };

  return (
    <div>
      <Typography.Title level={3}>Comparisons</Typography.Title>
      <Card>
        <Form layout="inline" onFinish={onRun} initialValues={{ dimension: 'SECTION' }}>
          <Form.Item name="dimension" label="Dimension">
            <Select
              style={{ width: 220 }}
              options={[
                { value: 'SECTION', label: 'By section' },
                { value: 'COURSE', label: 'By course' },
                { value: 'TERM', label: 'By term' },
                { value: 'ASSESSMENT_TYPE', label: 'By assessment type' },
              ]}
            />
          </Form.Item>
          <Form.Item><Button htmlType="submit" type="primary">Generate</Button></Form.Item>
        </Form>
      </Card>
      {option && (
        <Card title="Comparison result" style={{ marginTop: 16 }}>
          <ReactECharts option={option} style={{ height: 360 }} />
        </Card>
      )}
    </div>
  );
}
