import { useEffect, useState } from 'react';
import { Button, Form, Input, Modal, Table, message } from 'antd';
import { PlusOutlined, BookOutlined } from '@ant-design/icons';
import { PageHeader, Panel } from '../components/ui';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

export default function Courses() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    api
      .listCourses()
      .then((d) => setData(d || []))
      .catch(() => message.error('Failed to load courses'))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const onCreate = async () => {
    const values = await form.validateFields();
    try {
      await api.createCourse(values);
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
      <PageHeader
        title="Courses"
        subtitle="Maintain course definitions — a course is the scope for sections and analytics"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
            New course
          </Button>
        }
      />
      <Panel icon={<BookOutlined />} title="Course list">
        <Table
          className="cockpit-table"
          rowKey="id"
          loading={loading}
          dataSource={data}
          size="middle"
          columns={[
            { title: 'ID', dataIndex: 'id', width: 80 },
            {
              title: 'Code',
              dataIndex: 'code',
              render: (v) => <span style={{ color: palette.cyan, fontWeight: 600 }}>{v}</span>,
            },
            { title: 'Name', dataIndex: 'name', render: (v) => <span style={{ color: palette.textStrong }}>{v}</span> },
            { title: 'Term', dataIndex: 'term', render: (v) => <span style={{ color: palette.textSecondary }}>{v}</span> },
            {
              title: 'Created at',
              dataIndex: 'created_at',
              render: (v) => (v ? new Date(v).toLocaleString('en-US') : '-'),
            },
          ]}
        />
      </Panel>

      <Modal title="New course" open={open} onCancel={() => setOpen(false)} onOk={onCreate} okText="Create" cancelText="Cancel">
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="code" label="Course code" rules={[{ required: true, message: 'Please enter a course code' }]}>
            <Input placeholder="COMP8567" />
          </Form.Item>
          <Form.Item name="name" label="Course name" rules={[{ required: true, message: 'Please enter a course name' }]}>
            <Input placeholder="Advanced Software Engineering" />
          </Form.Item>
          <Form.Item name="term" label="Term" rules={[{ required: true, message: 'Please enter a term' }]}>
            <Input placeholder="Summer 2026" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
