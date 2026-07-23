import { useEffect, useState } from 'react';
import { Button, Form, Input, Modal, Table, message } from 'antd';
import { PlusOutlined, BookOutlined, EditOutlined } from '@ant-design/icons';
import { PageHeader, Panel } from '../components/ui';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

export default function Courses() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null); // null = 新建，否则为被编辑的行
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

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setOpen(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    form.setFieldsValue({ code: row.code, name: row.name, term: row.term });
    setOpen(true);
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        await api.updateCourse(editing.id, values);
        message.success('Course updated');
      } else {
        await api.createCourse(values);
        message.success('Course created');
      }
      setOpen(false);
      setEditing(null);
      form.resetFields();
      load();
    } catch (e) {
      message.error(e.response?.data?.error?.message || (editing ? 'Update failed' : 'Create failed'));
    }
  };

  return (
    <div>
      <PageHeader
        title="Courses"
        subtitle="Maintain course definitions — a course is the scope for sections and analytics"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
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
            {
              title: 'Actions',
              width: 120,
              render: (_, r) => (
                <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>
                  Edit
                </Button>
              ),
            },
          ]}
        />
      </Panel>

      <Modal
        title={editing ? 'Edit course' : 'New course'}
        open={open}
        onCancel={() => {
          setOpen(false);
          setEditing(null);
        }}
        onOk={onSubmit}
        okText={editing ? 'Save' : 'Create'}
        cancelText="Cancel"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item
            name="code"
            label="Course code"
            rules={[
              { required: true, message: 'Please enter a course code' },
              {
                pattern: /^[A-Za-z0-9-]+$/,
                message: 'Only letters, digits and hyphens are allowed',
              },
            ]}
          >
            <Input placeholder="COMP8567" />
          </Form.Item>
          <Form.Item name="name" label="Course name" rules={[{ required: true, message: 'Please enter a course name' }]}>
            <Input placeholder="Advanced Software Engineering" />
          </Form.Item>
          <Form.Item
            name="term"
            label="Term"
            rules={[
              { required: true, message: 'Please enter a term' },
              {
                pattern: /^[A-Za-z0-9 -]+$/,
                message: 'Only letters, digits, spaces and hyphens are allowed',
              },
            ]}
          >
            <Input placeholder="Summer 2026" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
