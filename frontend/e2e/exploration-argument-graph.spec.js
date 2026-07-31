import { test, expect } from '@playwright/test'

const PUBLIC_DEMO_BUTTON = /打开《安史之乱：历史、宣传与神话》公开演示/
const NODE_TYPES = [
  'action_or_turn',
  'consequence',
  'limitation',
  'material_observation',
  'question',
  'reasoning_mechanism',
]

test.describe('《安史之乱》论证图', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/#route=explore')
    await page.getByRole('button', { name: PUBLIC_DEMO_BUTTON }).click()
  })

  test('九幕均提供六类节点、显式关系语义和受限来源边界', async ({ page }) => {
    for (let sceneIndex = 0; sceneIndex < 9; sceneIndex += 1) {
      await page.evaluate((index) => window.__hkbExploration.selectScene(index), sceneIndex)

      const graph = page.getByTestId('argument-graph')
      await expect(graph).toHaveAttribute(
        'data-argument-graph-id',
        /-argument-graph$/,
      )
      await expect(graph.locator('.argument-node')).toHaveCount(6)
      await expect(graph.locator('.argument-edge-list [data-edge-relation]')).toHaveCount(7)
      await expect(
        graph.locator('.argument-edge-list [data-edge-relation="contradicts"]'),
      ).toHaveCount(0)

      const contract = await graph.locator('.argument-node').evaluateAll((nodes) => ({
        types: nodes.map((node) => node.dataset.nodeType).sort(),
        layers: nodes.map((node) => node.dataset.epistemicLayer),
      }))
      expect(contract.types).toEqual(NODE_TYPES)
      expect(contract.layers).toEqual(expect.arrayContaining([
        'historical_fact',
        'author_judgment',
        'platform_inference',
        'uncertainty',
      ]))

      const edgeRelations = await graph
        .locator('.argument-edge-list [data-edge-relation]')
        .evaluateAll((edges) => edges.map((edge) => edge.dataset.edgeRelation))
      expect(edgeRelations).toEqual(expect.arrayContaining([
        'frames',
        'grounds',
        'explains',
        'leads_to',
        'qualifies',
      ]))

      const publicDataBoundary = await page.evaluate(() => {
        const graphData = window.__hkbExploration.currentScene.argumentGraph
        return {
          accessState: graphData.accessState,
          nodeFields: Object.keys(graphData.nodes[0]),
          locatorLabel: graphData.locatorLabel,
        }
      })
      expect(publicDataBoundary.accessState).toBe('restricted')
      expect(publicDataBoundary.locatorLabel).toContain('章节级定位')
      expect(publicDataBoundary.nodeFields).not.toEqual(expect.arrayContaining([
        'text',
        'raw_text',
        'html',
        'quote',
      ]))
    }
  })

  test('节点详情解释层级，并能回到同一受限锚点展开来源说明', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    const materialNode = page.locator(
      '.argument-node[data-node-type="material_observation"]',
    )
    await materialNode.click()

    const dialog = page.getByRole('dialog', { name: '论证节点详情' })
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText('材料观察 · 原创衍生摘要')
    await expect(dialog).toContainText('作者判断')
    await expect(dialog).toContainText('章节级定位')
    await expect(dialog).toContainText('原文未公开')

    const expectedAnchorId = await page.evaluate(
      () => window.__hkbExploration.currentScene.argumentGraph.anchorId,
    )
    await page.getByRole('button', { name: '回到定位' }).click()
    const target = page.locator(`[data-anchor-id="${expectedAnchorId}"]`)
    await expect(target).toHaveAttribute('data-access-state', 'restricted')
    await expect(target.locator('.xr-public-anchor-trigger')).toHaveAttribute('aria-expanded', 'true')
    const sourceDetail = target.getByRole('region', { name: /第一章 · 章节级定位来源说明/ })
    await expect(sourceDetail).toBeVisible()
    await expect(sourceDetail).toContainText('原创衍生摘要')
    await expect(sourceDetail).toContainText('核心论点')
    await expect(sourceDetail).toContainText('源正文、私有 locator 与原文件未下发')

    await sourceDetail.getByRole('button', { name: '复制章节定位' }).click()
    await expect(sourceDetail.getByRole('status')).toHaveText('已复制章节定位')
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(
      '《安史之乱：历史、宣传与神话》 · 第一章 · 章节级定位',
    )
    await expect.poll(() => page.evaluate(() => ({
      anchorId: window.__hkbExploration.selectedAnchorId,
      sceneId: window.__hkbExploration.selectedSceneId,
    }))).toEqual({
      anchorId: expectedAnchorId,
      sceneId: 'anshi-scene-hebei',
    })
  })
})
