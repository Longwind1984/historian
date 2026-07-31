import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { execFileSync, spawn } from 'node:child_process'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const PACKAGE_VERSION = JSON.parse(readFileSync(path.join(REPO_ROOT, 'package.json'), 'utf8')).version
const RELEASE = Object.freeze({
  version: process.env.HISTORY_KB_VERSION || PACKAGE_VERSION,
  revision: process.env.HISTORY_KB_GIT_SHA || execFileSync(
    'git', ['rev-parse', '--short=8', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' },
  ).trim(),
  built_at: process.env.HISTORY_KB_BUILD_TIME || new Date().toISOString(),
})
// 与下方 proxy target 保持同一来源：e2e 手起 :8002 后端时经 env 指过去，默认 :8000。
const BACKEND = process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000'
const DISTRIBUTION_PROFILE = process.env.VITE_RESTRICTED_MAPS === '0' ? 'safe' : 'full'
const PRIVATE_EXPLORATIONS_ENABLED = process.env.VITE_PRIVATE_EXPLORATIONS === '1'

function distributionProfileMarker() {
  return {
    name: 'distribution-profile-marker',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'distribution-profile.json',
        source: `${JSON.stringify({
          distribution_profile: DISTRIBUTION_PROFILE,
          private_explorations_enabled: PRIVATE_EXPLORATIONS_ENABLED,
        })}\n`,
      })
    },
  }
}

function releaseMetadata() {
  return {
    name: 'release-metadata',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'release.json',
        source: `${JSON.stringify(RELEASE)}\n`,
      })
    },
  }
}

// preview / 本地开发一体化：`npm run dev` 不再要求先手动起后端 ——
// 探测 proxy 目标的 /api/meta/stats，不可达才自动拉起 FastAPI（可达则复用，e2e 场景）。
// 后端是 vite 的子进程：dev server 停（含 Kimi Work preview 生命周期回收）即随之退出，不残留。
function backendAutostart() {
  let child = null
  let announced = false
  const health = async (timeoutMs = 3000) => {
    try {
      const r = await fetch(`${BACKEND}/api/meta/stats`, { signal: AbortSignal.timeout(timeoutMs) })
      return r.ok
    } catch { return false }
  }
  const kill = () => { const c = child; child = null; try { c?.kill('SIGTERM') } catch {} }
  return {
    name: 'backend-autostart',
    async configureServer(server) {
      // Playwright 自己管理隔离后端；禁用时不探测也不拉起，避免两个 webServer
      // 并行启动期间 Vite 误判 :8002 未就绪后再 spawn 一个同端口进程。
      if (process.env.VITE_BACKEND_AUTOSTART === '0') {
        console.log('[backend-autostart] 已由 VITE_BACKEND_AUTOSTART=0 禁用')
        return
      }
      // 覆盖初次探测、拉起与后续重试的总墙钟上限；到点让 Vite 继续启动，
      // 前端断连页仍可工作。避免 90 × (1s sleep + 3s fetch) 最坏阻塞约 6 分钟。
      const readyDeadline = Date.now() + 45_000
      const healthBeforeDeadline = () => {
        const remaining = readyDeadline - Date.now()
        return remaining > 0 ? health(Math.min(3000, remaining)) : Promise.resolve(false)
      }
      if (await healthBeforeDeadline()) {
        console.log(`[backend-autostart] 复用已运行的后端 ${BACKEND}`)
        return
      }
      const port = new URL(BACKEND).port || '8000'
      const env = {
        ...process.env,
        // handoff 铁律：必须显式给 DATA_DIR/SCHEMA_DIR，否则默认 /app/data 静默加载 0 实体
        DATA_DIR: path.join(REPO_ROOT, 'data'),
        SCHEMA_DIR: path.join(REPO_ROOT, 'schema'),
      }
      const backendArgs = ['--host', '127.0.0.1', '--port', port]
      // 与 scripts/dev.sh / dev-backend.sh 共用同一启动器：backend/.venv → 根 .venv
      // → requirements.txt 约束的 uv 隔离环境。绝不借父项目环境或解析浮动依赖。
      // stdio: 'ignore' —— uvicorn 每请求一行日志，管道不消费会撑满缓冲把后端卡死
      child = spawn(path.join(REPO_ROOT, 'scripts/run-backend.sh'), backendArgs,
        { cwd: REPO_ROOT, env, stdio: 'ignore' })
      child.on('error', (e) => console.error(`[backend-autostart] 拉起失败: ${e.message}（请手动起后端）`))
      child.on('exit', (code) => { if (!announced && code) console.error(`[backend-autostart] 后端异常退出 code=${code}，端口 ${port} 是否被占？`) })
      // 后台等健康，就绪后给一句准话；首屏若先到可点「重试」（D5 已给断连页配重试钮）
      while (Date.now() < readyDeadline) {
        const sleepMs = Math.min(1000, readyDeadline - Date.now())
        if (sleepMs > 0) await new Promise((r) => setTimeout(r, sleepMs))
        if (await healthBeforeDeadline()) {
          announced = true
          console.log(`[backend-autostart] 后端就绪 ${BACKEND}（数据已加载）`)
          break
        }
      }
      if (!announced) {
        console.error(`[backend-autostart] 后端 45s 内未就绪 ${BACKEND}；Vite 继续启动，请在断连页重试或手动检查后端`)
      }
      server.httpServer?.on('close', kill)
      for (const sig of ['SIGINT', 'SIGTERM', 'exit']) process.once(sig, kill)
    },
  }
}

export default defineConfig({
  plugins: [vue(), distributionProfileMarker(), releaseMetadata(), backendAutostart()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: BACKEND,
        changeOrigin: true,
      },
      // 谭其骧地图集瓦片，后端自托管（见 backend/app/main.py 的 /tiles/atlas 挂载）。
      // 走同源代理而非直连 tile.osgeo.cn —— 那台服务器给 curl 返 CORS 头、给 maplibre 不返，
      // 详见 MapPanel.vue 的 atlasTileUrl 注释。
      '/tiles': {
        target: BACKEND,
        changeOrigin: true,
      },
    },
  },
  define: {
    __APP_RELEASE__: JSON.stringify(RELEASE),
    'process.env.VITE_API_BASE': JSON.stringify(process.env.VITE_API_BASE || ''),
  },
})
