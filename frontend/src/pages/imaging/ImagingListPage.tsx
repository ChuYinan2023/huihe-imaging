import { useEffect, useState, useCallback } from 'react';
import { Table, Select, Space, Tag, Button, Drawer, Descriptions, App, Card, Divider, Spin } from 'antd';
import { EyeOutlined, SwapOutlined, ExclamationCircleOutlined, DownloadOutlined, FileImageOutlined } from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { imagingService } from '../../services/imagingService';
import { projectService } from '../../services/projectService';
import { useAuthStore } from '../../stores/auth';
import dayjs from 'dayjs';

const statusMap: Record<string, { color: string; label: string }> = {
  uploading: { color: 'blue', label: '上传中' },
  anonymizing: { color: 'orange', label: '匿名化中' },
  completed: { color: 'green', label: '已完成' },
  upload_failed: { color: 'red', label: '上传失败' },
  anonymize_failed: { color: 'red', label: '匿名化失败' },
  rejected: { color: 'volcano', label: '已拒绝' },
};

function FileThumbnail({ fileId }: { fileId: number }) {
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let revoke = '';
    imagingService.getThumbnail(fileId)
      .then((res) => {
        const url = URL.createObjectURL(res.data);
        revoke = url;
        setSrc(url);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
    return () => { if (revoke) URL.revokeObjectURL(revoke); };
  }, [fileId]);

  if (loading) return <Spin size="small" />;
  if (error || !src) return <FileImageOutlined style={{ fontSize: 48, color: '#666' }} />;
  return <img src={src} alt="" style={{ maxHeight: 160, maxWidth: '100%', objectFit: 'contain' }} />;
}

export default function ImagingListPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const canCreateIssue = ['admin', 'expert', 'pm', 'crc', 'cra'].includes(user?.role ?? '');
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [subjectView, setSubjectView] = useState(false);

  // Filters — initialize from URL query params if present
  const [projectId, setProjectId] = useState<number | undefined>(() => {
    const v = searchParams.get('project_id');
    return v ? Number(v) : undefined;
  });
  const [centerId, setCenterId] = useState<number | undefined>();
  const [subjectId] = useState<number | undefined>(() => {
    const v = searchParams.get('subject_id');
    return v ? Number(v) : undefined;
  });
  const [status, setStatus] = useState<string | undefined>();
  const [visitPoint, setVisitPoint] = useState<string | undefined>();

  // Lookup data
  const [projects, setProjects] = useState<any[]>([]);
  const [centers, setCenters] = useState<any[]>([]);

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);

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
      if (subjectId) params.subject_id = subjectId;
      if (status) params.status_filter = status;
      if (visitPoint) params.visit_point = visitPoint;

      const res = subjectView
        ? await imagingService.listBySubject(params)
        : await imagingService.list(params);
      const items = res.data.items ?? res.data;
      setData(Array.isArray(items) ? items : []);
      setTotal(res.data.total ?? 0);
    } catch {
      message.error('获取影像列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, projectId, centerId, subjectId, status, visitPoint, subjectView, message]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const showDetail = async (record: any) => {
    try {
      const res = await imagingService.getDetail(record.id);
      setDetail(res.data);
      setDrawerOpen(true);
    } catch {
      message.error('获取详情失败');
    }
  };

  const columns: ColumnsType<any> = subjectView
    ? [
        { title: '受试者编号', dataIndex: 'screening_number', key: 'screening_number' },
        { title: '项目', dataIndex: 'project_name', key: 'project_name' },
        { title: '中心', dataIndex: 'center_name', key: 'center_name' },
        { title: '会话数', dataIndex: 'session_count', key: 'session_count' },
        {
          title: '最新状态',
          dataIndex: 'latest_status',
          key: 'latest_status',
          render: (val: string) => {
            const s = statusMap[val] ?? { color: 'default', label: val };
            return <Tag color={s.color}>{s.label}</Tag>;
          },
        },
      ]
    : [
        { title: '项目', dataIndex: 'project_name', key: 'project_name' },
        { title: '中心', dataIndex: 'center_name', key: 'center_name' },
        { title: '受试者编号', dataIndex: 'screening_number', key: 'screening_number' },
        { title: '访视点', dataIndex: 'visit_point', key: 'visit_point' },
        { title: '影像类型', dataIndex: 'imaging_type', key: 'imaging_type' },
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
          title: '创建时间',
          dataIndex: 'created_at',
          key: 'created_at',
          render: (val: string) => val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-',
        },
        {
          title: '操作',
          key: 'actions',
          render: (_: unknown, record: any) => (
            <Space size="small">
              <Button type="link" icon={<EyeOutlined />} onClick={() => showDetail(record)}>
                详情
              </Button>
              {canCreateIssue && (
                <Button type="link" icon={<ExclamationCircleOutlined />} onClick={() => navigate('/issues', { state: { sessionId: record.id } })}>
                  发起问题
                </Button>
              )}
            </Space>
          ),
        },
      ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>影像中心</h2>
        <Button
          icon={<SwapOutlined />}
          onClick={() => { setSubjectView(!subjectView); setPage(1); }}
        >
          {subjectView ? '影像列表' : '受试者视图'}
        </Button>
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
          value={status}
          onChange={(val) => { setStatus(val); setPage(1); }}
          options={Object.entries(statusMap).map(([k, v]) => ({ label: v.label, value: k }))}
        />
        <Select
          placeholder="访视点"
          allowClear
          style={{ width: 150 }}
          value={visitPoint}
          onChange={(val) => { setVisitPoint(val); setPage(1); }}
          options={['V1', 'V2', 'V3', 'V4', 'V5'].map((v) => ({ label: v, value: v }))}
        />
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
      />

      <Drawer
        title="影像详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={520}
        extra={canCreateIssue && detail ? (
          <Button type="primary" icon={<ExclamationCircleOutlined />} onClick={() => {
            setDrawerOpen(false);
            navigate('/issues', { state: { sessionId: detail.id } });
          }}>
            发起问题
          </Button>
        ) : null}
      >
        {detail && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="项目">{detail.project_name}</Descriptions.Item>
              <Descriptions.Item label="中心">{detail.center_name}</Descriptions.Item>
              <Descriptions.Item label="受试者编号">{detail.screening_number}</Descriptions.Item>
              <Descriptions.Item label="访视点">{detail.visit_point}</Descriptions.Item>
              <Descriptions.Item label="影像类型">{detail.imaging_type}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {(() => {
                  const s = statusMap[detail.status] ?? { color: 'default', label: detail.status };
                  return <Tag color={s.color}>{s.label}</Tag>;
                })()}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {detail.created_at ? dayjs(detail.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="文件数量">{detail.files?.length ?? 0}</Descriptions.Item>
            </Descriptions>

            {detail.files && detail.files.length > 0 && (
              <>
                <Divider>影像文件预览</Divider>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                  {detail.files.map((f: any) => (
                    <Card
                      key={f.id}
                      size="small"
                      style={{ width: 220 }}
                      cover={
                        <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', overflow: 'hidden' }}>
                          <FileThumbnail fileId={f.id} />
                        </div>
                      }
                      actions={[
                        <Button key="download" type="link" icon={<DownloadOutlined />} onClick={async () => {
                          try {
                            const res = await imagingService.downloadFile(f.id);
                            const url = URL.createObjectURL(res.data);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = f.original_filename;
                            a.click();
                            URL.revokeObjectURL(url);
                          } catch { message.error('下载失败'); }
                        }}>下载</Button>,
                      ]}
                    >
                      <Card.Meta
                        title={<span style={{ fontSize: 12 }}>{f.original_filename}</span>}
                        description={<span style={{ fontSize: 11, color: '#999' }}>{(f.file_size / 1024).toFixed(1)} KB</span>}
                      />
                    </Card>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}
