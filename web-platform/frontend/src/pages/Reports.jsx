import { useState } from 'react';
import { Button, Form, Input, Select, Table, Tag, message } from 'antd';
import { FileTextOutlined, DownloadOutlined, FilePdfOutlined } from '@ant-design/icons';
import { PageHeader, Panel } from '../components/ui';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

const REPORT_TYPES = [
  { value: 'CLASS_SUMMARY', label: 'Class summary' },
  { value: 'RISK_LIST', label: 'Risk list' },
  { value: 'COMPARISON', label: 'Comparison' },
];

const TYPE_LABEL = Object.fromEntries(REPORT_TYPES.map((t) => [t.value, t.label]));

export default function Reports() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(false);

  const onCreate = async (values) => {
    setLoading(true);
    try {
      const item = await api.createReport({ ...values, section_id: parseInt(values.section_id, 10) });
      setList((prev) => [item, ...prev]);
      message.success('Report generated');
    } catch {
      message.error('Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const download = (id) => window.open(`/api/v1/reports/${id}/download`, '_blank');

  return (
    <div>
      <PageHeader title="Reports" subtitle="Generate and download PDF / Excel reports by section and filters" />

      <Panel title="Create report" icon={<FilePdfOutlined />} style={{ marginBottom: 16 }}>
        <Form
          layout="inline"
          onFinish={onCreate}
          initialValues={{ report_type: 'CLASS_SUMMARY', format: 'PDF' }}
          style={{ rowGap: 12 }}
        >
          <Form.Item name="section_id" label="Section ID" rules={[{ required: true, message: 'Please enter a section ID' }]}>
            <Input style={{ width: 120 }} placeholder="1001" />
          </Form.Item>
          <Form.Item name="report_type" label="Type">
            <Select style={{ width: 170 }} options={REPORT_TYPES} />
          </Form.Item>
          <Form.Item name="format" label="Format">
            <Select
              style={{ width: 110 }}
              options={[
                { value: 'PDF', label: 'PDF' },
                { value: 'XLSX', label: 'Excel' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} icon={<FileTextOutlined />}>
              Generate
            </Button>
          </Form.Item>
        </Form>
      </Panel>

      <Panel title="Recent reports" icon={<FileTextOutlined />}>
        <Table
          className="cockpit-table"
          rowKey="report_id"
          dataSource={list}
          locale={{ emptyText: 'No reports yet — generate one above' }}
          size="middle"
          columns={[
            { title: 'ID', dataIndex: 'report_id', width: 80 },
            {
              title: 'Type',
              dataIndex: 'report_type',
              render: (v) => <span style={{ color: '#fff' }}>{TYPE_LABEL[v] || v}</span>,
            },
            {
              title: 'Status',
              dataIndex: 'status',
              render: (v) => <Tag color={v === 'SUCCESS' ? 'success' : 'processing'}>{v}</Tag>,
            },
            {
              title: 'Expires at',
              dataIndex: 'expires_at',
              render: (v) => (
                <span style={{ color: palette.textSecondary }}>
                  {v ? new Date(v).toLocaleString('en-US') : '-'}
                </span>
              ),
            },
            {
              title: 'Action',
              width: 120,
              render: (_, r) => (
                <Button type="link" size="small" icon={<DownloadOutlined />} onClick={() => download(r.report_id)}>
                  Download
                </Button>
              ),
            },
          ]}
        />
      </Panel>
    </div>
  );
}
