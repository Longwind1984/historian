import { test, expect } from '@playwright/test'

test.describe('移动端时间柱与底部抽屉', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test.beforeEach(async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.getByTestId('mobile-timeline')).toBeVisible()
    await expect(page.locator('.tc-wrap')).toBeVisible()
  })

  test('390px 下顶部与折叠筛选保持单行，时间柱占据主体', async ({ page }) => {
    const mast = page.locator('.mast')
    const filter = page.locator('.fb-bar')
    await expect(mast).toBeVisible()
    await expect(filter).toBeVisible()

    const mastMetrics = await mast.evaluate((el) => ({
      clientWidth: el.clientWidth,
      scrollWidth: el.scrollWidth,
      height: el.getBoundingClientRect().height,
    }))
    const filterMetrics = await filter.evaluate((el) => ({
      clientWidth: el.clientWidth,
      scrollWidth: el.scrollWidth,
      height: el.getBoundingClientRect().height,
    }))
    expect(mastMetrics.height).toBeLessThanOrEqual(54)
    expect(mastMetrics.scrollWidth).toBeLessThanOrEqual(mastMetrics.clientWidth + 1)
    expect(filterMetrics.height).toBeLessThanOrEqual(48)
    expect(filterMetrics.scrollWidth).toBeLessThanOrEqual(filterMetrics.clientWidth + 1)
    await expect(page.locator('.fb-focus', { hasText: '重点人物' })).toBeVisible()
    await expect(page.locator('.fb-role-toggle')).toBeVisible()
    await expect(page.locator('#person-role-filters')).toHaveCount(0)

    const columnBox = await page.locator('.tc-wrap').boundingBox()
    expect(columnBox.width).toBeGreaterThanOrEqual(389)
    expect(columnBox.height).toBeGreaterThan(600)
  })

  test('折叠首载不请求地图，首次展开后复用同一地图实例', async ({ page }) => {
    const loadedMapResources = () => page.evaluate(() => {
      const targets = [
        '/src/components/map/MapPanel.vue',
        '/node_modules/.vite/deps/maplibre-gl.js',
      ]
      return performance.getEntriesByType('resource')
        .map((entry) => new URL(entry.name, location.href).pathname)
        .filter((pathname) => targets.some((target) => pathname.endsWith(target)))
    })

    const drawer = page.getByTestId('mobile-moment-drawer')
    const content = page.locator('#mobile-moment-content')
    const handle = page.getByRole('button', { name: '展开此刻详情' })
    await expect(handle).toHaveAttribute('aria-expanded', 'false')
    await expect(handle).toHaveAttribute('aria-controls', 'mobile-moment-content')
    await expect(content).toHaveCount(1)
    await expect(content.locator('.mp-wrap')).toHaveCount(1)
    await expect(content.locator('.mp-moment')).toBeVisible()
    await expect(content.locator('.map-panel')).toHaveCount(0)
    // TimeColumn 已在 beforeEach 就绪；再留一个稳定窗，避免把尚未发出的懒加载误判为空集。
    await page.waitForTimeout(300)
    expect(await loadedMapResources()).toEqual([])

    await handle.click()
    await expect(page.locator('.maplibregl-map')).toBeVisible({ timeout: 20_000 })
    const afterFirstOpen = await loadedMapResources()
    expect(afterFirstOpen.length).toBeGreaterThan(0)
    for (const target of ['MapPanel.vue', 'maplibre-gl.js']) {
      expect(afterFirstOpen.some((pathname) => pathname.endsWith(target))).toBe(true)
    }
    await expect(page.locator('.maplibregl-map')).toHaveCount(1)

    await page.getByRole('button', { name: '收起此刻详情' }).click()
    await expect(page.getByRole('button', { name: '展开此刻详情' })).toHaveAttribute('aria-expanded', 'false')
    await expect(content.locator('.mp-wrap')).toHaveCount(1)
    await page.getByRole('button', { name: '展开此刻详情' }).click()
    await expect(page.locator('.maplibregl-map')).toBeVisible()
    await expect(page.locator('.maplibregl-map')).toHaveCount(1)
    expect(await loadedMapResources()).toEqual(afterFirstOpen)
    await expect(drawer).toBeVisible()
  })

  test('把手键盘可首次展开、收起真实 MomentPanel 和 MapPanel', async ({ page }) => {
    const drawer = page.getByTestId('mobile-moment-drawer')
    const handle = page.getByRole('button', { name: '展开此刻详情' })
    await expect(handle).toHaveAttribute('aria-expanded', 'false')

    const collapsedY = (await drawer.boundingBox()).y
    await handle.focus()
    await handle.press('Home')
    await expect(page.getByRole('button', { name: '收起此刻详情' })).toHaveAttribute('aria-expanded', 'true')
    await expect.poll(async () => (await drawer.boundingBox()).y).toBeLessThan(collapsedY - 200)
    await expect(page.locator('.mp-wrap')).toBeVisible()
    await expect(page.locator('.map-panel')).toBeVisible()
    await expect(page.locator('.mp-dossier')).toHaveCount(0)

    const openBox = await drawer.boundingBox()
    expect(openBox.y).toBeGreaterThan(480)

    const expandedHandle = page.getByRole('button', { name: '收起此刻详情' })
    await expandedHandle.focus()
    await expandedHandle.press('ArrowDown')
    await expect(page.getByRole('button', { name: '展开此刻详情' })).toHaveAttribute('aria-expanded', 'false')
    await page.getByRole('button', { name: '展开此刻详情' }).press('ArrowUp')
    await expect(page.getByRole('button', { name: '收起此刻详情' })).toHaveAttribute('aria-expanded', 'true')
  })

  test('把手纵向拖拽可展开并收起抽屉', async ({ page }) => {
    const drawer = page.getByTestId('mobile-moment-drawer')
    const handle = page.getByRole('button', { name: '展开此刻详情' })
    const box = await handle.boundingBox()
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width / 2, box.y - 360, { steps: 8 })
    await page.mouse.up()
    await expect(page.getByRole('button', { name: '收起此刻详情' })).toHaveAttribute('aria-expanded', 'true')
    await expect(page.locator('.maplibregl-map')).toBeVisible({ timeout: 20_000 })

    const expandedBox = await page.getByRole('button', { name: '收起此刻详情' }).boundingBox()
    await page.mouse.move(expandedBox.x + expandedBox.width / 2, expandedBox.y + expandedBox.height / 2)
    await page.mouse.down()
    await page.mouse.move(expandedBox.x + expandedBox.width / 2, expandedBox.y + 420, { steps: 8 })
    await page.mouse.up()
    await expect(page.getByRole('button', { name: '展开此刻详情' })).toHaveAttribute('aria-expanded', 'false')
    await expect(drawer).toBeVisible()
  })
})
