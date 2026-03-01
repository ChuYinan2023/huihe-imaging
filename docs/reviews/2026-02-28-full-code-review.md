# 全模块代码审查报告

- **日期**: 2026-02-28
- **审查范围**: 全部后端 + 前端代码
- **项目**: 汇禾影像管理系统 (huihe-imaging)

---

## 目录

1. [模块一：后端核心 (core)](#模块一后端核心-core)
2. [模块二：数据模型 (models)](#模块二数据模型-models)
3. [模块三：API 层 (api)](#模块三api-层-api)
4. [模块四：服务层 (services)](#模块四服务层-services)
5. [模块五：前端服务层 (services)](#模块五前端服务层-services)
6. [模块六：前端页面 (pages)](#模块六前端页面-pages)
7. [模块七：Celery 异步任务 (tasks)](#模块七celery-异步任务-tasks)
8. [总结：按严重性排序的关键问题](#总结按严重性排序的关键问题)

---

## 模块一：后端核心 (core)

### 涉及文件

- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/core/security.py`
- `backend/app/core/permissions.py`

### config.py

#### 问题 1 — [安全-高] 默认弱密钥无启动校验

**文件**: `backend/app/core/config.py:9,26,27`

```python
JWT_SECRET_KEY: str = "change-me-in-production"
DICOM_ANONYMIZATION_SALT: str = "change-me-in-production"
CSRF_SECRET_KEY: str = "change-me-csrf-secret"
```

**说明**: 虽然通过 `.env` 支持覆盖默认值，但如果忘记配置，系统会以弱密钥运行。应在应用启动时检查这些值是否已被修改，在非 DEBUG 模式下拒绝使用默认值启动。

**建议修复**:

```python
@model_validator(mode="after")
def check_production_secrets(self):
    if not self.DEBUG:
        if self.JWT_SECRET_KEY == "change-me-in-production":
            raise ValueError("JWT_SECRET_KEY must be changed in production")
        if self.DICOM_ANONYMIZATION_SALT == "change-me-in-production":
            raise ValueError("DICOM_ANONYMIZATION_SALT must be changed in production")
    return self
```

#### 问题 2 — [安全-中] COOKIE_SECURE 默认 False

**文件**: `backend/app/core/config.py:28`

```python
COOKIE_SECURE: bool = False
```

**说明**: 生产环境必须为 True，否则 cookie 可在 HTTP 连接中被截获。建议与 DEBUG 模式联动，或在启动验证中检查。

#### 问题 3 — [类型] ALLOWED_IMAGE_EXTENSIONS 使用裸 set 类型

**文件**: `backend/app/core/config.py:22`

```python
ALLOWED_IMAGE_EXTENSIONS: set = {".dcm", ".jpg", ".jpeg", ".png"}
```

**说明**: Pydantic Settings 对裸 `set` 类型从环境变量的反序列化行为不确定。建议使用 `frozenset` 或 `list` 以确保从 `.env` 文件正确加载。

---

### database.py

#### 整体评价

简洁明了，使用 `expire_on_commit=False` 避免了异步会话中常见的惰性加载问题。

#### 问题 4 — [性能] echo 模式与 DEBUG 联动风险

**文件**: `backend/app/core/database.py:5`

```python
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
```

**说明**: 如果生产环境 DEBUG 误留为 True，所有 SQL 语句将输出到日志，造成性能下降和信息泄露。建议使用独立的 `SQL_ECHO` 配置项。

---

### security.py

#### 整体评价

**良好**。JWT 设计完善：

- 使用 `iss`（issuer）和 `aud`（audience）区分 access/refresh token
- `nbf`（not before）防止时钟偏差
- `jti`（JWT ID）用于 refresh token 的一次性使用
- `fid`（family ID）实现 token family 轮换
- `tv`（token version）支持全量令牌撤销
- 使用 `leeway` 容忍时钟差异

**无重大问题。**

---

### permissions.py

#### 整体评价

**良好**。RBAC 权限矩阵设计清晰，`check_permission` 函数简洁。

#### 问题 5 — [设计] ADMIN 角色文档缺失

**文件**: `backend/app/core/permissions.py:21`

**说明**: 设计文档中只提到 CRC/CRA/DM/Expert/PM 五种角色，但代码中额外添加了 ADMIN 角色且拥有 `MANAGE_USERS` 等权限。应在设计文档中明确 ADMIN 角色的定义和职责。

---

## 模块二：数据模型 (models)

### 涉及文件

- `backend/app/models/user.py`
- `backend/app/models/project.py`
- `backend/app/models/imaging.py`
- `backend/app/models/issue.py`
- `backend/app/models/report.py`
- `backend/app/models/audit.py`
- `backend/app/models/refresh_token.py`
- `backend/app/models/__init__.py`

### 整体评价

使用 SQLAlchemy 2.0 `Mapped` 风格，类型注解完整，`DateTime(timezone=True)` 统一使用 UTC 时区。模型之间的外键关系设计合理。

### user.py

#### 问题 6 — [安全-低] 无密码复杂度约束

**文件**: `backend/app/models/user.py`

**说明**: 模型层没有密码复杂度约束，API 层的 `CreateUserRequest` 也没有密码长度或复杂度验证。前端仅有 `min: 6` 的客户端验证，容易被绕过。

**建议**: 在 `CreateUserRequest` 和 `ChangePasswordRequest` 的 Pydantic 模型中添加密码验证器：

```python
from pydantic import field_validator

@field_validator("password")
@classmethod
def validate_password(cls, v):
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain uppercase letter")
    return v
```

### project.py

**良好**: `UniqueConstraint` 正确使用（`uq_center_project_code`、`uq_subject_project_screening`、`uq_project_user`），Center/Subject/ProjectUser 关系设计合理。

### imaging.py

**良好**: `ImagingStatus` 枚举完整覆盖各种状态，`AnonymizationLog` 详细记录去标识化操作（原始标签哈希、策略版本、UID 映射）。

### issue.py

**良好**: `IssueStatus` 枚举清晰（PENDING → PROCESSING → REVIEWING → CLOSED），`IssueLog` 记录完整的操作历史（操作人、动作、内容、状态变更）。

### report.py, audit.py, refresh_token.py

**无重大问题。**

---

## 模块三：API 层 (api)

### 涉及文件

- `backend/app/api/deps.py`
- `backend/app/api/auth.py`
- `backend/app/api/users.py`
- `backend/app/api/projects.py`
- `backend/app/api/imaging.py`
- `backend/app/api/issues.py`
- `backend/app/api/reports.py`
- `backend/app/api/audit.py`

### deps.py

#### 整体评价

**良好**: CSRF 双重提交验证（cookie + header）、token 版本校验、客户端 IP 提取。

#### 问题 7 — [安全-低] X-Forwarded-For 信任问题

**文件**: `backend/app/api/deps.py:55-58`

```python
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

**说明**: 无条件信任 `X-Forwarded-For` 头。在没有反向代理的部署场景中，攻击者可以伪造此头来伪装 IP 地址。应仅在配置了可信代理后才读取此头。

**建议修复**:

```python
TRUSTED_PROXIES: set[str] = {"127.0.0.1", "::1"}  # 或从 config 读取

def get_client_ip(request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    if client_ip in TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return client_ip
```

---

### auth.py

#### 整体评价

**良好**: Refresh token rotation + family-based revocation 是优秀的安全设计。Token reuse 检测会废弃整个 family。

#### 问题 8 — [安全-高] logout 不废弃服务端 refresh token

**文件**: `backend/app/api/auth.py:177-204`

```python
@router.post("/logout")
async def logout(request, response, db):
    # ... 审计日志 ...
    response.delete_cookie("refresh_token", path="/api/auth")
    response.delete_cookie("csrf_token", path="/")
    return {"message": "Logged out"}
```

**说明**: logout 仅删除客户端 cookie，不废弃服务端的 refresh token 记录。如果攻击者在用户退出前截获了 refresh token，退出后该 token 在过期前仍然有效。

**建议修复**:

```python
@router.post("/logout")
async def logout(request, response, db):
    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = decode_token(token, audience="refresh")
            family_id = payload["fid"]
            # 废弃整个 token family
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == family_id)
                .values(used=True)
            )
            await db.commit()
        except Exception:
            pass

    response.delete_cookie("refresh_token", path="/api/auth")
    response.delete_cookie("csrf_token", path="/")
    return {"message": "Logged out"}
```

#### 问题 9 — [维护] 过期 refresh token 无清理机制

**文件**: `backend/app/api/auth.py`

**说明**: 每次登录创建新的 refresh token 记录，但从不清理过期或已使用的记录。长期运行后 `refresh_tokens` 表会持续膨胀。

**建议**: 添加定期清理任务（Celery beat）或在登录时清理该用户的过期 token：

```python
# 登录成功后，清理过期 token
await db.execute(
    delete(RefreshToken).where(
        RefreshToken.user_id == user.id,
        RefreshToken.expires_at < datetime.now(timezone.utc),
    )
)
```

---

### users.py

#### 问题 10 — [安全-高] DEFAULT_PASSWORD 硬编码 + 前后端不一致

**文件**: `backend/app/api/users.py:15`

```python
DEFAULT_PASSWORD = "Huihe@2024"
```

**后端响应**（第 219 行）:

```python
return {"message": "Password reset to default"}
```

**前端期望**（`UserListPage.tsx:97`）:

```typescript
content: `新密码: ${res.data.new_password ?? '请查看返回结果'}`,
```

**说明**:
1. 默认密码硬编码在源码中，任何能访问代码仓库的人都知道重置后的密码。
2. 后端返回 `message` 字段，前端读取 `new_password` 字段——永远得到 `undefined`，显示"请查看返回结果"。

**建议修复**:
- 生成随机临时密码并返回给管理员
- 或要求用户首次登录时强制修改密码

#### 问题 11 — [Bug] CreateUserRequest 无密码强度验证

**文件**: `backend/app/api/users.py:18-24`

**说明**: `password` 字段接受任意字符串，包括空字符串或单个字符。应添加最小长度和复杂度验证。

#### 问题 12 — [Bug] 更新用户 email 无唯一性检查

**文件**: `backend/app/api/users.py:152-187`

```python
update_data = body.model_dump(exclude_unset=True)
for field, value in update_data.items():
    setattr(user, field, value)
```

**说明**: 如果更新包含 `email` 字段，不会检查新 email 是否已被其他用户使用。可能导致数据库唯一约束冲突（500 错误）或在没有数据库约束的情况下产生重复数据。

**建议修复**:

```python
if "email" in update_data:
    existing = await db.execute(
        select(User).where(User.email == update_data["email"], User.id != user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")
```

---

### projects.py

#### 整体评价

完整的 CRUD 操作 + 嵌套资源管理（Center/Subject）。

#### 问题 13 — [Bug] ProjectUser 未使用，无项目级权限过滤

**文件**: `backend/app/api/projects.py:115-136` 和 `backend/app/models/project.py:38-43`

**说明**: `ProjectUser` 关联表已定义但完全未被使用。`list_projects` 返回所有项目给所有登录用户。按照业务逻辑，CRC 应该只能看到被分配的项目，Expert 只能看到自己负责的项目。

**建议**:

```python
@router.get("")
async def list_projects(...):
    query = select(Project)
    # 非管理员只能看到被分配的项目
    if current_user.role not in (UserRole.ADMIN, UserRole.PM):
        query = query.join(ProjectUser).where(ProjectUser.user_id == current_user.id)
    ...
```

---

### imaging.py

#### 整体评价

**良好**: 流式上传（8KB chunks）、文件大小限制（500MB）、SHA256 完整性校验、原子移动（`os.replace`）。

#### 问题 14 — [Bug] upload_file 不验证 session 所有权

**文件**: `backend/app/api/imaging.py:100-199`

```python
result = await db.execute(
    select(ImagingSession).where(ImagingSession.id == session_id)
)
```

**说明**: 仅检查 session 是否存在和状态是否为 UPLOADING，不检查 `uploaded_by` 是否为当前用户。任何有 `UPLOAD_IMAGING` 权限的 CRC 可以向别人创建的 session 上传文件。

**建议修复**:

```python
if session.uploaded_by != current_user.id:
    raise HTTPException(status_code=403, detail="Not your session")
```

#### 问题 15 — [安全-低] 响应泄露内部存储路径

**文件**: `backend/app/api/imaging.py:47-59`

```python
def _file_response(f: ImagingFile) -> dict:
    return {
        ...
        "file_path": f.file_path,          # e.g., "originals/abc123.dcm"
        "anonymized_path": f.anonymized_path,  # e.g., "anonymized/xyz789.dcm"
        ...
    }
```

**说明**: 向前端暴露了服务器内部的文件存储路径。虽然是相对路径，但仍泄露了目录结构信息。

**建议**: 移除 `file_path` 和 `anonymized_path`，仅返回文件 ID，由后端提供下载端点。

#### 问题 16 — [功能缺失] 上传后未触发匿名化任务

**文件**: `backend/app/api/imaging.py:181-183`

```python
# Transition status: UPLOADING -> ANONYMIZING
new_status = ImagingFSM.transition(session.status, ImagingStatus.ANONYMIZING)
session.status = new_status
```

**说明**: 状态转为 ANONYMIZING 但没有触发 Celery 异步任务执行实际的 DICOM 匿名化。`imaging_tasks.py` 中定义了相关任务但从未被调用。

**建议修复**:

```python
from app.tasks.imaging_tasks import anonymize_session

# 在 commit 之后触发异步任务
await db.commit()
anonymize_session.delay(session.id)
```

---

### issues.py

#### 整体评价

**良好**: FSM 状态转换逻辑清晰，日志记录完整，权限检查到位。

#### 问题 17 — [设计] PROCESSING 状态从未被持久化

**文件**: `backend/app/api/issues.py:214-244`

```python
if old_status == IssueStatus.PENDING:
    new_status = IssueFSM.transition(old_status, IssueStatus.PROCESSING)
    issue.status = new_status
    # ... 创建 log1 ...

    # Then processing -> reviewing
    old_status2 = new_status
    new_status2 = IssueFSM.transition(old_status2, IssueStatus.REVIEWING)
    issue.status = new_status2
    # ... 创建 log2 ...
```

**说明**: 当 issue 从 PENDING 状态开始处理时，代码在同一个请求中执行了两步转换（PENDING → PROCESSING → REVIEWING），在 `db.commit()` 前 issue 的状态已经是 REVIEWING。PROCESSING 状态从未被数据库持久化，使得该状态在数据层面几乎无意义。

**建议**: 如果 PROCESSING 状态有业务意义（如 CRC 正在处理中），应该分为两个独立的 API 调用。如果没有，考虑简化 FSM 直接从 PENDING → REVIEWING。

---

### reports.py

#### 问题 18 — [安全-中] 报告上传一次性读入内存

**文件**: `backend/app/api/reports.py:76-80`

```python
content = await file.read()  # 全部加载到内存
file_hash = hashlib.sha256(content).hexdigest()[:16]
stored_name = f"report_{session_id}_{file_hash}.pdf"
file_path = reports_dir / stored_name
file_path.write_bytes(content)
```

**说明**: 与 imaging 上传的流式处理不同，报告上传使用 `await file.read()` 一次性将整个文件加载到内存。没有文件大小限制。大文件可能导致内存溢出。

**建议修复**: 参照 imaging 上传的流式处理方式：

```python
max_size = 50 * 1024 * 1024  # 50MB
sha256 = hashlib.sha256()
file_size = 0
with open(tmp_path, "wb") as f:
    while chunk := await file.read(8192):
        file_size += len(chunk)
        if file_size > max_size:
            raise HTTPException(413, "File too large")
        sha256.update(chunk)
        f.write(chunk)
```

#### 问题 19 — [安全-低] sign_report 权限复用

**文件**: `backend/app/api/reports.py:174`

```python
if not check_permission(current_user.role, Permission.UPLOAD_REPORT):
```

**说明**: 签名操作和上传操作使用相同的权限 `UPLOAD_REPORT`。签名是更敏感的操作，应有独立的 `SIGN_REPORT` 权限。

---

### audit.py

#### 问题 20 — [Bug] 日期过滤使用字符串直接比较 DateTime

**文件**: `backend/app/api/audit.py:56-61`

```python
if date_from is not None:
    query = query.where(AuditLog.timestamp >= date_from)  # date_from 是 str
if date_to is not None:
    query = query.where(AuditLog.timestamp <= date_to)    # date_to 是 str
```

**说明**: `date_from` 和 `date_to` 为 `str` 类型，直接与 `DateTime` 列比较。SQLAlchemy 的隐式转换在不同数据库中行为不一致（SQLite vs PostgreSQL）。应解析为 `datetime` 对象。

**建议修复**:

```python
from datetime import datetime

if date_from is not None:
    try:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        query = query.where(AuditLog.timestamp >= dt_from)
    except ValueError:
        raise HTTPException(400, "Invalid date_from format")
```

#### 问题 21 — [Bug] 前后端字段名不匹配

**后端模型** (`backend/app/models/audit.py:13`): 时间字段为 `timestamp`
**后端 API 响应** (`backend/app/api/audit.py:20`): 返回 `timestamp`
**前端列定义** (`frontend/src/pages/audit/AuditLogPage.tsx:63`): 使用 `created_at`

**后端 API 响应**: 无 `operator_name` 字段
**前端列定义** (`AuditLogPage.tsx:67`): 使用 `operator_name`

**说明**: 字段名不一致导致前端表格相关列始终显示为空。

**建议修复**: 统一前后端字段命名，或在后端 `_audit_response` 中添加别名：

```python
def _audit_response(log: AuditLog) -> dict:
    return {
        ...
        "created_at": log.timestamp.isoformat() if log.timestamp else None,  # 兼容前端
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        ...
    }
```

---

## 模块四：服务层 (services)

### 涉及文件

- `backend/app/services/audit_service.py`
- `backend/app/services/state_machine.py`
- `backend/app/services/upload_service.py`
- `backend/app/services/dicom_service.py`
- `backend/app/services/storage_service.py`
- `backend/app/services/signature_service.py`

### audit_service.py

#### 整体评价

**良好**: 敏感信息自动脱敏（手机号显示为 `138****1234`，身份证号显示为 `110***********1234`）。

### state_machine.py

#### 整体评价

**良好**: 简洁优雅的 FSM 实现，基类 `FSM` + 具体的 `ImagingFSM` 和 `IssueFSM` 子类，转换表清晰。

### upload_service.py

#### 问题 22 — [代码质量] validate_file 逻辑冗余

**文件**: `backend/app/services/upload_service.py:15-25`

```python
def validate_file(filename: str, content_type: str | None) -> bool:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    if content_type and content_type not in ALLOWED_MIMES:
        # Allow octet-stream for DICOM files
        if ext == ".dcm" and content_type == "application/octet-stream":
            return True                    # 冗余：octet-stream 已在 ALLOWED_MIMES 中
        if content_type not in ALLOWED_MIMES:
            return False                   # 冗余：与外层 if 条件相同
    return True
```

**说明**:
1. `application/octet-stream` 已经在 `ALLOWED_MIMES` 集合中，所以 `.dcm` + `octet-stream` 的特殊处理永远不会执行（外层 `if content_type not in ALLOWED_MIMES` 已经排除了它）。
2. 内层的 `if content_type not in ALLOWED_MIMES: return False` 与外层条件完全重复。

**建议简化**:

```python
def validate_file(filename: str, content_type: str | None) -> bool:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    if content_type and content_type not in ALLOWED_MIMES:
        return False
    return True
```

### dicom_service.py

#### 整体评价

**良好**: PHI 标签列表全面（18 个 DICOM 标签），UID 重新映射设计合理，私有标签自动移除。

#### 问题 23 — [安全-中] UID 生成使用确定性哈希

**文件**: `backend/app/services/dicom_service.py:36-42`

```python
def generate_uid(original_uid: str, salt: str) -> str:
    hash_bytes = hashlib.sha256(f"{original_uid}{salt}".encode()).digest()
    ...
```

**说明**: UID 生成使用确定性 SHA256(original_uid + salt)。相同输入总是产生相同输出，这在某些场景下有用（可追溯），但如果 salt 泄露，攻击者可以构造彩虹表反推原始 UID 映射。

**建议**: 考虑使用 HMAC 替代简单拼接：

```python
import hmac
hash_bytes = hmac.new(salt.encode(), original_uid.encode(), hashlib.sha256).digest()
```

### storage_service.py

#### 整体评价

**良好**: `LocalStorage` 包含路径遍历防护，抽象接口 `StorageService` 设计合理（为未来的 S3/OSS 扩展做准备）。

#### 问题 24 — [设计] StorageService 未在 API 层使用

**文件**: `backend/app/services/storage_service.py` vs `backend/app/api/imaging.py`

**说明**: `StorageService` 定义了完整的存储抽象接口（`save`、`get`、`delete`、`atomic_move`），`LocalStorage` 实现了本地文件存储。但 imaging 上传 API 直接操作文件系统（`open(tmp_path, "wb")`、`os.replace`），完全绕过了 StorageService。

**影响**: 如果未来需要切换到 S3/OSS 存储，imaging 模块的代码需要大量修改。

**建议**: 通过依赖注入在 API 层使用 StorageService。

### signature_service.py

#### 整体评价

功能完整：读取 PDF → 创建签名覆盖层 → 合并到最后一页。

#### 问题 25 — [安全-低] 签名位置硬编码

**文件**: `backend/app/services/signature_service.py:15`

```python
c.drawImage(str(signature_path), 400, 50, width=120, height=60, ...)
```

**说明**: 签名位置 (400, 50) 和大小 (120x60) 硬编码。不同大小的 PDF 页面（A4、Letter 等）会导致签名位置偏移或超出页面边界。

**建议**: 根据页面实际大小动态计算签名位置。

---

## 模块五：前端服务层 (services)

### 涉及文件

- `frontend/src/services/api.ts`
- `frontend/src/services/imagingService.ts`
- `frontend/src/services/userService.ts`
- `frontend/src/services/projectService.ts`
- `frontend/src/services/issueService.ts`
- `frontend/src/services/reportService.ts`
- `frontend/src/services/auditService.ts`
- `frontend/src/stores/auth.ts`

### api.ts

#### 整体评价

**良好**: 401 响应自动刷新 token 并重试原请求，CSRF token 通过拦截器自动附加。

#### 问题 26 — [Bug] Token 存储在内存变量中，页面刷新后丢失

**文件**: `frontend/src/services/api.ts:8-9`

```typescript
let accessToken: string | null = null;
let csrfToken: string | null = null;
```

**说明**: token 存储在模块级变量中。页面刷新后 accessToken 和 csrfToken 丢失。`auth.ts` 的 `fetchMe` 可以恢复 user 状态，但 token 无法恢复——刷新后的第一次 API 请求会因为没有 Bearer token 而返回 401，然后 interceptor 尝试 refresh，但此时 CSRF token 也为 null。

**潜在问题**:
- 如果 refresh 端点也需要 CSRF 验证（但从后端代码看 refresh 不走 `get_current_user`，不验证 CSRF），问题仅限于第一次请求的额外延迟。
- 实际上后端 auth 端点（login/refresh/logout）的写操作也应该经过 CSRF 检查，但当前后端的 `verify_csrf` 只在 `get_current_user` 中调用。

#### 问题 27 — [Bug] 并发 401 请求竞态条件

**文件**: `frontend/src/services/api.ts:31-49`

**说明**: 如果同时有多个请求返回 401，每个请求都会独立尝试 refresh。由于后端的 refresh token 是一次性的（使用后标记为 used），第二个 refresh 请求会触发 "token reuse detected" 逻辑，废弃整个 token family，导致用户被强制登出。

**建议修复**: 使用请求队列/锁机制：

```typescript
let refreshPromise: Promise<any> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      if (!refreshPromise) {
        refreshPromise = axios.post('/api/auth/refresh', {}, { withCredentials: true })
          .finally(() => { refreshPromise = null; });
      }
      try {
        const res = await refreshPromise;
        accessToken = res.data.access_token;
        csrfToken = res.data.csrf_token;
        error.config.headers.Authorization = `Bearer ${accessToken}`;
        return api(error.config);
      } catch {
        clearTokens();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

### stores/auth.ts

**良好**: Zustand store 设计简洁，login/logout/fetchMe 三个核心操作。

### 其他 service 文件

**良好**: API 调用封装简洁、一致。

---

## 模块六：前端页面 (pages)

### 涉及文件

- `frontend/src/layouts/MainLayout.tsx`
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/router/index.tsx`
- `frontend/src/pages/login/LoginPage.tsx`
- `frontend/src/pages/dashboard/DashboardPage.tsx`
- `frontend/src/pages/imaging/ImagingUploadPage.tsx`
- `frontend/src/pages/imaging/ImagingListPage.tsx`
- `frontend/src/pages/issues/IssueListPage.tsx`
- `frontend/src/pages/issues/IssueDetailPage.tsx`
- `frontend/src/pages/reports/ReportListPage.tsx`
- `frontend/src/pages/projects/ProjectListPage.tsx`
- `frontend/src/pages/users/UserListPage.tsx`
- `frontend/src/pages/audit/AuditLogPage.tsx`
- `frontend/src/pages/settings/SettingsPage.tsx`

### MainLayout.tsx

#### 问题 28 — [Bug] useEffect 依赖数组缺失

**文件**: `frontend/src/layouts/MainLayout.tsx:31-34`

```tsx
useEffect(() => {
    if (!isAuthenticated) {
        fetchMe().catch(() => navigate('/login'));
    }
}, []);  // 缺少 isAuthenticated, fetchMe, navigate 依赖
```

**说明**: `useEffect` 依赖数组为空但内部引用了 `isAuthenticated`、`fetchMe`、`navigate`。React 严格模式下 ESLint 会警告。

#### 问题 29 — [Bug] 在 render 函数中调用 navigate

**文件**: `frontend/src/layouts/MainLayout.tsx:41-44`

```tsx
if (!isAuthenticated || !user) {
    navigate('/login');
    return null;
}
```

**说明**: 在组件渲染阶段直接调用 `navigate()` 是 React 反模式，可能导致警告 "Cannot update a component while rendering a different component"。应将导航逻辑放入 `useEffect`。

### router/index.tsx

#### 问题 30 — [安全-高] ProtectedRoute 未使用

**文件**: `frontend/src/router/index.tsx` 和 `frontend/src/components/ProtectedRoute.tsx`

**说明**: `ProtectedRoute` 组件已实现（支持角色检查），但路由配置中完全没有使用它。所有子路由直接挂在 `MainLayout` 下，路由保护完全依赖 `MainLayout` 中的重定向逻辑。

**影响**: 非 admin 用户可以通过直接输入 URL（如 `/users`、`/audit`）访问不应看到的页面。虽然 API 层有权限检查会返回 403，但用户仍然能看到页面 UI。

**建议修复**:

```tsx
{
    path: '/',
    element: <MainLayout />,
    children: [
        { index: true, element: <DashboardPage /> },
        { path: 'users', element: <ProtectedRoute roles={['admin']}><UserListPage /></ProtectedRoute> },
        { path: 'audit', element: <ProtectedRoute roles={['admin']}><AuditLogPage /></ProtectedRoute> },
        { path: 'projects', element: <ProtectedRoute roles={['admin', 'pm']}><ProjectListPage /></ProtectedRoute> },
        // ...
    ],
}
```

### ImagingUploadPage.tsx

#### 整体评价

**良好**: 四步向导流程设计合理，级联选择（项目 → 中心 → 受试者），逐文件上传带进度条。

#### 问题 31 — [Bug] 文件移除使用 name 匹配

**文件**: `frontend/src/pages/imaging/ImagingUploadPage.tsx:273`

```tsx
onRemove={(file) => {
    setFileList(prev => prev.filter(f => f.name !== file.name));
}}
```

**说明**: 如果用户选择了两个同名文件（来自不同目录），移除其中一个会同时移除两个。应使用唯一标识（如 `lastModified` + `size` 组合）来区分文件。

### ImagingListPage.tsx

#### 问题 32 — [Bug] 受试者视图数据结构前后端不匹配

**文件**: `frontend/src/pages/imaging/ImagingListPage.tsx:93-108`

**前端列定义**:

```tsx
{ title: '受试者编号', dataIndex: 'screening_number', key: 'screening_number' },
{ title: '项目', dataIndex: 'project_name', key: 'project_name' },
{ title: '中心', dataIndex: 'center_name', key: 'center_name' },
{ title: '会话数', dataIndex: 'session_count', key: 'session_count' },
```

**后端返回** (`backend/app/api/imaging.py:253-273`):

```python
return {"subjects": grouped}
# grouped = {subject_id: [session_response, ...]}
```

**说明**: 后端返回的是 `{subjects: {1: [{session}], 2: [{session}]}}` 格式的字典，不是数组。前端的 Table 组件需要数组作为 dataSource。而且后端没有返回 `screening_number`、`project_name`、`center_name`、`session_count` 等字段。

**影响**: 受试者视图功能完全不可用。

### IssueDetailPage.tsx

**良好**: 操作按钮根据角色和状态动态显示逻辑正确（CRC 处理 pending/processing，Expert 审核 reviewing）。

### ReportListPage.tsx

#### 问题 33 — [Bug] has_signature 字段后端不存在

**文件**: `frontend/src/pages/reports/ReportListPage.tsx:112-116`

```tsx
{
    title: '已签名',
    dataIndex: 'has_signature',
    ...
}
```

**后端 _report_response** (`backend/app/api/reports.py:29-42`): 返回 `signed_file_path` 字段，不是 `has_signature`。

**建议修复**: 前端使用 `signed_file_path` 判断：

```tsx
render: (_, record) => record.signed_file_path
    ? <Tag icon={<CheckCircleOutlined />} color="success">已签名</Tag>
    : <Tag color="default">未签名</Tag>,
```

#### 问题 34 — [UX] 报告上传需手动输入 session_id

**文件**: `frontend/src/pages/reports/ReportListPage.tsx:198-203`

```tsx
<Form.Item name="session_id" label="关联影像会话 ID">
    <InputNumber style={{ width: '100%' }} min={1} placeholder="影像会话 ID" />
</Form.Item>
```

**说明**: 用户需要手动输入数字 ID。对于非技术用户，无法知道具体的 session ID 是多少。应提供影像会话的下拉选择列表，类似 IssueListPage 中创建问题时的做法。

### ProjectListPage.tsx

**良好**: 完整的项目 CRUD + 展开行显示中心列表 + 添加中心。

### UserListPage.tsx

**良好**: 完整的用户管理功能（创建、编辑、重置密码、启用/禁用）。

### AuditLogPage.tsx

#### 问题 35 — [Bug] 前后端字段名不匹配（同问题 21）

**说明**: 审计日志页面使用 `created_at` 和 `operator_name` 字段，但后端 `_audit_response` 返回 `timestamp` 且不包含 `operator_name`。导致时间列和操作人列始终为空。

### SettingsPage.tsx

#### 问题 36 — [功能缺失] 签名上传仅前端预览

**文件**: `frontend/src/pages/settings/SettingsPage.tsx:119`

```tsx
<p>签名上传功能即将上线，当前仅供预览。</p>
```

**说明**: 选择签名图片后只有客户端预览，没有上传到服务端的 API 调用。后端也没有提供签名上传端点。

---

## 模块七：Celery 异步任务 (tasks)

### 涉及文件

- `backend/app/tasks/celery_app.py`
- `backend/app/tasks/ai_tasks.py`
- `backend/app/tasks/imaging_tasks.py`
- `backend/app/tasks/notification_tasks.py`

### 整体评价

**功能未联通**: 异步任务模块定义了以下任务但均未被 API 层调用：

| 任务 | 用途 | 状态 |
|------|------|------|
| `anonymize_session` | DICOM 去标识化 | 未调用 |
| `summarize_report` | AI 报告摘要 | 未调用 |
| `send_notification` | 消息通知 | 未调用 |

**影响**:
- 影像上传后状态停留在 ANONYMIZING，永远不会变成 COMPLETED
- 报告的 `ai_summary` 字段永远为 null
- 没有任何通知发送

---

## 总结：按严重性排序的关键问题

### 高优先级（应立即修复）

| # | 模块 | 问题 | 影响 |
|---|------|------|------|
| 1 | `api/auth.py` | logout 不废弃服务端 refresh token | 安全漏洞：退出后令牌仍可用 |
| 2 | `router/index.tsx` | ProtectedRoute 已实现但未使用 | 前端无路由级权限控制 |
| 3 | `api/imaging.py` | 上传后匿名化任务未触发 | 核心功能缺失：DICOM 无法匿名化 |
| 4 | `core/config.py` | 生产弱密钥无启动检查 | 安全漏洞：可能以弱密钥运行 |
| 5 | `api/users.py` | DEFAULT_PASSWORD 硬编码 + 前后端不一致 | 安全漏洞 + 功能 Bug |
| 6 | `services/api.ts` | 页面刷新后 token 丢失 + 并发 401 竞态 | 用户体验差 + 可能被强制登出 |

### 中优先级（应在近期迭代中修复）

| # | 模块 | 问题 | 影响 |
|---|------|------|------|
| 7 | `api/reports.py` | 报告上传一次性读入内存，无大小限制 | 大文件导致内存溢出 |
| 8 | `api/projects.py` | ProjectUser 未使用，无项目级权限过滤 | 数据隔离缺失 |
| 9 | `api/audit.py` | 前后端字段名不匹配 | 审计日志页面数据显示为空 |
| 10 | `ImagingListPage` | 受试者视图数据结构前后端不匹配 | 受试者视图功能不可用 |
| 11 | `ReportListPage` | has_signature 字段后端不存在 | 签名状态列显示异常 |
| 12 | `api/users.py` | email 更新无唯一性检查 | 数据库约束错误或数据重复 |
| 13 | `api/imaging.py` | 不验证 session 所有权 | 跨用户操作漏洞 |
| 14 | `api/issues.py` | PROCESSING 状态从未持久化 | 状态机设计与实际行为不一致 |

### 低优先级（可在后续版本修复）

| # | 模块 | 问题 | 影响 |
|---|------|------|------|
| 15 | `api/imaging.py` | 响应泄露内部文件路径 | 信息泄露 |
| 16 | `upload_service.py` | 文件验证逻辑冗余 | 代码质量 |
| 17 | `storage_service.py` | StorageService 未在 API 层使用 | 架构一致性 |
| 18 | `MainLayout.tsx` | navigate 在 render 中调用 | React 反模式 |
| 19 | `ImagingUploadPage` | 文件移除使用 name 匹配 | 同名文件 Bug |
| 20 | `SettingsPage` | 签名上传功能未实现 | 功能缺失 |
| 21 | `dicom_service.py` | UID 生成使用确定性哈希 | 安全增强 |
| 22 | `signature_service.py` | 签名位置硬编码 | 兼容性问题 |
| 23 | `api/deps.py` | X-Forwarded-For 无条件信任 | IP 伪造风险 |
| 24 | `api/auth.py` | 过期 refresh token 无清理 | 数据库膨胀 |
| 25 | `ReportListPage` | 报告上传需手动输入 session_id | 用户体验差 |

---

## 架构亮点

尽管存在上述问题，项目在以下方面设计良好：

1. **JWT 安全体系**: Token family rotation + reuse detection + version-based revocation
2. **CSRF 防护**: 双重提交验证（cookie + header）
3. **审计日志**: 全操作审计 + 敏感信息自动脱敏
4. **状态机**: 清晰的 FSM 实现确保状态转换合法性
5. **DICOM 去标识化**: 全面的 PHI 标签处理 + UID 重映射 + 私有标签清除
6. **文件上传**: 流式处理 + 大小限制 + SHA256 完整性校验 + 原子移动
7. **路径遍历防护**: StorageService 和报告下载均有路径检查
8. **RBAC 权限**: 清晰的角色-权限矩阵
