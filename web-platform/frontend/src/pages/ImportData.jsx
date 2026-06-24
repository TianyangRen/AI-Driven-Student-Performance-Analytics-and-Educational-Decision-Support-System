import { Card, Steps, Upload, Button, Typography, Select, message, Descriptions, Tag, Space } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import client from '../api/client';

export default function ImportData() {
  const { sectionId } = useParams();
  const [importType, setImportType] = useState('SCORE');
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(false);

  const customRequest = async ({ file, onSuccess, onError }) => {
    const form = new FormData();
    form.append('file', file);
    form.append('import_type', importType);
    setLoading(true);
    try {
      const r = await client.post(`/sections/${sectionId}/imports`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setBatch(r.data?.data);
      message.success('Uploaded — validating');
      onSuccess?.(r.data);
    } catch (e) {
      message.error('Upload failed');
      onError?.(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Typography.Title level={3}>Import data · Section #{sectionId}</Typography.Title>
      <Steps
        current={batch ? 2 : 0}
        items={[{ title: 'Choose type' }, { title: 'Upload file' }, { title: 'Review result' }]}
        style={{ marginBottom: 24 }}
      />
      <Card title="1. Select import type" style={{ marginBottom: 16 }}>
        <Select
          value={importType}
          onChange={setImportType}
          style={{ width: 240 }}
          options={[
            { value: 'ROSTER', label: 'Student roster (ROSTER)' },
            { value: 'SCORE', label: 'Scores (SCORE)' },
            { value: 'ACTIVITY', label: 'Activity (ACTIVITY)' },
            { value: 'MIXED', label: 'Mixed (MIXED)' },
          ]}
        />
      </Card>
      <Card title="2. Upload CSV / Excel file" style={{ marginBottom: 16 }}>
        <Upload.Dragger
          customRequest={customRequest}
          maxCount={1}
          accept=".csv,.xlsx,.xls"
          disabled={loading}
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p>Click or drag a file to this area to upload</p>
          <p style={{ color: '#888' }}>CSV / Excel supported · max 20MB per file</p>
        </Upload.Dragger>
      </Card>
      {batch && (
        <Card title="3. Import batch status">
          <Descriptions column={2} bordered>
            <Descriptions.Item label="Batch ID">{batch.batch_id}</Descriptions.Item>
            <Descriptions.Item label="Status"><Tag color="processing">{batch.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="Type">{batch.import_type}</Descriptions.Item>
            <Descriptions.Item label="File name">{batch.file_name}</Descriptions.Item>
          </Descriptions>
          <Space style={{ marginTop: 16 }}>
            <Button onClick={() => client.get(`/imports/${batch.batch_id}`).then((r) => setBatch(r.data?.data))}>
              Refresh status
            </Button>
            <Button type="link" onClick={() => client.get(`/imports/${batch.batch_id}/errors`).then((r) => message.info(`Errors: ${(r.data?.data?.errors || []).length}`))}>
              View error details
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
}
