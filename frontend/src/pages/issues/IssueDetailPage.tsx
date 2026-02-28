import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Descriptions, Tag, Timeline, Button, Modal, Input, Space, Spin, App, Card } from 'antd';
import { ArrowLeftOutlined, CheckOutlined, CloseOutlined, SendOutlined } from '@ant-design/icons';
import { issueService } from '../../services/issueService';
import { useAuthStore } from '../../stores/auth';
import dayjs from 'dayjs';

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'orange', label: '待处理' },
  processing: { color: 'blue', label: '处理中' },
  reviewing: { color: 'purple', label: '审核中' },
  closed: { color: 'green', label: '已关闭' },
};

export default function IssueDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const user = useAuthStore((s) => s.user);
  const isCrc = user?.role === 'crc';
  const isExpert = user?.role === 'expert';

  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Process modal (CRC)
  const [processOpen, setProcessOpen] = useState(false);
  const [processContent, setProcessContent] = useState('');
  const [processSubmitting, setProcessSubmitting] = useState(false);

  // Review modal (Expert)
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject'>('approve');
  const [reviewContent, setReviewContent] = useState('');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await issueService.getDetail(Number(id));
      setDetail(res.data);
    } catch {
      message.error('获取问题详情失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleProcess = async () => {
    if (!processContent.trim()) {
      message.warning('请输入处理结果');
      return;
    }
    setProcessSubmitting(true);
    try {
      await issueService.process(Number(id), processContent);
      message.success('处理结果已提交');
      setProcessOpen(false);
      setProcessContent('');
      fetchDetail();
    } catch {
      message.error('提交失败');
    } finally {
      setProcessSubmitting(false);
    }
  };

  const handleReview = async () => {
    setReviewSubmitting(true);
    try {
      await issueService.review(Number(id), reviewAction, reviewContent || undefined);
      message.success(reviewAction === 'approve' ? '已通过' : '已打回');
      setReviewOpen(false);
      setReviewContent('');
      fetchDetail();
    } catch {
      message.error('操作失败');
    } finally {
      setReviewSubmitting(false);
    }
  };

  const openReview = (action: 'approve' | 'reject') => {
    setReviewAction(action);
    setReviewContent('');
    setReviewOpen(true);
  };

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  if (!detail) {
    return <div>未找到问题</div>;
  }

  const s = statusMap[detail.status] ?? { color: 'default', label: detail.status };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/issues')}>
          返回列表
        </Button>
      </Space>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions title={`问题 #${detail.id}`} bordered column={2} size="small">
          <Descriptions.Item label="状态">
            <Tag color={s.color}>{s.label}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建人">{detail.created_by_name ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="指派人">{detail.assigned_to_name ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="访视点">{detail.visit_point ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="影像类型">{detail.imaging_type ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {detail.created_at ? dayjs(detail.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {detail.description}
          </Descriptions.Item>
        </Descriptions>

        <Space style={{ marginTop: 16 }}>
          {isCrc && (detail.status === 'pending' || detail.status === 'processing') && (
            <Button type="primary" icon={<SendOutlined />} onClick={() => setProcessOpen(true)}>
              提交处理结果
            </Button>
          )}
          {isExpert && detail.status === 'reviewing' && (
            <>
              <Button type="primary" icon={<CheckOutlined />} onClick={() => openReview('approve')}>
                通过
              </Button>
              <Button danger icon={<CloseOutlined />} onClick={() => openReview('reject')}>
                打回
              </Button>
            </>
          )}
        </Space>
      </Card>

      <Card title="处理记录">
        {detail.logs && detail.logs.length > 0 ? (
          <Timeline
            items={detail.logs.map((log: any) => ({
              children: (
                <div>
                  <div>
                    <strong>{log.operator_name ?? '系统'}</strong>
                    <span style={{ marginLeft: 8, color: '#999' }}>
                      {log.action ?? log.type}
                    </span>
                    <span style={{ marginLeft: 8, color: '#999' }}>
                      {log.created_at ? dayjs(log.created_at).format('YYYY-MM-DD HH:mm:ss') : ''}
                    </span>
                  </div>
                  {log.content && <div style={{ marginTop: 4 }}>{log.content}</div>}
                </div>
              ),
            }))}
          />
        ) : (
          <div style={{ color: '#999' }}>暂无处理记录</div>
        )}
      </Card>

      <Modal
        title="提交处理结果"
        open={processOpen}
        onOk={handleProcess}
        onCancel={() => setProcessOpen(false)}
        confirmLoading={processSubmitting}
        okText="提交"
        cancelText="取消"
      >
        <Input.TextArea
          rows={4}
          value={processContent}
          onChange={(e) => setProcessContent(e.target.value)}
          placeholder="请输入处理结果"
        />
      </Modal>

      <Modal
        title={reviewAction === 'approve' ? '通过确认' : '打回确认'}
        open={reviewOpen}
        onOk={handleReview}
        onCancel={() => setReviewOpen(false)}
        confirmLoading={reviewSubmitting}
        okText="确定"
        cancelText="取消"
      >
        <Input.TextArea
          rows={4}
          value={reviewContent}
          onChange={(e) => setReviewContent(e.target.value)}
          placeholder={reviewAction === 'approve' ? '审核意见（可选）' : '请输入打回原因'}
        />
      </Modal>
    </div>
  );
}
