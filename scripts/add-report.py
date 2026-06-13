#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add-report.py — 发布一份新调研报告时，一条命令更新仓库全部 5 处索引：

  1. manifest.json            （权威数据源，驱动全局 sidebar）
  2. {topic}/README.md        （GitHub 代码视图；新话题自动创建）
  3. {topic}/index.html       （GitHub Pages 入口；新话题自动创建）
  4. README.md INDEX 区块     （主页代码视图）
  5. index.html 话题卡片      （主页 Pages 入口；报告数以 manifest 为准自动纠偏）

只追加、不重写，不会覆盖已有手工内容。重复运行安全（已存在的条目自动跳过）。

用法：
  已有话题追加报告:
    python3 scripts/add-report.py --topic typeless --date 2026-06-11 \
        --file 2026-06-11-typeless-v2.html --title "更新版竞品调研"

  新话题首次发布（多 4 个参数）:
    python3 scripts/add-report.py --topic wispr-flow --date 2026-06-11 \
        --file 2026-06-11-wispr-flow.html --title "初版竞品调研" \
        --topic-name "Wispr Flow" --tagline "AI 语音输入 · 竞品调研" \
        --desc "主页话题卡片简介" \
        --conclusion "结论1" --conclusion "结论2"
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_BASE = "https://kdsz001.github.io/ray-research"

TOPIC_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} · 调研话题 · Ray Research</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/sidebar.css">
<script defer src="../assets/sidebar.js"></script>
<script>
(function() {{
  try {{
    var saved = localStorage.getItem('ray-theme');
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if ((saved || (prefersDark ? 'dark' : 'light')) === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }} catch (e) {{}}
}})();
</script>
<style>
:root {{
  --bg: #f6f3ec; --bg-card: #ffffff; --ink: #14110d; --muted: #6e6358; --light: #a39787;
  --rule: #14110d; --rule-light: #d8d1c2; --accent: #a73121; --link: #1c4d6b;
  --serif: "Source Serif 4", Georgia, serif;
  --sans: "Inter", -apple-system, "PingFang SC", sans-serif;
  --mono: "JetBrains Mono", "SF Mono", monospace;
}}
[data-theme="dark"] {{
  --bg: #15120e; --bg-card: #1f1b16; --ink: #ebe3d3; --muted: #8d8170; --light: #5c5346;
  --rule: #ebe3d3; --rule-light: #3a342c; --accent: #e87a5f; --link: #6cb1d6;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: var(--sans); background: var(--bg); color: var(--ink);
  line-height: 1.65; font-size: 16px; max-width: 720px; margin: 0 auto; padding: 80px 32px;
  -webkit-font-smoothing: antialiased; transition: background 0.2s, color 0.2s;
}}
.eyebrow {{
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 18px;
  display: flex; align-items: center; gap: 12px;
}}
.eyebrow::before {{ content: ""; width: 24px; height: 1px; background: var(--accent); }}
.eyebrow a {{ color: var(--accent); text-decoration: none; }}
h1 {{
  font-family: var(--serif); font-weight: 600; font-size: 56px;
  line-height: 1.05; letter-spacing: -0.02em; margin-bottom: 18px;
}}
.lead {{ font-family: var(--serif); font-style: italic; font-size: 19px; color: var(--muted); margin-bottom: 50px; }}
h2 {{
  font-family: var(--serif); font-weight: 600; font-size: 22px;
  margin: 48px 0 18px; letter-spacing: -0.01em;
}}
.report-list {{
  border-top: 1px solid var(--ink); list-style: none;
}}
.report-list li {{
  padding: 20px 0; border-bottom: 1px solid var(--rule-light);
  display: grid; grid-template-columns: 110px 1fr; gap: 20px; align-items: baseline;
}}
.report-list .date {{ font-family: var(--mono); font-size: 11px; color: var(--muted); letter-spacing: 0.05em; }}
.report-list .title {{ font-family: var(--serif); font-size: 19px; font-weight: 600; }}
.report-list a {{ color: var(--ink); text-decoration: none; }}
.report-list a:hover {{ color: var(--accent); }}
ul.findings {{ list-style: none; margin: 0; }}
ul.findings li {{
  padding: 12px 0 12px 22px; position: relative; line-height: 1.55; color: var(--muted);
  border-bottom: 1px dashed var(--rule-light);
}}
ul.findings li::before {{
  content: "→"; position: absolute; left: 0; color: var(--accent); font-family: var(--mono);
}}
ul.findings li:last-child {{ border: none; }}
ul.findings li strong {{ color: var(--ink); }}

#theme-toggle {{
  position: fixed; top: 14px; right: 24px; z-index: 1000;
  width: 36px; height: 36px; border-radius: 50%;
  background: var(--bg-card); border: 1px solid var(--rule-light);
  color: var(--ink); cursor: pointer; display: flex; align-items: center; justify-content: center;
  padding: 0; transition: all 0.15s;
}}
#theme-toggle:hover {{ border-color: var(--ink); }}
#theme-toggle .icon-moon {{ display: none; }}
[data-theme="dark"] #theme-toggle .icon-sun {{ display: none; }}
[data-theme="dark"] #theme-toggle .icon-moon {{ display: block; }}

footer {{
  margin-top: 80px; padding-top: 24px; border-top: 1px solid var(--rule-light);
  font-family: var(--mono); font-size: 11px; color: var(--light); letter-spacing: 0.05em;
}}
footer a {{ color: var(--muted); text-decoration: none; }}
</style>
</head>
<body>

<button id="theme-toggle" aria-label="切换夜间模式">
  <svg class="icon-sun" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="4"/>
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
  </svg>
  <svg class="icon-moon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
</button>

<div class="eyebrow"><a href="../">← 返回 Ray Research</a> · 调研话题</div>
<h1>{name}</h1>
<p class="lead">{tagline}</p>

<h2>报告列表</h2>
<ul class="report-list">
{report_items}
</ul>

<h2>跨报告核心结论</h2>
<ul class="findings">
{finding_items}
</ul>

<footer>
  <a href="../">Ray Research</a> · <a href="https://github.com/kdsz001/ray-research" target="_blank" rel="noopener noreferrer">GitHub</a>
</footer>

<script>
var btn = document.getElementById('theme-toggle');
btn.addEventListener('click', function() {{
  var current = document.documentElement.getAttribute('data-theme');
  var next = current === 'dark' ? 'light' : 'dark';
  if (next === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  else document.documentElement.removeAttribute('data-theme');
  try {{ localStorage.setItem('ray-theme', next); }} catch (e) {{}}
}});
</script>

</body>
</html>
"""

TOPIC_README_TEMPLATE = """# {name} · 调研话题分组

> {tagline}

## 报告列表

| 日期 | 报告 | 在线浏览 |
|------|------|---------|
| {date} | [{title}]({file}) | [↗ 在线打开]({pages_url}) |

## 核心结论

{conclusions}
"""


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def read(path):
    return path.read_text(encoding="utf-8")


def write(path, content):
    path.write_text(content, encoding="utf-8")


def report_li(date, file, title):
    return (f"  <li>\n    <span class=\"date\">{date}</span>\n"
            f"    <a class=\"title\" href=\"{file}\">{title} →</a>\n  </li>")


def update_manifest(args):
    path = ROOT / "manifest.json"
    data = json.loads(read(path))
    topic = next((t for t in data["topics"] if t["slug"] == args.topic), None)
    is_new = topic is None
    if is_new:
        if not (args.topic_name and args.tagline):
            die("新话题必须提供 --topic-name 和 --tagline")
        topic = {"slug": args.topic, "name": args.topic_name,
                 "tagline": args.tagline, "reports": []}
        data["topics"].insert(0, topic)  # 新话题放最前（主页与 sidebar 都是新的在上）
    if any(r["file"] == args.file for r in topic["reports"]):
        print(f"  manifest.json: 报告 {args.file} 已存在，跳过")
    else:
        topic["reports"].append({"date": args.date, "file": args.file, "title": args.title})
        write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f"  manifest.json: {'新建话题 ' + args.topic + ' 并' if is_new else ''}追加报告 ✓")
    return topic, is_new


def update_topic_readme(args, topic):
    path = ROOT / args.topic / "README.md"
    pages_url = f"{PAGES_BASE}/{args.topic}/{args.file}"
    row = f"| {args.date} | [{args.title}]({args.file}) | [↗ 在线打开]({pages_url}) |"
    if not path.exists():
        conclusions = "\n".join(f"- {c}" for c in (args.conclusion or ["（待补充）"]))
        write(path, TOPIC_README_TEMPLATE.format(
            name=topic["name"], tagline=topic["tagline"], date=args.date,
            title=args.title, file=args.file, pages_url=pages_url, conclusions=conclusions))
        print(f"  {args.topic}/README.md: 新建 ✓")
        return
    content = read(path)
    if args.file in content:
        print(f"  {args.topic}/README.md: 已含该报告，跳过")
        return
    lines = content.split("\n")
    last_row = max((i for i, l in enumerate(lines) if l.startswith("|")), default=None)
    if last_row is None:
        die(f"{path} 里找不到报告表格，请手工补一行：\n{row}")
    lines.insert(last_row + 1, row)
    write(path, "\n".join(lines))
    print(f"  {args.topic}/README.md: 追加表格行 ✓")


def update_topic_index(args, topic):
    path = ROOT / args.topic / "index.html"
    li = report_li(args.date, args.file, args.title)
    if not path.exists():
        findings = "\n".join(f"  <li>{c}</li>" for c in (args.conclusion or ["（待补充）"]))
        write(path, TOPIC_INDEX_TEMPLATE.format(
            name=topic["name"], tagline=topic["tagline"],
            report_items=li, finding_items=findings))
        print(f"  {args.topic}/index.html: 新建 ✓")
        return
    content = read(path)
    if f'href="{args.file}"' in content:
        print(f"  {args.topic}/index.html: 已含该报告，跳过")
        return
    anchor = "</ul>"
    start = content.find('<ul class="report-list">')
    if start == -1:
        die(f"{path} 里找不到 <ul class=\"report-list\">，请手工补：\n{li}")
    end = content.find(anchor, start)
    content = content[:end] + li + "\n" + content[end:]
    write(path, content)
    print(f"  {args.topic}/index.html: 追加报告条目 ✓")


def update_main_readme(args, topic):
    path = ROOT / "README.md"
    content = read(path)
    pages_url = f"{PAGES_BASE}/{args.topic}/{args.file}"
    row = f"| {args.date} | [{args.title}]({args.topic}/{args.file}) | [↗ Open]({pages_url}) |"
    if f"({args.topic}/{args.file})" in content:
        print("  README.md: 已含该报告，跳过")
        return
    marker = f"]({args.topic}/)"
    lines = content.split("\n")
    heading_idx = next((i for i, l in enumerate(lines)
                        if l.startswith("###") and marker in l), None)
    if heading_idx is not None:
        # 该话题 section 内最后一个表格行之后插入
        last_row = None
        for i in range(heading_idx + 1, len(lines)):
            if lines[i].startswith("###") or "INDEX-END" in lines[i]:
                break
            if lines[i].startswith("|"):
                last_row = i
        if last_row is None:
            die(f"README.md 话题 {args.topic} 的 section 里没找到表格，请手工补：\n{row}")
        lines.insert(last_row + 1, row)
        write(path, "\n".join(lines))
        print("  README.md: 话题表格追加行 ✓")
        return
    start_idx = next((i for i, l in enumerate(lines) if "INDEX-START" in l), None)
    if start_idx is None:
        die("README.md 里找不到 <!-- INDEX-START --> 标记")
    section = [
        "",
        f"### 🎯 [{topic['name']}]({args.topic}/) · {topic['tagline']}",
        "",
        "| 日期 | 报告 | 在线浏览 |",
        "|------|------|---------|",
        row,
    ]
    lines[start_idx + 1:start_idx + 1] = section
    write(path, "\n".join(lines))
    print("  README.md: 新建话题 section ✓")


def update_main_index(args, topic):
    path = ROOT / "index.html"
    content = read(path)
    link_line = (f'          <a href="{args.topic}/{args.file}">'
                 f"{args.date} {args.title}</a>")
    card_anchor = f'<h3><a href="{args.topic}/">'
    n_reports = len(topic["reports"])
    if card_anchor in content:
        card_start = content.find(card_anchor)
        reports_start = content.find('<div class="topic-reports">', card_start)
        if reports_start == -1:
            die(f"index.html 话题 {args.topic} 卡片里找不到 topic-reports，请手工补")
        reports_end = content.find("</div>", reports_start)
        block = content[reports_start:reports_end]
        if f'href="{args.topic}/{args.file}"' not in block:
            content = content[:reports_end] + link_line + "\n        " + content[reports_end:]
            reports_end += len(link_line) + 9
        # 报告数以 manifest 为准纠偏
        num_start = content.find('<span class="num">', reports_end)
        if num_start != -1:
            num_end = content.find("</span>", num_start)
            content = (content[:num_start] + f'<span class="num">{n_reports}'
                       + content[num_end:])
        write(path, content)
        print(f"  index.html: 话题卡片更新（报告数 → {n_reports}）✓")
        return
    desc = args.desc or topic["tagline"]
    card = f"""    <div class="topic">
      <div>
        <div class="topic-meta">{topic['tagline']}</div>
        <h3><a href="{args.topic}/">{topic['name']}</a></h3>
        <p class="topic-desc">
          {desc}
        </p>
        <div class="topic-reports">
{link_line}
        </div>
      </div>
      <div class="topic-stats">
        <span class="num">{n_reports}</span>
        份报告
      </div>
    </div>
"""
    anchor = '<div class="topic-list">'
    pos = content.find(anchor)
    if pos == -1:
        die("index.html 里找不到 <div class=\"topic-list\">")
    insert_at = content.find("\n", pos) + 1
    content = content[:insert_at] + card + content[insert_at:]
    write(path, content)
    print("  index.html: 新建话题卡片 ✓")


def main():
    p = argparse.ArgumentParser(description="发布报告时一条命令更新全部索引")
    p.add_argument("--topic", required=True, help="话题 slug（小写短横线，如 wispr-flow）")
    p.add_argument("--date", required=True, help="报告日期 YYYY-MM-DD")
    p.add_argument("--file", required=True, help="报告文件名（须已放在话题目录下）")
    p.add_argument("--title", required=True, help="报告标题")
    p.add_argument("--topic-name", help="话题显示名（新话题必填，如 Wispr Flow）")
    p.add_argument("--tagline", help="话题一句话定位（新话题必填）")
    p.add_argument("--desc", help="主页话题卡片简介（新话题建议提供，缺省用 tagline）")
    p.add_argument("--conclusion", action="append", help="核心结论（可重复传多条，新话题用）")
    args = p.parse_args()

    report_path = ROOT / args.topic / args.file
    if not report_path.exists():
        die(f"报告文件不存在：{report_path}\n先把 HTML 复制到话题目录再运行本脚本")

    print(f"更新索引：{args.topic} / {args.file}")
    topic, _ = update_manifest(args)
    update_topic_readme(args, topic)
    update_topic_index(args, topic)
    update_main_readme(args, topic)
    update_main_index(args, topic)
    print("✅ 全部索引已更新（manifest / 话题 README / 话题 index / 主 README / 主 index）")


if __name__ == "__main__":
    main()
