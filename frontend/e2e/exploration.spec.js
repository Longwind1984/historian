import { test, expect } from '@playwright/test'

const PUBLIC_DEMO_BUTTON = /打开《安史之乱：历史、宣传与神话》公开演示/
const PRIVATE_SENTINEL = '__PRIVATE_ORIGINAL_MUST_NOT_LEAK__'
const RAW_SOURCE_URL = /(?:raw[-_]?source|source[-_]?content|anchor[-_]?content|\/sources\/[^/]+\/anchors\/[^/]+\/content)/i
const PUBLIC_DEMO_ID = 'anshi-public-demo-v1'
const DEFAULT_SCENE = {
  id: 'anshi-scene-hebei',
  anchorId: 'anshi-anchor-hebei',
  title: '河北与范阳：盛世边缘的结构性风险',
  time: '755 年以前',
  locationId: 'pl_youzhou',
}
const LOCATED_SCENE = {
  id: 'anshi-scene-luoyang',
  anchorId: 'anshi-anchor-luoyang',
  title: '范阳至洛阳：起兵、推进与帝国迟滞',
  time: '755—756',
  locationId: 'pl_luoyang_sui',
}
const NO_LOCATION_SCENE = {
  id: 'anshi-scene-tongguan',
  anchorId: 'anshi-anchor-tongguan',
  title: '潼关与灵宝：军事判断被政治命令改写',
  time: '756',
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function clientLeakSnapshot(page) {
  return page.evaluate(() => {
    const storage = {}
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index)
      storage[key] = localStorage.getItem(key)
    }
    return {
      html: document.documentElement.innerHTML,
      text: document.body.innerText,
      store: JSON.stringify(window.__hkbExploration?.$state || {}),
      storage: JSON.stringify(storage),
    }
  })
}

test.describe('单书探索工作区', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
  })

  test('稳定 Demo URL 可直接恢复公开工作台与指定 Scene', async ({ page }) => {
    await page.goto(`/#route=explore&demo=anshi&scene=${NO_LOCATION_SCENE.id}`)

    await expect(page.getByTestId('exploration-workspace')).toBeVisible()
    await expect(page.getByTestId('exploration-entry')).toHaveCount(0)
    await expect(page.locator('.explore-bar')).toContainText('公开演示 · 原文受限')
    await expect.poll(() => page.evaluate(() => ({
      kind: window.__hkbExploration.workspaceKind,
      demo: window.__hkbExploration.sampleDemoId,
      scene: window.__hkbExploration.selectedSceneId,
    }))).toEqual({
      kind: 'sample',
      demo: PUBLIC_DEMO_ID,
      scene: NO_LOCATION_SCENE.id,
    })
    const shareState = await page.evaluate(() => Object.fromEntries(
      new URLSearchParams(window.location.hash.slice(1)),
    ))
    expect(shareState).toMatchObject({
      route: 'explore',
      demo: 'anshi',
      scene: NO_LOCATION_SCENE.id,
    })
  })

  test('《安史之乱》公开受限 Demo 保持锚点、Scene、时间、地图与零原文泄露同一状态', async ({ page }) => {
    const rawSourceRequests = []
    const allRequests = []
    page.on('request', (request) => allRequests.push(request.url()))
    await page.route(RAW_SOURCE_URL, async (route) => {
      rawSourceRequests.push(route.request().url())
      await route.fulfill({
        status: 200,
        contentType: 'text/plain; charset=utf-8',
        body: PRIVATE_SENTINEL,
      })
    })

    await page.goto('/#route=explore')
    await page.getByRole('button', { name: PUBLIC_DEMO_BUTTON }).click()

    await expect(page.locator('.explore-bar')).toContainText('安史之乱')
    await expect(page.locator('.explore-bar')).toContainText('公开演示 · 原文受限')
    await expect(page.locator('.explore-bar')).toContainText('公开原创衍生摘要')
    await expect(page.getByText('《红太阳是怎样升起的》')).toHaveCount(0)
    await expect(page.getByText('高华 · 示例摘要')).toHaveCount(0)

    const initialContract = await page.evaluate(() => {
      const store = window.__hkbExploration
      return {
        workspaceKind: store.workspaceKind,
        sampleDemoId: store.sampleDemoId,
        snapshot: store.snapshot,
        selectedSceneId: store.selectedSceneId,
        selectedAnchorId: store.selectedAnchorId,
        selectedEvidenceAnchorId: store.selectedEvidenceAnchorId,
        currentScene: JSON.parse(JSON.stringify(store.currentScene)),
        currentAnchor: JSON.parse(JSON.stringify(store.currentParagraph)),
      }
    })
    expect(initialContract).toMatchObject({
      workspaceKind: 'sample',
      sampleDemoId: PUBLIC_DEMO_ID,
      snapshot: null,
      selectedSceneId: DEFAULT_SCENE.id,
      selectedAnchorId: DEFAULT_SCENE.anchorId,
      selectedEvidenceAnchorId: DEFAULT_SCENE.anchorId,
      currentScene: {
        id: DEFAULT_SCENE.id,
        primaryAnchorId: DEFAULT_SCENE.anchorId,
        location: { id: DEFAULT_SCENE.locationId },
      },
      currentAnchor: {
        id: DEFAULT_SCENE.anchorId,
        sceneId: DEFAULT_SCENE.id,
        accessState: 'restricted',
      },
    })
    const restrictedAnchor = initialContract.currentAnchor
    for (const forbiddenField of ['text', 'raw_text', 'html', 'quote']) {
      expect(Object.hasOwn(restrictedAnchor, forbiddenField)).toBe(false)
    }
    await expect(page.locator('.xr-public-anchor')).toHaveCount(9)
    await expect(page.locator('.xr-public-anchor:not([data-access-state="restricted"])')).toHaveCount(0)

    const nodeButton = page.locator('.logic-node').filter({ hasText: '原创衍生摘要' }).first()
    await nodeButton.click()
    await expect(page.getByRole('dialog', { name: '论证节点详情' })).toBeVisible()
    await page.getByRole('button', { name: '回到定位' }).click()

    const restrictedTarget = page.locator(`[data-anchor-id="${restrictedAnchor.id}"]`)
    await expect(page.getByRole('tab', { name: '阅读窗口' })).toHaveAttribute('aria-selected', 'true')
    await expect(restrictedTarget).toBeVisible()
    await expect(restrictedTarget).toHaveAttribute('data-access-state', 'restricted')
    await expect(restrictedTarget).toContainText('原文未公开')
    await expect.poll(() => page.evaluate(() => ({
      anchor: window.__hkbExploration.selectedAnchorId,
      scene: window.__hkbExploration.selectedSceneId,
      evidence: window.__hkbExploration.selectedEvidenceAnchorId,
    }))).toEqual({
      anchor: restrictedAnchor.id,
      scene: DEFAULT_SCENE.id,
      evidence: restrictedAnchor.id,
    })

    await page.getByRole('tab', { name: '时间' }).click()
    await page.getByRole('button', {
      name: new RegExp(escapeRegExp(LOCATED_SCENE.title)),
    }).click()

    await expect.poll(() => page.evaluate(() => ({
      scene: window.__hkbExploration.selectedSceneId,
      anchor: window.__hkbExploration.selectedAnchorId,
      evidence: window.__hkbExploration.selectedEvidenceAnchorId,
    }))).toEqual({
      scene: LOCATED_SCENE.id,
      anchor: LOCATED_SCENE.anchorId,
      evidence: LOCATED_SCENE.anchorId,
    })
    await expect(page.locator('.mast-year-main')).toContainText(LOCATED_SCENE.time)
    await expect(page.getByTestId('explore-map-panel')).toHaveAttribute(
      'data-location-id',
      LOCATED_SCENE.locationId,
    )
    await expect(page.getByTestId('explore-scene-card')).toContainText(LOCATED_SCENE.title)

    await page.getByRole('button', {
      name: new RegExp(escapeRegExp(NO_LOCATION_SCENE.title)),
    }).click()
    await expect(page.locator('.mast-year-main')).toContainText(NO_LOCATION_SCENE.time)
    await expect(page.getByTestId('explore-map-panel')).toHaveAttribute('data-map-state', 'no_location')
    await expect(page.getByTestId('explore-map-panel')).toHaveAttribute('data-location-id', '')
    await expect(page.getByText('材料关联 · 非人物移动')).toHaveCount(0)
    await expect.poll(() => page.evaluate(() => {
      const map = window.__hkbExplorationMap
      return [
        'explore-scene-place',
        'explore-related-places',
        'explore-scene-relations',
      ].map((sourceId) => (
        map?.getSource(sourceId)?.serialize()?.data?.features?.length ?? -1
      ))
    })).toEqual([0, 0, 0])
    await expect.poll(() => page.evaluate(() => ({
      scene: window.__hkbExploration.selectedSceneId,
      anchor: window.__hkbExploration.selectedAnchorId,
    }))).toEqual({
      scene: NO_LOCATION_SCENE.id,
      anchor: NO_LOCATION_SCENE.anchorId,
    })

    await page.getByRole('button', { name: '播放脉络' }).click()
    await page.getByRole('combobox', { name: '播放速度' }).selectOption('1.5')
    const playbackStart = await page.evaluate(() => window.__hkbExploration.sceneIndex)
    await page.getByRole('button', { name: '开始播放' }).click()
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.sceneIndex), {
      timeout: 4_000,
    }).toBeGreaterThan(playbackStart)
    await expect.poll(() => page.evaluate(() => {
      const store = window.__hkbExploration
      return {
        selectedSceneId: store.selectedSceneId,
        sceneId: store.currentScene.id,
        selectedAnchorId: store.selectedAnchorId,
        primaryAnchorId: store.currentScene.primaryAnchorId,
      }
    })).toEqual(expect.objectContaining({
      selectedSceneId: expect.any(String),
      sceneId: expect.any(String),
      selectedAnchorId: expect.any(String),
      primaryAnchorId: expect.any(String),
    }))
    const playbackSync = await page.evaluate(() => {
      const store = window.__hkbExploration
      return store.selectedSceneId === store.currentScene.id
        && store.selectedAnchorId === store.currentScene.primaryAnchorId
        && store.selectedEvidenceAnchorId === store.currentScene.primaryAnchorId
    })
    expect(playbackSync).toBe(true)
    const mapBounds = await page.getByTestId('explore-map-canvas').boundingBox()
    await page.mouse.move(mapBounds.x + mapBounds.width * 0.5, mapBounds.y + mapBounds.height * 0.5)
    await page.mouse.down()
    await page.mouse.move(mapBounds.x + mapBounds.width * 0.64, mapBounds.y + mapBounds.height * 0.5, { steps: 4 })
    await page.mouse.up()
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.playbackStatus)).toBe('paused')

    expect(rawSourceRequests).toEqual([])
    expect(allRequests.filter((url) => RAW_SOURCE_URL.test(url))).toEqual([])
    const leak = await clientLeakSnapshot(page)
    expect(leak.html).not.toContain(PRIVATE_SENTINEL)
    expect(leak.text).not.toContain(PRIVATE_SENTINEL)
    expect(leak.store).not.toContain(PRIVATE_SENTINEL)
    expect(leak.storage).not.toContain(PRIVATE_SENTINEL)
  })

  test('私人导入保持原合同，切换公开 Demo 后清除私人原文与选择状态', async ({ page }) => {
    await page.goto('/#route=explore')

    await expect(page.getByTestId('exploration-workspace')).toBeVisible()
    await expect(page.locator('.fb-bar')).toHaveCount(0)
    await expect(page.getByTestId('exploration-entry')).toBeVisible()
    await page.getByRole('button', { name: '上传本地书籍' }).click()
    const uploadDialog = page.getByRole('dialog', { name: '上传本地书籍' })
    await uploadDialog.locator('.file-picker input').setInputFiles({
      name: '我的研究材料.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from([
        '# 第一章',
        '',
        '这是用户导入的第一段材料，只用于验证私人文本锚点。',
        '',
        '这是用户导入的第二段材料，不应套用公开 Demo 的历史判断。',
        '',
        PRIVATE_SENTINEL,
      ].join('\n')),
    })
    await uploadDialog.getByRole('button', { name: '导入并进入阅读器' }).click()

    await expect(page.locator('.explore-bar')).toContainText('私人文本 · 连续阅读 · 时间与空间待确认')
    await expect(page.locator('.explore-bar')).toContainText('重启后清除')
    await expect(page.locator('.xr-meta')).toContainText('段落锚点 · 无伪页码')
    await expect(page.locator('.xe-imported-state')).toContainText('未生成证据关系')
    await expect(page.getByText('等待结构提议与人工复核')).toBeVisible()
    await expect(page.getByText(PRIVATE_SENTINEL)).toBeVisible()
    await expect(page.getByTestId('explore-map-panel')).toHaveAttribute('data-map-state', 'no_location')
    await expect(page.getByTestId('explore-map-panel')).toHaveAttribute('data-location-id', '')

    const secondParagraph = page.getByText('这是用户导入的第二段材料，不应套用公开 Demo 的历史判断。')
    await secondParagraph.click()
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.activeImportedAnchorId))
      .toMatch(/^p_/)

    await page.getByLabel('向书籍与材料提问').fill('这两段材料之间是什么关系？')
    await page.getByRole('button', { name: '记录问题' }).click()
    await expect(page.locator('.xe-records')).toContainText('这两段材料之间是什么关系？')
    await expect(page.locator('.xe-records')).toContainText('仅记录，未调用模型')

    await page.getByLabel('向书籍与材料提问').fill(PRIVATE_SENTINEL)
    await expect.poll(() => page.evaluate(() => (
      Object.values(localStorage).some((value) => String(value).includes('__PRIVATE_ORIGINAL_MUST_NOT_LEAK__'))
    ))).toBe(true)

    await page.getByRole('button', { name: '返回' }).click()
    await page.getByRole('button', { name: PUBLIC_DEMO_BUTTON }).click()

    await expect(page.locator('.explore-bar')).toContainText('公开演示 · 原文受限')
    await expect(page.getByText(PRIVATE_SENTINEL)).toHaveCount(0)
    await expect(page.getByText('这是用户导入的第一段材料，只用于验证私人文本锚点。')).toHaveCount(0)
    await expect.poll(() => page.evaluate(() => ({
      snapshot: window.__hkbExploration.snapshot,
      composerText: window.__hkbExploration.composerText,
      activeImportedAnchorId: window.__hkbExploration.activeImportedAnchorId,
      storage: Object.values(localStorage).join('\n'),
    }))).toEqual({
      snapshot: null,
      composerText: '',
      activeImportedAnchorId: null,
      storage: expect.not.stringContaining(PRIVATE_SENTINEL),
    })
  })

  test('移动端公开 Demo 保持受限锚点和 Scene，同样不暴露原文与私人 composer', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/#route=explore')
    await page.getByRole('button', { name: PUBLIC_DEMO_BUTTON }).click()

    await expect(page.getByRole('button', { name: '阅读' })).toBeVisible()
    await expect(page.getByRole('button', { name: '论证' })).toBeVisible()
    await expect(page.getByRole('button', { name: '时空' })).toBeVisible()
    await expect(page.getByRole('button', { name: '证据' })).toBeVisible()
    await expect(page.getByRole('button', { name: '出处' })).toHaveCount(0)
    await expect(page.getByText('导入并进入阅读器')).toHaveCount(0)
    await expect(page.locator('[data-access-state="restricted"]').first()).toContainText('原文未公开')

    await page.getByRole('button', { name: '论证' }).click()
    await expect(page.getByTestId('argument-graph')).toBeVisible()

    await page.getByRole('button', { name: '时空' }).click()
    await expect(page.getByTestId('explore-map-panel')).toBeVisible()
    await page.getByRole('button', {
      name: new RegExp(`切换到${escapeRegExp(LOCATED_SCENE.title)}`),
    }).click()
    await expect.poll(() => page.evaluate(() => ({
      scene: window.__hkbExploration.selectedSceneId,
      anchor: window.__hkbExploration.selectedAnchorId,
    }))).toEqual({
      scene: LOCATED_SCENE.id,
      anchor: LOCATED_SCENE.anchorId,
    })

    await page.getByRole('button', { name: '证据' }).click()
    await expect(page.getByText('关系化证据')).toBeVisible()
    await expect(page.getByLabel('向书籍与材料提问')).toHaveCount(0)
    await expect(page.getByText(PRIVATE_SENTINEL)).toHaveCount(0)
    await expect(page.getByText('《红太阳是怎样升起的》')).toHaveCount(0)
  })

  test('移动端按工作区显示范围或证据，并在入口切换后回到合理默认页', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/#route=explore')

    await page.getByLabel('输入历史问题').fill('靖难之役如何改变明初的权力结构？')
    await page.getByRole('button', { name: '开始框定范围' }).click()

    await expect(page.getByRole('button', { name: '阅读' })).toBeVisible()
    await expect(page.getByRole('button', { name: '论证' })).toBeVisible()
    await expect(page.getByRole('button', { name: '时空' })).toBeVisible()
    await expect(page.getByRole('button', { name: '范围', exact: true })).toHaveClass(/active/)
    await expect(page.getByRole('button', { name: '证据' })).toHaveCount(0)
    await expect(page.locator('.xe-scope-contract')).toBeVisible()

    await page.getByRole('button', { name: '返回' }).click()
    await page.getByRole('button', { name: PUBLIC_DEMO_BUTTON }).click()

    await expect(page.getByRole('button', { name: '阅读窗口' })).toHaveClass(/active/)
    await expect(page.getByRole('button', { name: '证据' })).toBeVisible()
    await expect(page.getByRole('button', { name: '范围', exact: true })).toHaveCount(0)
    await expect(page.locator('[data-access-state="restricted"]').first()).toContainText('原文未公开')
  })
})
