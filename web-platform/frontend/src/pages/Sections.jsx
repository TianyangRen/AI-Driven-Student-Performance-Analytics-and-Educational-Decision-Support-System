import { Button, Form, Input, Modal, Select, Space, Table, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function Sections() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    Promise.all([client.get('/sections'), client.get('/courses')])
      .then(([s, c]) => {
        setData(s.data?.data || []);
        setCourses(c.data?.data || []);
      })
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const onCreate = async () => {
    const values = await form.validateFields();
    try {
      await client.post('/sections', values);
      message.success('Section created');
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
        <Typography.Title level={3} style={{ margin: 0 }}>Sections</Typography.Title>
        <Button type="primary" onClick={() => setOpen(true)}>New section</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 80 },
          { title: 'Course', render: (_, r) => `${r.course_code} · ${r.course_name}` },
          { title: 'Section code', dataIndex: 'section_code' },
          { title: 'Status', dataIndex: 'status' },
          {
            title: 'Actions',
            render: (_, r) => (
              <Space>
                <a onClick={() => navigate(`/sections/${r.id}/overview`)}>Overview</a>
                <a onClick={() => navigate(`/sections/${r.id}/import`)}>Import</a>
                <a onClick={() => navigate(`/sections/${r.id}/predictions`)}>Predict</a>
              </Space>
            ),
          },
        ]}
      />
      <Modal title="New section" open={open} onCancel={() => setOpen(false)} onOk={onCreate}>
        <Form form={form} layout="vertical">
          <Form.Item name="course" label="Course" rules={[{ required: true }]}>
            <Select options={courses.map((c) => ({ value: c.id, label: `${c.code} · ${c.name}` }))} />
          </Form.Item>
          <Form.Item name="section_code" label="Section code" rules={[{ required: true }]}>
            <Input placeholder="01" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
