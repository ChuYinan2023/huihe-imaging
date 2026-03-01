import { useEffect, useState, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, App, Tag, Space } from 'antd';
import { PlusOutlined, EditOutlined, UploadOutlined, FileSearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
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
  project_id: number;
  code: string;
  name: string;
}

interface Subject {
  id: number;
  center_id: number;
  project_id: number;
  screening_number: string;
  created_at: string;
}

const statusMap: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '进行中' },
  completed: { color: 'blue', label: '已完成' },
  archived: { color: 'default', label: '已归档' },
};

export default function ProjectListPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
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

  // Subject modal
  const [subjectModalOpen, setSubjectModalOpen] = useState(false);
  const [subjectProjectId, setSubjectProjectId] = useState<number | null>(null);
  const [subjectCenterId, setSubjectCenterId] = useState<number | null>(null);
  const [subjectForm] = Form.useForm();

  // Expanded center subjects cache
  const [subjectsMap, setSubjectsMap] = useState<Record<number, Subject[]>>({});
  const [subjectsLoading, setSubjectsLoading] = useState<Record<number, boolean>>({});

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

  const fetchSubjects = async (projectId: number, centerId: number) => {
    const key = centerId;
    setSubjectsLoading(prev => ({ ...prev, [key]: true }));
    try {
      const res = await projectService.listSubjects(projectId);
      const all: Subject[] = res.data.items ?? res.data;
      const filtered = all.filter((s: Subject) => s.center_id === centerId);
      setSubjectsMap(prev => ({ ...prev, [key]: filtered }));
    } catch {
      message.error('获取受试者列表失败');
    } finally {
      setSubjectsLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const openAddSubject = (projectId: number, centerId: number) => {
    setSubjectProjectId(projectId);
    setSubjectCenterId(centerId);
    subjectForm.resetFields();
    setSubjectModalOpen(true);
  };

  const handleSubjectSubmit = async () => {
    if (!subjectProjectId || !subjectCenterId) return;
    try {
      const values = await subjectForm.validateFields();
      setSubmitting(true);
      await projectService.addSubject(subjectProjectId, subjectCenterId, values);
      message.success('受试者添加成功');
      setSubjectModalOpen(false);
      fetchSubjects(subjectProjectId, subjectCenterId);
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.detail ?? '添加受试者失败');
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

  const subjectColumns: ColumnsType<Subject> = [
    { title: '筛选号', dataIndex: 'screening_number', key: 'screening_number' },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => val ? new Date(val).toLocaleDateString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Subject) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<UploadOutlined />}
            onClick={() => navigate('/imaging/upload', { state: { projectId: record.project_id, centerId: record.center_id, subjectId: record.id } })}
          >
            上传影像
          </Button>
          <Button
            type="link"
            size="small"
            icon={<FileSearchOutlined />}
            onClick={() => navigate(`/imaging?subject_id=${record.id}&project_id=${record.project_id}`)}
          >
            查看影像
          </Button>
        </Space>
      ),
    },
  ];

  const centerExpandedRowRender = (projectId: number) => (center: Center) => {
    const subjects = subjectsMap[center.id] ?? [];
    const isLoading = subjectsLoading[center.id] ?? false;

    return (
      <div style={{ padding: '8px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <strong>受试者列表</strong>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => openAddSubject(projectId, center.id)}>
            添加受试者
          </Button>
        </div>
        <Table
          rowKey="id"
          columns={subjectColumns}
          dataSource={subjects}
          loading={isLoading}
          pagination={false}
          size="small"
        />
      </div>
    );
  };

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
          expandable={{
            expandedRowRender: centerExpandedRowRender(record.id),
            onExpand: (expanded, center) => {
              if (expanded && !subjectsMap[center.id]) {
                fetchSubjects(record.id, center.id);
              }
            },
          }}
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

      <Modal
        title="添加受试者"
        open={subjectModalOpen}
        onOk={handleSubjectSubmit}
        onCancel={() => setSubjectModalOpen(false)}
        confirmLoading={submitting}
        okText="确定"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={subjectForm} layout="vertical" preserve={false}>
          <Form.Item
            name="screening_number"
            label="筛选号"
            rules={[{ required: true, message: '请输入受试者筛选号' }]}
          >
            <Input placeholder="如 SCR-001" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
