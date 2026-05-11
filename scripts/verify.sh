#!/usr/bin/env bash
# verify.sh — 检查 manifest.json 与文件系统一致性
# 用法：bash scripts/verify.sh
# 退出码：0 = OK，1 = 有不一致

set -u
cd "$(dirname "$0")/.."

ERRORS=0

# 1. manifest.json 是合法 JSON
if ! python3 -c "import json; json.load(open('manifest.json'))" 2>/dev/null; then
  echo "❌ manifest.json 不是合法 JSON"
  ERRORS=$((ERRORS+1))
fi

# 2. 每个 manifest 中的 report 文件实际存在
MISSING_FILES=$(python3 <<'PY'
import json, os
m = json.load(open('manifest.json'))
missing = []
for t in m.get('topics', []):
    slug = t.get('slug')
    for r in t.get('reports', []):
        f = r.get('file')
        if not f or not slug:
            continue
        path = os.path.join(slug, f)
        if not os.path.isfile(path):
            missing.append(path)
print('\n'.join(missing))
PY
)
if [ -n "$MISSING_FILES" ]; then
  echo "❌ manifest 中列出但磁盘上找不到："
  echo "$MISSING_FILES" | sed 's/^/    /'
  ERRORS=$((ERRORS+1))
fi

# 3. 磁盘上的 report HTML 都在 manifest 中
ORPHAN_FILES=$(python3 <<'PY'
import json, os
m = json.load(open('manifest.json'))
in_manifest = set()
for t in m.get('topics', []):
    slug = t.get('slug')
    for r in t.get('reports', []):
        if r.get('file') and slug:
            in_manifest.add(os.path.join(slug, r['file']))

# 扫描所有话题目录下的 *.html，排除 index.html
on_disk = set()
for d in os.listdir('.'):
    if not os.path.isdir(d) or d.startswith('.') or d in ('assets', 'scripts', 'node_modules'):
        continue
    for f in os.listdir(d):
        if f.endswith('.html') and f != 'index.html':
            on_disk.add(os.path.join(d, f))

orphans = on_disk - in_manifest
print('\n'.join(sorted(orphans)))
PY
)
if [ -n "$ORPHAN_FILES" ]; then
  echo "❌ 磁盘上存在但 manifest 没列出（sidebar 看不到）："
  echo "$ORPHAN_FILES" | sed 's/^/    /'
  ERRORS=$((ERRORS+1))
fi

# 4. 每个 topic 目录有 index.html
MISSING_INDEX=$(python3 <<'PY'
import json, os
m = json.load(open('manifest.json'))
missing = []
for t in m.get('topics', []):
    slug = t.get('slug')
    if not slug:
        continue
    p = os.path.join(slug, 'index.html')
    if not os.path.isfile(p):
        missing.append(p)
print('\n'.join(missing))
PY
)
if [ -n "$MISSING_INDEX" ]; then
  echo "❌ 话题目录缺 index.html（GitHub Pages 会 404）："
  echo "$MISSING_INDEX" | sed 's/^/    /'
  ERRORS=$((ERRORS+1))
fi

# 5. report HTML 都引入了 sidebar.css + sidebar.js
SIDEBAR_MISSING=$(python3 <<'PY'
import json, os
m = json.load(open('manifest.json'))
missing = []
for t in m.get('topics', []):
    slug = t.get('slug')
    for r in t.get('reports', []):
        f = r.get('file')
        if not f or not slug:
            continue
        path = os.path.join(slug, f)
        if not os.path.isfile(path):
            continue
        try:
            content = open(path, encoding='utf-8').read()
            if 'assets/sidebar.css' not in content or 'assets/sidebar.js' not in content:
                missing.append(path)
        except:
            pass
print('\n'.join(missing))
PY
)
if [ -n "$SIDEBAR_MISSING" ]; then
  echo "⚠️  报告 HTML 没引入 sidebar 资源（不会显示全局导航）："
  echo "$SIDEBAR_MISSING" | sed 's/^/    /'
  ERRORS=$((ERRORS+1))
fi

if [ $ERRORS -eq 0 ]; then
  echo "✅ 仓库一致性检查通过"
fi
exit $ERRORS
