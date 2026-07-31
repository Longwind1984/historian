import { test, expect } from '@playwright/test'

const demoOnly = process.env.VITE_PRIVATE_EXPLORATIONS === '0'

test.describe('公网 demo-only 安全门', () => {
  test.skip(!demoOnly, '仅在 VITE_PRIVATE_EXPLORATIONS=0 时运行')

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
  })

  test('探索入口自动进入公开 Demo，且前后端都不暴露私人入口', async ({ page }) => {
    await page.goto('/#route=explore')

    await expect(page.getByTestId('exploration-workspace')).toBeVisible()
    await expect(page.getByTestId('exploration-entry')).toHaveCount(0)
    await expect(page.locator('.explore-bar')).toContainText('公开演示 · 原文受限')
    await expect(page.getByRole('button', { name: '返回' })).toHaveCount(0)
    await expect(page.locator('.entry-label')).toHaveText('公开演示')

    const shareState = await page.evaluate(() => Object.fromEntries(
      new URLSearchParams(window.location.hash.slice(1)),
    ))
    expect(shareState).toMatchObject({ route: 'explore', demo: 'anshi' })

    await expect(page.getByTestId('exploration-entry')).toHaveCount(0)
    await expect(page.getByText('你想理解哪段历史？')).toHaveCount(0)
    await expect(page.getByRole('button', { name: '上传本地书籍' })).toHaveCount(0)

    const promptResponse = await page.request.post('/api/explorations/from-prompt', {
      data: { prompt: '这条请求在公网 demo-only 环境必须被拒绝' },
    })
    expect(promptResponse.status()).toBe(404)
  })
})
