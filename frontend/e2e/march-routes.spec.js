import { test, expect } from '@playwright/test'

async function openMarchRoute(page, year, name, expectedLegs) {
  await page.goto(`/#year=${year}&basemap=素`)
  await expect(page.locator('.mast')).toBeVisible()
  await page.locator('.tc-scale-trigger').click()
  await page.locator('.tc-segmented button', { hasText: '编年' }).click()

  const card = page.locator('.tc-event-card', { hasText: name }).first()
  await expect(card).toBeVisible({ timeout: 15_000 })
  await card.click()

  await page.waitForFunction((count) => {
    const map = window.__hkbMap
    const data = map?.getSource('march')?.serialize()?.data
    return map?.getLayer('march-line') && data?.features?.length === count
  }, expectedLegs, { timeout: 15_000 })

  await expect(page.locator('.march-arrow')).toHaveCount(expectedLegs)
  return page.locator('.march-arrow').evaluateAll(
    (nodes) => nodes.map((node) => node.getAttribute('title')),
  )
}

test('安史之乱多阶段路线实际绘成两段箭头', async ({ page }) => {
  const arrowNotes = await openMarchRoute(page, 755, '安史之乱', 2)
  expect(arrowNotes).toEqual([
    '幽州 → 洛阳(东都) · 安禄山于范阳节度使治所幽州起兵南下，越河北而陷洛阳；此段只表达叛军攻取东都的第一阶段。《资治通鉴·卷217》',
    '洛阳(东都) → 长安 · 叛军据洛阳后西进，唐军失潼关，继而陷长安；库内尚无潼关地点，故本段仅记两座都城间的阶段起讫，不代替逐站路线。《资治通鉴·卷218》',
  ])
})

test('黄巢攻入长安阶段路线挂在具体事件并实际绘图', async ({ page }) => {
  const arrowNotes = await openMarchRoute(page, 880, '黄巢攻入长安', 1)
  expect(arrowNotes).toEqual([
    '洛阳(东都) → 长安 · 黄巢广明元年（880）十一月陷洛阳，继陷虢州、破潼关并经华州入长安；此段只记880年攻取东、西两京的具体阶段，不与875—884年黄巢起义父事件重复。《资治通鉴·卷254》',
  ])
})

test('宋灭南唐沿江路线实际绘成两段箭头', async ({ page }) => {
  const arrowNotes = await openMarchRoute(page, 974, '宋灭南唐', 2)
  expect(arrowNotes).toEqual([
    '江陵 → 采石矶 · 宋军自荆南顺流而东，继而驻军采石矶；此段记曹彬大军沿江进至采石矶的阶段。《宋史·曹彬传》',
    '采石矶 → 金陵 · 宋军自采石矶渡江后师进次秦淮，金陵受围；此段记采石矶至南唐都城的进军阶段。《宋史·曹彬传》',
  ])
})

test('崖山海战最后海路一程实际绘成箭头', async ({ page }) => {
  const arrowNotes = await openMarchRoute(page, 1279, '崖山海战', 1)
  expect(arrowNotes).toEqual([
    '潮陽 → 崖山 · 张弘范由潮阳港乘舟入海，经甲子门获知宋帝所在，乃进至崖山；此段只记最后一程海上进军，不概括此前沿海战事。《宋史纪事本末·卷一百八·二王之立》',
  ])
})

for (const route of [
  {
    year: 618,
    name: '唐朝建立',
    title: '唐建立前的晋阳至长安阶段实际绘图',
    arrow: '晋阳 → 大兴城 · 617年李渊自太原起兵，进攻并攻克长安；此段只记晋阳起兵至入长安的建唐前置军事阶段，不把618年受禅建国概括成行军。《旧唐书·高祖本纪》《资治通鉴·卷185》',
  },
  {
    year: 757,
    name: '唐收复两京',
    title: '唐收复长安至洛阳阶段实际绘图',
    arrow: '大兴城 → 洛阳(东都) · 757年九月唐军先收复长安，继而收复洛阳；此段只记收复两京的先后阶段，不延伸到河北追击。《旧唐书·肃宗本纪》《资治通鉴·卷220》',
  },
  {
    year: 979,
    name: '高梁河之战',
    title: '灭北汉后转攻幽州阶段实际绘图',
    arrow: '晋阳 → 幽州 · 宋太宗灭北汉后由太原径攻辽南京幽州；此段只记灭北汉后转攻幽州，不代替高梁河战场内的交战路线。《宋史·太宗本纪》《辽史·景宗本纪》',
  },
  {
    year: 917,
    name: '夹河之战',
    title: '夹河末期郓州至汴梁阶段实际绘图',
    arrow: '郓州 → 汴梁 · 923年李存勖从郓州突入，直捣汴梁灭后梁；此段只记夹河长期拉锯末期的郓州至汴梁进军，不概括917—923年全线。《资治通鉴·卷270-272》《新五代史·唐本纪》',
  },
]) {
  test(route.title, async ({ page }) => {
    const arrowNotes = await openMarchRoute(page, route.year, route.name, 1)
    expect(arrowNotes).toEqual([route.arrow])
  })
}
