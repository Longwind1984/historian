import { test, expect } from '@playwright/test'

async function openExpandedMap(page, year = 750) {
  await page.goto(`/#year=${year}`)
  await expect(page.locator('#map-container canvas')).toBeVisible({ timeout: 20_000 })
  await expect(page.getByTestId('map-story-controls')).toHaveCount(0)
  await page.getByRole('button', { name: '放大地图为主体' }).click()
  await expect(page.getByTestId('map-story-controls')).toBeVisible()
  await page.waitForFunction(() => window.__hkbMapStory?.loaded)
}

test.describe('展开地图历史播放', () => {
  test('播放事件时地图、左时间轴和简介浮窗联动，手动接管地图即暂停', async ({ page }) => {
    await openExpandedMap(page, 750)

    const total = await page.evaluate(() => window.__hkbMapStory.entries.length)
    expect(total).toBeGreaterThan(100)
    await page.getByRole('button', { name: '播放地图历史' }).click()
    await expect(page.getByRole('button', { name: '暂停地图历史播放' })).toBeVisible()
    await expect(page.getByTestId('map-story-card')).toBeVisible()
    await expect(page.getByTestId('map-story-card')).toContainText('怛罗斯之战')
    await expect(page.locator('.evt-mark')).toHaveCount(1)

    await expect.poll(() => page.evaluate(() => ({
      story: window.__hkbMapStory.current.year,
      timeline: window.__hkbTimeline.year,
    }))).toEqual({ story: 751, timeline: 751 })

    // 5.2s 有界计时器必须真的自动推进到下一项，不能只证明按钮能换卡。
    await expect.poll(() => page.evaluate(() => window.__hkbMapStory.current.year), {
      timeout: 7_000,
    }).toBe(755)
    await expect(page.getByTestId('map-story-card')).toContainText('安史之乱')
    await expect.poll(() => page.evaluate(() => window.__hkbTimeline.year)).toBe(755)

    // 手动暂停后再点下一项，验证离散控制仍走同一联动通道。
    await page.getByRole('button', { name: '暂停地图历史播放' }).click()
    await page.getByRole('button', { name: '下一个历史条目' }).click()
    await expect(page.getByTestId('map-story-card')).toContainText('马嵬驿之变')
    await expect.poll(() => page.evaluate(() => window.__hkbTimeline.year)).toBe(756)

    // 重新播放后直接拖拽地图，视为用户接管镜头，当前卡保留但计时器暂停。
    await page.getByRole('button', { name: '播放地图历史' }).click()
    const canvas = page.locator('#map-container canvas')
    const box = await canvas.boundingBox()
    await page.mouse.move(box.x + box.width * 0.45, box.y + box.height * 0.5)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.5, { steps: 4 })
    await page.mouse.up()
    await expect(page.getByRole('button', { name: '播放地图历史' })).toBeVisible()
    await expect(page.getByTestId('map-story-card')).toContainText('马嵬驿之变')
  })

  test('关键人物生平节点只借严格匹配的关联事件定位，收起地图停止播放', async ({ page }) => {
    await openExpandedMap(page, -1100)

    const selected = await page.evaluate(() => {
      const index = window.__hkbMapStory.entries.findIndex((entry) =>
        entry.kind === 'life_event'
        && entry.entity_id === 'p_zhou_wu_wang'
        && entry.focus_entity_id === 'b_muye')
      if (index < 0) return null
      window.__hkbMapStory.selectIndex(index)
      return window.__hkbMapStory.entries[index]
    })
    expect(selected).toBeTruthy()
    await expect(page.getByTestId('map-story-card')).toContainText('姬发 · 生平')
    await expect(page.getByTestId('map-story-card')).toContainText('牧野之战灭商')
    await expect(page.getByTestId('map-story-card')).toContainText('地点依据同年关联事件「牧野之战」')
    await expect.poll(() => page.evaluate(() => window.__hkbTimeline.year)).toBe(-1046)
    await expect.poll(() => page.evaluate(() => window.__hkbTimeline.momentPins.length)).toBeGreaterThan(0)
    await expect.poll(() => page.url()).toContain('entity=p_zhou_wu_wang%3APerson')

    await page.getByRole('button', { name: '播放地图历史' }).click()
    await expect(page.getByRole('button', { name: '暂停地图历史播放' })).toBeVisible()
    await page.getByRole('button', { name: '收起地图' }).click()
    await expect(page.getByTestId('map-story-controls')).toHaveCount(0)
    await expect.poll(() => page.evaluate(() => window.__hkbMapStory.playing)).toBe(false)
  })
})
