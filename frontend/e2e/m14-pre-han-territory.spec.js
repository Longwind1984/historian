import { test, expect } from '@playwright/test'

// M14 西汉之前疆域 —— 先秦(郡县制前)CHGIS 无矢量疆域源,谭其骧「古」图集有权威印刷图。
// 覆盖:① 直开先秦年份不残留旧朝代疆域(异步竞态守卫);② 素底给「切古」入口、
//      古底说「本图即疆域」而非「无疆域数据」;③ 秦抽取窗与当年有效记录不混淆。
// 前置:dev server 已跑在 http://127.0.0.1:5174(vite 代理 /api -> 127.0.0.1:8002)

const legendItems = (page) => page.evaluate(() =>
  [...document.querySelectorAll('.map-legend-item')].map((e) => e.textContent.replace(/\s+/g, '').trim()))

test('M14-1 直开战国(素底):不残留旧朝代疆域 + 出「切古」入口', async ({ page }) => {
  // 直开触发竞态:immediate watch 先画默认年 750(唐 871 块,慢),再画 -300(空,快),
  // 无守卫时 750 的响应后落地会覆盖成「唐 871」。守卫后应稳定为空。
  await page.goto('/#year=-300&basemap=素')
  await expect(page.locator('.mast')).toBeVisible()
  await page.waitForTimeout(6000)  // 让两次 territories 请求都落地

  const items = await legendItems(page)
  expect(items, `图例不应残留任何朝代疆域,实为 ${JSON.stringify(items)}`).toHaveLength(0)
  // 素底:出一键切古的入口,标注该年图幅
  const sw = page.locator('.map-atlas-switch')
  await expect(sw).toBeVisible()
  await expect(sw).toContainText('战国')
  await expect(sw).toContainText('古')
})

test('M14-2 切古按钮:点击后底图切到「古」并显示本图即疆域', async ({ page }) => {
  await page.goto('/#year=-300&basemap=素')
  await expect(page.locator('.mast')).toBeVisible()
  await page.waitForTimeout(6000)
  await page.locator('.map-atlas-switch').click()
  await page.waitForTimeout(1500)
  // 切古后:map-year 标注图集「战国」,且出「本图即...」说明而非空态
  const note = page.locator('.map-atlas-note')
  await expect(note).toBeVisible()
  await expect(note).toContainText('战国')
  // 「无疆域数据」空态不应再出现(它此前误导地盖在有权威图的年份上)
  await expect(page.locator('.map-overlay')).not.toContainText('无疆域数据')
})

test('M14-3 古底先秦:图例不写「无疆域数据」', async ({ page }) => {
  await page.goto('/#year=-300&basemap=古')
  await expect(page.locator('.mast')).toBeVisible()
  await page.waitForTimeout(6000)
  await expect(page.locator('.map-overlay')).not.toContainText('无疆域数据')
  await expect(page.locator('.map-atlas-note')).toContainText('战国')
})

test('M14-4 前215只显示当年有效CHGIS行政记录，不把抽取窗10条冒充秦疆域', async ({ page }) => {
  await page.goto('/#year=-215')
  await expect(page.locator('.mast')).toBeVisible()
  await page.waitForTimeout(6000)
  const records = await page.evaluate(async () => {
    const r = await fetch('/api/territories?year=-215').then((x) => x.json())
    return (r.features || []).map((f) => f.properties)
  })
  expect(records, '前215年应只有4条自身时段仍有效的CHGIS记录').toHaveLength(4)
  expect(records.every((p) => p.beg_yr <= -215 && p.end_yr >= -215)).toBe(true)
  expect(records.every((p) => p.record_kind === 'chgis_prefecture' && !p.polity_id)).toBe(true)
  // 图例明确标成行政建置记录，不虚构「秦朝疆域」。
  const items = await legendItems(page)
  expect(items.some((t) => t.includes('CHGIS府级行政建置记录') && t.includes('4'))).toBe(true)
  expect(items.some((t) => t.includes('秦朝'))).toBe(false)
})

test('M14-5 修复后的秦末三块几何在地图视口内实际渲染', async ({ page }) => {
  await page.goto('/#year=-209&basemap=素')
  await expect(page.locator('.mast')).toBeVisible()
  await page.waitForTimeout(6000)
  const names = await page.evaluate(async () => {
    const map = window.__hkbMap
    if (!map?.getLayer('territory-fill')) return []
    map.fitBounds([[108, 24], [121, 34]], { duration: 0, padding: 8 })
    await new Promise((resolve) => setTimeout(resolve, 600))
    return [...new Set(map.queryRenderedFeatures({ layers: ['territory-fill'] })
      .map((f) => f.properties?.name_ch).filter(Boolean))]
  })
  expect(names).toEqual(expect.arrayContaining(['鄣郡', '会稽郡', '象郡']))
})

test('M14-6 真无图幅的年份(现代 1950,谭图止于 1911)仍显「无疆域数据」', async ({ page }) => {
  // 「无疆域数据」在真的既无矢量又无图幅时是诚实的,不该被误改成切古入口 ——
  // 否则等于宣称一个不存在的图幅。1950 年无矢量疆域、无谭图图幅,是干净的兜底 case。
  await page.goto('/#year=1950&basemap=古')
  await expect(page.locator('.mast')).toBeVisible()
  await page.waitForTimeout(6000)
  expect(await legendItems(page)).toHaveLength(0)
  await expect(page.locator('.map-overlay')).toContainText('无疆域数据')
  await expect(page.locator('.map-atlas-note')).toHaveCount(0)
  await expect(page.locator('.map-atlas-switch')).toHaveCount(0)
})
