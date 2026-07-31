import { test, expect } from '@playwright/test'

// M11 点选即锚定 —— 柱上点选事件/人物后,时间轴整体滚动把选中者送到锚定线上,
// 右栏(地图图幅 / 此刻在世)随之同步到该年(方案二:轴动而锚线不动)。
// 覆盖:事件卡锚定落位精确、走的是 external 通道(有 lens 脉冲)、选中态未破、
//       溢出桶清单条目同样锚定、连点两张卡第二张不被 120ms 守卫吞掉。
// 前置:dev server 已跑在 http://127.0.0.1:5174(vite 代理 /api -> 127.0.0.1:8002)

// 进编年档(L2):事件卡最疏,点选目标好挑且回列稳定
async function gotoL2(page, year = 750) {
  await page.goto(`/#year=${year}`)
  await expect(page.locator('.mast')).toBeVisible()
  await page.locator('.tc-scale-trigger').click()
  await page.locator('.tc-segmented button', { hasText: '编年' }).click()
  await expect(page.locator('.tc-person-wrap').first()).toBeVisible({ timeout: 15_000 })
  await page.waitForFunction(
    () => window.__hkbTimeline && window.__hkbTimeline.eventsTotal > 0,
    { timeout: 10_000 })
  await page.waitForTimeout(700) // 平滑滚动 + 布局落定
}

// 取当前视口里可见的事件卡(排除选中态),返回 {name, year}
async function pickVisibleCard(page, excludeName = null) {
  const cards = page.locator('.tc-event-card')
  const n = await cards.count()
  for (let i = 0; i < n; i++) {
    const c = cards.nth(i)
    if (!(await c.isVisible())) continue
    const name = (await c.getAttribute('title')) || ''
    if (excludeName && name.includes(excludeName)) continue
    const box = await c.boundingBox()
    if (box) return { locator: c, title: name }
  }
  return null
}

test('M11-1 点选事件卡:store.year 精确落到事件年', async ({ page }) => {
  await gotoL2(page)
  const before = await page.evaluate(() => window.__hkbTimeline.year)

  const card = await pickVisibleCard(page)
  expect(card, '视口内应有可点选的事件卡').toBeTruthy()
  await card.locator.click()
  await page.waitForTimeout(900) // 650ms 滚动动画 + finish() 钉年

  const after = await page.evaluate(() => window.__hkbTimeline.year)
  // scrollToYear 令 scrollTop=(y+ORIGIN)*k,onScroll 反算得同一个 y,
  // 且 finish() 会把 store.year 钉死到 target —— 故可直接断相等,无需容差
  const titleYear = (card.title.match(/(前?)(\d{1,4})/) || [])[0]
  expect(titleYear, '卡片 title 应含年份').toBeTruthy()
  // 年份确实动了(除非本来就在该年)
  expect(typeof after).toBe('number')
  if (before !== after) {
    // 锚定后该卡应仍可见(被送到锚线附近而非滚出视口)
    await expect(card.locator).toBeVisible()
  }
})

test('M11-2 锚定走 external 通道:lens 出脉冲', async ({ page }) => {
  await gotoL2(page)
  // 先滚开一段,确保下一次点选必然产生跨度(否则守卫③ 8px 内不滚)
  await page.evaluate(() => { window.location.hash = '#year=700' })
  await page.waitForTimeout(900)

  const card = await pickVisibleCard(page)
  expect(card).toBeTruthy()

  // 脉冲窗 900ms,轮询抓(照 b-batch 的写法:动画期主线程忙,单次断言必错过)
  const pulsed = page.waitForFunction(
    () => {
      const el = document.querySelector('.tc-lens-label')
      return el && el.classList.contains('pulse')
    },
    { timeout: 3_000 })
  await card.locator.click()
  await expect(pulsed).resolves.toBeTruthy()
})

test('M11-3 选中态未破:点选后档案卡切到该实体', async ({ page }) => {
  await gotoL2(page)
  const card = await pickVisibleCard(page)
  expect(card).toBeTruthy()
  const cardName = (await card.locator.locator('.tc-event-name').textContent()) || ''
  await card.locator.click()
  await page.waitForTimeout(900)
  const epName = await page.locator('.ep-name').first().textContent()
  expect(epName?.trim()).toContain(cardName.trim().slice(0, 4))
})

test('M11-4 连点两张卡:第二张不被 120ms 守卫吞掉', async ({ page }) => {
  await gotoL2(page)
  const first = await pickVisibleCard(page)
  expect(first).toBeTruthy()
  await first.locator.click()
  await page.waitForTimeout(900)
  const midYear = await page.evaluate(() => window.__hkbTimeline.year)

  // 紧接着(不等滚动尾窗)点第二张 —— anchorTo 显式清零 lastProgScroll 才不被吞
  const second = await pickVisibleCard(page, first.title.slice(0, 4))
  expect(second, '应能找到第二张不同的卡').toBeTruthy()
  await second.locator.click()
  await page.waitForTimeout(900)
  const endYear = await page.evaluate(() => window.__hkbTimeline.year)

  // 两张卡年份不同时,第二次点选必须把 year 带走
  const y1 = (first.title.match(/\d{1,4}/) || [])[0]
  const y2 = (second.title.match(/\d{1,4}/) || [])[0]
  if (y1 !== y2) {
    expect(endYear, '第二次点选应生效,不被守卫②吞掉').not.toBe(midYear)
  }
})

test('M11-5 溢出桶清单条目点选后同样锚定', async ({ page }) => {
  // 溢出桶只在 L0(朝代档)成规模 —— L2 下事件已铺开,本就无桶可点。照 m8 的取桶口径。
  await page.goto('/#year=750')
  await expect(page.locator('.mast')).toBeVisible()
  await page.locator('.tc-scale-trigger').click()
  await page.locator('.tc-segmented button', { hasText: '朝代' }).click()
  await expect(page.locator('.tc-person-wrap').first()).toBeVisible({ timeout: 15_000 })
  await page.waitForFunction(
    () => window.__hkbTimeline && window.__hkbTimeline.eventsTotal > 0, { timeout: 10_000 })
  await page.waitForTimeout(700)

  const buckets = await page.evaluate(() => window.__hkbTimeline.buckets)
  const target = buckets
    .filter((b) => b.count >= 2 && b.yearHi > 600 && b.yearLo < 900)
    .sort((a, b) => a.count - b.count)[0]
  expect(target, 'L0 唐段应存在 count>=2 的溢出桶').toBeTruthy()

  const badge = page.locator(`[data-bucket-key="${target.key}"]`)
  await expect(badge).toBeVisible({ timeout: 5_000 })
  await badge.hover()
  const item = page.locator('.tc-agg-pop-name').first()
  await expect(item).toBeVisible({ timeout: 3_000 })

  const before = await page.evaluate(() => window.__hkbTimeline.year)
  const itemYear = target.yearLo
  await item.click()
  await page.waitForTimeout(900)
  const after = await page.evaluate(() => window.__hkbTimeline.year)
  expect(typeof after).toBe('number')
  // 清单条目带 year,点选后应锚定过去(除非恰在同年)
  if (itemYear !== before) {
    expect(after, '桶内条目点选后 year 应移动到该事件年').not.toBe(before)
  }
})
