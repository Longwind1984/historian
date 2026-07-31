import { test, expect } from '@playwright/test'

// M12 亚年粒度 —— 时间轴最细粒度从「年」下探到「月/日」。
// 覆盖:同年不同月的事件几何分离(此前必然重叠→溢出)、历法口径按 1912 分野
//      (农历中文月名 / 公历数字)与口径注记、日档内高可用且定位精确、
//      锚定带月份分量、m8 契约(eventYears 仍为整数)未破。
// 前置:dev server 已跑在 http://127.0.0.1:5174(vite 代理 /api -> 127.0.0.1:8002)
//
// 档位按钮序:0 朝代 / 1 帝王 / 2 编年 / 3 月 / 4 日

async function goto(page, year, lodIdx) {
  await page.goto(`/#year=${year}`)
  await expect(page.locator('.mast')).toBeVisible()
  await page.waitForFunction(
    () => window.__hkbTimeline && window.__hkbTimeline.eventsTotal > 0, { timeout: 15_000 })
  await page.locator('.tc-scale-trigger').click()
  await page.locator('.tc-segmented button').nth(lodIdx).click()
  await page.waitForTimeout(1200)
}

const cardY = async (page, name) => page.evaluate((n) => {
  const c = [...document.querySelectorAll('.tc-event-card')]
    .find((x) => (x.getAttribute('title') || '').includes(n))
  if (!c) return null
  const r = c.getBoundingClientRect()
  return { y: r.top + r.height / 2, title: c.getAttribute('title') }
}, name)

test('M12-1 月档:同年不同月的事件几何分离(编年档下本是重叠的)', async ({ page }) => {
  // 1937 年两件:七七事变 7-7、南京大屠杀 12-13。相隔 5.18 个月。
  await goto(page, 1937, 2)   // 编年 k=12:同年 → yPos 相同 → 必有一件被挤进溢出槽
  const atYear = { qiqi: await cardY(page, '七七事变'), nanjing: await cardY(page, '南京大屠杀') }
  expect(atYear.qiqi || atYear.nanjing, '编年档至少有一件在列上').toBeTruthy()

  await page.locator('.tc-scale-trigger').click()
  await page.locator('.tc-segmented button').nth(3).click()   // 月档
  await page.waitForTimeout(1400)
  const qiqi = await cardY(page, '七七事变')
  const nanjing = await cardY(page, '南京大屠杀')
  expect(qiqi, '月档下七七事变应在列上').toBeTruthy()
  expect(nanjing, '月档下南京大屠杀应在列上(不再被同年挤走)').toBeTruthy()

  // 理论间距 = 5.18 月 × (k/12)。k≈187.3 → ≈81px。放宽到 ≥25px(卡高行距)即算分离成功
  const gap = Math.abs(qiqi.y - nanjing.y)
  expect(gap, `两件应纵向分离,实测 ${gap.toFixed(1)}px`).toBeGreaterThanOrEqual(25)
})

test('M12-2 历法口径:1912 前用农历中文月名,1912 后用公历数字', async ({ page }) => {
  await goto(page, 755, 3)
  const tang = await cardY(page, '安史之乱')
  expect(tang, '755 年应见安史之乱').toBeTruthy()
  // 农历:中文月名。755 年十二月 —— 不是「12月」
  expect(tang.title).toMatch(/年[一二三四五六七八九十正腊]+月/)
  expect(tang.title).not.toMatch(/年\d+月/)

  await goto(page, 1937, 3)
  const modern = await cardY(page, '七七事变')
  expect(modern, '1937 年应见七七事变').toBeTruthy()
  // 公历:阿拉伯数字,且带日
  expect(modern.title).toMatch(/1937年7月7日/)
})

test('M12-3 历法口径注记随年代切换,且只在亚年档出现', async ({ page }) => {
  await goto(page, 755, 2)   // 编年档:不该有注记
  await expect(page.locator('.tc-calendar-note')).toHaveCount(0)

  await page.locator('.tc-scale-trigger').click()
  await page.locator('.tc-segmented button').nth(3).click()
  await page.waitForTimeout(1200)
  await expect(page.locator('.tc-calendar-note')).toContainText('农历')
  await expect(page.locator('.tc-calendar-note')).toContainText('未换算')

  await goto(page, 1937, 3)
  await expect(page.locator('.tc-calendar-note')).toContainText('公历')
})

test('M12-4 日档:1206 万 px 内高可用,scrollTop 精确不被浏览器钳制', async ({ page }) => {
  await goto(page, 1937, 4)
  const g = await page.evaluate(() => {
    const sc = document.querySelector('.tc-scroll')
    const h = window.__hkbTimeline
    return { k: Math.round(h.k), scrollHeight: sc.scrollHeight, scrollTop: Math.round(sc.scrollTop) }
  })
  expect(g.k, '日档 k 应为 2922 px/年(=8px/日)').toBe(2922)
  // TOP(240) + SPAN(4126)*2922 + 760 = 12,057,172
  expect(g.scrollHeight).toBe(12057172)
  // Chrome 单元素高度上限实测 33,554,428px —— 远未触顶,故不该被钳
  expect(g.scrollHeight).toBeLessThan(33554428)
  // 1937 年附近的 scrollTop 应在 1180 万量级且非 0(被钳会掉回小值)
  expect(g.scrollTop).toBeGreaterThan(11_000_000)
})

test('M12-5 锚定带月份分量:点选七七事变落在 7 月而非该年正月', async ({ page }) => {
  await goto(page, 1937, 3)
  await page.evaluate(() => {
    const c = [...document.querySelectorAll('.tc-event-card')]
      .find((x) => (x.getAttribute('title') || '').includes('七七事变'))
    c.click()
  })
  await page.waitForTimeout(1400)
  const ex = await page.evaluate(() => window.__hkbTimeline.exactYear)
  // 1937-7-7 的 tYear = 1937 + (6 + 6/30.44)/12 = 1937.51643
  expect(ex).toBeGreaterThan(1937.45)
  expect(ex).toBeLessThan(1937.60)
  // lens 读数也应带月份
  await expect(page.locator('.tc-lens-label')).toContainText('1937年7月')
})

test('M12-6 m8 契约未破:eventYears 仍为整数,小数年另走 eventTYears', async ({ page }) => {
  await goto(page, 750, 3)
  const h = await page.evaluate(() => {
    const t = window.__hkbTimeline
    return {
      allInt: t.eventYears.every((y) => Number.isInteger(y)),
      hasT: Array.isArray(t.eventTYears) && t.eventTYears.length === t.eventYears.length,
      someFractional: t.eventTYears.some((v, i) => Math.abs(v - t.eventYears[i]) > 1e-9),
    }
  })
  expect(h.allInt, 'eventYears 必须全是整数(m8 回列反推按整数年做候选过滤)').toBe(true)
  expect(h.hasT, 'eventTYears 应等长并存').toBe(true)
  expect(h.someFractional, '带月份的事件其 tYear 应含小数分量').toBe(true)
})
