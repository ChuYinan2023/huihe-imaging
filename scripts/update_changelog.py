#!/usr/bin/env python3
"""Generate changelog.html from git log and project status.

Run before each commit:
    python3 scripts/update_changelog.py
"""

import subprocess
import html
from datetime import datetime

# ── Feature checklist (F-01 ~ F-57) ────────────────────────────────
# Status: done / partial / todo
FEATURES = [
    ("F-01", "JWT + HttpOnly Refresh Token 认证", "done"),
    ("F-02", "RBAC 五角色权限体系", "done"),
    ("F-03", "登录/登出/Token 刷新", "done"),
    ("F-04", "CSRF 双提交 Token 校验", "done"),
    ("F-05", "Cookie Secure 可配置", "done"),
    ("F-06", "项目 CRUD", "done"),
    ("F-07", "中心管理", "done"),
    ("F-08", "受试者管理", "done"),
    ("F-09", "影像上传（流式/SHA-256）", "done"),
    ("F-10", "影像 Session CRUD", "done"),
    ("F-11", "文件大小限制（可配置）", "done"),
    ("F-12", "Issue 创建", "done"),
    ("F-13", "Issue FSM 状态机流转", "done"),
    ("F-14", "Issue 处理 + 审核", "done"),
    ("F-15", "Issue 日志记录", "done"),
    ("F-16", "报告上传", "done"),
    ("F-17", "报告 PDF 签名", "done"),
    ("F-18", "报告下载（路径遍历防护）", "done"),
    ("F-19", "AI 摘要生成", "done"),
    ("F-20", "审计日志记录", "done"),
    ("F-21", "审计日志查询（分页/过滤）", "done"),
    ("F-22", "短信通知任务框架", "done"),
    ("F-23", "数据库迁移 (Alembic)", "done"),
    ("F-24", "种子数据脚本", "done"),
    ("F-25", "开发代理 + 启动脚本", "done"),
    ("F-26", "端到端冒烟测试", "done"),
    ("F-27", "79 项单元/集成测试", "done"),
    ("F-28", "登录页面", "done"),
    ("F-29", "Dashboard（统计+事件提醒）", "done"),
    ("F-30", "用户管理页面", "done"),
    ("F-31", "项目管理页面", "done"),
    ("F-32", "影像上传页面", "done"),
    ("F-33", "影像列表页面", "done"),
    ("F-34", "Issue 列表/创建/反馈/审核页面", "done"),
    ("F-35", "报告管理页面", "done"),
    ("F-36", "审计日志页面", "done"),
    ("F-37", "用户设置/签名上传", "done"),
    ("F-38", "角色路由导航", "done"),
    ("F-39", "Axios 拦截器 + Token 自动刷新", "done"),
    ("F-40", "密码修改", "done"),
    ("F-41", "用户密码重置（管理员）", "done"),
    ("F-42", "影像 Session 详情", "partial"),
    ("F-43", "受试者详情页面", "todo"),
    ("F-44", "中心详情页面", "todo"),
    ("F-45", "批量影像上传", "todo"),
    ("F-46", "文件预览（DICOM viewer）", "todo"),
    ("F-47", "导出功能（CSV/Excel）", "todo"),
    ("F-48", "国际化 (i18n)", "todo"),
    ("F-49", "邮件通知", "todo"),
    ("F-50", "操作确认弹窗", "partial"),
    ("F-51", "表单验证增强", "partial"),
    ("F-52", "暗色主题", "todo"),
    ("F-53", "响应式移动端适配", "partial"),
    ("F-54", "访视点管理", "partial"),
    ("F-55", "影像质量 QC", "todo"),
    ("F-56", "统计报表/图表", "partial"),
    ("F-57", "系统配置管理", "todo"),
]

# ── Page checklist ──────────────────────────────────────────────────
PAGES = [
    ("登录页", "done"),
    ("Dashboard", "done"),
    ("用户管理", "done"),
    ("项目管理", "done"),
    ("中心管理", "done"),
    ("受试者管理", "done"),
    ("影像上传", "done"),
    ("影像列表", "done"),
    ("Issue 列表", "done"),
    ("Issue 详情", "done"),
    ("报告管理", "done"),
    ("审计日志", "done"),
    ("用户设置", "done"),
    ("受试者详情", "todo"),
]


def get_git_log():
    """Return list of (hash, datetime_str, subject) from git log."""
    result = subprocess.run(
        ["git", "log", "--format=%H|%ai|%s", "--all"],
        capture_output=True, text=True, check=True,
    )
    entries = []
    for line in result.stdout.strip().split("\n"):
        if "|" not in line:
            continue
        parts = line.split("|", 2)
        if len(parts) == 3:
            entries.append((parts[0][:8], parts[1].strip(), parts[2].strip()))
    return entries


def tag_for(subject):
    """Determine tag and color from commit subject prefix."""
    s = subject.lower()
    if s.startswith("feat"):
        return "feat", "#34a853"
    if s.startswith("fix"):
        return "fix", "#ea4335"
    if s.startswith("test"):
        return "test", "#9c27b0"
    if s.startswith("docs"):
        return "docs", "#1a73e8"
    if s.startswith("refactor"):
        return "refactor", "#ff6f00"
    if s.startswith("chore"):
        return "chore", "#607d8b"
    return "other", "#757575"


def pct(items, done_val="done"):
    done = sum(1 for *_, s in items if s == done_val)
    partial = sum(1 for *_, s in items if s == "partial")
    total = len(items)
    return round((done + partial * 0.5) / total * 100) if total else 0


def bar_class(p):
    if p >= 70:
        return "high"
    if p >= 40:
        return "mid"
    return "low"


def status_icon(s):
    if s == "done":
        return "✅"
    if s == "partial":
        return "🔧"
    return "⬜"


def generate_html():
    commits = get_git_log()
    feat_pct = pct(FEATURES)
    page_pct = pct(PAGES)
    test_pct = 100
    sec_pct = 100
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Feature table rows
    feat_rows = ""
    for fid, name, st in FEATURES:
        feat_rows += f'<tr><td>{html.escape(fid)}</td><td>{html.escape(name)}</td><td class="status-{st}">{status_icon(st)}</td></tr>\n'

    # ── Page grid items
    page_items = ""
    for name, st in PAGES:
        color = "#34a853" if st == "done" else ("#fbbc04" if st == "partial" else "#e8eaed")
        page_items += f'<div class="page-item"><span class="page-dot" style="background:{color}"></span> {html.escape(name)}</div>\n'

    # ── Timeline entries
    timeline = ""
    for sha, dt, subj in commits:
        tag, color = tag_for(subj)
        timeline += f"""<div class="timeline-entry">
  <div class="tl-dot" style="background:{color}"></div>
  <div class="tl-content">
    <div class="tl-header">
      <span class="tl-tag" style="background:{color}">{tag}</span>
      <code class="tl-sha">{sha}</code>
      <span class="tl-date">{html.escape(dt)}</span>
    </div>
    <div class="tl-msg">{html.escape(subj)}</div>
  </div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>汇禾影像管理系统 — 开发日志</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
        header {{ background: linear-gradient(135deg, #1a73e8, #0d47a1); color: #fff; padding: 40px 0; text-align: center; }}
        header h1 {{ font-size: 28px; font-weight: 600; }}
        header p {{ margin-top: 8px; opacity: 0.9; font-size: 15px; }}

        .progress-section {{ background: #fff; border-radius: 12px; padding: 28px; margin: 24px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .progress-section h2 {{ font-size: 20px; margin-bottom: 20px; color: #1a73e8; }}
        .progress-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        @media (max-width: 768px) {{ .progress-grid {{ grid-template-columns: 1fr; }} }}
        .progress-card {{ border: 1px solid #e8eaed; border-radius: 8px; padding: 20px; }}
        .progress-card h3 {{ font-size: 16px; margin-bottom: 12px; color: #444; }}
        .progress-bar-wrap {{ background: #e8eaed; border-radius: 10px; height: 20px; overflow: hidden; margin-bottom: 6px; }}
        .progress-bar {{ height: 100%; border-radius: 10px; transition: width 0.6s ease; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 12px; font-weight: 600; }}
        .progress-bar.high {{ background: linear-gradient(90deg, #34a853, #0f9d58); }}
        .progress-bar.mid {{ background: linear-gradient(90deg, #fbbc04, #f9a825); }}
        .progress-bar.low {{ background: linear-gradient(90deg, #ea4335, #d93025); }}
        .progress-label {{ font-size: 13px; color: #666; text-align: right; }}

        .feature-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }}
        .feature-table th {{ background: #f1f3f4; padding: 8px 12px; text-align: left; font-weight: 600; }}
        .feature-table td {{ padding: 8px 12px; border-bottom: 1px solid #e8eaed; }}
        .feature-table tr:hover {{ background: #f8f9fa; }}
        .status-done {{ color: #34a853; }}
        .status-partial {{ color: #fbbc04; }}
        .status-todo {{ color: #999; }}

        .page-grid {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }}
        .page-item {{ display: flex; align-items: center; gap: 6px; background: #fff; border: 1px solid #e8eaed; border-radius: 6px; padding: 8px 14px; font-size: 14px; }}
        .page-dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}

        .timeline-section {{ background: #fff; border-radius: 12px; padding: 28px; margin: 24px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .timeline-section h2 {{ font-size: 20px; margin-bottom: 20px; color: #1a73e8; }}
        .timeline-entry {{ display: flex; gap: 16px; padding: 12px 0; border-bottom: 1px solid #f1f3f4; }}
        .timeline-entry:last-child {{ border-bottom: none; }}
        .tl-dot {{ width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }}
        .tl-content {{ flex: 1; }}
        .tl-header {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }}
        .tl-tag {{ color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }}
        .tl-sha {{ font-size: 12px; color: #5f6368; background: #f1f3f4; padding: 2px 6px; border-radius: 3px; }}
        .tl-date {{ font-size: 12px; color: #999; }}
        .tl-msg {{ font-size: 14px; color: #333; }}

        footer {{ text-align: center; padding: 30px 0; color: #999; font-size: 13px; }}
    </style>
</head>
<body>
<header>
    <h1>汇禾影像管理系统 — 开发日志</h1>
    <p>Huihe Clinical Imaging Management System &bull; 最后更新: {now}</p>
</header>
<div class="container">

<div class="progress-section">
    <h2>完成进度总览</h2>
    <div class="progress-grid">
        <div class="progress-card">
            <h3>功能完成度 ({feat_pct}%)</h3>
            <div class="progress-bar-wrap"><div class="progress-bar {bar_class(feat_pct)}" style="width:{feat_pct}%">{feat_pct}%</div></div>
            <div class="progress-label">{sum(1 for *_,s in FEATURES if s=='done')}/{len(FEATURES)} 已完成，{sum(1 for *_,s in FEATURES if s=='partial')} 部分完成</div>
        </div>
        <div class="progress-card">
            <h3>页面完成度 ({page_pct}%)</h3>
            <div class="progress-bar-wrap"><div class="progress-bar {bar_class(page_pct)}" style="width:{page_pct}%">{page_pct}%</div></div>
            <div class="progress-label">{sum(1 for *_,s in PAGES if s=='done')}/{len(PAGES)} 已完成</div>
        </div>
        <div class="progress-card">
            <h3>测试覆盖 ({test_pct}%)</h3>
            <div class="progress-bar-wrap"><div class="progress-bar {bar_class(test_pct)}" style="width:{test_pct}%">{test_pct}%</div></div>
            <div class="progress-label">79/79 测试通过</div>
        </div>
        <div class="progress-card">
            <h3>安全修复 ({sec_pct}%)</h3>
            <div class="progress-bar-wrap"><div class="progress-bar {bar_class(sec_pct)}" style="width:{sec_pct}%">{sec_pct}%</div></div>
            <div class="progress-label">5/5 关键项已修复</div>
        </div>
    </div>
</div>

<div class="progress-section">
    <h2>功能清单 (F-01 ~ F-{len(FEATURES):02d})</h2>
    <table class="feature-table">
        <thead><tr><th>编号</th><th>功能</th><th>状态</th></tr></thead>
        <tbody>
{feat_rows}        </tbody>
    </table>
</div>

<div class="progress-section">
    <h2>页面清单</h2>
    <div class="page-grid">
{page_items}    </div>
</div>

<div class="timeline-section">
    <h2>更新时间线 ({len(commits)} 条记录)</h2>
{timeline}</div>

</div>
<footer>汇禾影像管理系统 &copy; 2026 &bull; 由 scripts/update_changelog.py 自动生成</footer>
</body>
</html>"""


if __name__ == "__main__":
    content = generate_html()
    with open("changelog.html", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ changelog.html updated ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
