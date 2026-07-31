import { test, expect } from '@playwright/test'

// C批 P2 效率层回归(M6):C1 全局快捷键 / C2 搜索升级 / C3 年代导航去重
// 前置:dev server 已跑在 http://127.0.0.1:5174(vite 代理 /api -> 127.0.0.1:8002)

// 从 masthead 年份读数解析当前年(「甲子 · 750」/「前221」两种形态;D1 起无 CE 后缀)
async function readYear(page) {
  const t = await page.locator('.mast-year-sub').innerText()
  const m = t.match(/前(\d+)|(\d{3,4})/)
  if (!m) return null
  return m[1] ? -parseInt(m[1], 10) : parseInt(m[2], 10)
}

test.describe('C批 P2 效率层', () => {
  test('C1 / 聚焦搜索框(斜杠不落字)', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })

    await page.keyboard.press('/')
    const input = page.locator('input[placeholder*="搜索"]')
    await expect(input).toBeFocused()
    await expect(input).toHaveValue('')   // preventDefault:斜杠不输入
  })

  test('C1 ←/→ 步进 ±1,Shift ±10', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })
    // 等平滑滚动落定,避免方向键与挂载定位动画交叠
    await page.waitForTimeout(800)

    await page.keyboard.press('ArrowRight')
    await expect(page.locator('.mast-year-sub')).toContainText('751')
    await page.keyboard.press('Shift+ArrowRight')
    await expect(page.locator('.mast-year-sub')).toContainText('761')
    await page.keyboard.press('ArrowLeft')
    await expect(page.locator('.mast-year-sub')).toContainText('760')
  })

  test('C1 Space 播放:年份自走,再按 Space 停', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })
    await page.waitForTimeout(800)

    const y0 = await readYear(page)
    await page.keyboard.press('Space')
    // 播放指示:lens 胶囊显 ⏸
    await expect(page.locator('.tc-lens-playing')).toBeVisible()
    await page.waitForTimeout(1100)   // 400ms/年,至少走 2 年
    const y1 = await readYear(page)
    expect(y1).toBeGreaterThan(y0)

    await page.keyboard.press('Space')   // 暂停
    await expect(page.locator('.tc-lens-playing')).toHaveCount(0)
    const y2 = await readYear(page)
    await page.waitForTimeout(900)
    expect(await readYear(page)).toBe(y2)   // 停后年份不再自走
  })

  test('C1 g 跳年:前221 -> year=-221;Esc 分层清除选中', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })
    // 默认选中李白,Esc 应清掉
    await expect(page.locator('.ep-name')).toContainText('李白', { timeout: 15_000 })

    await page.keyboard.press('g')
    const jump = page.locator('.yj-input')
    await expect(jump).toBeVisible()
    await jump.fill('前221')
    await jump.press('Enter')
    await expect(page.locator('.yj-input')).toHaveCount(0)
    await expect(page.locator('.mast-year-sub')).toContainText('前221', { timeout: 15_000 })
    expect(await readYear(page)).toBe(-221)

    await page.keyboard.press('Escape')
    await expect(page).not.toHaveURL(/entity=/, { timeout: 5_000 })
  })

  test('C1 ? 帮助浮层:开/关', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })

    await page.keyboard.press('?')
    await expect(page.locator('.hk-panel')).toBeVisible()
    await page.keyboard.press('Escape')   // Esc 第一层:关帮助
    await expect(page.locator('.hk-panel')).toHaveCount(0)
    // masthead ? 钮同效
    await page.locator('.mast-help').click()
    await expect(page.locator('.hk-panel')).toBeVisible()
    await page.locator('.hk-close').click()
    await expect(page.locator('.hk-panel')).toHaveCount(0)
  })

  test('C3 时间工具组内的图标按钮唤起跳年框', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })

    await expect(page.locator('.tc-era-chips')).toHaveCount(0)
    // gutter 朝代块仍 clickable 且带 hover 提示
    await expect(page.locator('.tc-gutter-block[title*="点击前往"]').first()).toBeVisible()

    await page.locator('.tc-tool-button[aria-label="跳至年份"]').click()
    await expect(page.locator('.yj-input')).toBeVisible()
    await page.locator('.yj-input').press('Escape')
    await expect(page.locator('.yj-input')).toHaveCount(0)
  })
})
