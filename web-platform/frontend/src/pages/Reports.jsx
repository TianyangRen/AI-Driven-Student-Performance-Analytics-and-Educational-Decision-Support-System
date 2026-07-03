import { useEffect, useState } from 'react';
import { Button, Form, Select, Table, Tag, message } from 'antd';
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

// CLASS_SUMMARY / RISK_LIST 针对某个 section；COMPARISON 针对某个维度
const SECTION_TYPES = new Set(['CLASS_SUMMARY', 'RISK_LIST']);
const DIMENSIONS = [
  { value: 'SECTION', label: 'By section' },
  { value: 'COURSE', label: 'By course' },
  { value: 'TERM', label: 'By term' },
  { value: 'ASSESSMENT_TYPE', label: 'By assessment type' },
];

export default function Reports() {
  const [form] = Form.useForm();
  const [list, setList] = useState([]);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const reportType = Form.useWatch('report_type', form);
  const needsSection = SECTION_TYPES.has(reportType);

  useEffect(() => {
    api.listSections().then((s) => setSections(s || [])).catch(() => {});
  }, []);

  const sectionOptions = sections.map((s) => ({
    value: s.id,
    label: `${s.course_code}-${s.section_code}`,
  }));

  const onCreate = async (values) => {
    setLoading(true);
    try {
      const payload = needsSection
        ? { report_type: values.report_type, section_id: values.section_id }
        : { report_type: values.report_type, dimension: values.dimension || 'SECTION' };
      const item = await api.createReport(payload);
      setList((prev) => [item, ...prev]);
      message.success('Report generated');
    } catch (e) {
      message.error(e?.response?.data?.error?.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  const download = async (id) => {
    try {
      const resp = await api.downloadReport(id);
      const url = URL.createObjectURL(resp.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      message.error('Download failed (report may be missing or expired)');
    }
  };

  return (
    <div>
      <PageHeader title="Reports" subtitle="Generate and download Excel (.xlsx) reports by section or comparison dimension" />

      <Panel title="Create report" icon={<FilePdfOutlined />} style={{ marginBottom: 16 }}>
        <Form
          form={form}
          layout="inline"
          onFinish={onCreate}
          initialValues={{ report_type: 'CLASS_SUMMARY', dimension: 'SECTION' }}
          style={{ rowGap: 12 }}
        >
          <Form.Item name="report_type" label="Type">
            <Select style={{ width: 170 }} options={REPORT_TYPES} />
          </Form.Item>

          {needsSection ? (
            <Form.Item
              name="section_id"
              label="Section"
              rules={[{ required: true, message: 'Please choose a section' }]}
            >
              <Select
                style={{ width: 190 }}
                options={sectionOptions}
                placeholder="Choose a section"
                showSearch
                optionFilterProp="label"
              />
            </Form.Item>
          ) : (
            <Form.Item name="dimension" label="Dimension">
              <Select style={{ width: 190 }} options={DIMENSIONS} />
            </Form.Item>
          )}

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
