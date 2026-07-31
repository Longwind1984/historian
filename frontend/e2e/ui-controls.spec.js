import { test, expect } from '@playwright/test'

test.describe('界面控件收敛与默认值', () => {
  test('单一主题按钮跟随系统并可在澄夜间往返切换', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' })
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    const themeToggle = page.locator('.mast-palette')
    await expect(themeToggle).toHaveCount(1)
    await expect(themeToggle).toContainText('夜')
    await expect(themeToggle).toHaveAttribute('aria-label', '当前夜色主题，切换到澄色主题')
    await expect(themeToggle.locator('svg')).toHaveCount(1)

    await themeToggle.click()
    await expect(themeToggle).toContainText('澄')
    await expect(themeToggle).toHaveAttribute('aria-label', '当前澄色主题，切换到夜色主题')

    await themeToggle.click()
    await expect(themeToggle).toContainText('夜')
    await expect(themeToggle).toHaveAttribute('aria-label', '当前夜色主题，切换到澄色主题')

    await page.emulateMedia({ colorScheme: 'light' })
    await expect(themeToggle).toContainText('澄')
    await expect(themeToggle).toHaveAttribute('aria-label', '当前澄色主题，切换到夜色主题')
  })

  test('系统主题能力缺失时按本地时钟降级且页面仍可用', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window, 'matchMedia', { configurable: true, value: undefined })
    })
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    const expected = await page.evaluate(() => {
      const hour = new Date().getHours()
      return hour >= 6 && hour < 18 ? '澄' : '夜'
    })
    await expect(page.locator('.mast-palette'))
      .toHaveAttribute('aria-label', `当前${expected}色主题，切换到${expected === '澄' ? '夜' : '澄'}色主题`)
  })

  test('尺度与人物类型默认折叠，帝王和重点人物留在外层', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()

    await expect(page.locator('.tc-scale-trigger')).toContainText('帝王')
    await expect(page.locator('.tc-segmented')).toHaveCount(0)
    await page.locator('.tc-scale-trigger').click()
    await expect(page.locator('.tc-segmented button')).toHaveCount(5)

    await expect(page.locator('.fb-focus', { hasText: '重点人物' })).toBeVisible()
    await expect(page.locator('#person-role-filters')).toHaveCount(0)
    await page.locator('.fb-role-toggle').click()
    await expect(page.locator('#person-role-filters .fb-chip')).toHaveCount(13)
  })

  test('古地图为默认，图层收起且不遮挡缩放控件', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('#map-container canvas')).toBeVisible({ timeout: 20_000 })
    const expandButton = page.getByRole('button', { name: '放大地图为主体' })
    await expect(expandButton.locator('svg')).toHaveCount(1)
    await expect(expandButton).not.toContainText('放')
    await expect(page.locator('#map-basemap-options')).toHaveCount(0)
    await page.locator('.bm-layer-toggle').click()
    await expect(page.locator('.bm-btn[aria-label="谭其骧历史地图 · 随年换幅底图"]')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.maplibregl-ctrl-bottom-left .maplibregl-ctrl-zoom-in')).toBeVisible()

    const overlap = await page.evaluate(() => {
      const a = document.querySelector('.map-tools').getBoundingClientRect()
      const b = document.querySelector('.maplibregl-ctrl-bottom-left').getBoundingClientRect()
      return Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left))
        * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top))
    })
    expect(overlap).toBe(0)
  })

  test('顶部工具与主题图标使用居中的 Lucide SVG', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.search-bar > .search-icon')).toHaveCount(1)

    for (const selector of ['.mast-help', '.mast-info', '.mast-palette']) {
      const offset = await page.locator(selector).evaluate((button) => {
        const b = button.getBoundingClientRect()
        const i = button.querySelector('svg').getBoundingClientRect()
        const label = button.querySelector('span')
        const contentLeft = label
          ? Math.min(i.left, label.getBoundingClientRect().left)
          : i.left
        const contentRight = label
          ? Math.max(i.right, label.getBoundingClientRect().right)
          : i.right
        return {
          x: Math.abs((b.left + b.width / 2) - ((contentLeft + contentRight) / 2)),
          y: Math.abs((b.top + b.height / 2) - (i.top + i.height / 2)),
        }
      })
      expect(offset.x).toBeLessThanOrEqual(1)
      expect(offset.y).toBeLessThanOrEqual(1)
    }
  })
})
