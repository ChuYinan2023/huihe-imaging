# 汇禾影像管理系统 — 典型业务全流程

## 概述

本文档描述一个完整的项目数据从创建、上传、质疑处理到报告签署的典型业务流程，涵盖五种角色的协作。

---

## 第一阶段：项目搭建（Admin / PM）

### 1. 创建项目
- **角色**：Admin 或 PM
- **路径**：项目管理 → 新建项目
- **填写**：项目编号（如 `PROJ-001`）、项目名称、描述
- **API**：`POST /api/projects`

### 2. 添加中心
- 在项目下添加研究中心（如 `CTR-01 北京协和医院`）
- **API**：`POST /api/projects/{project_id}/centers`

### 3. 添加受试者
- 在中心下添加受试者，填写筛选号（如 `SCR-001`）
- **API**：`POST /api/projects/{project_id}/centers/{center_id}/subjects`

---

## 第二阶段：影像采集与上传（CRC）

### 4. 创建影像 Session
- **角色**：CRC
- **路径**：影像上传页面
- **选择**：项目 → 中心 → 受试者 → 访视点（如 `Baseline`）
- 系统自动关联 project_id / center_id / subject_id
- **API**：`POST /api/imaging/sessions`

### 5. 上传影像文件
- 在 Session 下上传 DICOM 或其他影像文件
- 后端流式接收（8KB 分块），实时计算 SHA-256 校验
- 超过 `MAX_FILE_SIZE_MB` 自动拒绝（413）
- **API**：`POST /api/imaging/sessions/{session_id}/files`

---

## 第三阶段：质疑处理（CRA → CRC → PM）

### 6. 发起质疑（Issue）
- **角色**：CRA（临床监查员）发现问题后
- **路径**：Issue 列表 → 创建 Issue
- 关联一个 Imaging Session，描述问题
- 状态：`PENDING`（待处理）
- **API**：`POST /api/issues`

### 7. 处理质疑
- **角色**：CRC 或相关人员
- **操作**：在 Issue 详情中点击"处理"，填写处理内容
- 状态流转：`PENDING` → `PROCESSING` → `REVIEWING`（自动提交审核）
- **API**：`PUT /api/issues/{issue_id}/process`

### 8. 审核质疑
- **角色**：PM
- 两种操作：
  - **通过（approve）**：`REVIEWING` → `CLOSED`，Issue 关闭
  - **驳回（reject）**：`REVIEWING` → `PENDING`，退回重新处理
- **API**：`PUT /api/issues/{issue_id}/review`

### 状态机流转图

```
PENDING ──→ PROCESSING ──→ REVIEWING ──→ CLOSED
   ↑                            │
   └────────── reject ──────────┘
```

---

## 第四阶段：报告管理（CRA / PM）

### 9. 上传报告
- **角色**：CRA
- 上传 PDF 报告文件，关联到影像 Session
- **API**：`POST /api/reports`

### 10. AI 摘要（可选）
- 对报告内容生成 AI 摘要
- **API**：`POST /api/reports/{report_id}/summarize`

### 11. 报告签名
- **角色**：PM 或授权人员
- 使用上传的个人签名图片对 PDF 进行数字签名
- **API**：`PUT /api/reports/{report_id}/sign`

### 12. 下载报告
- 各角色按权限下载已签名的报告
- **API**：`GET /api/reports/{report_id}/download`

---

## 第五阶段：审计与监控（Admin / DM）

### 13. 审计日志
- 系统自动记录所有操作（登录、创建、修改、上传、签名等）
- 包含：操作人、IP、时间、操作类型、变更前后值
- Admin 可在审计日志页面查询、过滤
- **API**：`GET /api/audit-logs`

---

## 角色权限总览

| 操作 | Admin | PM | CRC | CRA | DM |
|------|:-----:|:--:|:---:|:---:|:--:|
| 管理项目/中心 | ✅ | ✅ | - | - | - |
| 添加受试者 | ✅ | ✅ | ✅ | - | - |
| 上传影像 | ✅ | - | ✅ | - | - |
| 发起 Issue | ✅ | ✅ | ✅ | ✅ | - |
| 处理 Issue | ✅ | - | ✅ | - | - |
| 审核 Issue | ✅ | ✅ | - | - | - |
| 上传/签名报告 | ✅ | ✅ | - | ✅ | - |
| 查看审计日志 | ✅ | - | - | - | - |
| 用户管理 | ✅ | - | - | - | - |

---

## 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| Admin | admin1 | Admin@2026 |
| PM | pm1 | Pm@2026 |
| CRC | crc1 | Crc@2026 |
| CRA | cra1 | Cra@2026 |
| DM | dm1 | Dm@2026 |

## 建议操作顺序

1. 用 **admin1** 登录 → 创建项目 → 添加中心 → 添加受试者
2. 切换 **crc1** 登录 → 创建影像 Session → 上传影像文件
3. 切换 **cra1** 登录 → 发起 Issue（质疑）
4. 切换 **crc1** 登录 → 处理 Issue
5. 切换 **pm1** 登录 → 审核 Issue（通过或驳回）
6. 切换 **cra1** 登录 → 上传报告
7. 切换 **pm1** 登录 → 签名报告
8. 用 **admin1** 登录 → 查看审计日志，确认全流程记录
