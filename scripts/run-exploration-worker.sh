#!/usr/bin/env bash
# 统一探索 worker 启动器：与后端使用同一仓库环境和依赖锁定。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
REQ_FILE="$BACKEND_DIR/requirements.txt"

export DATA_DIR="${DATA_DIR:-$REPO_ROOT/data}"
export SCHEMA_DIR="${SCHEMA_DIR:-$REPO_ROOT/schema}"

run_with_python() {
  local python_bin="$1"
  shift
  if ! "$python_bin" -c 'import fastapi, langgraph' >/dev/null 2>&1; then
    echo "[exploration-worker] 环境缺少后端依赖: $python_bin" >&2
    return 1
  fi
  cd "$BACKEND_DIR"
  exec "$python_bin" -m app.exploration.worker "$@"
}

if [ -n "${VENV_PATH:-}" ]; then
  if [ ! -x "$VENV_PATH/bin/python" ]; then
    echo "[exploration-worker] VENV_PATH 无可执行 Python: $VENV_PATH/bin/python" >&2
    exit 1
  fi
  run_with_python "$VENV_PATH/bin/python" "$@"
fi

for candidate in "$BACKEND_DIR/.venv/bin/python" "$REPO_ROOT/.venv/bin/python"; do
  if [ -x "$candidate" ] && "$candidate" -c 'import fastapi, langgraph' >/dev/null 2>&1; then
    run_with_python "$candidate" "$@"
  fi
done

if command -v uv >/dev/null 2>&1; then
  cd "$BACKEND_DIR"
  exec uv run --with-requirements "$REQ_FILE" python -m app.exploration.worker "$@"
fi

echo "[exploration-worker] 未找到可用的仓库虚拟环境或 uv。" >&2
exit 1
