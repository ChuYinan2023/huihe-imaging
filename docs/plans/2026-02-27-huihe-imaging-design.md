# 汇禾影像管理系统 — 系统设计文档

**版本**: 1.0
**日期**: 2026-02-27
**状态**: 已批准

---

## 1. 项目概述

汇禾影像管理系统是一个面向临床试验的医学影像管理平台，核心业务流程为：

1. **影像上传与脱敏** — CRC 上传影像，系统自动脱敏处理
2. **影像质量审核** — 专家审阅影像，发现问题则发起问题记录
3. **问题闭环追踪** — CRC 整改 → 专家复核 → 关闭问题
4. **报告生成与签名** — 专家上传阅片报告，电子签名合成 PDF
5. **多角色权限体系** — CRC/CRA/DM/Expert/PM 不同角色不同权限

涉及 AI 能力两处：报告信息汇总（AI 识别报告内容）和 AI 视觉模型（PDF 文档识别）。

### 系统形态

- WEB 网页形态，PC 浏览器访问
- 开发周期：45-50 个工作日

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React + TypeScript | SPA 应用 |
| UI 组件库 | Ant Design | 企业级后台组件 |
| 构建工具 | Vite | 快速构建 |
| 状态管理 | Zustand | 轻量状态管理 |
| 路由 | React Router v6 | 前端路由 |
| HTTP 客户端 | Axios | 请求拦截器 |
| 后端 | Python FastAPI | 异步 Web 框架 |
| ORM | SQLAlchemy + Alembic | 数据库迁移 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | 环境变量切换 |
| 异步任务 | Celery + Redis | 统一任务队列 |
| 文件存储 | 本地文件系统 (StorageService 抽象) | 可迁移到 S3/OSS |

### 后端依赖

```
# Web 框架
fastapi
uvicorn[standard]
python-multipart

# 数据库
sqlalchemy
alembic
aiosqlite              # 开发环境
asyncpg                # 生产 PostgreSQL

# 认证
pyjwt
passlib[bcrypt]

# 配置
pydantic-settings

# 异步任务
celery[redis]
redis

# 影像处理
pydicom

# PDF 处理
pypdf2
reportlab

# HTTP 客户端 (AI/SMS 外部调用)
httpx

# 工具
python-dateutil
```

---

## 3. 项目结构

```
huihe-imaging/
├── frontend/                      # React 前端
│   ├── src/
│   │   ├── components/            # 通用组件
│   │   ├── pages/                 # 页面
│   │   │   ├── login/             # 登录
│   │   │   ├── dashboard/         # 工作台
│   │   │   ├── imaging/           # 影像脱敏 & 影像中心
│   │   │   ├── issues/            # 问题管理
│   │   │   ├── reports/           # 报告管理
│   │   │   ├── projects/          # 项目管理
│   │   │   ├── users/             # 账号管理
│   │   │   └── audit/             # 审计日志
│   │   ├── services/              # API 调用层
│   │   ├── stores/                # Zustand 状态管理
│   │   ├── utils/                 # 工具函数
│   │   └── router/                # 路由配置
│   └── vite.config.ts
│
├── backend/                       # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                   # API 路由
│   │   │   ├── auth.py            # 认证
│   │   │   ├── users.py           # 用户管理
│   │   │   ├── projects.py        # 项目管理
│   │   │   ├── imaging.py         # 影像上传/脱敏
│   │   │   ├── issues.py          # 问题追踪
│   │   │   ├── reports.py         # 报告管理
│   │   │   └── audit.py           # 审计日志
│   │   ├── models/                # SQLAlchemy 数据模型
│   │   ├── services/              # 业务逻辑
│   │   │   ├── storage_service.py # 存储抽象层
│   │   │   ├── dicom_service.py   # DICOM 脱敏
│   │   │   ├── upload_service.py  # 断点续传
│   │   │   ├── ai_service.py      # AI 报告识别
│   │   │   └── signature_service.py # 电子签名合成
│   │   ├── core/                  # 核心配置
│   │   │   ├── config.py          # 环境配置
│   │   │   ├── security.py        # JWT 认证
│   │   │   └── permissions.py     # RBAC 权限
│   │   ├── tasks/                 # Celery 异步任务
│   │   │   ├── imaging_tasks.py   # 脱敏任务
│   │   │   ├── ai_tasks.py        # AI 识别任务
│   │   │   └── notification_tasks.py # 短信通知任务
│   │   └── main.py
│   ├── storage/                   # 本地文件存储 (同一挂载点)
│   │   ├── tmp/                   # 临时上传目录
│   │   ├── originals/             # 原始影像
│   │   ├── anonymized/            # 脱敏后影像
│   │   ├── reports/               # 报告文件
│   │   └── signatures/            # 签名图片
│   └── requirements.txt
│
└── docs/                          # 文档
```

---

## 4. 数据模型

### 核心实体关系

```
Project (项目)
  ├── 1:N → Center (中心)
  ├── N:M → User (用户-项目关联)

Center (中心)
  ├── 1:N → Subject (受试者)

Subject (受试者)
  ├── 1:N → ImagingSession (影像会话)

ImagingSession (影像会话)
  ├── visit_point: V1/V2/V3...     (随访点)
  ├── imaging_type: CT/MRI/...     (影像类型)
  ├── status: FSM 管理              (见第6节)
  ├── 1:N → ImagingFile (影像文件)
  ├── 1:N → Issue (问题记录)
  └── 0:1 → Report (报告)

Issue (问题追踪)
  ├── status: FSM 管理              (见第6节)
  ├── created_by: Expert
  ├── assigned_to: CRC
  ├── 1:N → IssueLog (追踪日志)
  └── 0:1 → Report (关联报告)

Report (报告)
  ├── file_path: PDF 路径
  ├── signed_file_path: 签名后 PDF 路径
  ├── ai_summary: AI 提取的报告摘要

User (用户)
  ├── role: Admin/CRC/CRA/DM/Expert/PM
  ├── token_version: int             (踢人机制)
  ├── signature_path: 签名图片路径
  └── 1:N → AuditLog (操作日志)

RefreshToken (刷新令牌)
  ├── token_hash: SHA256 哈希
  ├── jti: 唯一标识
  ├── family_id: 轮换链路标识
  ├── used: bool (是否已使用)

AnonymizationLog (脱敏日志)
  ├── session_id: 关联影像会话
  ├── original_tag_hash: 原始标签快照哈希
  ├── strategy_version: 脱敏策略版本
  ├── private_tags_removed: int
  ├── uid_mappings: JSON

AuditLog (审计日志 - 不可篡改)
  ├── operator_id, ip, user_agent
  ├── timestamp: UTC
  ├── action, resource_type, resource_id
  ├── before_value, after_value  (字段级脱敏后存储)
```

### 角色权限矩阵

| 功能 | Admin | PM | Expert | CRC | CRA | DM |
|------|-------|-----|--------|-----|-----|-----|
| 用户管理 | ✓ | - | - | - | - | - |
| 项目管理 | ✓ | ✓ | - | - | - | - |
| 上传影像 | - | - | - | ✓ | - | - |
| 发起问题 | - | - | ✓ | - | - | - |
| 处理问题 | - | - | - | ✓ | - | - |
| 复核问题 | - | - | ✓ | - | - | - |
| 上传报告 | - | - | ✓ | - | - | - |
| 下载数据 | ✓ | ✓ | - | - | - | ✓ |
| 查看日志 | ✓ | - | - | - | - | - |
| 查看报告 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 5. 认证与安全

### 双 Token 认证机制

- **Access Token**: 短期（15分钟），存前端内存/变量，不持久化
- **Refresh Token**: HttpOnly + Secure + SameSite=Strict Cookie，7天有效

### CSRF 防护

- 双提交 Token 模式
- 登录时返回 CSRF token 在响应体中
- 前端存入内存，每次请求通过 `X-CSRF-Token` header 携带
- 后端校验 header 值与 cookie 中的 CSRF token 一致

### Refresh Token 存储与轮换

- 数据库只存 `refresh_token_hash`（SHA256），不存明文
- 每个 token 携带 `jti`（唯一ID）和 `family_id`（轮换链路标识）
- 轮换时：生成新 token → 新 jti + 同 family_id → 旧 jti 标记已用
- 检测到已用 jti 被重放 → 整个 family 失效（防 token 窃取）

### 管理员踢人 — token_version

- User 表 `token_version` 字段（整数，默认 1）
- JWT claim 中携带 `tv`（token_version）
- 校验：`jwt.tv == user.token_version`，不匹配则拒绝
- 踢人：`user.token_version += 1`，O(1) 校验，无需黑名单

### JWT 校验规则

- 强制校验 claims：`exp`, `nbf`, `iat`, `iss`, `aud`, `tv`
- 时钟偏移容忍：`leeway=30s`
- `iss` 固定为 `huihe-imaging`
- `aud` 区分 `access` / `refresh`

### 上传安全

- MIME 类型 + 文件后缀双校验
- 文件大小限制（可配置，DICOM 默认 500MB/文件）
- 分片上传流式计算 SHA256，不加载整片到内存
- 文件先写入 `storage/tmp/` 临时路径
- 全部分片完成 → 合并 → 计算整体 hash → 与客户端提交的 hash 比对
- 校验通过 → `os.replace()` 原子移动到正式目录（tmp 与正式目录同一挂载点）
- 校验失败 → 删除临时文件，返回错误
- 文件存储时重命名为 UUID，防目录遍历

---

## 6. 状态机 (FSM)

### 影像状态

```
uploading → anonymizing → completed
uploading → upload_failed
anonymizing → anonymize_failed
completed → rejected      (专家发起问题)
rejected → completed      (问题关闭)
```

非法跳转后端强校验，抛异常。

### 问题状态

```
pending → processing      (CRC 接手)
processing → reviewing    (CRC 提交处理结果)
reviewing → closed        (专家通过)
reviewing → pending       (专家打回)
```

---

## 7. 核心业务流程

### 影像上传与脱敏

1. CRC 填写元信息（项目/中心/受试者/随访点/影像类型）
2. 前端校验格式（DICOM/.dcm, JPEG, PNG）— MIME + 后缀双校验
3. 断点续传（分片上传），每片流式计算 SHA256
4. 文件落 `storage/tmp/`，校验通过 → `os.replace()` 到正式目录
5. Celery `imaging` 队列触发脱敏任务（幂等：session_id + file_hash 去重）
6. DICOM 脱敏：
   - 标签黑名单清除（PatientName, PatientID, DOB 等 PHI）
   - 移除所有私有标签（`tag.is_private == True`）
   - UID 重写：`2.25.{SHA256(原始UID+salt) 转十进制截断}`，总长度 ≤ 64
   - 保存脱敏日志（AnonymizationLog）
7. JPEG/PNG 直接存储
8. 状态更新为 `completed`

### 问题追踪闭环

1. Expert 发现问题 → 创建问题（关联影像，填写描述）
2. 状态 `pending`，Celery `notification` 队列发短信通知 CRC（幂等去重）
3. CRC 查看问题 → 线下整改 → 在线填写处理结果 → 状态 `reviewing`
4. Expert 复核：通过 → `closed`；不通过 → `pending`，再次通知
5. 全程记录操作日志（IssueLog）

### 报告签名

1. Expert 上传 PDF 报告 → 关联受试者和访视信息
2. Celery `ai` 队列触发 AI 识别（幂等：report_id + file_hash 去重）
3. AI 识别 PDF 内容 → 提取摘要存 `ai_summary`
4. Expert 签名 → PyPDF2 + ReportLab 合成签名到 PDF
5. 生成带签名的最终 PDF

---

## 8. 文件存储抽象

```python
class StorageService(ABC):
    @abstractmethod
    def save(self, path: str, data: bytes) -> str: ...

    @abstractmethod
    def get(self, path: str) -> bytes: ...

    @abstractmethod
    def delete(self, path: str) -> bool: ...

    @abstractmethod
    def get_url(self, path: str) -> str: ...

class LocalStorage(StorageService): ...     # 首期实现
class S3Storage(StorageService): ...        # 后续迁移
```

`tmp/` 和正式存储目录必须在同一挂载点（启动时配置校验）。

---

## 9. 异步任务 (Celery)

统一使用 Celery + Redis，不使用 FastAPI BackgroundTasks。

### 队列划分

| 队列 | 任务 | 重试策略 |
|------|------|----------|
| `imaging` | DICOM 脱敏 | 指数退避，最多 3 次 |
| `ai` | PDF 报告 AI 识别 | 指数退避，最多 3 次 |
| `notification` | 短信通知 | 指数退避，最多 3 次 |

### 幂等机制

- 脱敏任务：`session_id + file_hash` 为幂等键
- 短信通知：`issue_id + event_type + timestamp_minute` 去重
- AI 识别：`report_id + file_hash` 去重
- 幂等键存 Redis，TTL 与任务超时对齐

---

## 10. 审计日志

### 不可篡改设计

- 追加写入，不允许 UPDATE/DELETE（数据库层面保护）
- 记录字段：`operator_id`, `ip`, `user_agent`, `timestamp(UTC)`, `action`, `resource_type`, `resource_id`, `before_value`, `after_value`

### 字段级脱敏

- `before_value` / `after_value` 写入前经脱敏函数处理
- 手机号：`138****1234`
- 身份证：`110***********1234`
- 脱敏规则可配置，敏感字段列表统一维护

---

## 11. 前端页面清单

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录 | `/login` | 用户名密码登录 |
| 工作台 | `/dashboard` | 统计数据 + 操作记录 + 事件提醒 |
| 影像列表 | `/imaging` | 影像列表/受试者模式切换，多维筛选 |
| 影像上传 | `/imaging/upload` | 上传表单 + 断点续传进度 |
| 问题列表 | `/issues` | 问题列表 + 多维筛选 |
| 问题详情 | `/issues/:id` | 问题描述 + 操作日志 + CRC 反馈表单 |
| 报告列表 | `/reports` | 报告列表 + 筛选 + AI 摘要 |
| 项目管理 | `/projects` | 项目 CRUD + 中心配置 |
| 用户管理 | `/users` | 用户 CRUD + 角色分配 |
| 审计日志 | `/audit` | 操作日志列表 |
| 个人设置 | `/settings` | 修改密码 + 上传签名 |
