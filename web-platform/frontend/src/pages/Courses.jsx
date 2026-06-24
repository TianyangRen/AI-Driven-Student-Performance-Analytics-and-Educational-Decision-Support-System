import { Button, Form, Input, Modal, Space, Table, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import client from '../api/client';

export default function Courses() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    client.get('/courses').then((r) => {
      setData(r.data?.data || []);
    }).catch(() => message.error('Failed to load courses')).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const onCreate = async () => {
    const values = await form.validateFields();
    try {
      await client.post('/courses', values);
      message.success('Course created');
      setOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      message.error(e.response?.data?.error?.message || 'Create failed');
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', display: 'flex' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>Courses</Typography.Title>
        <Button type="primary" onClick={() => setOpen(true)}>New course</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 80 },
          { title: 'Code', dataIndex: 'code' },
          { title: 'Name', dataIndex: 'name' },
          { title: 'Term', dataIndex: 'term' },
          { title: 'Created at', dataIndex: 'created_at' },
        ]}
      />
      <Modal title="New course" open={open} onCancel={() => setOpen(false)} onOk={onCreate}>
        <Form form={form} layout="vertical">
          <Form.Item name="code" label="Course code" rules={[{ required: true }]}><Input placeholder="COMP8567" /></Form.Item>
          <Form.Item name="name" label="Course name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="term" label="Term" rules={[{ required: true }]}><Input placeholder="Summer 2026" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
