import { useState } from 'react';
import { Steps, Upload, Button, Select, message, Descriptions, Tag, Space, Row, Col } from 'antd';
import { InboxOutlined, ArrowLeftOutlined, FileExcelOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader, Panel } from '../components/ui';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

const IMPORT_TYPES = [
  { value: 'ROSTER', label: 'Student roster (ROSTER)' },
  { value: 'SCORE', label: 'Scores (SCORE)' },
  { value: 'ACTIVITY', label: 'Activity (ACTIVITY)' },
  { value: 'MIXED', label: 'Mixed (MIXED)' },
];

const STATUS_COLOR = {
  VALIDATING: 'processing',
  SUCCESS: 'success',
  PARTIAL: 'warning',
  FAILED: 'error',
  UPLOADED: 'default',
};

export default function ImportData() {
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const [importType, setImportType] = useState('SCORE');
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(false);

  const customRequest = async ({ file, onSuccess, onError }) => {
    const form = new FormData();
    form.append('file', file);
    form.append('import_type', importType);
    setLoading(true);
    try {
      const data = await api.createImport(sectionId, form);
      setBatch(data);
      message.success('Uploaded — validating');
      onSuccess?.(data);
    } catch (e) {
      message.error('Upload failed');
      onError?.(e);
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    const data = await api.getImport(batch.batch_id);
    setBatch(data);
    message.success('Status refreshed');
  };

  return (
    <div>
      <PageHeader
        title={`Import Data · Section #${sectionId}`}
        subtitle="CSV / Excel supported, with template and field validation before import (demo)"
        extra={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/sections')}>
            Back
          </Button>
        }
      />

      <Panel bodyStyle={{ padding: '24px 28px' }} style={{ marginBottom: 16 }}>
        <Steps
          current={batch ? 2 : importType ? 1 : 0}
          items={[{ title: 'Choose type' }, { title: 'Upload file' }, { title: 'Review result' }]}
        />
      </Panel>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Panel title="1 · Select import type" icon={<FileExcelOutlined />} style={{ height: '100%' }}>
            <Select
              value={importType}
              onChange={setImportType}
              style={{ width: '100%' }}
              size="large"
              options={IMPORT_TYPES}
            />
            <div style={{ marginTop: 16, color: palette.textMuted, fontSize: 12, lineHeight: 1.8 }}>
              · Roster: student enrollment relationships<br />
              · Scores: assessment scores and submission status<br />
              · Activity: attendance, participation, logins<br />
              · Mixed: a combined file with multiple record types
            </div>
          </Panel>
        </Col>
        <Col xs={24} lg={14}>
          <Panel title="2 · Upload CSV / Excel file" icon={<InboxOutlined />} style={{ height: '100%' }}>
            <Upload.Dragger
              customRequest={customRequest}
              maxCount={1}
              accept=".csv,.xlsx,.xls"
              disabled={loading}
              style={{ background: 'rgba(10,19,48,0.4)', border: '1px dashed rgba(94,124,196,0.4)' }}
            >
              <p style={{ fontSize: 44, color: palette.cyan, margin: '8px 0' }}>
                <InboxOutlined />
              </p>
              <p style={{ color: palette.textStrong, fontSize: 15 }}>Click or drag a file to this area to upload</p>
              <p style={{ color: palette.textMuted, fontSize: 12 }}>CSV / Excel · up to 20MB per file</p>
            </Upload.Dragger>
          </Panel>
        </Col>
      </Row>

      {batch && (
        <Panel
          title="3 · Import batch status"
          icon={<FileExcelOutlined />}
          style={{ marginTop: 16 }}
          extra={
            <Space>
              <Button size="small" icon={<ReloadOutlined />} onClick={refresh}>
                Refresh
              </Button>
              <Button
                size="small"
                type="link"
                onClick={() =>
                  api.getImportErrors(batch.batch_id).then((d) => message.info(`Error rows: ${(d?.errors || []).length}`))
                }
              >
                View error details
              </Button>
            </Space>
          }
        >
          <Descriptions column={{ xs: 1, sm: 2 }} bordered size="middle">
            <Descriptions.Item label="Batch ID">{batch.batch_id}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={STATUS_COLOR[batch.status] || 'default'}>{batch.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Type">{batch.import_type}</Descriptions.Item>
            <Descriptions.Item label="File name">{batch.file_name}</Descriptions.Item>
          </Descriptions>
        </Panel>
      )}
    </div>
  );
}
