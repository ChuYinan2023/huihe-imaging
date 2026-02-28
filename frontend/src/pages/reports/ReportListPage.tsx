import { useEffect, useState, useCallback } from 'react';
import { Table, Select, Space, Button, Modal, Form, InputNumber, Upload, App, Tag } from 'antd';
import { PlusOutlined, UploadOutlined, DownloadOutlined, EditOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload';
import { reportService } from '../../services/reportService';
import { projectService } from '../../services/projectService';
import { useAuthStore } from '../../stores/auth';
import dayjs from 'dayjs';

export default function ReportListPage() {
  const { message } = App.useApp();
  const user = useAuthStore((s) => s.user);
  const isExpert = user?.role === 'expert';

  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Filters
  const [projectId, setProjectId] = useState<number | undefined>();
  const [projects, setProjects] = useState<any[]>([]);

  // Upload modal
  const [uploadOpen, setUploadOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [form] = Form.useForm();

  useEffect(() => {
    projectService.list(1, 100).then((res) => {
      setProjects(res.data.items ?? res.data ?? []);
    }).catch(() => {});
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize };
      if (projectId) params.project_id = projectId;
      const res = await reportService.list(params);
      setData(res.data.items ?? res.data ?? []);
      setTotal(res.data.total ?? 0);
    } catch {
      message.error('获取报告列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, projectId, message]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUpload = async () => {
    try {
      const values = await form.validateFields();
      if (fileList.length === 0) {
        message.warning('请选择文件');
        return;
      }
      setSubmitting(true);
      const file = fileList[0].originFileObj as File;
      await reportService.upload(values.session_id, file);
      message.success('报告上传成功');
      setUploadOpen(false);
      setFileList([]);
      form.resetFields();
      fetchData();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error('上传失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSign = async (id: number) => {
    try {
      await reportService.sign(id);
      message.success('签名成功');
      fetchData();
    } catch {
      message.error('签名失败');
    }
  };

  const handleDownload = async (record: any) => {
    try {
      const res = await reportService.download(record.id);
      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = record.file_name ?? `report_${record.id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('下载失败');
    }
  };

  const columns: ColumnsType<any> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    { title: '受试者', dataIndex: 'screening_number', key: 'screening_number' },
    { title: '项目', dataIndex: 'project_name', key: 'project_name' },
    { title: '访视点', dataIndex: 'visit_point', key: 'visit_point' },
    {
      title: '已签名',
      dataIndex: 'has_signature',
      key: 'has_signature',
      render: (val: boolean) => val
        ? <Tag icon={<CheckCircleOutlined />} color="success">已签名</Tag>
        : <Tag color="default">未签名</Tag>,
    },
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
        <Space>
          <Button type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(record)}>
            下载
          </Button>
          {isExpert && !record.has_signature && (
            <Button type="link" icon={<EditOutlined />} onClick={() => handleSign(record.id)}>
              签名
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>报告管理</h2>
        {isExpert && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setFileList([]); setUploadOpen(true); }}>
            上传报告
          </Button>
        )}
      </div>

      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          placeholder="选择项目"
          allowClear
          style={{ width: 180 }}
          value={projectId}
          onChange={(val) => { setProjectId(val); setPage(1); }}
          options={projects.map((p: any) => ({ label: p.name, value: p.id }))}
        />
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        expandable={{
          expandedRowRender: (record: any) => (
            <div>
              <strong>AI 摘要：</strong>
              <p style={{ margin: 0 }}>{record.ai_summary ?? '暂无摘要'}</p>
            </div>
          ),
          rowExpandable: () => true,
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
        title="上传报告"
        open={uploadOpen}
        onOk={handleUpload}
        onCancel={() => setUploadOpen(false)}
        confirmLoading={submitting}
        okText="上传"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="session_id"
            label="关联影像会话 ID"
            rules={[{ required: true, message: '请输入影像会话 ID' }]}
          >
            <InputNumber style={{ width: '100%' }} min={1} placeholder="影像会话 ID" />
          </Form.Item>
          <Form.Item label="报告文件" required>
            <Upload
              beforeUpload={() => false}
              fileList={fileList}
              onChange={({ fileList: fl }) => setFileList(fl.slice(-1))}
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>选择文件</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
