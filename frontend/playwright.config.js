import { defineConfig } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONTEND_DIR = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(FRONTEND_DIR, '..')

// E2E 使用隔离端口冷启动，不复用任何陈旧进程；Playwright 结束时回收整个进程组。
export default defineConfig({
  testDir: './e2e',
  // 单个共享 dev server：串行跑，避免两个 spec 抢同一份后端状态
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['line']],

  webServer: [
    {
      name: 'backend',
      command: 'scripts/run-backend.sh --host 127.0.0.1 --port 8002 --log-level warning --no-access-log',
      cwd: REPO_ROOT,
      env: {
        ...process.env,
        PRIVATE_EXPLORATIONS_ENABLED: process.env.PRIVATE_EXPLORATIONS_ENABLED ?? '1',
      },
      url: 'http://127.0.0.1:8002/api/meta/stats',
      timeout: 120_000,
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3_000 },
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      name: 'frontend',
      command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
      cwd: FRONTEND_DIR,
      env: {
        ...process.env,
        VITE_DEV_PROXY_TARGET: 'http://127.0.0.1:8002',
        VITE_BACKEND_AUTOSTART: '0',
        VITE_PRIVATE_EXPLORATIONS: process.env.VITE_PRIVATE_EXPLORATIONS ?? '1',
      },
      url: 'http://127.0.0.1:5174',
      timeout: 120_000,
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 3_000 },
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],

  use: {
    baseURL: 'http://127.0.0.1:5174',
    // EntityDetail 默认展开最多占画布 50%：高度需 ≥900 才能保证 .graph-canvas ≥300px
    viewport: { width: 1440, height: 900 },
    actionTimeout: 15_000,
    trace: 'retain-on-failure',
  },

  projects: [
    // 用系统 Chrome(本机已装, 实测可用), 不下载 chromium 二进制
    { name: 'chrome', use: { channel: 'chrome' } },
  ],
})
