import { test, expect } from '@playwright/test'

const safeProfile = process.env.VITE_RESTRICTED_MAPS === '0'
const RAW_SOURCE_URL = /(?:raw[-_]?source|source[-_]?content|anchor[-_]?content|\/sources\/[^/]+\/anchors\/[^/]+\/content)/i

test.describe('安全分发 profile', () => {
  test.skip(!safeProfile, '仅在 VITE_RESTRICTED_MAPS=0 时运行')

  test('不暴露 CHGIS/谭图入口，也不请求自托管图集瓦片', async ({ page }) => {
    const requests = []
    page.on('request', (request) => requests.push(request.url()))
    await page.addInitScript(() => localStorage.setItem('history-kb-basemap', '古'))
    await page.route('**/api/territories?**', async (route) => {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'FeatureCollection',
          layers: { chgis_admin_records: 0, polity_territories: 0 },
          features: [],
        }),
      })
    })

    await page.goto('/#year=-300&basemap=古')
    await expect(page.locator('.mast')).toBeVisible()
    await expect.poll(() => page.evaluate(() => Boolean(window.__hkbMap))).toBe(true)
    await expect(page.getByRole('button', { name: /谭其骧历史地图/ })).toHaveCount(0)
    await expect(page.locator('.map-atlas-switch')).toHaveCount(0)
    await expect(page.locator('.map-overlay')).not.toContainText('CHGIS')
    await expect.poll(() => page.evaluate(() => localStorage.getItem('history-kb-basemap'))).toBe('素')
    await expect.poll(() => new URL(page.url()).hash).not.toContain('basemap=')

    await page.getByRole('button', { name: '打开资料来源与致谢' }).click()
    const dialog = page.getByRole('dialog', { name: '资料来源与致谢' })
    await expect(dialog).toContainText('本公开分发版不包含 CHGIS 几何')
    await expect(dialog).toContainText('不附带或请求这些配准瓦片')
    await dialog.getByRole('button', { name: '关闭' }).click()

    await page.goto('/#route=explore&scene=scene-focus')
    await expect(page.getByTestId('exploration-workspace')).toBeVisible()
    await page.getByRole('button', { name: /打开《安史之乱：历史、宣传与神话》公开演示/ }).click()
    await expect(page.getByTestId('explore-map-panel')).toBeVisible()
    await expect(page.locator('.explore-reference-caption')).toHaveCount(0)
    await expect(page.locator('.explore-bar')).toContainText('公开演示 · 原文受限')
    await expect(page.locator('.explore-bar')).toContainText('公开原创衍生摘要')

    await page.waitForTimeout(500)
    expect(requests.some((url) => url.includes('/tiles/atlas/'))).toBe(false)
    expect(requests.some((url) => RAW_SOURCE_URL.test(url))).toBe(false)
  })
})
