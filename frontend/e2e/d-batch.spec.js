import { test, expect } from '@playwright/test'

// D批 P2 呈现一致性回归(M6):D1 文案分层/路径联想选实体、D3 年谱 life_events、D4 疆域标注层
// 前置:dev server 已跑在 http://127.0.0.1:5174(vite 代理 /api -> 127.0.0.1:8002)
// 地图图层断言走 DEV 调试桩 window.__hkbMap(同 timeline.spec.js 的既有模式)

test.describe('D批 P2 呈现一致性', () => {
  test('D1 路径起终点:输入检索 -> 联想点选 -> chip 出现且可清除', async ({ page }) => {
    await page.goto('/#year=750&route=graph')
    await expect(page.locator('.sm-title')).toContainText('谱系星图', { timeout: 15_000 })

    await page.locator('.wg-chip', { hasText: '路径' }).click()
    await expect(page.locator('[data-testid="path-from-input"]')).toBeVisible()

    // 输入「苏轼」-> 联想列表出现 -> 点选后变成 chip(印章+名)
    await page.locator('[data-testid="path-from-input"]').fill('苏轼')
    await page.locator('.wg-sugg li', { hasText: '苏轼' }).first().click()
    const chip = page.locator('.wg-pick-chip', { hasText: '苏轼' })
    await expect(chip).toBeVisible()

    // chip 可清除,清完回到检索输入框
    await chip.locator('.wg-pick-x').click()
    await expect(page.locator('[data-testid="path-from-input"]')).toBeVisible()
  })

  test('D1 文案:年份读数无「 CE」后缀', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })
    // masthead 与右栏年号读数都不再带 CE(负年由「前」表达)
    await expect(page.locator('.mast-year-sub')).not.toContainText('CE')
    await expect(page.locator('.mp-title-sub')).not.toContainText('CE')
    // 品牌层从繁:副标为「以時為軸」,无英文残留
    await expect(page.locator('.mast-subtitle')).toContainText('以時為軸')
  })

  test('D1 图谱模式标为「全局 · 双链前列」', async ({ page }) => {
    await page.goto('about:blank')   // 换文档,保证 loadFromUrl 重跑(同 graph.spec.js B3)
    await page.goto('/#year=750&route=graph')
    await expect(page.locator('.wg-mode')).toContainText('双链前列', { timeout: 15_000 })
    await expect(page.locator('.wg-mode')).not.toContainText('Top')
  })

  test('D3 年谱 tab:李白显示「生于碎叶」(籍贯 id 解析)+「年谱待补」注记', async ({ page }) => {
    await page.goto('/#year=750&entity=p_li_bai')
    await expect(page.locator('.ep-name')).toContainText('李白', { timeout: 15_000 })

    await page.locator('.ep-tabs button', { hasText: '年谱' }).click()
    // 生于拼接 bug 已修:生年行带籍贯(birthplace id -> 碎叶)
    await expect(page.locator('.ep-chrono-label').first()).toContainText('生于碎叶', { timeout: 10_000 })
    // 李白暂无 life_events:显式「待补」而非空 tab(原则 6)
    await expect(page.locator('.ep-chrono-note')).toContainText('年谱待补 · 仅录生卒')
  })

  test('D4 地图 style 中存在 territory-label 标注层', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    // 等疆域绘制完成(750 年 -> 唐等政权疆域),再查 style 图层清单
    await expect.poll(async () => page.evaluate(() => {
      const m = window.__hkbMap
      if (!m || !m.isStyleLoaded()) return false
      return m.getStyle().layers.some(l => l.id === 'territory-label')
    }), { timeout: 15_000 }).toBe(true)
  })
})
