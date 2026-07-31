import { expect, test } from '@playwright/test'

const PUBLIC_DEMO_BUTTON = /打开《安史之乱：历史、宣传与神话》公开演示/

async function openPublicDemo(page) {
  await page.addInitScript(() => localStorage.clear())
  await page.goto('/#route=explore')
  await page.getByRole('button', { name: PUBLIC_DEMO_BUTTON }).click()
  await expect(page.getByTestId('explore-map-panel')).toBeVisible()
  await expect.poll(() => page.evaluate(() => (
    window.__hkbExplorationMap?.isStyleLoaded() || false
  ))).toBe(true)
}

async function renderedStoryData(page) {
  return page.evaluate(() => {
    const map = window.__hkbExplorationMap
    const pointData = map?.getSource('explore-scene-place')?.serialize()?.data
    const lineData = map?.getSource('explore-scene-relations')?.serialize()?.data
    return {
      points: (pointData?.features || []).map((feature) => ({
        sceneId: feature.properties.sceneId,
        order: feature.properties.order,
        active: feature.properties.active,
        coordinates: feature.geometry.coordinates,
      })),
      lines: (lineData?.features || []).map((feature) => ({
        claim: feature.properties.claim,
        semantic: feature.properties.semantic,
        samples: feature.geometry.coordinates.length,
      })),
      dashPattern: map?.getPaintProperty(
        'explore-scene-relations',
        'line-dasharray',
      ) ?? null,
      zoom: map?.getZoom() ?? null,
    }
  })
}

test.describe('探索地图全览', () => {
  test('默认绘出有坐标的七幕、实线采样曲线，并诚实列出未定位 Scene', async ({ page }) => {
    await openPublicDemo(page)

    const panel = page.getByTestId('explore-map-panel')
    await expect(panel).toHaveAttribute('data-view-mode', 'overview')
    await expect(page.getByRole('button', { name: '全览' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await expect(page.getByRole('list', { name: '九幕叙事顺序' }).locator('li')).toHaveCount(9)
    await expect(page.locator('.explore-map-sequence li.missing')).toHaveCount(2)
    await expect(page.getByText('叙事顺序 · 非行军路线')).toBeVisible()

    const missingButtons = page.locator('.explore-map-sequence li.missing button')
    await expect(missingButtons.nth(0)).toContainText('潼关与灵宝')
    await expect(missingButtons.nth(0)).toContainText('未定位')
    await expect(missingButtons.nth(1)).toContainText('河阳至邙山')
    await expect(missingButtons.nth(1)).toContainText('未定位')

    await expect.poll(() => renderedStoryData(page)).toMatchObject({
      points: [
        { order: 1 },
        { order: 2 },
        { order: 4 },
        { order: 5 },
        { order: 6 },
        { order: 7 },
        { order: 8 },
      ],
      lines: Array.from({ length: 6 }, () => ({
        claim: 'sequence_not_route',
        semantic: 'narrative_sequence',
        samples: 29,
      })),
      dashPattern: null,
    })
    await expect.poll(async () => (await renderedStoryData(page)).zoom)
      .toBeLessThanOrEqual(5.4)
  })

  test('键盘选择无坐标幕会进入聚焦并清空覆盖层；全览可无损恢复', async ({ page }) => {
    await openPublicDemo(page)

    const missingScene = page.getByRole('button', {
      name: '第 3 幕地图节点，无可靠坐标，进入详情',
    })
    await missingScene.focus()
    await expect(missingScene).toBeFocused()
    await missingScene.press('Enter')

    const panel = page.getByTestId('explore-map-panel')
    await expect(panel).toHaveAttribute('data-view-mode', 'focus')
    await expect(panel).toHaveAttribute('data-map-state', 'no_location')
    await expect(page.getByRole('status')).toContainText('已清除地点与连线')
    await expect.poll(() => page.evaluate(() => ({
      sceneId: window.__hkbExploration.selectedSceneId,
      points: window.__hkbExplorationMap
        ?.getSource('explore-scene-place')?.serialize()?.data?.features?.length,
      lines: window.__hkbExplorationMap
        ?.getSource('explore-scene-relations')?.serialize()?.data?.features?.length,
    }))).toEqual({
      sceneId: 'anshi-scene-tongguan',
      points: 0,
      lines: 0,
    })

    await page.getByRole('button', { name: '全览' }).click()
    await expect(panel).toHaveAttribute('data-view-mode', 'overview')
    await expect.poll(async () => (await renderedStoryData(page)).points.length).toBe(7)
    await expect.poll(async () => (await renderedStoryData(page)).lines.length).toBe(6)
  })

  test('播放时切换全览与聚焦不暂停 Scene 推进', async ({ page }) => {
    await openPublicDemo(page)

    await page.getByRole('button', { name: '播放脉络' }).click()
    await page.getByRole('combobox', { name: '播放速度' }).selectOption('1.5')
    const startIndex = await page.evaluate(() => window.__hkbExploration.sceneIndex)
    await page.getByRole('button', { name: '开始播放' }).click()
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.sceneIndex), {
      timeout: 4_000,
    }).toBeGreaterThan(startIndex)

    const panel = page.getByTestId('explore-map-panel')
    await expect(panel).toHaveAttribute('data-view-mode', 'overview')
    await page.getByRole('button', { name: '聚焦', exact: true }).click()
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.isPlaying)).toBe(true)
    await expect(panel).toHaveAttribute('data-view-mode', 'focus')

    await page.getByRole('button', { name: '全览' }).click()
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.isPlaying)).toBe(true)
    await expect(panel).toHaveAttribute('data-view-mode', 'overview')
    await page.getByRole('button', { name: '暂停播放' }).click()
  })
})
