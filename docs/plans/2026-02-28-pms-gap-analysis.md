# PMS 文档 vs 当前实现 — 差距分析

**日期**: 2026-02-28
**对比基准**: PMS 项目规划书 + 技术方案 (`/home/chu2026/Documents/github/PMS/docs/`)
**实现版本**: huihe-imaging `master` 分支 (commit 66af49b)

---

## 1. 整体结论

**匹配度约 80%**。Phase 1（基础平台 + 影像管理）核心业务流程完整实现，技术架构、数据模型、API 设计与 PMS 文档一致。差距主要集中在上传机制、合规接入和部分辅助功能。

---

## 2. 已实现功能

| PMS 功能编号 | 功能 | 实现状态 |
|---|---|---|
| F-01~03 | 登录 / 会话保持 / 退出 | ✅ 双令牌（Access + Refresh HttpOnly Cookie） |
| F-04~08 | 用户列表 / 新增 / 编辑 / 停用 / 重置密码 | ✅ |
| F-09 | 强制下线 | ✅ token_version 机制 |
| F-10~15 | 项目 / 中心 / 受试者 / 项目成员管理 | ✅ |
| F-16~17 | 创建影像会话 + 文件上传（DICOM/JPEG/PNG） | ✅ |
| F-20 | SHA256 完整性校验 | ✅ |
| F-21~25 | DICOM 自动脱敏 + 私有标签移除 + UID 重写 + 脱敏日志 + 非 DICOM 直通 | ✅ |
| F-26~29 | 影像列表 + 多维筛选 + 受试者视图 + 影像详情 | ✅ |
| F-33~38 | 问题创建 / 列表 / 详情 / CRC 处理 / 专家复核 / 操作日志 | ✅ |
| F-41~46 | 报告上传 / 列表 / AI 摘要 / 电子签名 / 下载 | ✅ |
| F-47~49 | 工作台统计 / 待办事项 / 事件提醒 | ✅ |
| F-50~52 | 审计日志列表 / 不可篡改模型 | ✅ 模型 + API 端点已有 |
| F-53 | 修改密码 | ✅ |
| — | 6 角色 RBAC（Admin/PM/Expert/CRC/CRA/DM） | ✅ 权限矩阵完全匹配 |
| — | 影像 FSM + 问题 FSM 状态机 | ✅ |
| — | Celery 异步任务（3 队列 + 幂等机制） | ✅ |
| — | StorageService 抽象 + LocalStorage | ✅ 含路径遍历防护 |
| — | Refresh Token 族链轮换 + 重放检测 | ✅ |
| — | 种子数据 + E2E 冒烟测试 | ✅ 79 个测试全部通过 |

### 技术栈匹配

| 项目 | PMS 技术方案 | 实现 | 匹配 |
|---|---|---|---|
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 + Zustand + React Router v6 + Axios | 同 | ✅ |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic | 同 | ✅ |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | 同 | ✅ |
| 异步任务 | Celery + Redis（3 队列） | 同 | ✅ |
| 影像处理 | pydicom | 同 | ✅ |
| PDF | PyPDF2 + ReportLab | 同 | ✅ |
| 文件存储 | 本地文件系统 (StorageService 抽象) | 同 | ✅ |
| 项目结构 | 技术方案第 3 节目录布局 | 同 | ✅ |
| 数据模型 | 12 张表 + 关键约束 | 同 | ✅ |
| API 端点 | 技术方案第 11 节全部路径 | 同 | ✅ |

---

## 3. 未实现 / 有差距

### 3.1 重要差距（需优先修复）

| PMS 要求 | 编号 | 差距说明 | 影响 |
|---|---|---|---|
| 审计日志接入业务端点 | F-50~52 | AuditService 存在且可用，但所有 API 端点均未调用它写入审计记录，审计日志表为空 | **合规硬性要求**（21 CFR Part 11） |
| 大文件分片断点续传 | F-18 | 当前整文件读入内存后写入磁盘，大 DICOM 文件（可达 500MB）会导致 OOM | **大文件场景必需** |
| 流式 SHA256 | 技术方案 5.6 | 技术方案要求"分片上传流式计算 SHA256，不整片加载内存"，实际整文件 `await file.read()` | 与分片续传同一问题 |
| CSRF 后端校验 | 技术方案 5.4 | 登录返回 CSRF token、前端发送 X-CSRF-Token header，但后端从未校验该 header | **安全要求** |
| Cookie secure 标志 | 技术方案 5.1 | Refresh Token cookie `secure=False` 硬编码，生产环境必须为 True | 生产部署前必须修复 |

### 3.2 中等差距（应修复）

| PMS 要求 | 编号 | 差距说明 |
|---|---|---|
| 上传进度展示 | F-19 | 前端有进度 UI 但基于整文件上传百分比，非分片级进度 |
| 影像文件在线预览 | F-30 | 未实现 JPEG/PNG 在线预览功能 |
| 影像质控标记 | F-31~32 | 专家审阅并标记影像合格/问题的独立功能未实现（当前通过创建 Issue 间接实现） |
| 数据导出 | F-55~57 | 影像/问题/报告列表导出 Excel 功能未实现 |
| 签名上传后端 API | F-54 | 前端 UI 有签名上传预览，但后端无对应 API 端点，导致报告签名功能不可用 |
| 路由守卫 | 技术方案 10.1 | ProtectedRoute 组件已实现但未在路由配置中使用，用户可直接访问无权限 URL |
| 报告下载路径校验 | — | 报告下载端点未使用 StorageService 的路径遍历防护 |

### 3.3 低优先级差距

| PMS 要求 | 差距说明 |
|---|---|
| 短信通知 (F-39~40) | Celery task 桩已有，需对接真实 SMS 服务商（预期内） |
| AI 报告识别 (F-44) | Celery task 桩已有，需对接 AI 视觉模型（预期内） |
| 移动端自适应 | 规划书要求 Android/iOS 浏览器可用，当前未做响应式布局 |
| 密码强度校验 | 无最小密码复杂度要求 |
| CORS 可配置 | 硬编码 `localhost:5173`，生产环境需改为环境变量 |
| 影像列表缺少关联名称 | API 返回 project_id/center_id 但不返回名称，前端表格显示空白 |
| Dashboard 受试者数 | 仪表盘受试者统计恒为 0（缺少 API） |

---

## 4. 修复优先级建议

| 优先级 | 任务 | 预估工作量 |
|---|---|---|
| P0 | 审计日志接入所有 API 端点 | 1-2 天 |
| P0 | 文件上传改为流式分片 + 断点续传 | 2-3 天 |
| P0 | CSRF 后端校验中间件 | 0.5 天 |
| P0 | Cookie secure 改为可配置 | 0.5 天 |
| P1 | 启用 ProtectedRoute 路由守卫 | 0.5 天 |
| P1 | 签名上传后端 API | 0.5 天 |
| P1 | 报告下载路径遍历防护 | 0.5 天 |
| P1 | 影像列表返回关联名称 | 0.5 天 |
| P2 | 影像在线预览（JPEG/PNG） | 1 天 |
| P2 | 数据导出 Excel | 1-2 天 |
| P2 | 影像质控标记功能 | 1 天 |
| P2 | 密码强度校验 | 0.5 天 |
| P3 | 移动端响应式布局 | 2-3 天 |
| P3 | SMS / AI 服务对接 | 取决于服务商 |

---

## 5. 参考文档

- PMS 产品规划：`/home/chu2026/Documents/github/PMS/docs/pms-product-roadmap.md`
- PMS 项目规划书：`/home/chu2026/Documents/github/PMS/docs/pms-platform-plan.md`
- PMS 技术方案：`/home/chu2026/Documents/github/PMS/docs/pms-technical-design.md`
- 系统设计文档：`docs/plans/2026-02-27-huihe-imaging-design.md`
- 实施计划：`docs/plans/2026-02-27-huihe-imaging-implementation.md`
