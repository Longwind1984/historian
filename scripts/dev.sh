#!/usr/bin/env bash
# scripts/dev.sh — 一键启动本地开发环境
#
# 同时拉起后端、探索 worker 与前端，Ctrl-C 一次全停。
# 端口被占时打印占用进程并退出码 1；不自动安装依赖。
#
# 用法:
#   scripts/dev.sh                 # 前后端都起
#   scripts/dev.sh --backend-only  # 起后端与探索 worker
#   scripts/dev.sh --frontend-only # 只起前端
#
# 环境变量:
#   VENV_PATH   后端虚拟环境路径 (可选；默认依次探测 backend/.venv、根 .venv、uv)
#   DATA_DIR    后端数据目录      (默认 <repo>/data)
#   SCHEMA_DIR  后端 schema 目录  (默认 <repo>/schema)
#   PRIVATE_EXPLORATIONS_ENABLED / VITE_PRIVATE_EXPLORATIONS
#               私人 Prompt / 上传开关（本地默认 1）
set -euo pipefail

MODE="both"
for arg in "$@"; do
  case "$arg" in
    --backend-only)  MODE="be" ;;
    --frontend-only) MODE="fe" ;;
    -h|--help)
      cat <<'EOF'
用法: scripts/dev.sh [选项]
  (无参数)          同时启动后端(:8000)与前端(:5173)
  --backend-only    启动后端与探索 worker
  --frontend-only   仅启动前端
环境变量: VENV_PATH / DATA_DIR / SCHEMA_DIR
          PRIVATE_EXPLORATIONS_ENABLED / VITE_PRIVATE_EXPLORATIONS（默认 1）
Ctrl-C 停止全部服务。
EOF
      exit 0 ;;
    *) echo "[dev] 未知参数: $arg (用 --help 查看)" >&2; exit 2 ;;
  esac
done

# 仓库根：用 git 定位，不写死绝对路径
REPO_ROOT="$(git rev-parse --show-toplevel)"

# 公开构建默认 demo-only；开发入口显式打开私人会话能力，避免依赖隐含环境判断。
export PRIVATE_EXPLORATIONS_ENABLED="${PRIVATE_EXPLORATIONS_ENABLED:-1}"
export VITE_PRIVATE_EXPLORATIONS="${VITE_PRIVATE_EXPLORATIONS:-1}"

# 运行期状态
WORK=""
BE_PID=""; WORKER_PID=""; FE_PID=""
BE_LOG_PID=""; WORKER_LOG_PID=""; FE_LOG_PID=""
CLEANED_UP=0

cleanup() {
  [ "$CLEANED_UP" = "1" ] && return 0
  CLEANED_UP=1
  if [ -n "$BE_PID$WORKER_PID$FE_PID" ]; then
    echo "[dev] 正在停止服务..." >&2
  fi
  for pid in "$BE_PID" "$WORKER_PID" "$FE_PID" "$BE_LOG_PID" "$WORKER_LOG_PID" "$FE_LOG_PID"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
  sleep 0.3 2>/dev/null || true
  for pid in "$BE_PID" "$WORKER_PID" "$FE_PID"; do
    [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null || true
  done
  [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true
}
trap 'cleanup; exit 130' INT TERM
trap 'cleanup' EXIT

# 端口占用检查：被占时打印占用进程并返回非 0
check_ports() {
  if ! command -v lsof >/dev/null 2>&1; then
    echo "[dev] ⚠ 未找到 lsof，跳过端口占用检查" >&2
    return 0
  fi
  local occupied=0 port
  for port in "$@"; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
      echo "[dev] ✗ 端口 $port 已被占用，占用进程如下：" >&2
      lsof -nP -iTCP:"$port" -sTCP:LISTEN >&2 2>/dev/null || true
      echo >&2
      occupied=1
    fi
  done
  return $occupied
}

# 按模式决定要检查/启动的端口
PORTS=()
if [ "$MODE" = "be" ] || [ "$MODE" = "both" ]; then PORTS+=(8000); fi
if [ "$MODE" = "fe" ] || [ "$MODE" = "both" ]; then PORTS+=(5173); fi

check_ports "${PORTS[@]}" || { echo "[dev] 请先释放上述端口再重试。" >&2; exit 1; }

# 前端依赖检查（缺失则提示 npm ci，不自动安装）
if [ "$MODE" != "be" ]; then
  if [ ! -d "$REPO_ROOT/frontend/node_modules" ]; then
    echo "[dev] ✗ frontend/node_modules 缺失，请先在 frontend/ 下运行:  npm ci" >&2
    exit 1
  fi
fi

# 后端环境由 run-backend.sh 统一选择；这里只设置服务配置。
if [ "$MODE" != "fe" ]; then
  export DATA_DIR="${DATA_DIR:-$REPO_ROOT/data}"
  export SCHEMA_DIR="${SCHEMA_DIR:-$REPO_ROOT/schema}"
  export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080}"
fi

# 日志前缀用的 FIFO（拿到服务真实 PID，便于清理）
WORK="$(mktemp -d)"
make_fifo() { command mkfifo -m 600 "$1" 2>/dev/null || command mkfifo "$1"; }

prefix() { awk -v t="$1" '{ print t" "$0; fflush() }'; }

echo "[dev] 启动中 (mode=$MODE)..."
if [ "$MODE" != "fe" ]; then
  BE_FIFO="$WORK/be.fifo"; make_fifo "$BE_FIFO"
  ( exec "$REPO_ROOT/scripts/run-backend.sh" --host 127.0.0.1 --port 8000 --reload ) >"$BE_FIFO" 2>&1 &
  BE_PID=$!
  prefix "[be]" <"$BE_FIFO" &
  BE_LOG_PID=$!
  echo "[dev] 后端: http://localhost:8000/docs  (pid $BE_PID)"
  WORKER_FIFO="$WORK/worker.fifo"; make_fifo "$WORKER_FIFO"
  ( exec "$REPO_ROOT/scripts/run-exploration-worker.sh" ) >"$WORKER_FIFO" 2>&1 &
  WORKER_PID=$!
  prefix "[worker]" <"$WORKER_FIFO" &
  WORKER_LOG_PID=$!
  echo "[dev] 探索 worker: 已启动             (pid $WORKER_PID)"
fi
if [ "$MODE" != "be" ]; then
  FE_FIFO="$WORK/fe.fifo"; make_fifo "$FE_FIFO"
  ( cd "$REPO_ROOT/frontend" && exec npm run dev ) >"$FE_FIFO" 2>&1 &
  FE_PID=$!
  prefix "[fe]" <"$FE_FIFO" &
  FE_LOG_PID=$!
  echo "[dev] 前端: http://localhost:5173       (pid $FE_PID)"
fi
echo "[dev] Ctrl-C 停止全部"

wait
