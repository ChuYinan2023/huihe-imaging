# 前端交互与主数据流 Review

**日期**: 2026-02-28
**范围**: 前端交互代码，聚焦主数据流程（认证→影像上传→问题追踪→报告管理）
**文件覆盖**: api.ts, auth store, 6 个 service, 10 个页面组件, router, MainLayout

---

## 一、问题汇总

| # | 严重度 | 模块 | 问题 |
|---|--------|------|------|
| F-01 | **高** | 认证 | 刷新令牌后 CSRF token 未同步更新到后续请求 |
| F-02 | **高** | 认证 | fetchMe 失败不清除过期 token，后续请求持续 401 循环 |
| F-03 | **高** | 路由 | 所有子路由无前端权限守卫，URL 直接可访问 |
| F-04 | **高** | 问题管理 | 创建问题仅限 Expert 角色，但后端允许 CRC/PM/CRA 等多角色创建 |
| F-05 | **中** | 报告 | 报告上传仅限 Expert，但后端 UPLOAD_REPORT 权限含 PM/CRA |
| F-06 | **中** | 报告 | 报告上传关联 session_id 为手动输入数字，无选择器 |
| F-07 | **中** | 仪表盘 | 受试者统计永远显示 0，缺少 API 调用 |
| F-08 | **中** | 影像上传 | 重复文件（同名）不做去重提示，onRemove 按 name 匹配有误 |
| F-09 | **中** | 问题列表 | 后端接收 `status_filter` 但 IssueListPage 发送 `status` |
| F-10 | **中** | 影像列表 | 影像详情 drawer 缺少关联字段（project_name 等），依赖后续 getDetail 但 detail API 不返回这些字段 |
| F-11 | **中** | 报告列表 | 表格显示 screening_number/project_name/visit_point 但 report API 不返回这些字段 |
| F-12 | **中** | 报告列表 | 签名操作无确认对话框，误触即签 |
| F-13 | **低** | 全局 | 所有 service 返回值类型为 `any`，无 TypeScript 类型定义 |
| F-14 | **低** | 认证 | token 仅存内存变量，F5 刷新后丢失（依赖 fetchMe 恢复但不带 token） |
| F-15 | **低** | 布局 | MainLayout useEffect 缺少 deps（fetchMe/navigate），React Strict Mode 下可能双执行 |
| F-16 | **低** | 问题详情 | CRC 处理按钮对 `processing` 状态仍显示，但后端 process_issue 从 processing→reviewing 逻辑不同 |
| F-17 | **低** | 影像上传 | 上传失败后「继续上传」重置状态但不清除 session，可能创建空 session |
| F-18 | **低** | 全局 | 所有列表页独立调 projectService.list(1,100)，重复请求未缓存 |

---

## 二、详细分析

### F-01 [高] 刷新令牌后 CSRF 未同步

**位置**: `api.ts:37-41`

```typescript
const res = await axios.post('/api/auth/refresh', {}, { withCredentials: true });
accessToken = res.data.access_token;
csrfToken = res.data.csrf_token;
error.config.headers.Authorization = `Bearer ${accessToken}`;
error.config.headers['X-CSRF-Token'] = csrfToken;
```

**问题**: 刷新成功后更新了模块级 `csrfToken` 变量，也更新了重试请求的 header。但后端 `/refresh` 同时通过 `set-cookie` 设置了新的 `csrf_token` cookie。如果后续请求的 CSRF 校验同时比对 header 和 cookie，新 cookie 值和旧 cookie 值的切换时序可能不一致。

**影响**: 在 cookie 刷新与 header 刷新之间的极短窗口内，并发请求可能 CSRF 校验失败。

**建议**: 确认后端 CSRF 校验逻辑（双提交模式：header vs cookie 一致），或在刷新后添加短暂防抖避免并发请求。

---

### F-02 [高] fetchMe 失败不清除过期 token

**位置**: `stores/auth.ts:43-51`

```typescript
fetchMe: async () => {
    set({ loading: true });
    try {
      const res = await api.get('/auth/me');
      set({ user: res.data, isAuthenticated: true, loading: false });
    } catch {
      set({ user: null, isAuthenticated: false, loading: false });
    }
},
```

**问题**: fetchMe 失败时设置 `isAuthenticated: false` 但 **没有调用 `clearTokens()`**。模块级 `accessToken` 变量仍残留过期值。后续任何 API 调用都会带上过期 token → 401 → 触发 refresh 拦截器 → 如果 refresh 也失败则 `window.location.href = '/login'` 硬刷新。

**影响**: 页面在 loading 结束后短暂渲染（isAuthenticated=false），MainLayout 触发 `navigate('/login')`，同时 api 拦截器也触发 `window.location.href = '/login'`，产生竞态。

**建议**: fetchMe catch 中增加 `clearTokens()`。

---

### F-03 [高] 路由无前端权限守卫

**位置**: `router/index.tsx`

```typescript
const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <MainLayout />, children: [
      { path: 'users', element: <UserListPage /> },
      { path: 'audit', element: <AuditLogPage /> },
      ...
  ]},
]);
```

**问题**: 所有子路由仅依赖 MainLayout 中的 `isAuthenticated` 检查。CRC 用户直接输入 `/users` 或 `/audit` 可进入页面。虽然后端 API 会 403 拒绝，但页面 UI 仍渲染（空数据或报错）。

**影响**:
- 用户体验差：CRC 看到空白的用户管理页
- 信息泄露风险：AuditLogPage 仅在 `user.role !== 'admin'` 时显示一行文字，其他页面无此检查

**建议**: 添加 `<ProtectedRoute requiredRoles={['admin']}>` 路由守卫组件，或在 router 配置中加 `loader` 检查角色。

---

### F-04 [高] 创建问题角色限制前后端不一致

**位置**: `IssueListPage.tsx:23`

```typescript
const isExpert = user?.role === 'expert';
// ...
{isExpert && (
  <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>发起问题</Button>
)}
```

**后端**: `permissions.py` 中 `CREATE_ISSUE` 权限分配给 Expert、PM、CRC、CRA 四个角色。

**问题**: 前端硬编码 `isExpert` 作为「创建问题」按钮的显示条件，PM/CRC/CRA 角色登录后看不到该按钮，但如果直接调 API 是成功的。

**影响**: PM/CRC/CRA 无法通过 UI 创建问题，功能缺失。

**建议**: 改为 `const canCreate = ['expert', 'pm', 'crc', 'cra'].includes(user?.role ?? '')`，或从后端获取权限列表。

---

### F-05 [中] 报告上传角色限制前后端不一致

**位置**: `ReportListPage.tsx:14`

```typescript
const isExpert = user?.role === 'expert';
// 上传按钮和签名按钮都用 isExpert 控制
```

**后端**: `UPLOAD_REPORT` 权限分配给 PM、Expert、CRA 三个角色。

**问题**: PM 和 CRA 角色无法通过 UI 上传报告或签名，但 API 允许。

---

### F-06 [中] 报告上传 session_id 为手动输入

**位置**: `ReportListPage.tsx:199-203`

```typescript
<Form.Item name="session_id" label="关联影像会话 ID">
  <InputNumber style={{ width: '100%' }} min={1} placeholder="影像会话 ID" />
</Form.Item>
```

**问题**: 用户需要手动输入影像会话 ID 数字。与问题创建页面（IssueListPage）的 Select 选择器不一致。普通用户不知道 session ID 是什么数字。

**建议**: 复用 IssueListPage 中已有的 session 选择器模式：加载 imaging sessions 列表，用 Select 展示 `#ID - 受试者编号 - 访视点`。

---

### F-07 [中] 仪表盘受试者统计永远为 0

**位置**: `DashboardPage.tsx:29-30`

```typescript
setStats({
  subjects: 0,  // 硬编码为 0
  imaging_sessions: imagingRes.data?.total || 0,
  issues: issuesRes.data?.total || 0,
});
```

**问题**: subjects 统计值硬编码为 0，没有调用任何 API 获取受试者数量。UI 上有 Statistic 组件展示此数字。

**建议**: 增加 `/projects/{id}/subjects` 或专用统计 API 来获取总受试者数。

---

### F-08 [中] 影像上传文件去重和移除逻辑问题

**位置**: `ImagingUploadPage.tsx:318-323`

```typescript
beforeUpload={(file) => {
  setFileList(prev => [...prev, file]);  // 同名文件可重复添加
  return false;
},
onRemove={(file) => {
  setFileList(prev => prev.filter(f => f.name !== file.name));  // 同名文件全部移除
},
```

**问题**:
1. 用户选择同名文件时不警告，直接追加到列表
2. onRemove 按 `name` 匹配删除，如果有两个同名文件会全部移除

**建议**: beforeUpload 中检查重复文件名；onRemove 用 uid 或数组索引匹配。

---

### F-09 [中] 问题列表状态过滤参数名不匹配

**位置**: `IssueListPage.tsx:69`

```typescript
if (statusFilter) params.status = statusFilter;
```

**后端** `issues.py:148`: 参数名为 `status_filter`。

**问题**: 前端发送 `status` 参数，后端期望 `status_filter`。**但实际后端参数名是 `status_filter: str | None = None`**（行 127），而前端发送 `status`。这意味着状态过滤在问题列表页完全不生效。

**注意**: 需确认后端实际参数名。查看 issues.py:148 — `if status_filter is not None: query = query.where(Issue.status == status_filter)`。前端发送 `params.status` 而非 `params.status_filter`，所以 **状态过滤无效**。

**建议**: 前端改为 `params.status_filter = statusFilter`。

---

### F-10 [中] 影像详情缺少关联名称字段

**位置**: `ImagingListPage.tsx:94-101`（showDetail）

```typescript
const showDetail = async (record: any) => {
  const res = await imagingService.getDetail(record.id);
  setDetail(res.data);
  setDrawerOpen(true);
};
```

**后端** `imaging.py:375-398`（get_session）: 返回 `_session_response(session)` + `files`，但 **不含** `project_name`、`center_name`、`screening_number`。

**Drawer 模板** 使用 `detail.project_name`、`detail.center_name`、`detail.screening_number`：

```typescript
<Descriptions.Item label="项目">{detail.project_name}</Descriptions.Item>
<Descriptions.Item label="中心">{detail.center_name}</Descriptions.Item>
<Descriptions.Item label="受试者编号">{detail.screening_number}</Descriptions.Item>
```

**问题**: 详情 API 不返回这些字段，Drawer 中对应行显示为空。

**建议**: 后端 `get_session` 增加 JOIN 返回关联名称，或前端从列表行 record 中携带这些值传入 Drawer。

---

### F-11 [中] 报告列表字段与后端响应不匹配

**位置**: `ReportListPage.tsx:105-109`

```typescript
{ title: '受试者', dataIndex: 'screening_number', key: 'screening_number' },
{ title: '项目', dataIndex: 'project_name', key: 'project_name' },
{ title: '访视点', dataIndex: 'visit_point', key: 'visit_point' },
{ title: '已签名', dataIndex: 'has_signature', key: 'has_signature' },
```

**后端** `reports.py:29-42`（`_report_response`）返回字段:
```python
"id", "session_id", "subject_id", "project_id", "issue_id",
"file_path", "signed_file_path", "ai_summary",
"uploaded_by", "created_at", "updated_at"
```

**问题**:
1. `screening_number` — 后端不返回此字段，显示为空
2. `project_name` — 后端不返回此字段，显示为空
3. `visit_point` — 后端不返回此字段，显示为空
4. `has_signature` — 后端不返回此字段，前端列用 bool 渲染签名状态。后端返回 `signed_file_path`（null 或路径），前端应用 `!!record.signed_file_path` 判断
5. `file_path` — 后端返回了内部存储路径，不应暴露

**影响**: 报告列表 4 列显示为空，签名状态不显示。

**建议**:
- 后端 list_reports 增加 JOIN Subject/Project/ImagingSession 返回显示字段
- 后端返回 `has_signature: bool(report.signed_file_path)` 代替暴露路径
- 移除 `file_path`/`signed_file_path` 内部字段

---

### F-12 [中] 签名操作无确认对话框

**位置**: `ReportListPage.tsx:80-88`

```typescript
const handleSign = async (id: number) => {
  try {
    await reportService.sign(id);
    message.success('签名成功');
    fetchData();
  } catch {
    message.error('签名失败');
  }
};
```

**问题**: 电子签名是不可逆的法律行为（尤其在临床试验场景），点击「签名」按钮直接执行无确认。

**建议**: 增加 `Modal.confirm({ title: '确认签名', content: '电子签名后不可撤销...' })`。

---

### F-13 [低] 全局缺少 TypeScript 类型定义

**位置**: 所有 service 文件、所有页面组件

```typescript
// Services 全部返回 AxiosResponse<any>
export const issueService = {
  list: (params: Record<string, any>) => api.get('/issues', { params }),
  // ...
};

// Pages 中大量 any 类型
const [data, setData] = useState<any[]>([]);
const [detail, setDetail] = useState<any>(null);
```

**问题**: 无接口类型定义，编译时无法捕获后端字段变更导致的显示问题（如 F-11）。

**建议**: 定义 `interface ImagingSession`, `interface Issue`, `interface Report` 等响应类型，与后端字段保持同步。

---

### F-14 [低] Token 存储在内存变量，刷新即丢失

**位置**: `api.ts:8-9`

```typescript
let accessToken: string | null = null;
let csrfToken: string | null = null;
```

**问题**: 页面 F5 刷新后 accessToken 丢失。MainLayout 会调 `fetchMe()` 恢复会话，但 fetchMe 请求不带 token → 401 → 拦截器触发 refresh → refresh 依赖 httpOnly cookie（存活）→ 获取新 token。

**流程可用但脆弱**: 依赖 refresh cookie 存活 + refresh API 一次成功。如果 refresh 也失败（网络波动），用户被强制登出。

---

### F-15 [低] MainLayout useEffect 缺少依赖数组

**位置**: `MainLayout.tsx:31-34`

```typescript
useEffect(() => {
  if (!isAuthenticated) {
    fetchMe().catch(() => navigate('/login'));
  }
}, []);  // 缺少 isAuthenticated, fetchMe, navigate
```

**问题**: ESLint exhaustive-deps 警告。React Strict Mode 下 useEffect 可能执行两次，导致 fetchMe 并发调用。

---

### F-16 [低] CRC 处理按钮在 processing 状态下的行为

**位置**: `IssueDetailPage.tsx:132`

```typescript
{isCrc && (detail.status === 'pending' || detail.status === 'processing') && (
  <Button type="primary" onClick={() => setProcessOpen(true)}>提交处理结果</Button>
)}
```

**后端逻辑差异**:
- `pending` → 触发双步转换（pending→processing→reviewing），创建 2 条 log
- `processing` → 单步转换（processing→reviewing），创建 1 条 log

**问题**: 按钮文本都是「提交处理结果」，但 processing 状态下再提交其实只是「提交审核」。用户可能困惑为什么 pending 时操作会生成 2 条记录。

---

### F-17 [低] 上传失败后重置不清理已创建 session

**位置**: `ImagingUploadPage.tsx:389-394`

```typescript
<Button key="again" onClick={() => {
  setCurrent(0);  // 回到第一步
  setFileList([]);
  setFileStatuses([]);
  setUploadedCount(0);
  // 不清除已创建的 session
}}>继续上传</Button>
```

**问题**: 如果上传全部失败，用户点「继续上传」会重新走向导，但之前创建的 session（status=UPLOADING、0 files）留在数据库中成为孤儿记录。

---

### F-18 [低] 项目列表重复请求未缓存

**位置**: DashboardPage、ImagingListPage、ImagingUploadPage、IssueListPage、ReportListPage

```typescript
// 每个页面独立加载
projectService.list(1, 100).then(...)
```

**问题**: 5 个页面各自请求 `/projects?page=1&page_size=100`，切换页面时重复请求。

**建议**: 将项目/中心列表放入 Zustand store 缓存，或用 React Query/SWR 自动缓存。

---

## 三、数据流一致性矩阵

| 流程 | 前端发送 | 后端期望 | 匹配 | 说明 |
|------|----------|----------|------|------|
| 问题列表状态过滤 | `status` | `status_filter` | **不匹配** | F-09 |
| 影像列表状态过滤 | `status_filter` | `status_filter` | 匹配 | |
| 报告列表字段 | screening_number, project_name, visit_point, has_signature | 后端不返回 | **不匹配** | F-11 |
| 影像详情字段 | project_name, center_name, screening_number | 后端不返回 | **不匹配** | F-10 |
| 创建问题权限 | 仅 Expert | Expert/PM/CRC/CRA | **不匹配** | F-04 |
| 上传报告权限 | 仅 Expert | Expert/PM/CRA | **不匹配** | F-05 |
| 审计日志字段 | created_at | timestamp | **不匹配** | 已知 Issue #8 |
| 审计日志操作人 | operator_name | 后端不返回 | **不匹配** | 已知 Issue #8 |
| 登录响应 | user.phone | 后端不返回 | **不匹配** | auth.py:92-101 无 phone |
| /me 响应 | phone | 返回 phone | 匹配 | |

---

## 四、按优先级排序的修复建议

### 必须修复（影响功能正确性）

1. **F-04/F-05**: 创建问题、上传/签名报告的角色硬编码 → 改为权限列表或后端返回可用操作
2. **F-09**: 问题列表状态过滤参数 `status` → `status_filter`
3. **F-11**: 报告列表后端增加 JOIN 返回 screening_number/project_name/visit_point/has_signature
4. **F-10**: 影像详情后端增加 JOIN 返回关联名称字段

### 建议修复（影响用户体验）

5. **F-03**: 添加路由级权限守卫 ProtectedRoute
6. **F-06**: 报告上传 session_id 改为 Select 选择器
7. **F-07**: 仪表盘受试者统计接入 API
8. **F-12**: 签名操作增加确认对话框
9. **F-02**: fetchMe 失败时调用 clearTokens()
10. **F-08**: 文件上传去重提示和正确的 onRemove

### 改善性优化（低优先级）

11. **F-13**: 定义 TypeScript 响应类型
12. **F-18**: 项目列表请求缓存
13. **F-15**: useEffect 依赖修正
14. **F-16**: 处理/提交审核按钮文案区分
15. **F-17**: 上传失败后清理孤儿 session
