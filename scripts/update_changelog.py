#!/usr/bin/env python3
"""Generate changelog.html from changelog-data.json.

Data file: changelog-data.json (project root)
  - features[]: feature checklist with id/module/name/status/note
  - pages[]:    page checklist with name/status
  - stats:      test/security counters
  - entries[]:  detailed changelog entries (newest first)

To add a new entry, append to the "entries" array in the JSON and run:
    python3 scripts/update_changelog.py

Pre-commit hook runs this automatically.
"""

import json
import html as html_mod
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "changelog-data.json"
OUTPUT_FILE = ROOT / "changelog.html"

TAG_COLORS = {
    "feat": "#1a73e8",
    "fix": "#ea4335",
    "docs": "#34a853",
    "test": "#fbbc04",
    "refactor": "#ff6f00",
    "chore": "#607d8b",
}

STATUS_LABELS = {
    "done": ("已完成", "status-done", "done"),
    "partial": ("部分完成", "status-partial", "partial"),
    "todo": ("待开发", "status-todo", "todo"),
}


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def pct(items):
    done = sum(1 for i in items if i["status"] == "done")
    partial = sum(1 for i in items if i["status"] == "partial")
    total = len(items)
    return round((done + partial * 0.5) / total * 100) if total else 0


def bar_class(p):
    if p >= 70:
        return "high"
    if p >= 40:
        return "mid"
    return "low"


def esc(s):
    return html_mod.escape(s)


def render_features(features):
    rows = ""
    for f in features:
        sl = STATUS_LABELS.get(f["status"], ("未知", "status-todo", "todo"))
        label = f.get("note", sl[0]) if f["status"] == "partial" else sl[0]
        rows += f'<tr><td>{esc(f["id"])}</td><td>{esc(f["module"])}</td><td>{esc(f["name"])}</td><td class="{sl[1]}">{esc(label)}</td></tr>\n'
    return rows


def render_pages(pages):
    items = ""
    for p in pages:
        dot_class = STATUS_LABELS.get(p["status"], ("", "", "todo"))[2]
        items += f'<div class="page-item"><span>{esc(p["name"])}</span><span class="dot {dot_class}"></span></div>\n'
    return items


def render_entries(entries):
    items = ""
    for e in entries:
        tag = e.get("tag", "feat")
        color = TAG_COLORS.get(tag, "#757575")
        tag_text_color = "#333" if tag == "test" else "#fff"
        # Convert \n in desc to <br>
        desc_html = esc(e["desc"]).replace("\n", "<br>")
        items += f"""
                <div class="timeline-item">
                    <div class="timeline-dot {tag}"></div>
                    <div class="timeline-content">
                        <div class="timeline-time">{esc(e["date"])}</div>
                        <div class="timeline-title"><span class="tag {tag}" style="color:{tag_text_color}">{tag}</span>{esc(e["title"])}</div>
                        <div class="timeline-desc">{desc_html}</div>
                        <div class="timeline-hash">{esc(e.get("commits", ""))}</div>
                    </div>
                </div>
"""
    return items


def generate_html(data):
    features = data["features"]
    pages = data["pages"]
    stats = data["stats"]
    entries = data["entries"]

    feat_pct = pct(features)
    page_pct = pct(pages)
    feat_done = sum(1 for f in features if f["status"] == "done")
    page_done = sum(1 for p in pages if p["status"] == "done")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

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
        .feature-table th {{ background: #f8f9fa; text-align: left; padding: 8px 12px; font-weight: 600; border-bottom: 2px solid #e8eaed; }}
        .feature-table td {{ padding: 6px 12px; border-bottom: 1px solid #f0f0f0; }}
        .feature-table tr:hover {{ background: #f8f9fa; }}
        .status-done {{ color: #0f9d58; font-weight: 600; }}
        .status-partial {{ color: #f9a825; font-weight: 600; }}
        .status-todo {{ color: #999; }}

        .page-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; margin-top: 12px; }}
        .page-item {{ background: #f8f9fa; border-radius: 6px; padding: 10px 14px; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }}
        .page-item .dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
        .page-item .dot.done {{ background: #0f9d58; }}
        .page-item .dot.partial {{ background: #f9a825; }}
        .page-item .dot.todo {{ background: #ccc; }}

        .changelog {{ margin-top: 24px; }}
        .changelog h2 {{ font-size: 20px; margin-bottom: 16px; color: #1a73e8; }}
        .timeline {{ position: relative; padding-left: 32px; }}
        .timeline::before {{ content: ''; position: absolute; left: 11px; top: 0; bottom: 0; width: 2px; background: #e8eaed; }}
        .timeline-item {{ position: relative; margin-bottom: 24px; }}
        .timeline-dot {{ position: absolute; left: -32px; top: 4px; width: 22px; height: 22px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 0 0 2px #e8eaed; }}
        .timeline-dot.feat {{ background: #1a73e8; }}
        .timeline-dot.fix {{ background: #ea4335; }}
        .timeline-dot.docs {{ background: #34a853; }}
        .timeline-dot.test {{ background: #fbbc04; }}
        .timeline-dot.refactor {{ background: #ff6f00; }}
        .timeline-dot.chore {{ background: #607d8b; }}
        .timeline-content {{ background: #fff; border-radius: 8px; padding: 16px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
        .timeline-time {{ font-size: 12px; color: #888; margin-bottom: 4px; }}
        .timeline-title {{ font-size: 15px; font-weight: 600; }}
        .timeline-desc {{ font-size: 13px; color: #666; margin-top: 6px; }}
        .timeline-hash {{ font-family: monospace; font-size: 11px; color: #aaa; margin-top: 4px; }}
        .tag {{ display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 10px; color: #fff; margin-right: 6px; }}
        .tag.feat {{ background: #1a73e8; }}
        .tag.fix {{ background: #ea4335; }}
        .tag.docs {{ background: #34a853; }}
        .tag.test {{ background: #fbbc04; color: #333; }}
        .tag.refactor {{ background: #ff6f00; }}
        .tag.chore {{ background: #607d8b; }}

        footer {{ text-align: center; padding: 30px; color: #999; font-size: 13px; }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>汇禾影像管理系统 (Huihe Imaging)</h1>
            <p>PMS 上市后监管平台 Phase 1 — 开发迭代记录 | 最后更新：{now}</p>
        </div>
    </header>

    <div class="container">
        <div class="progress-section">
            <h2>整体进度</h2>
            <div class="progress-grid">
                <div class="progress-card">
                    <h3>功能清单完成度 (F-01 ~ F-{len(features):02d})</h3>
                    <div class="progress-bar-wrap">
                        <div class="progress-bar {bar_class(feat_pct)}" style="width: {feat_pct}%">{feat_pct}%</div>
                    </div>
                    <div class="progress-label">{feat_done} / {len(features)} 项已完成</div>
                </div>
                <div class="progress-card">
                    <h3>页面清单完成度</h3>
                    <div class="progress-bar-wrap">
                        <div class="progress-bar {bar_class(page_pct)}" style="width: {page_pct}%">{page_pct}%</div>
                    </div>
                    <div class="progress-label">{page_done} / {len(pages)} 页已完成</div>
                </div>
                <div class="progress-card">
                    <h3>后端测试</h3>
                    <div class="progress-bar-wrap">
                        <div class="progress-bar high" style="width: {round(stats['tests_passed']/stats['tests_total']*100)}%">{round(stats['tests_passed']/stats['tests_total']*100)}%</div>
                    </div>
                    <div class="progress-label">{stats['tests_passed']} / {stats['tests_total']} 通过</div>
                </div>
                <div class="progress-card">
                    <h3>安全审查修复</h3>
                    <div class="progress-bar-wrap">
                        <div class="progress-bar high" style="width: {round(stats['security_fixed']/stats['security_total']*100)}%">{round(stats['security_fixed']/stats['security_total']*100)}%</div>
                    </div>
                    <div class="progress-label">{stats['security_fixed']} / {stats['security_total']} 项已修复</div>
                </div>
            </div>
        </div>

        <div class="progress-section">
            <h2>功能清单 (F-01 ~ F-{len(features):02d})</h2>
            <table class="feature-table">
                <thead><tr><th>编号</th><th>模块</th><th>功能</th><th>状态</th></tr></thead>
                <tbody>
{render_features(features)}                </tbody>
            </table>
        </div>

        <div class="progress-section">
            <h2>页面清单</h2>
            <div class="page-grid">
{render_pages(pages)}            </div>
        </div>

        <div class="progress-section changelog">
            <h2>更新日志</h2>
            <div class="timeline">
{render_entries(entries)}
            </div>
        </div>
    </div>

    <footer>
        <p>汇禾影像管理系统 &copy; 2026 | 由 changelog-data.json + scripts/update_changelog.py 生成</p>
    </footer>
</body>
</html>"""


if __name__ == "__main__":
    if not DATA_FILE.exists():
        print(f"✗ {DATA_FILE} not found")
        exit(1)
    data = load_data()
    content = generate_html(data)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ changelog.html updated ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
