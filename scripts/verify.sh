#!/usr/bin/env bash
# verify.sh — bash 包装器，调用 verify.py
# 用法：bash scripts/verify.sh
# 退出码：透传 verify.py（0 = OK，1 = 有不一致，其它 = 脚本本身出错）

set -euo pipefail
exec python3 "$(dirname "$0")/verify.py" "$@"
