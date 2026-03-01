import { useEffect, useState } from 'react';
import { Card, Col, Row, Statistic, Table, Alert, Typography } from 'antd';
import { TeamOutlined, PictureOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/auth';
import api from '../../services/api';
import { projectService } from '../../services/projectService';
import dayjs from 'dayjs';

const { Title } = Typography;

interface DashboardStats {
  subjects: number;
  imaging_sessions: number;
  issues: number;
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const [stats, setStats] = useState<DashboardStats>({ subjects: 0, imaging_sessions: 0, issues: 0 });
  const [recentLogs, setRecentLogs] = useState<any[]>([]);
  const [pendingIssues, setPendingIssues] = useState<number>(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [imagingRes, issuesRes, projRes] = await Promise.all([
          api.get('/imaging', { params: { page_size: 1 } }).catch(() => ({ data: { total: 0 } })),
          api.get('/issues', { params: { page_size: 1 } }).catch(() => ({ data: { total: 0 } })),
          projectService.list(1, 100).catch(() => ({ data: { items: [] } })),
        ]);
        // Count subjects across all projects
        const projects = projRes.data?.items ?? projRes.data ?? [];
        let subjectCount = 0;
        for (const proj of projects) {
          try {
            const subRes = await projectService.listSubjects(proj.id);
            const subs = subRes.data?.items ?? subRes.data ?? [];
            subjectCount += Array.isArray(subs) ? subs.length : 0;
          } catch { /* ignore */ }
        }
        setStats({
          subjects: subjectCount,
          imaging_sessions: imagingRes.data?.total || 0,
          issues: issuesRes.data?.total || 0,
        });

        if (user?.role === 'crc') {
          const pendingRes = await api.get('/issues', { params: { status: 'pending', page_size: 1 } }).catch(() => ({ data: { total: 0 } }));
          setPendingIssues(pendingRes.data?.total || 0);
        }

        if (user?.role === 'admin') {
          const logsRes = await api.get('/audit', { params: { page_size: 10 } }).catch(() => ({ data: { items: [] } }));
          setRecentLogs(logsRes.data?.items || []);
        }
      } catch {
        // ignore dashboard fetch errors
      }
    };
    fetchData();
  }, [user]);

  const logColumns = [
    { title: '时间', dataIndex: 'timestamp', key: 'timestamp', render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
    { title: '操作', dataIndex: 'action', key: 'action' },
    { title: '资源类型', dataIndex: 'resource_type', key: 'resource_type' },
    { title: '资源ID', dataIndex: 'resource_id', key: 'resource_id' },
  ];

  return (
    <div>
      <Title level={4}>工作台</Title>

      {user?.role === 'crc' && pendingIssues > 0 && (
        <Alert
          message={`您有 ${pendingIssues} 个待处理的问题`}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic title="受试者" value={stats.subjects} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="影像会话" value={stats.imaging_sessions} prefix={<PictureOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="问题" value={stats.issues} prefix={<ExclamationCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      {user?.role === 'admin' && recentLogs.length > 0 && (
        <Card title="最近操作记录">
          <Table dataSource={recentLogs} columns={logColumns} rowKey="id" pagination={false} size="small" />
        </Card>
      )}
    </div>
  );
}
