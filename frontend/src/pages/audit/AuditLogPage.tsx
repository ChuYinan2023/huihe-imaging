import { useEffect, useState, useCallback } from 'react';
import { Table, Select, Input, DatePicker, Space, App } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { auditService } from '../../services/auditService';
import { useAuthStore } from '../../stores/auth';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

const resourceTypeOptions = [
  { label: '用户', value: 'user' },
  { label: '项目', value: 'project' },
  { label: '影像', value: 'imaging' },
  { label: '问题', value: 'issue' },
  { label: '报告', value: 'report' },
];

export default function AuditLogPage() {
  const { message } = App.useApp();
  const user = useAuthStore((s) => s.user);

  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Filters
  const [action, setAction] = useState<string | undefined>();
  const [resourceType, setResourceType] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize };
      if (action) params.action = action;
      if (resourceType) params.resource_type = resourceType;
      if (dateRange?.[0]) params.date_from = dateRange[0].format('YYYY-MM-DD');
      if (dateRange?.[1]) params.date_to = dateRange[1].format('YYYY-MM-DD');
      const res = await auditService.list(params);
      setData(res.data.items ?? res.data ?? []);
      setTotal(res.data.total ?? 0);
    } catch {
      message.error('获取审计日志失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, action, resourceType, dateRange, message]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (user?.role !== 'admin') {
    return <div style={{ textAlign: 'center', marginTop: 100, color: '#999' }}>仅管理员可查看审计日志</div>;
  }

  const columns: ColumnsType<any> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (val: string) => val ? dayjs(val).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    { title: '操作人', dataIndex: 'operator_name', key: 'operator_name', width: 120 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 120 },
    { title: '资源类型', dataIndex: 'resource_type', key: 'resource_type', width: 100 },
    { title: '资源 ID', dataIndex: 'resource_id', key: 'resource_id', width: 100 },
    { title: 'IP 地址', dataIndex: 'ip', key: 'ip', width: 140 },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>审计日志</h2>

      <Space wrap style={{ marginBottom: 16 }}>
        <Input
          placeholder="操作类型"
          allowClear
          style={{ width: 150 }}
          value={action}
          onChange={(e) => { setAction(e.target.value || undefined); setPage(1); }}
        />
        <Select
          placeholder="资源类型"
          allowClear
          style={{ width: 150 }}
          value={resourceType}
          onChange={(val) => { setResourceType(val); setPage(1); }}
          options={resourceTypeOptions}
        />
        <RangePicker
          value={dateRange as [dayjs.Dayjs, dayjs.Dayjs] | null}
          onChange={(vals) => { setDateRange(vals as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null); setPage(1); }}
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
    </div>
  );
}
