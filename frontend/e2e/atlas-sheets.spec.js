import { test, expect } from '@playwright/test'

// M9 图幅注册波：跳年看「古」底图图例文本（图集「<label>」），锁死 ATLAS_SHEETS 年代表。
// 区间与认图依据见 MapPanel.vue ATLAS_SHEETS 注释；注册清单见 WORKLOG 2026-07-19 M9 段。
// 前置：dev server 已跑在 http://127.0.0.1:5174（vite 代理 /api -> 127.0.0.1:8002）。
// 注意：图例只在 basemap=古 时渲染（.map-note-sub），URL 直接带 basemap 参数恢复。

const gu = encodeURIComponent('古')

// [年份, 图例应含文本]
const CASES = [
  [-100, '西汉'],   // mp0324：长安 + 西域都护府/匈奴
  [100,  '东汉'],   // mp0334：雒阳 + 西域长史府/鲜卑
  [262,  '三国'],   // mp0346：图例纪年 魏景元三年(262)
  [281,  '西晋'],   // mp035a：图例纪年 太康二年(281)—— M9 新发现（勘察曾误判西汉重复幅）
  [330,  '东晋'],   // mp0375「东晋 · 十六国」：图题纪年 327
  [669,  '唐'],     // mp03db「唐 · 前期」：总章二年(669)
  [750,  '唐'],     // mp03dc「唐 · 中期」：开元二十九年(741)
  [850,  '唐'],     // mp03dd「唐 · 后期」：元和十五年(820)
  [1050, '北宋'],   // mp0503「北宋 · 辽」：东京开封府/北京大名府
  [1142, '金'],     // mp053d「金 · 南宋」：皇统二年/绍兴十二年(1142)
  [1200, '金'],     // mp053e「金 · 南宋」：泰和八年/嘉定元年(1208)
  [1450, '明'],     // mp0589「明 · 前期」：宣德八年(1433)
  [1600, '明'],     // mp058a「明 · 后期」：万历十年(1582)
  [1750, '清'],     // mp05c1「清 · 前期」：嘉庆二十五年(1820)
  [1900, '清'],     // mp05d1「清 · 晚期」：光绪三十四年(1908)
]

test.describe('M9 图集年代表（跳年换幅）', () => {
  for (const [year, label] of CASES) {
    test(`${year} 年 → 图集「${label}」`, async ({ page }) => {
      await page.goto(`/#year=${year}&basemap=${gu}`)
      await expect(page.locator('.mast')).toBeVisible()
      await expect(page.locator('.map-note-sub')).toContainText(`图集「${label}`, { timeout: 15_000 })
    })
  }

  test('9 年（新莽，无图）→ 兜底注明「该年代图幅待补」', async ({ page }) => {
    await page.goto(`/#year=9&basemap=${gu}`)
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.map-note-sub')).toContainText('该年代图幅待补', { timeout: 15_000 })
  })

  test('1300 年（元全图不存在，勘察穷尽）→ 兜底注明「该年代图幅待补」', async ({ page }) => {
    await page.goto(`/#year=1300&basemap=${gu}`)
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.map-note-sub')).toContainText('该年代图幅待补', { timeout: 15_000 })
  })
})
