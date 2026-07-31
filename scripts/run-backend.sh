#!/usr/bin/env bash
# 统一后端启动器：只使用仓库内环境，或按 requirements.txt 创建 uv 隔离环境。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
REQ_FILE="$BACKEND_DIR/requirements.txt"

export DATA_DIR="${DATA_DIR:-$REPO_ROOT/data}"
export SCHEMA_DIR="${SCHEMA_DIR:-$REPO_ROOT/schema}"

run_with_python() {
  local python_bin="$1"
  shift
  if ! "$python_bin" -c 'import uvicorn' >/dev/null 2>&1; then
    echo "[backend] 环境缺少 uvicorn: $python_bin" >&2
    return 1
  fi
  cd "$BACKEND_DIR"
  exec "$python_bin" -m uvicorn app.main:app "$@"
}

if [ -n "${VENV_PATH:-}" ]; then
  if [ ! -x "$VENV_PATH/bin/python" ]; then
    echo "[backend] VENV_PATH 无可执行 Python: $VENV_PATH/bin/python" >&2
    exit 1
  fi
  run_with_python "$VENV_PATH/bin/python" "$@"
fi

for candidate in "$BACKEND_DIR/.venv/bin/python" "$REPO_ROOT/.venv/bin/python"; do
  if [ -x "$candidate" ] && "$candidate" -c 'import uvicorn' >/dev/null 2>&1; then
    run_with_python "$candidate" "$@"
  fi
done

if command -v uv >/dev/null 2>&1; then
  cd "$BACKEND_DIR"
  exec uv run --with-requirements "$REQ_FILE" python -m uvicorn app.main:app "$@"
fi

echo "[backend] 未找到可用的仓库虚拟环境或 uv。请先执行：" >&2
echo "  cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
exit 1
