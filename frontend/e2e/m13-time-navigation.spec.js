import { test, expect } from '@playwright/test'

async function gotoTimeline(page, year = 750) {
  await page.goto(`/#year=${year}`)
  await expect(page.locator('.mast')).toBeVisible({ timeout: 20_000 })
  await page.waitForFunction(
    () => window.__hkbTimeline && window.__hkbTimeline.eventsTotal > 0,
    { timeout: 15_000 },
  )
  await page.waitForTimeout(750)
}

async function jump(page, value) {
  await page.keyboard.press('g')
  const input = page.locator('.yj-input')
  await expect(input).toBeFocused()
  await input.fill(value)
  await input.press('Enter')
  await expect(input).toHaveCount(0)
}

test.describe('M13 精确时间导航', () => {
  test('严格解析年份/月格式，拒绝 13 月与未承诺的日格式', async ({ page }) => {
    // 直接打开纯模块，避免为解析单测启动整页数据加载。
    await page.goto('/src/utils/timeNavigation.js')
    const parsed = await page.evaluate(async () => {
      const { parseTimeNavigation } = await import('/src/utils/timeNavigation.js')
      const values = [
        '755年七月', '755-07', '前221年三月', '前221', '-221', '750',
        '755年十三月', '755-13', '755-00', '755-7', '755-07-01', '前0年三月',
      ]
      return Object.fromEntries(values.map((v) => [v, parseTimeNavigation(v)]))
    })
    expect(parsed['755年七月']).toEqual({ year: 755, month: 7, day: null })
    expect(parsed['755-07']).toEqual({ year: 755, month: 7, day: null })
    expect(parsed['前221年三月']).toEqual({ year: -221, month: 3, day: null })
    expect(parsed['前221']).toEqual({ year: -221, month: null, day: null })
    expect(parsed['-221']).toEqual({ year: -221, month: null, day: null })
    expect(parsed['750']).toEqual({ year: 750, month: null, day: null })
    for (const invalid of ['755年十三月', '755-13', '755-00', '755-7', '755-07-01', '前0年三月']) {
      expect(parsed[invalid], invalid).toBeNull()
    }
  })

  test('YearJump 走 transient 精确通道：轴停七月，整数 year/URL 不变口径', async ({ page }) => {
    await gotoTimeline(page)
    await jump(page, '755年七月')

    await expect.poll(
      () => page.evaluate(() => window.__hkbTimeline?.exactYear),
      { timeout: 10_000 },
    ).toBeCloseTo(755.5, 3)
    const state = await page.evaluate(() => window.__hkbTimeline)
    expect(state.year).toBe(755)
    expect(state.lod).toBe(3) // 年档不足以承载月份，自动进入既有月档
    expect(state.axisUnit).toBe('month')
    await expect(page.locator('.tc-lens-label')).toContainText('755年七月')
    await expect(page).toHaveURL(/year=755(?:&|$)/)

    await jump(page, '前221年三月')
    await expect.poll(
      () => page.evaluate(() => window.__hkbTimeline?.exactYear),
      { timeout: 10_000 },
    ).toBeCloseTo(-221 + 2 / 12, 3)
    expect(await page.evaluate(() => window.__hkbTimeline.year)).toBe(-221)
    await expect(page.locator('.tc-lens-label')).toContainText('前221年三月')
    await expect(page).toHaveURL(/year=-221(?:&|$)/)

    // 非法月份不关闭弹层，也不发新导航请求。
    const seq = await page.evaluate(() => window.__hkbTimeline.navigationSeq)
    await page.keyboard.press('g')
    const input = page.locator('.yj-input')
    await input.fill('755-13')
    await input.press('Enter')
    await expect(input).toBeVisible()
    expect(await page.evaluate(() => window.__hkbTimeline.navigationSeq)).toBe(seq)
  })

  test('方向键按年/月/轴日 LOD 步进，输入框聚焦时不劫持', async ({ page }) => {
    await gotoTimeline(page)
    await jump(page, '755-07')
    const july = 755.5

    await page.keyboard.press('ArrowRight')
    await expect.poll(
      () => page.evaluate(() => window.__hkbTimeline?.exactYear),
      { timeout: 10_000 },
    ).toBeCloseTo(july + 1 / 12, 3)
    expect(await page.evaluate(() => window.__hkbTimeline.year)).toBe(755)

    await page.locator('.tc-scale-trigger').click()
    await page.locator('.tc-segmented button', { hasText: '日' }).click()
    await expect.poll(() => page.evaluate(() => window.__hkbTimeline?.axisUnit)).toBe('day')
    await expect.poll(
      () => page.evaluate(() => window.__hkbTimeline?.exactYear),
    ).toBeCloseTo(july + 1 / 12, 4)
    const beforeDay = await page.evaluate(() => window.__hkbTimeline.exactYear)
    await page.keyboard.press('ArrowRight')
    await expect.poll(
      () => page.evaluate(() => window.__hkbTimeline?.exactYear),
      { timeout: 10_000 },
    ).toBeCloseTo(beforeDay + 1 / (12 * 30.44), 4)
    expect(await page.evaluate(() => window.__hkbTimeline.year)).toBe(755)

    const beforeInput = await page.evaluate(() => window.__hkbTimeline.exactYear)
    await page.keyboard.press('g')
    const input = page.locator('.yj-input')
    await input.fill('755-07')
    await input.press('ArrowRight')
    await page.waitForTimeout(150)
    expect(await page.evaluate(() => window.__hkbTimeline.exactYear)).toBeCloseTo(beforeInput, 5)
  })

  test('年谱 pin 的圆点复用选中人物 lane 中心', async ({ page }) => {
    await gotoTimeline(page)
    const person = page.locator('.tc-person-wrap.selected').first()
    const pin = page.locator('.tc-moment-pin').first()
    await expect(person).toBeVisible()
    await expect(pin).toBeVisible()
    const centers = await page.evaluate(() => {
      const bar = document.querySelector('.tc-person-wrap.selected .tc-person-bar')?.getBoundingClientRect()
      const dot = document.querySelector('.tc-moment-pin .tc-moment-dot')?.getBoundingClientRect()
      return bar && dot ? { bar: bar.x + bar.width / 2, dot: dot.x + dot.width / 2 } : null
    })
    expect(centers).toBeTruthy()
    expect(Math.abs(centers.bar - centers.dot)).toBeLessThanOrEqual(1)
  })
})
