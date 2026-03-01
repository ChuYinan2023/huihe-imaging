import { useEffect, useState, useCallback } from 'react';
import { Table, Select, Space, Tag, Button, Modal, Form, Input, App } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate, useLocation } from 'react-router-dom';
import { issueService } from '../../services/issueService';
import { projectService } from '../../services/projectService';
import { imagingService } from '../../services/imagingService';
import { useAuthStore } from '../../stores/auth';
import dayjs from 'dayjs';

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待处理' },
  processing: { color: 'blue', label: '处理中' },
  reviewing: { color: 'purple', label: '审核中' },
  closed: { color: 'green', label: '已关闭' },
};

export default function IssueListPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const canCreateIssue = ['admin', 'expert', 'pm', 'crc', 'cra'].includes(user?.role ?? '');

  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Filters
  const [projectId, setProjectId] = useState<number | undefined>();
  const [centerId, setCenterId] = useState<number | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  // Lookups
  const [projects, setProjects] = useState<any[]>([]);
  const [centers, setCenters] = useState<any[]>([]);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [form] = Form.useForm();

  // Auto-open create modal if navigated from imaging detail with sessionId
  useEffect(() => {
    const state = location.state as { sessionId?: number } | null;
    if (state?.sessionId && canCreateIssue) {
      // Load sessions then open modal with pre-selected session
      imagingService.list({ page: 1, page_size: 100 }).then((res) => {
        setSessions(res.data.items ?? res.data ?? []);
        form.setFieldsValue({ session_id: state.sessionId });
        setCreateOpen(true);
      }).catch(() => {});
      // Clear navigation state to prevent re-opening on re-render
      window.history.replaceState({}, '');
    }
  }, [location.state, canCreateIssue, form]);

  useEffect(() => {
    projectService.list(1, 100).then((res) => {
      setProjects(res.data.items ?? res.data ?? []);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (projectId) {
      projectService.listCenters(projectId).then((res) => {
        setCenters(res.data.items ?? res.data ?? []);
      }).catch(() => {});
    } else {
      setCenters([]);
      setCenterId(undefined);
    }
  }, [projectId]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize };
      if (projectId) params.project_id = projectId;
      if (centerId) params.center_id = centerId;
      if (statusFilter) params.status_filter = statusFilter;
      const res = await issueService.list(params);
      setData(res.data.items ?? res.data ?? []);
      setTotal(res.data.total ?? 0);
    } catch {
      message.error('获取问题列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, projectId, centerId, statusFilter, message]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const openCreate = async () => {
    form.resetFields();
    try {
      const params: Record<string, any> = { page: 1, page_size: 100 };
      if (projectId) params.project_id = projectId;
      const res = await imagingService.list(params);
      setSessions(res.data.items ?? res.data ?? []);
    } catch {
      setSessions([]);
    }
    setCreateOpen(true);
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await issueService.create(values);
      message.success('问题已创建');
      setCreateOpen(false);
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error('创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  const columns: ColumnsType<any> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    { title: '受试者编号', dataIndex: 'screening_number', key: 'screening_number' },
    { title: '访视点', dataIndex: 'visit_point', key: 'visit_point' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (val: string) => {
        const s = statusMap[val] ?? { color: 'default', label: val };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 250,
    },
    { title: '创建人', dataIndex: 'created_by_name', key: 'created_by_name' },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: any) => (
        <Button type="link" onClick={() => navigate(`/issues/${record.id}`)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>问题管理</h2>
        {canCreateIssue && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            发起问题
          </Button>
        )}
      </div>

      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          placeholder="选择项目"
          allowClear
          style={{ width: 180 }}
          value={projectId}
          onChange={(val) => { setProjectId(val); setCenterId(undefined); setPage(1); }}
          options={projects.map((p: any) => ({ label: p.name, value: p.id }))}
        />
        <Select
          placeholder="选择中心"
          allowClear
          style={{ width: 180 }}
          value={centerId}
          onChange={(val) => { setCenterId(val); setPage(1); }}
          options={centers.map((c: any) => ({ label: c.name, value: c.id }))}
          disabled={!projectId}
        />
        <Select
          placeholder="状态"
          allowClear
          style={{ width: 150 }}
          value={statusFilter}
          onChange={(val) => { setStatusFilter(val); setPage(1); }}
          options={Object.entries(statusMap).map(([k, v]) => ({ label: v.label, value: k }))}
        />
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        onRow={(record) => ({ onClick: () => navigate(`/issues/${record.id}`), style: { cursor: 'pointer' } })}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
      />

      <Modal
        title="发起问题"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={submitting}
        okText="提交"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="session_id"
            label="关联影像会话"
            rules={[{ required: true, message: '请选择影像会话' }]}
          >
            <Select
              placeholder="选择影像会话"
              showSearch
              optionFilterProp="label"
              options={sessions.map((s: any) => ({
                label: `#${s.id} - ${s.screening_number ?? ''} - ${s.visit_point ?? ''}`,
                value: s.id,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="description"
            label="问题描述"
            rules={[{ required: true, message: '请输入问题描述' }]}
          >
            <Input.TextArea rows={4} placeholder="请描述问题详情" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
