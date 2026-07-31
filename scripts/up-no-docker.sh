#!/usr/bin/env bash
# 已由 scripts/dev.sh 取代（保留本文件以兼容旧习惯）。
# 转发所有参数给 dev.sh。
echo "[up-no-docker] 已由 scripts/dev.sh 取代，正在转发…" >&2
exec "$(dirname "$0")/dev.sh" "$@"
