import { Button, Card, Form, Input, Select, Space, Table, Tag, Typography, message } from 'antd';
import { useState } from 'react';
import client from '../api/client';

export default function Reports() {
  const [list, setList] = useState([]);

  const onCreate = async (values) => {
    try {
      const r = await client.post('/reports', { ...values, section_id: parseInt(values.section_id, 10) });
      const item = r.data?.data;
      setList((prev) => [item, ...prev]);
      message.success('Report generated');
    } catch (e) {
      message.error('Generation failed');
    }
  };

  const download = (id) => {
    window.open(`/api/v1/reports/${id}/download`, '_blank');
  };

  return (
    <div>
      <Typography.Title level={3}>Reports</Typography.Title>
      <Card title="Create report" style={{ marginBottom: 16 }}>
        <Form layout="inline" onFinish={onCreate} initialValues={{ report_type: 'CLASS_SUMMARY', format: 'PDF' }}>
          <Form.Item name="section_id" label="Section ID" rules={[{ required: true }]}><Input style={{ width: 120 }} placeholder="1001" /></Form.Item>
          <Form.Item name="report_type" label="Type">
            <Select style={{ width: 200 }} options={[
              { value: 'CLASS_SUMMARY', label: 'Class summary' },
              { value: 'RISK_LIST', label: 'Risk list' },
              { value: 'COMPARISON', label: 'Comparison' },
            ]} />
          </Form.Item>
          <Form.Item name="format" label="Format">
            <Select style={{ width: 100 }} options={[{ value: 'PDF', label: 'PDF' }, { value: 'XLSX', label: 'Excel' }]} />
          </Form.Item>
          <Form.Item><Button type="primary" htmlType="submit">Generate</Button></Form.Item>
        </Form>
      </Card>
      <Card title="Recent reports">
        <Table
          rowKey="report_id"
          dataSource={list}
          columns={[
            { title: 'ID', dataIndex: 'report_id' },
            { title: 'Type', dataIndex: 'report_type' },
            { title: 'Status', dataIndex: 'status', render: (v) => <Tag color="green">{v}</Tag> },
            { title: 'Expires at', dataIndex: 'expires_at' },
            { title: 'Actions', render: (_, r) => <a onClick={() => download(r.report_id)}>Download</a> },
          ]}
        />
      </Card>
    </div>
  );
}
