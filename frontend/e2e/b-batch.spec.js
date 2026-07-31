import { test, expect } from '@playwright/test'

// B批 P1 闭环修复回归（M6）：B1 搜索跳年 / B3 在世 chips ⇄ 时间柱互高亮
// 前置：dev server 已跑在 http://127.0.0.1:5174（vite 代理 /api -> 127.0.0.1:8002）

test.describe('B批 P1 闭环修复', () => {
  test('B1 搜索选中人物 -> 时间柱滚到其年代 + lens 脉冲', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })

    // 搜「苏轼」-> 点选 -> 代表年=生年 1037，时间柱借 watch store.year 平滑滚过去
    await page.locator('input[placeholder*="搜索"]').fill('苏轼')
    const item = page.locator('.search-results .item', { hasText: '苏轼' }).first()
    await expect(item).toBeVisible()
    await item.click()

    // lens 胶囊朱红脉冲（类名只挂 ~350ms）必须在点选后立刻轮询捕捉——
    // 放在档案断言之后必错过脉冲窗口（此前就是因此误报失败）
    await expect.poll(
      () => page.locator('.tc-lens-label').evaluate((el) => el.classList.contains('pulse')),
      { timeout: 3_000, intervals: [30, 60, 100] },
    ).toBe(true)

    // 档案到位（A 批既有行为），年份读数与 lens 胶囊跟到 1037（B1 新增）
    await expect(page.locator('.ep-name')).toContainText('苏轼')
    await expect(page.locator('.mast-year-sub')).toContainText('1037', { timeout: 15_000 })
    await expect(page.locator('.tc-lens-label')).toContainText('1037')

    // 滚动落定后，选中人物生命条进入视口并显名 —— 柱子真的到了他的年代
    await expect(page.locator('.tc-person-wrap.selected')).toContainText('苏轼', { timeout: 8_000 })
  })

  test('B1 搜索选中地点 -> 不滚柱（无代表年，年份不动）', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toContainText('750', { timeout: 15_000 })

    // 搜「长安」-> 结果里的「地点」条目 -> 选中后档案到位，但年份不跳
    await page.locator('input[placeholder*="搜索"]').fill('长安')
    const item = page.locator('.search-results .item').filter({ hasText: '地点' }).first()
    await expect(item).toBeVisible()
    await item.click()
    await expect(page.locator('.ep-name')).toContainText('长安')

    // 等过一个平滑滚动周期，年份读数与 lens 都保持 750（Place 无代表年 -> 不滚柱）
    await page.waitForTimeout(900)
    await expect(page.locator('.mast-year-sub')).toContainText('750')
    await expect(page.locator('.tc-lens-label')).toContainText('750')
  })

  test('B3 hover 在世 chip -> 柱上生命条显名提亮；反向 hover 柱条 -> chip 加框', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    const chip = page.locator('.mp-chip', { hasText: '杜甫' }).first()
    await expect(chip).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.ep-name')).toContainText('李白')
    // 默认选中李白会触发 350ms hover 抑制窗，先等它过去再 hover
    await page.waitForTimeout(500)

    // 正向：hover chip 杜甫 -> setHover -> 柱上对应生命条 hovered（强制显名 + 提亮）
    await chip.hover()
    await expect(page.locator('.tc-person-wrap.hovered')).toHaveCount(1)
    await expect(page.locator('.tc-person-wrap.hovered')).toContainText('杜甫')
    // hover 只做跨区高亮，不再误切右侧档案；档案必须等显式激活。
    await expect(page.locator('.ep-name')).toContainText('李白')
    // 移开后高亮消失（mouseleave -> setHover(null)）
    await page.locator('.mp-cap').first().hover()
    await expect(page.locator('.tc-person-wrap.hovered')).toHaveCount(0)

    // 反向：hover 柱上杜甫生命条 -> hoveredEntityId -> 其 chip 加框（.hov）
    const wrap = page.locator('.tc-person-wrap[title*="杜甫"]')
    await wrap.dispatchEvent('mouseenter')
    await expect(page.locator('.mp-chip.hov', { hasText: '杜甫' })).toHaveCount(1)
    // 时间柱本体 hover 也只做视觉预览，右侧档案继续锁定李白。
    await expect(page.locator('.ep-name')).toContainText('李白')
    await wrap.dispatchEvent('mouseleave')
    await expect(page.locator('.mp-chip.hov')).toHaveCount(0)

    // 键盘 focus 只预览，Enter 才正式选中；与鼠标点击走同一 selectEntity 契约。
    await wrap.focus()
    await expect(page.locator('.ep-name')).toContainText('李白')
    await wrap.press('Enter')
    await expect(page.locator('.ep-name')).toContainText('杜甫')

    const liBaiChip = page.locator('.mp-chip', { hasText: '李白' }).first()
    await expect(liBaiChip).toBeVisible()
    await liBaiChip.click()
    await expect(page.locator('.ep-name')).toContainText('李白')

    // 档案内关系项保留纯 hover 高亮通道，不改变正式选中与右侧详情。
    const relation = page.locator('.ep-relation').first()
    await expect(relation).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(500)
    await relation.hover()
    await expect(page.locator('.ep-name')).toContainText('李白')
  })
})
