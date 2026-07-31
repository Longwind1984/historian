#!/usr/bin/env bash
# Start the production images via Docker Compose.
set -euo pipefail
cd "$(dirname "$0")/.."

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "✗ 未找到 Docker Compose。请安装 docker compose 插件或 legacy docker-compose。" >&2
  exit 1
fi

[ ! -f .env ] && cp .env.example .env

wait_http() {
  local label="$1" url="$2" timeout_seconds="${3:-60}"
  local deadline=$((SECONDS + timeout_seconds))
  while ((SECONDS < deadline)); do
    if curl --fail --silent --show-error --connect-timeout 2 --max-time 5 "$url" >/dev/null 2>&1; then
      echo "✓ $label ready: $url"
      return 0
    fi
    sleep 1
  done
  echo "✗ $label 未在 ${timeout_seconds}s 内就绪: $url" >&2
  return 1
}

command -v curl >/dev/null 2>&1 || { echo "✗ 需要 curl 做容器 HTTP 探活" >&2; exit 1; }

echo "→ ${compose[*]} up -d --build"
"${compose[@]}" up -d --build
wait_http "backend" "http://127.0.0.1:8000/api/meta/stats"

echo "→ running bounded backend HTTP smoke (failure is fatal)"
# 这两条分别要求容器内 /app/schema 与 /app/data 已正确挂载并被真实服务加载。
# 不调用 tests/test_smoke.py：它按宿主仓库层级推导路径，不适用于 /app 镜像布局。
wait_http "backend schema" "http://127.0.0.1:8000/api/meta/schema" 5
wait_http "backend entities" "http://127.0.0.1:8000/api/entities?limit=1" 5

# 经前端 Nginx 真正走一遍同源 API 与瓦片代理；不是只测容器内 TestClient。
wait_http "frontend API proxy" "http://127.0.0.1:8080/api/meta/stats"
wait_http "frontend tile proxy" "http://127.0.0.1:8080/tiles/atlas/mp0302/2/2/1.png"
echo "✓ up. frontend: http://localhost:8080  api: http://localhost:8000"
