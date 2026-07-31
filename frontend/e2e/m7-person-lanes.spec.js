import { test, expect } from '@playwright/test'

// M7 时间柱人物区可读性重构 —— T7.0 钉子先行(施工前应按预期失败)
// 覆盖:车道双自适应/聚合溢出道(T7.2+T7.4)、拖分栏实时重算(T7.1)、
//       选中聚光(T7.3)、关系连线 x 几何(T7.3)
// 前置:dev server 已跑在 http://127.0.0.1:5174(vite 代理 /api -> 127.0.0.1:8002)

// 柱上人物条的 left 集合(px)
const collectLefts = () => Array.from(document.querySelectorAll('.tc-person-wrap')).map((el) => parseFloat(el.style.left))

test.describe('M7 人物区可读性', () => {
  test('T7.2 L0 道距 ≥4px,或聚合溢出道存在且可读(+N 计数 + hover 名单)', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    // L0 朝代档(默认开的是 L1)
    await page.locator('.tc-scale-trigger').click()
    await page.locator('.tc-segmented button', { hasText: '朝代' }).click()
    await expect(page.locator('.tc-person-wrap').first()).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(400) // 布局落定

    // 全部人物条车道位去重后的最小间距
    const lefts = await page.evaluate(collectLefts)
    expect(lefts.length).toBeGreaterThan(0)
    const uniq = [...new Set(lefts)].sort((a, b) => a - b)
    let minPitch = Infinity
    for (let i = 1; i < uniq.length; i++) minPitch = Math.min(minPitch, uniq[i] - uniq[i - 1])

    const agg = page.locator('.tc-agg-badge')
    const aggOk = (await agg.count()) > 0
    expect(minPitch >= 4 || aggOk, `最小道距 ${minPitch.toFixed(2)}px 且无聚合道`).toBe(true)

    if (aggOk) {
      // 聚合道计数徽标 +N
      await expect(agg).toHaveText(/^\+\d+$/)
      // hover 见名单
      await agg.hover()
      await expect(page.locator('.tc-agg-pop')).toBeVisible()
      expect(await page.locator('.tc-agg-pop-name').count()).toBeGreaterThan(0)
    }
  })

  test('T7.1 拖 SplitPane 人物区布局实时重算(全程不滚动)', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.tc-person-wrap').first()).toBeVisible({ timeout: 15_000 })
    await page.waitForTimeout(400)

    const before = await page.evaluate(collectLefts)
    const st0 = await page.locator('.tc-scroll').evaluate((el) => el.scrollTop)

    // 主分栏(时间柱 | 右栏)手柄右拖 200px
    const handle = page.locator('.app-body > .sp-root > .sp-handle')
    const box = await handle.boundingBox()
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.down()
    await page.mouse.move(box.x + 200, box.y + box.height / 2, { steps: 8 })
    await page.mouse.up()
    await page.waitForTimeout(250)

    // 全程未滚动 —— 重算只能来自尺寸观测,不能来自滚动回写
    const st1 = await page.locator('.tc-scroll').evaluate((el) => el.scrollTop)
    expect(st1).toBe(st0)

    const after = await page.evaluate(collectLefts)
    expect(after.join(','), '拖分栏后人物条 left 应实时重算').not.toBe(before.join(','))
  })

  test('T7.3 选中聚光:选中人物后非选中条淡出至 ≤0.3', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    // 默认演示锚点选中李白;选中条已上轴再断言
    await expect(page.locator('.tc-person-wrap.selected')).toBeVisible({ timeout: 15_000 })
    const op = await page.locator('.tc-person-wrap:not(.selected)').first()
      .evaluate((el) => parseFloat(getComputedStyle(el).opacity))
    expect(op, '非选中条应淡出(复用事件 dim 模式)').toBeLessThanOrEqual(0.3)
  })

  test('T7.3 关系连线 x 落在人物区 px 几何内(不再是旧百分比残留)', async ({ page }) => {
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.tc-person-wrap.selected')).toBeVisible({ timeout: 15_000 })

    const lines = page.locator('.tc-relation-svg line')
    // 不断言可见性:同车道连线 x1==x2 时 bbox 宽度为 0,Playwright 视为 hidden —— 只等数量
    await expect.poll(() => lines.count(), { timeout: 8_000 }).toBeGreaterThan(0)
    const n = await lines.count()

    // 人物区实际范围:条 left 的 min..max(聚合道在最右一道,留余量)
    const lefts = await page.evaluate(collectLefts)
    const minL = Math.min(...lefts)
    const maxL = Math.max(...lefts)
    for (let i = 0; i < n; i++) {
      for (const attr of ['x1', 'x2']) {
        const v = await lines.nth(i).getAttribute(attr)
        expect(v.endsWith('%'), `line[${i}].${attr}=${v} 仍是百分比单位`).toBe(false)
        const x = parseFloat(v)
        expect(x, `line[${i}].${attr}=${x} 左越界`).toBeGreaterThanOrEqual(minL - 4)
        expect(x, `line[${i}].${attr}=${x} 右越出人物区`).toBeLessThanOrEqual(maxL + 40)
      }
    }
  })
})
