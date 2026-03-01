import { useState, useEffect } from 'react';
import { Steps, Button, Select, Space, App, Upload, Progress, Result, Card } from 'antd';
import { InboxOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { projectService } from '../../services/projectService';
import { imagingService } from '../../services/imagingService';

const { Dragger } = Upload;

interface ProjectOption { id: number; code: string; name: string }
interface CenterOption { id: number; code: string; name: string }
interface SubjectOption { id: number; screening_number: string }

interface FileStatus {
  uid: string;
  name: string;
  percent: number;
  status: 'uploading' | 'done' | 'error';
}

const visitOptions = [
  { label: 'V1', value: 'V1' },
  { label: 'V2', value: 'V2' },
  { label: 'V3', value: 'V3' },
  { label: 'V4', value: 'V4' },
];

const imagingTypeOptions = [
  { label: 'CT', value: 'CT' },
  { label: 'MRI', value: 'MRI' },
  { label: 'PET', value: 'PET' },
  { label: 'X-Ray', value: 'X-Ray' },
  { label: '其他', value: 'Other' },
];

export default function ImagingUploadPage() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [current, setCurrent] = useState(0);
  const [preloaded, setPreloaded] = useState(false);

  // Step 1 state
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [centers, setCenters] = useState<CenterOption[]>([]);
  const [subjects, setSubjects] = useState<SubjectOption[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [centerId, setCenterId] = useState<number | null>(null);
  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [loadingCenters, setLoadingCenters] = useState(false);
  const [loadingSubjects, setLoadingSubjects] = useState(false);

  // Step 2 state
  const [visitPoint, setVisitPoint] = useState<string | null>(null);
  const [imagingType, setImagingType] = useState<string | null>(null);

  // Step 3 state
  const [fileList, setFileList] = useState<File[]>([]);
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadedCount, setUploadedCount] = useState(0);

  // Pre-fill from navigation state (e.g. from project page "上传影像" button)
  useEffect(() => {
    const state = location.state as { projectId?: number; centerId?: number; subjectId?: number } | null;
    if (state?.projectId && !preloaded) {
      setPreloaded(true);
      const init = async () => {
        try {
          // Load projects
          const projRes = await projectService.list(1, 100);
          const projList = projRes.data.items ?? projRes.data;
          setProjects(projList);
          setProjectId(state.projectId!);

          // Load centers
          const centerRes = await projectService.listCenters(state.projectId!);
          const centerList = centerRes.data.items ?? centerRes.data;
          setCenters(centerList);
          if (state.centerId) setCenterId(state.centerId);

          // Load subjects
          if (state.centerId) {
            const subRes = await projectService.listSubjects(state.projectId!);
            const allSubs: SubjectOption[] = subRes.data.items ?? subRes.data;
            const filtered = allSubs.filter((s: any) => s.center_id === state.centerId);
            setSubjects(filtered.length > 0 ? filtered : allSubs);
            if (state.subjectId) setSubjectId(state.subjectId);
          }
        } catch {
          message.error('预加载数据失败');
        }
      };
      init();
    }
  }, [location.state, preloaded, message]);

  // Load projects on first open
  const loadProjects = async () => {
    if (projects.length > 0) return;
    setLoadingProjects(true);
    try {
      const res = await projectService.list(1, 100);
      setProjects(res.data.items ?? res.data);
    } catch {
      message.error('获取项目列表失败');
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleProjectChange = async (val: number) => {
    setProjectId(val);
    setCenterId(null);
    setSubjectId(null);
    setCenters([]);
    setSubjects([]);
    setLoadingCenters(true);
    try {
      const res = await projectService.listCenters(val);
      setCenters(res.data.items ?? res.data);
    } catch {
      message.error('获取中心列表失败');
    } finally {
      setLoadingCenters(false);
    }
  };

  const handleCenterChange = async (val: number) => {
    setCenterId(val);
    setSubjectId(null);
    setSubjects([]);
    if (!projectId) return;
    setLoadingSubjects(true);
    try {
      const res = await projectService.listSubjects(projectId);
      const allSubjects: SubjectOption[] = res.data.items ?? res.data;
      // Filter subjects by center if the data includes center_id
      const filtered = allSubjects.filter((s: any) => !s.center_id || s.center_id === val);
      setSubjects(filtered.length > 0 ? filtered : allSubjects);
    } catch {
      message.error('获取受试者列表失败');
    } finally {
      setLoadingSubjects(false);
    }
  };

  const handleUpload = async () => {
    if (!projectId || !centerId || !subjectId || !visitPoint || !imagingType) return;

    setUploading(true);
    setUploadedCount(0);

    try {
      // Create session
      const sessionRes = await imagingService.createSession({
        project_id: projectId,
        center_id: centerId,
        subject_id: subjectId,
        visit_point: visitPoint,
        imaging_type: imagingType,
      });
      const sessionId = sessionRes.data.id;

      // Initialize file statuses
      const initialStatuses: FileStatus[] = fileList.map((f, i) => ({
        uid: `file-${i}`,
        name: f.name,
        percent: 0,
        status: 'uploading' as const,
      }));
      setFileStatuses(initialStatuses);

      // Upload files sequentially
      let completed = 0;
      for (let i = 0; i < fileList.length; i++) {
        try {
          await imagingService.uploadFile(sessionId, fileList[i], (percent) => {
            setFileStatuses(prev => prev.map((fs, idx) =>
              idx === i ? { ...fs, percent } : fs
            ));
          });
          setFileStatuses(prev => prev.map((fs, idx) =>
            idx === i ? { ...fs, percent: 100, status: 'done' as const } : fs
          ));
          completed++;
          setUploadedCount(completed);
        } catch {
          setFileStatuses(prev => prev.map((fs, idx) =>
            idx === i ? { ...fs, status: 'error' as const } : fs
          ));
        }
      }

      if (completed === fileList.length) {
        // Complete session — transition to anonymizing
        await imagingService.completeSession(sessionId);
        message.success('所有文件上传成功');
        setCurrent(3);
      } else {
        message.warning(`${completed}/${fileList.length} 个文件上传成功`);
      }
    } catch {
      message.error('创建上传会话失败');
    } finally {
      setUploading(false);
    }
  };

  const canGoNext = () => {
    if (current === 0) return !!projectId && !!centerId && !!subjectId;
    if (current === 1) return !!visitPoint && !!imagingType;
    if (current === 2) return fileList.length > 0;
    return false;
  };

  const steps = [
    { title: '选择受试者' },
    { title: '检查信息' },
    { title: '上传文件' },
    { title: '完成' },
  ];

  const renderStep = () => {
    switch (current) {
      case 0:
        return (
          <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 500 }}>
            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>选择项目</div>
              <Select
                style={{ width: '100%' }}
                placeholder="请选择项目"
                value={projectId}
                onChange={handleProjectChange}
                onFocus={loadProjects}
                loading={loadingProjects}
                options={projects.map(p => ({ label: `${p.code} - ${p.name}`, value: p.id }))}
                showSearch
                optionFilterProp="label"
              />
            </div>
            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>选择中心</div>
              <Select
                style={{ width: '100%' }}
                placeholder="请先选择项目"
                value={centerId}
                onChange={handleCenterChange}
                loading={loadingCenters}
                disabled={!projectId}
                options={centers.map(c => ({ label: `${c.code} - ${c.name}`, value: c.id }))}
                showSearch
                optionFilterProp="label"
              />
            </div>
            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>选择受试者</div>
              <Select
                style={{ width: '100%' }}
                placeholder="请先选择中心"
                value={subjectId}
                onChange={setSubjectId}
                loading={loadingSubjects}
                disabled={!centerId}
                options={subjects.map(s => ({ label: s.screening_number, value: s.id }))}
                showSearch
                optionFilterProp="label"
              />
            </div>
          </Space>
        );

      case 1:
        return (
          <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 500 }}>
            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>访视时间点</div>
              <Select
                style={{ width: '100%' }}
                placeholder="请选择访视时间点"
                value={visitPoint}
                onChange={setVisitPoint}
                options={visitOptions}
              />
            </div>
            <div>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>影像类型</div>
              <Select
                style={{ width: '100%' }}
                placeholder="请选择影像类型"
                value={imagingType}
                onChange={setImagingType}
                options={imagingTypeOptions}
              />
            </div>
          </Space>
        );

      case 2:
        return (
          <div style={{ maxWidth: 600 }}>
            {!uploading && (
              <Dragger
                multiple
                beforeUpload={(file) => {
                  setFileList(prev => [...prev, file]);
                  return false; // prevent auto upload
                }}
                onRemove={(file) => {
                  setFileList(prev => prev.filter(f => f.name !== file.name));
                }}
                fileList={fileList.map((f, i) => ({
                  uid: `file-${i}`,
                  name: f.name,
                  size: f.size,
                  type: f.type,
                  status: 'done' as const,
                  originFileObj: f as any,
                }))}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">支持多文件上传</p>
              </Dragger>
            )}

            {uploading && fileStatuses.length > 0 && (
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                {fileStatuses.map((fs) => (
                  <Card key={fs.uid} size="small">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {fs.name}
                      </span>
                      {fs.status === 'done' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                      {fs.status === 'error' && <span style={{ color: '#ff4d4f' }}>失败</span>}
                    </div>
                    {fs.status === 'uploading' && <Progress percent={fs.percent} size="small" />}
                    {fs.status === 'done' && <Progress percent={100} size="small" />}
                  </Card>
                ))}
              </Space>
            )}

            {!uploading && fileList.length > 0 && (
              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <Button type="primary" size="large" onClick={handleUpload}>
                  开始上传 ({fileList.length} 个文件)
                </Button>
              </div>
            )}
          </div>
        );

      case 3:
        return (
          <Result
            status="success"
            title="上传完成"
            subTitle={`成功上传 ${uploadedCount} 个文件`}
            extra={[
              <Button type="primary" key="list" onClick={() => navigate('/imaging')}>
                查看影像列表
              </Button>,
              <Button key="again" onClick={() => {
                setCurrent(0);
                setFileList([]);
                setFileStatuses([]);
                setUploadedCount(0);
              }}>
                继续上传
              </Button>,
            ]}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>影像上传</h2>
      <Steps current={current} items={steps} style={{ marginBottom: 32 }} />

      <div style={{ minHeight: 300, display: 'flex', justifyContent: 'center', paddingTop: 24 }}>
        {renderStep()}
      </div>

      {current < 3 && current !== 2 && (
        <div style={{ marginTop: 24, textAlign: 'center' }}>
          <Space>
            {current > 0 && (
              <Button onClick={() => setCurrent(current - 1)}>
                上一步
              </Button>
            )}
            <Button type="primary" disabled={!canGoNext()} onClick={() => setCurrent(current + 1)}>
              下一步
            </Button>
          </Space>
        </div>
      )}
    </div>
  );
}
