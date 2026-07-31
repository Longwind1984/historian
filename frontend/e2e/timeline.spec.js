import { test, expect } from '@playwright/test'

// 时间柱主路径冒烟 + P0b 疆域回归
// 前置：dev server 已跑在 http://127.0.0.1:5174（vite 代理 /api -> 127.0.0.1:8002）

test.describe('时间柱主路径', () => {
  test('A1-A3 朝代读数 / 在世人物 / 搜索切换', async ({ page }) => {
    await page.goto('/#year=750')

    // app 加载完成(splash 消失)
    await expect(page.locator('.mast')).toBeVisible()

    // A1. 标题含"唐"(此刻朝代读数 = ERAS[唐 618-907])；"此刻在世"计数 >0
    await expect(page.locator('.mp-title-main')).toContainText('唐', { timeout: 15_000 })
    await expect(page.locator('.mp-moment-meta')).toContainText(/此刻在世 [1-9]\d* 人/)

    // A2. 在世列表点击「李白」-> 详情面板出现"李白"与生卒年(701–762)
    await page.locator('.mp-chip', { hasText: '李白' }).first().click()
    await expect(page.locator('.ep-name')).toContainText('李白')
    await expect(page.locator('.ep-meta')).toContainText('701')
    await expect(page.locator('.ep-meta')).toContainText('762')

    // A3. 搜索「苏轼」-> 下拉出现苏轼 -> 点击 -> 详情切换为苏轼
    await page.locator('input[placeholder*="搜索"]').fill('苏轼')
    await expect(page.locator('.search-results .item', { hasText: '苏轼' }).first()).toBeVisible()
    await page.locator('.search-results .item', { hasText: '苏轼' }).first().click()
    await expect(page.locator('.ep-name')).toContainText('苏轼')
  })

  test('A4 P0b 回归: 750 年疆域图层存在, 图例非空', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()

    // territory-fill 图层在 10s 内挂载（锁死 P0b: 疆域绘制不再依赖瓦片就绪）
    await page.waitForFunction(
      () => !!(window.__hkbMap && window.__hkbMap.getLayer && window.__hkbMap.getLayer('territory-fill')),
      { timeout: 10_000 }
    )

    // 不显示「无疆域数据」（降级态 D5 起统一为 EmptyState 组件，作用域限定地图浮层）
    await expect(page.locator('.map-overlay .empty-state')).toHaveCount(0)

    // 图例: 至少 1 个政权条目, 或降级文案「疆域 N 块」(750 年带政权信息, 走条目分支)
    const legendItems = page.locator('.map-legend-item')
    const legendNote = page.locator('.map-overlay .empty-state')
    await expect(legendItems.first().or(legendNote)).toBeVisible({ timeout: 10_000 })
  })
})
