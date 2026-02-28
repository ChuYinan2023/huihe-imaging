import { useEffect, useState, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, App, Tag } from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { projectService } from '../../services/projectService';

interface Project {
  id: number;
  code: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
}

interface Center {
  id: number;
  code: string;
  name: string;
}

const statusMap: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '进行中' },
  completed: { color: 'blue', label: '已完成' },
  archived: { color: 'default', label: '已归档' },
};

export default function ProjectListPage() {
  const { message } = App.useApp();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Project modal
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [projectForm] = Form.useForm();

  // Center modal
  const [centerModalOpen, setCenterModalOpen] = useState(false);
  const [centerProjectId, setCenterProjectId] = useState<number | null>(null);
  const [centerForm] = Form.useForm();

  // Expanded row centers cache
  const [centersMap, setCentersMap] = useState<Record<number, Center[]>>({});
  const [centersLoading, setCentersLoading] = useState<Record<number, boolean>>({});

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await projectService.list(page, pageSize);
      setProjects(res.data.items ?? res.data);
      setTotal(res.data.total ?? res.data.length ?? 0);
    } catch {
      message.error('获取项目列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, message]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const fetchCenters = async (projectId: number) => {
    setCentersLoading(prev => ({ ...prev, [projectId]: true }));
    try {
      const res = await projectService.listCenters(projectId);
      setCentersMap(prev => ({ ...prev, [projectId]: res.data.items ?? res.data }));
    } catch {
      message.error('获取中心列表失败');
    } finally {
      setCentersLoading(prev => ({ ...prev, [projectId]: false }));
    }
  };

  const openCreateProject = () => {
    setEditingProject(null);
    projectForm.resetFields();
    setProjectModalOpen(true);
  };

  const openEditProject = (project: Project) => {
    setEditingProject(project);
    projectForm.setFieldsValue({
      code: project.code,
      name: project.name,
      description: project.description,
    });
    setProjectModalOpen(true);
  };

  const handleProjectSubmit = async () => {
    try {
      const values = await projectForm.validateFields();
      setSubmitting(true);
      if (editingProject) {
        await projectService.update(editingProject.id, {
          name: values.name,
          description: values.description,
        });
        message.success('项目更新成功');
      } else {
        await projectService.create(values);
        message.success('项目创建成功');
      }
      setProjectModalOpen(false);
      fetchProjects();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(editingProject ? '更新失败' : '创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  const openAddCenter = (projectId: number) => {
    setCenterProjectId(projectId);
    centerForm.resetFields();
    setCenterModalOpen(true);
  };

  const handleCenterSubmit = async () => {
    if (!centerProjectId) return;
    try {
      const values = await centerForm.validateFields();
      setSubmitting(true);
      await projectService.addCenter(centerProjectId, values);
      message.success('中心添加成功');
      setCenterModalOpen(false);
      fetchCenters(centerProjectId);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error('添加中心失败');
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ColumnsType<Project> = [
    { title: '项目编号', dataIndex: 'code', key: 'code' },
    { title: '项目名称', dataIndex: 'name', key: 'name' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const s = statusMap[status] ?? { color: 'default', label: status };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => val ? new Date(val).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Project) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => openEditProject(record)}>
          编辑
        </Button>
      ),
    },
  ];

  const centerColumns: ColumnsType<Center> = [
    { title: '中心编号', dataIndex: 'code', key: 'code' },
    { title: '中心名称', dataIndex: 'name', key: 'name' },
  ];

  const expandedRowRender = (record: Project) => {
    const centers = centersMap[record.id] ?? [];
    const isLoading = centersLoading[record.id] ?? false;

    return (
      <div style={{ padding: '8px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <strong>中心列表</strong>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => openAddCenter(record.id)}>
            添加中心
          </Button>
        </div>
        <Table
          rowKey="id"
          columns={centerColumns}
          dataSource={centers}
          loading={isLoading}
          pagination={false}
          size="small"
        />
      </div>
    );
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>项目管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateProject}>
          新增项目
        </Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={projects}
        loading={loading}
        expandable={{
          expandedRowRender,
          onExpand: (expanded, record) => {
            if (expanded && !centersMap[record.id]) {
              fetchCenters(record.id);
            }
          },
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
      />

      <Modal
        title={editingProject ? '编辑项目' : '新增项目'}
        open={projectModalOpen}
        onOk={handleProjectSubmit}
        onCancel={() => setProjectModalOpen(false)}
        confirmLoading={submitting}
        okText="确定"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={projectForm} layout="vertical" preserve={false}>
          <Form.Item
            name="code"
            label="项目编号"
            rules={[{ required: true, message: '请输入项目编号' }]}
          >
            <Input disabled={!!editingProject} />
          </Form.Item>
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加中心"
        open={centerModalOpen}
        onOk={handleCenterSubmit}
        onCancel={() => setCenterModalOpen(false)}
        confirmLoading={submitting}
        okText="确定"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={centerForm} layout="vertical" preserve={false}>
          <Form.Item
            name="code"
            label="中心编号"
            rules={[{ required: true, message: '请输入中心编号' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="name"
            label="中心名称"
            rules={[{ required: true, message: '请输入中心名称' }]}
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
