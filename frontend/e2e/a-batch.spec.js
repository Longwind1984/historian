import { test, expect } from '@playwright/test'

// A批 P0 断点修复回归（M6）：A1 星图 CTA / A4 URL 状态恢复
// 前置：dev server 已跑在 http://127.0.0.1:5174（vite 代理 /api -> 127.0.0.1:8002）

test.describe('A批 P0 交互断点', () => {
  test('A1 档案主 CTA「展开谱系星图 →」切路由且档案随行', async ({ page }) => {
    await page.goto('/#year=750&entity=p_li_bai:Person')
    await expect(page.locator('.mast')).toBeVisible()
    // 时间柱档案加载出李白
    await expect(page.locator('.ep-name')).toContainText('李白', { timeout: 15_000 })

    // 主 CTA：此前调错 store 必抛 TypeError、按钮毫无反应
    await page.locator('.mp-btn-primary', { hasText: '展开谱系星图' }).click()

    // 切到星图路由（URL 同步 route=graph），侧栏档案仍是同一实体
    await expect(page).toHaveURL(/route=graph/)
    await expect(page.locator('.sm-title')).toContainText('谱系星图', { timeout: 15_000 })
    await expect(page.locator('.ep-name')).toContainText('李白', { timeout: 15_000 })
  })

  test('A4 冷启动恢复 URL 的年份与实体（id:Type 新形式）', async ({ page }) => {
    await page.goto('/#year=1127&entity=p_yuefei:Person')
    await expect(page.locator('.mast')).toBeVisible()

    // 年份读数落在 1127（南宋建炎）而非默认 750
    await expect(page.locator('.mast-year-sub')).toContainText('1127', { timeout: 15_000 })
    // 档案落在岳飞，不被默认选中李白覆盖
    await expect(page.locator('.ep-name')).toContainText('岳飞', { timeout: 15_000 })
  })

  test('A4 旧形式裸 id 链接向后兼容', async ({ page }) => {
    await page.goto('/#year=750&entity=p_li_bai')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.ep-name')).toContainText('李白', { timeout: 15_000 })
  })

  test('A4 已打开页面改 hash 同样生效（hashchange 重载）', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })

    // 同文档改 hash（模拟把分享链接贴进已打开的页面）：此前不重载、毫无反应
    await page.evaluate(() => { window.location.hash = '#year=1127&entity=p_yuefei:Person' })
    await expect(page.locator('.mast-year-sub')).toContainText('1127', { timeout: 15_000 })
    await expect(page.locator('.ep-name')).toContainText('岳飞', { timeout: 15_000 })
  })
})
