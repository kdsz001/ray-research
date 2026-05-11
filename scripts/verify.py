#!/usr/bin/env python3
"""verify.py — 检查 manifest.json 与文件系统一致性。

用法：python3 scripts/verify.py
退出码：0 = OK，1 = 有不一致
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "manifest.json"

# 不参与扫描的顶层目录
IGNORED_DIRS = {".git", "assets", "scripts", "node_modules"}


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"manifest.json 不存在：{MANIFEST_PATH}")
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def manifest_files(manifest: dict) -> set[str]:
    """返回 manifest 中声明的 (slug/file) 相对路径集合。"""
    out: set[str] = set()
    for t in manifest.get("topics", []):
        slug = t.get("slug")
        if not isinstance(slug, str):
            continue
        for r in t.get("reports", []):
            f = r.get("file")
            if isinstance(f, str):
                out.add(f"{slug}/{f}")
    return out


def disk_report_files() -> set[str]:
    """扫描磁盘上所有话题目录下的 *.html（排除 index.html）。"""
    out: set[str] = set()
    for entry in REPO_ROOT.iterdir():
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in IGNORED_DIRS:
            continue
        for f in entry.iterdir():
            if f.suffix == ".html" and f.name != "index.html":
                out.add(f"{entry.name}/{f.name}")
    return out


def check_missing_files(manifest: dict) -> list[str]:
    """manifest 中列出但磁盘上找不到。"""
    missing = []
    for rel in sorted(manifest_files(manifest)):
        if not (REPO_ROOT / rel).is_file():
            missing.append(rel)
    return missing


def check_orphan_files(manifest: dict) -> list[str]:
    """磁盘上存在但 manifest 没列出。"""
    return sorted(disk_report_files() - manifest_files(manifest))


def check_missing_topic_index(manifest: dict) -> list[str]:
    """每个话题目录应有 index.html。"""
    missing = []
    for t in manifest.get("topics", []):
        slug = t.get("slug")
        if not isinstance(slug, str):
            continue
        idx = REPO_ROOT / slug / "index.html"
        if not idx.is_file():
            missing.append(f"{slug}/index.html")
    return missing


def check_sidebar_injection(manifest: dict) -> list[str]:
    """每份 report 应引入 sidebar.css + sidebar.js。"""
    missing = []
    for rel in sorted(manifest_files(manifest)):
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            missing.append(f"{rel} (读取失败: {exc})")
            continue
        if "assets/sidebar.css" not in content or "assets/sidebar.js" not in content:
            missing.append(rel)
    return missing


def main() -> int:
    try:
        manifest = load_manifest()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"❌ 无法解析 manifest.json：{exc}", file=sys.stderr)
        return 1

    errors = 0

    missing_files = check_missing_files(manifest)
    if missing_files:
        print("❌ manifest 中列出但磁盘上找不到：")
        for f in missing_files:
            print(f"    {f}")
        errors += 1

    orphan_files = check_orphan_files(manifest)
    if orphan_files:
        print("❌ 磁盘上存在但 manifest 没列出（sidebar 看不到）：")
        for f in orphan_files:
            print(f"    {f}")
        errors += 1

    missing_idx = check_missing_topic_index(manifest)
    if missing_idx:
        print("❌ 话题目录缺 index.html（GitHub Pages 会 404）：")
        for f in missing_idx:
            print(f"    {f}")
        errors += 1

    sidebar_missing = check_sidebar_injection(manifest)
    if sidebar_missing:
        print("⚠️  报告 HTML 没引入 sidebar 资源（不会显示全局导航）：")
        for f in sidebar_missing:
            print(f"    {f}")
        errors += 1

    if errors == 0:
        print("✅ 仓库一致性检查通过")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
