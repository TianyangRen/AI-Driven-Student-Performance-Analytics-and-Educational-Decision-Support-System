import { useEffect, useState } from 'react';
import { Button, Form, Input, Modal, Select, Table, Tag, Space, message } from 'antd';
import {
  PlusOutlined,
  ApartmentOutlined,
  DashboardOutlined,
  CloudUploadOutlined,
  ThunderboltOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { PageHeader, Panel } from '../components/ui';
import { palette } from '../theme/tokens';
import * as api from '../api/resources';

export default function Sections() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null); // null = 新建，否则为被编辑的行
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    Promise.all([api.listSections(), api.listCourses()])
      .then(([s, c]) => {
        setData(s || []);
        setCourses(c || []);
      })
      .catch(() => message.error('Failed to load'))
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
    form.setFieldsValue({
      course: row.course,
      section_code: row.section_code,
      status: row.status,
    });
    setOpen(true);
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    try {
      if (editing) {
        // course 不允许改挂到别的课程，编辑时只提交编号与状态
        await api.updateSection(editing.id, {
          section_code: values.section_code,
          status: values.status,
        });
        message.success('Section updated');
      } else {
        await api.createSection(values);
        message.success('Section created');
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
        title="Sections"
        subtitle="A section is the core analysis unit for data import, metrics and risk prediction"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            New section
          </Button>
        }
      />
      <Panel icon={<ApartmentOutlined />} title="Section list">
        <Table
          className="cockpit-table"
          rowKey="id"
          loading={loading}
          dataSource={data}
          size="middle"
          columns={[
            { title: 'ID', dataIndex: 'id', width: 70 },
            {
              title: 'Course',
              render: (_, r) => (
                <span>
                  <span style={{ color: palette.cyan, fontWeight: 600 }}>{r.course_code}</span>
                  <span style={{ color: palette.textSecondary }}> · {r.course_name}</span>
                </span>
              ),
            },
            {
              title: 'Section code',
              dataIndex: 'section_code',
              render: (v) => <span style={{ color: palette.textStrong }}>{v}</span>,
            },
            {
              title: 'Status',
              dataIndex: 'status',
              render: (v) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v}</Tag>,
            },
            {
              title: 'Actions',
              width: 360,
              render: (_, r) => (
                <Space size={4}>
                  <Button type="link" size="small" icon={<DashboardOutlined />} onClick={() => navigate(`/sections/${r.id}/overview`)}>
                    Overview
                  </Button>
                  <Button type="link" size="small" icon={<CloudUploadOutlined />} onClick={() => navigate(`/sections/${r.id}/import`)}>
                    Import
                  </Button>
                  <Button type="link" size="small" icon={<ThunderboltOutlined />} onClick={() => navigate(`/sections/${r.id}/predictions`)}>
                    Predict
                  </Button>
                  <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>
                    Edit
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Panel>

      <Modal
        title={editing ? 'Edit section' : 'New section'}
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
          <Form.Item name="course" label="Course" rules={[{ required: true, message: 'Please select a course' }]}>
            <Select
              placeholder="Select a course"
              disabled={!!editing}
              options={courses.map((c) => ({ value: c.id, label: `${c.code} · ${c.name}` }))}
            />
          </Form.Item>
          <Form.Item
            name="section_code"
            label="Section code"
            rules={[
              { required: true, message: 'Please enter a section code' },
              {
                pattern: /^[A-Za-z0-9-]+$/,
                message: 'Only letters, digits and hyphens are allowed',
              },
            ]}
          >
            <Input placeholder="01" />
          </Form.Item>
          {editing && (
            <Form.Item name="status" label="Status" rules={[{ required: true, message: 'Please select a status' }]}>
              <Select
                options={[
                  { value: 'ACTIVE', label: 'ACTIVE' },
                  { value: 'ARCHIVED', label: 'ARCHIVED' },
                  { value: 'HIDDEN', label: 'HIDDEN' },
                ]}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
