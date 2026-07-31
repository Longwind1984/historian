import { test, expect } from '@playwright/test'

function epubSnapshot() {
  const paragraphs = Array.from({ length: 40 }, (_, index) => ({
    id: `epub-p-${index + 1}`,
    section_id: index < 20 ? 'epub-s-1' : 'epub-s-2',
    ordinal: index,
    text: `EPUB 连续正文第 ${index + 1} 段。${'用于验证章节窗口渲染与滚动锚点联动。'.repeat(4)}`,
    anchor_kind: 'paragraph',
    page_label: null,
    locator: {
      source_format: 'epub',
      section_index: index < 20 ? 0 : 1,
      paragraph_index: index < 20 ? index : index - 20,
      spine_index: index < 20 ? 0 : 1,
      href: index < 20 ? 'OPS/chapter-1.xhtml' : 'OPS/chapter-2.xhtml',
      progression_percent: (index / 39) * 100,
    },
  }))
  return {
    id: 'explore-epub-test',
    revision: 1,
    created_at: '2026-07-27T00:00:00Z',
    updated_at: '2026-07-27T00:00:00Z',
    retention: 'process_memory',
    persistence_warning: 'Process restart clears this private exploration.',
    session_boundary: {
      storage: 'process_memory',
      ttl_seconds: 21600,
      max_sessions: 64,
      max_total_source_chars: 8000000,
      restart_clears_session: true,
    },
    entry_mode: 'book',
    document: {
      id: 'doc-epub-test',
      title: 'EPUB 测试书',
      author: '测试作者',
      version_label: '用户上传版本',
      source_format: 'epub',
      checksum_sha256: 'test',
      char_count: 4000,
      section_count: 2,
      paragraph_count: 40,
      retention: 'process_memory',
      ephemeral: true,
      sections: [
        { id: 'epub-s-1', title: '第一章', level: 1, ordinal: 0, paragraphs: paragraphs.slice(0, 20) },
        { id: 'epub-s-2', title: '第二章', level: 1, ordinal: 1, paragraphs: paragraphs.slice(20) },
      ],
    },
    brief: { question: null, time_range: null, geography: [], threads: ['文本结构'], status: 'draft' },
    scope_contract: null,
    active_anchor_id: paragraphs[0].id,
    active_scene_id: null,
    reading_progress: {
      anchor_id: paragraphs[0].id,
      progression_percent: paragraphs[0].locator.progression_percent,
      locator: paragraphs[0].locator,
      updated_at: '2026-07-27T00:00:00Z',
    },
    external_reading_bridge: null,
    scenes: [],
    claims: [],
    evidence: [],
    composer_entries: [],
    analysis_queue: [],
  }
}

test.describe('探索 v5 入口与阅读器', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
  })

  test('默认是真空入口，Prompt 真实建立范围合同并 hydration 到同一工作区', async ({ page }) => {
    let promptPayload = null
    let scopePayload = null
    await page.route('**/api/explorations/from-prompt', async (route) => {
      promptPayload = route.request().postDataJSON()
      await route.continue()
    })
    await page.route('**/api/explorations/*/mutations', async (route) => {
      const payload = route.request().postDataJSON()
      if (payload.type === 'update_scope_contract') scopePayload = payload
      await route.continue()
    })
    await page.goto('/#route=explore')

    await expect(page.getByTestId('exploration-entry')).toBeVisible()
    await expect(page.getByText('你想理解哪段历史？')).toBeVisible()
    await expect(page.getByRole('button', { name: '上传本地书籍' })).toBeVisible()
    await expect(page.getByText('EPUB · TXT · Markdown').first()).toBeVisible()
    await expect(page.locator('.mast-year-sub')).toHaveCount(0)
    await expect(page.getByTestId('explore-map-panel')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /打开《安史之乱：历史、宣传与神话》公开演示/ })).toBeVisible()
    await expect(page.getByText('《红太阳是怎样升起的》')).toHaveCount(0)

    const uploadTrigger = page.getByRole('button', { name: '上传本地书籍' })
    await uploadTrigger.click()
    await expect(page.getByRole('dialog', { name: '上传本地书籍' })).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(uploadTrigger).toBeFocused()

    await page.getByLabel('输入历史问题').fill('靖难之役如何改变明初的权力结构？')
    await page.getByRole('button', { name: '开始框定范围' }).click()

    await expect.poll(() => promptPayload).toEqual({
      prompt: '靖难之役如何改变明初的权力结构？',
    })
    await expect(page.getByRole('button', { name: '返回' })).toBeVisible()
    await expect(page.locator('.brief')).toContainText('靖难之役如何改变明初的权力结构？')
    await expect(page.locator('.explore-bar')).toContainText('当前进程临时会话')
    await expect(page.locator('.xe-scope-contract')).toContainText('时间范围')
    await expect(page.locator('.xe-scope-contract')).toContainText('空间范围')
    await expect(page.locator('.xe-scope-contract')).toContainText('叙事主线')
    await expect(page.locator('.xe-scope-contract')).toContainText('继续追问')
    await expect(page.getByTestId('explore-map-panel')).toHaveAttribute('data-map-state', 'no_location')
    await expect.poll(() => page.evaluate(() => ({
      kind: window.__hkbExploration.workspaceKind,
      revision: window.__hkbExploration.snapshot?.revision,
      entryMode: window.__hkbExploration.snapshot?.entry_mode,
      anchor: window.__hkbExploration.selectedAnchorId,
      scene: window.__hkbExploration.selectedSceneId,
      evidence: window.__hkbExploration.selectedEvidenceAnchorId,
      sync: window.__hkbExploration.questionSyncState,
    }))).toMatchObject({
      kind: 'question',
      revision: 1,
      entryMode: 'prompt',
      anchor: 'question',
      evidence: 'question',
      sync: 'synced',
    })
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.selectedSceneId))
      .toMatch(/^scene_/)

    for (const label of ['调整研究 Brief 高度', '调整论证与地图高度']) {
      const separator = page.getByRole('separator', { name: label })
      await expect(separator).toHaveAttribute('aria-orientation', 'horizontal')
      const before = Number(await separator.getAttribute('aria-valuenow'))
      await separator.press('ArrowDown')
      await expect.poll(async () => Number(await separator.getAttribute('aria-valuenow'))).toBeGreaterThan(before)
    }
    await page.getByRole('separator', { name: '调整研究 Brief 高度' }).press('End')
    await expect.poll(async () => (await page.locator('.map-section').boundingBox())?.height || 0)
      .toBeGreaterThanOrEqual(239)

    await page.getByLabel('确认时间范围').fill('1402—1424')
    await page.getByLabel('确认空间范围').fill('南京、北京')
    await page.getByLabel('确认叙事主线').fill('权力结构、军事进程')
    await page.getByRole('button', { name: '确认范围' }).click()
    await expect.poll(() => scopePayload).toEqual({
      type: 'update_scope_contract',
      base_revision: 1,
      user_supplied_time_range: '1402—1424',
      user_supplied_geography: ['南京', '北京'],
      user_supplied_threads: ['权力结构', '军事进程'],
    })
    await expect(page.locator('.xe-scope-contract')).toContainText('时间、空间与叙事主线均已由用户明确提供。')
    await expect(page.locator('.brief')).toContainText('1402—1424')
    await expect(page.locator('.brief')).toContainText('南京 · 北京')
    await expect.poll(() => page.evaluate(() => ({
      revision: window.__hkbExploration.snapshot?.revision,
      missing: window.__hkbExploration.snapshot?.scope_contract?.fields_needing_confirmation,
      threads: window.__hkbExploration.snapshot?.brief?.threads,
    }))).toEqual({
      revision: 2,
      missing: [],
      threads: ['权力结构', '军事进程'],
    })
  })

  test('Prompt 服务失败时只保留明确标记的本地草案', async ({ page }) => {
    await page.route('**/api/explorations/from-prompt', (route) => route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: '范围服务暂时不可用' }),
    }))
    await page.goto('/#route=explore')
    await page.getByLabel('输入历史问题').fill('测试失败时是否会伪装成服务端探索')
    await page.getByRole('button', { name: '开始框定范围' }).click()

    await expect(page.locator('.explore-bar')).toContainText('本地草案')
    await expect(page.locator('.explore-bar')).toContainText('未同步服务端')
    await expect(page.getByRole('alert')).toContainText('范围服务暂时不可用')
    await expect.poll(() => page.evaluate(() => ({
      snapshot: window.__hkbExploration.snapshot,
      sync: window.__hkbExploration.questionSyncState,
      prompt: window.__hkbExploration.questionPrompt,
    }))).toEqual({
      snapshot: null,
      sync: 'failed_local',
      prompt: '测试失败时是否会伪装成服务端探索',
    })
  })

  test('EPUB 以 ArrayBuffer/base64 进入独立 adapter，正文只渲染当前章节并联动锚点', async ({ page }) => {
    let importPayload = null
    let serverSnapshot = epubSnapshot()
    const mutationPayloads = []
    await page.route('**/api/explorations/import-epub', async (route) => {
      importPayload = route.request().postDataJSON()
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(serverSnapshot) })
    })
    await page.route('**/api/explorations/explore-epub-test/mutations', async (route) => {
      const payload = route.request().postDataJSON()
      mutationPayloads.push(payload)
      const paragraph = serverSnapshot.document.sections
        .flatMap((section) => section.paragraphs)
        .find((item) => item.id === payload.anchor_id)
      serverSnapshot = {
        ...serverSnapshot,
        revision: serverSnapshot.revision + 1,
        updated_at: `2026-07-27T00:00:0${serverSnapshot.revision}Z`,
        active_anchor_id: paragraph?.id || serverSnapshot.active_anchor_id,
        reading_progress: paragraph ? {
          anchor_id: paragraph.id,
          progression_percent: paragraph.locator.progression_percent,
          locator: paragraph.locator,
          updated_at: '2026-07-27T00:00:01Z',
        } : serverSnapshot.reading_progress,
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(serverSnapshot) })
    })
    await page.goto('/#route=explore')

    const bytes = Buffer.from('PK\u0003\u0004fake-epub-binary')
    await page.getByRole('button', { name: '上传本地书籍' }).click()
    const uploadDialog = page.getByRole('dialog', { name: '上传本地书籍' })
    await expect(uploadDialog).toBeVisible()
    await expect(uploadDialog).toContainText('EPUB、TXT、Markdown')
    await uploadDialog.locator('.file-picker input').setInputFiles({
      name: '测试书.epub',
      mimeType: 'application/epub+zip',
      buffer: bytes,
    })
    await expect(uploadDialog.locator('.file-picker')).toContainText('EPUB')
    await uploadDialog.getByRole('button', { name: '导入并进入阅读器' }).click()

    await expect.poll(() => importPayload).not.toBeNull()
    expect(importPayload.filename).toBe('测试书.epub')
    expect(importPayload.content_base64).toBe(bytes.toString('base64'))
    await expect(page.locator('.explore-bar')).toContainText('EPUB 测试书')
    await expect(page.getByLabel('选择章节')).toHaveValue('0')
    await expect(page.locator('.xr-section [data-anchor-id]')).toHaveCount(20)
    await expect(page.getByText(/EPUB 连续正文第 21 段/)).toHaveCount(0)

    await page.getByLabel('选择章节').selectOption('1')
    await expect(page.locator('.xr-section').getByText(/EPUB 连续正文第 21 段/)).toBeVisible()
    await expect(page.locator('.xr-section').getByText(/EPUB 连续正文第 1 段。/)).toHaveCount(0)
    await page.locator('.xr-section [data-anchor-id]').last().scrollIntoViewIfNeeded()
    await page.locator('.xr-pages').evaluate((element) => { element.scrollTop = element.scrollHeight })

    await expect.poll(() => mutationPayloads.length).toBeGreaterThan(0)
    await expect.poll(() => page.evaluate(() => {
      const store = window.__hkbExploration
      return {
        inSecondChapter: /^epub-p-(2[1-9]|3\d|40)$/.test(store.selectedAnchorId || ''),
        sameContext: store.selectedSceneId === `anchor-context:${store.selectedAnchorId}`
          && store.selectedEvidenceAnchorId === store.selectedAnchorId,
        progress: Math.round(store.readingProgress),
      }
    })).toEqual({
      inSecondChapter: true,
      sameContext: true,
      progress: 100,
    })
    expect(mutationPayloads.every((payload) => payload.type === 'update_reading_progress')).toBe(true)
    expect(mutationPayloads.map((payload) => payload.base_revision))
      .toEqual(mutationPayloads.map((_, index) => index + 1))
    await expect.poll(() => page.evaluate(() => ({
      anchor: window.__hkbExploration.snapshot?.reading_progress?.anchor_id,
      href: window.__hkbExploration.snapshot?.reading_progress?.locator?.href,
      section: window.__hkbExploration.snapshot?.reading_progress?.locator?.section_index,
    }))).toEqual({
      anchor: mutationPayloads.at(-1).anchor_id,
      href: 'OPS/chapter-2.xhtml',
      section: 1,
    })
    const selectedText = await page.evaluate(() => window.__hkbExploration.selectedContextText)
    await expect(page.locator('.xe-imported-state')).toContainText(selectedText.slice(0, 28))
  })

  test('微信读书使用顶层 Chrome 伴读，并保留手动位置同步兜底', async ({ page }) => {
    let syncPayload = null
    await page.route('**/api/explorations/*/mutations', async (route) => {
      const payload = route.request().postDataJSON()
      if (payload.type === 'sync_external_reading_progress') syncPayload = payload
      await route.continue()
    })
    await page.goto('/#route=explore')
    await page.getByRole('button', { name: '上传本地书籍' }).click()
    const uploadDialog = page.getByRole('dialog', { name: '上传本地书籍' })
    await uploadDialog.locator('.file-picker input').setInputFiles({
      name: '微信读书桥接材料.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from('# 第一章\n\n这是用于建立真实临时探索的用户材料。'),
    })
    await uploadDialog.getByRole('button', { name: '导入并进入阅读器' }).click()
    await page.getByRole('tab', { name: '微信读书' }).click()

    await expect(page.getByText('微信读书在 Chrome 顶层运行')).toBeVisible()
    await expect(page.getByText(/伴读侧边栏只读取你主动选择的段落/)).toBeVisible()
    await expect(page.getByRole('link', { name: '打开微信读书' })).toHaveAttribute('href', 'https://weread.qq.com/')
    await expect(page.locator('iframe[title="微信读书网页阅读窗口"]')).toHaveCount(0)
    await expect(page.getByRole('button', { name: '在本站尝试嵌入' })).toHaveCount(0)
    const syncDisclosure = page.getByRole('button', { name: '同步阅读位置' })
    await expect(syncDisclosure).toHaveAttribute('aria-expanded', 'false')
    await expect(page.getByLabel('微信读书阅读位置')).toHaveCount(0)
    const webPanel = page.locator('.xr-web')
    await syncDisclosure.click()
    await expect(syncDisclosure).toHaveAttribute('aria-expanded', 'true')
    await expect(webPanel).toHaveClass(/expanded/)
    await page.getByLabel('微信读书阅读位置').fill('第三章 · 42%')
    await page.getByLabel('粘贴微信读书段落').fill('这是用户主动粘贴的当前段落。')
    await page.getByRole('button', { name: '同步', exact: true }).click()
    await expect.poll(() => syncPayload).toMatchObject({
      type: 'sync_external_reading_progress',
      base_revision: 1,
      provider: 'weread',
      url: 'https://weread.qq.com/',
      external_locator: '第三章 · 42%',
      user_provided_excerpt: '这是用户主动粘贴的当前段落。',
    })
    await expect(page.getByText(/已同步：第三章 · 42% · 非自动实时联动/)).toBeVisible()
    await expect(syncDisclosure).toHaveAttribute('aria-expanded', 'true')
    await expect.poll(() => page.evaluate(() => ({
      anchor: window.__hkbExploration.selectedAnchorId,
      scene: window.__hkbExploration.selectedSceneId,
      evidence: window.__hkbExploration.selectedEvidenceAnchorId,
      revision: window.__hkbExploration.snapshot?.revision,
      syncMode: window.__hkbExploration.snapshot?.external_reading_bridge?.sync_mode,
      domAccess: window.__hkbExploration.snapshot?.external_reading_bridge?.dom_access,
    }))).toEqual({
      anchor: 'web-bridge',
      scene: 'web-context',
      evidence: 'web-bridge',
      revision: 2,
      syncMode: 'manual_sync',
      domAccess: false,
    })
    await syncDisclosure.click()
    await expect(syncDisclosure).toHaveAttribute('aria-expanded', 'false')
    await expect(page.getByLabel('微信读书阅读位置')).toHaveCount(0)
    await expect(webPanel).not.toHaveClass(/expanded/)
  })
})
