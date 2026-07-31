import { test, expect } from '@playwright/test'

const PUBLIC_DEMO_BUTTON = /打开《安史之乱：历史、宣传与神话》公开演示/

const REFERENCES = [
  ['anshi-ref-rebellion-start', 'e_an_lushan_rebellion', 'Event', '755'],
  ['anshi-ref-mawei', 'e_mawei_zhibian', 'Event', '756'],
  ['anshi-ref-suzong', 'p_li_heng_suzong', 'Person', '756'],
  ['anshi-ref-capitals', 'e_tang_shoufu_liangjing', 'Event', '757'],
  ['anshi-ref-wang-wei', 'p_wang_wei', 'Person', '761'],
  ['anshi-ref-daizong', 'p_li_yu_daizong', 'Person', '762'],
  ['anshi-ref-rebellion-end', 'e_an_lushan_rebellion', 'Event', '763'],
]

test.describe('探索左栏时间坐标系', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/#route=explore')
    await page.getByRole('button', { name: PUBLIC_DEMO_BUTTON }).click()
  })

  test('微信读书命名、Scene 主轨与可核实体参照轨保持 explore 状态', async ({ page }) => {
    await expect(page.getByRole('tab', { name: '微信读书' })).toBeVisible()
    await expect(page.getByRole('tab', { name: '网页', exact: true })).toHaveCount(0)

    await page.getByRole('tab', { name: '时间' }).click()
    const axis = page.getByTestId('exploration-time-axis')
    await expect(axis).toBeVisible()
    await expect(axis).toHaveAttribute('aria-label', '安史之乱纵向年代轴')
    await expect(axis.getByText('主轨 · 书中 Scene')).toBeVisible()
    await expect(axis.getByText('参照轨 · 仓库实体')).toBeVisible()
    await expect(axis.locator('.xr-time-rows > li')).toHaveCount(9)
    await expect(axis.locator('[data-scene-id]')).toHaveCount(9)
    await expect(axis.locator('[data-reference-id]')).toHaveCount(REFERENCES.length)

    for (const [referenceId, entityId, entityType, year] of REFERENCES) {
      const reference = axis.locator(`[data-reference-id="${referenceId}"]`)
      await expect(reference).toHaveAttribute('data-entity-id', entityId)
      await expect(reference).toHaveAttribute('data-entity-type', entityType)
      await expect(reference).toHaveAttribute('data-year', year)
    }

    const suiyangScene = axis.locator('[data-scene-id="anshi-scene-suiyang"]')
    await suiyangScene.focus()
    await expect(suiyangScene).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(suiyangScene).toHaveAttribute('aria-pressed', 'true')
    await expect.poll(() => page.evaluate(() => ({
      scene: window.__hkbExploration.selectedSceneId,
      anchor: window.__hkbExploration.selectedAnchorId,
    }))).toEqual({
      scene: 'anshi-scene-suiyang',
      anchor: 'anshi-anchor-suiyang',
    })

    const sceneBeforeReference = await page.evaluate(
      () => window.__hkbExploration.selectedSceneId,
    )
    const maweiReference = axis.locator('[data-reference-id="anshi-ref-mawei"]')
    await maweiReference.focus()
    await expect(maweiReference).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(maweiReference).toHaveAttribute('aria-pressed', 'true')

    await expect.poll(() => page.evaluate(() => {
      const params = new URLSearchParams(window.location.hash.slice(1))
      return {
        route: params.get('route'),
        year: params.get('year'),
        entity: params.get('entity'),
        scene: params.get('scene'),
      }
    })).toEqual({
      route: 'explore',
      year: '756',
      entity: 'e_mawei_zhibian:Event',
      scene: sceneBeforeReference,
    })
    await expect.poll(
      () => page.evaluate(() => window.__hkbExploration.selectedSceneId),
    ).toBe(sceneBeforeReference)
    await expect(page.getByRole('button', { name: '探索', exact: true })).toHaveClass(/active/)
  })
})
