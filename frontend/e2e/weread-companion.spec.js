import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'

const EXTENSION_ORIGIN = 'chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
const PRIVATE_TEXT = '__COMPANION_PRIVATE_TEXT_MUST_NOT_ENTER_STORAGE__'
const SHARED_CONTRACT = JSON.parse(
  await readFile(
    new URL('../../contracts/weread-companion/v1-example.json', import.meta.url),
    'utf8',
  ),
)

function selection(overrides = {}) {
  return {
    ...SHARED_CONTRACT,
    id: 'selection-1',
    ...overrides,
  }
}

async function receive(page, payload, origin = EXTENSION_ORIGIN, options = {}) {
  return page.evaluate(
    ([message, messageOrigin, receiveOptions]) =>
      window.__hkbCompanionTest.receive(message, messageOrigin, receiveOptions),
    [payload, origin, options],
  )
}

test.describe('微信读书 Chrome companion 网页桥', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      if (!sessionStorage.getItem('hkb-e2e-preserve-storage')) localStorage.clear()
    })
  })

  test('仅 companion query 与严格扩展消息可进入；无工作区不伪装成功', async ({ page }) => {
    await page.setViewportSize({ width: 420, height: 900 })
    await page.goto('/?companion=1#route=explore')
    await expect.poll(() => page.evaluate(() => Boolean(window.__hkbCompanionTest))).toBe(true)
    await expect(page.locator('.mast-brand')).toBeVisible()
    await expect(page.getByTestId('exploration-entry')).toBeVisible()
    await expect(page.locator('.mast-search-wrap')).toBeHidden()
    await expect(page.locator('.mast-route')).toBeHidden()

    const noWorkspace = await receive(page, selection())
    expect(noWorkspace).toEqual({
      version: 1,
      type: 'hkb.weread.ack',
      id: 'selection-1',
      status: 'no_workspace',
      reason: 'no_workspace',
    })
    expect(JSON.stringify(noWorkspace)).not.toContain(SHARED_CONTRACT.text)

    expect(await receive(page, selection(), 'https://weread.qq.com')).toBeNull()
    expect(await receive(page, selection(), EXTENSION_ORIGIN, { source: 'other' })).toBeNull()
    expect(await receive(
      page,
      selection(),
      'chrome-extension://bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      { exactOrigin: EXTENSION_ORIGIN },
    )).toBeNull()
    expect(await receive(page, selection({ id: 'selection-2', url: 'https://example.com/' }))).toEqual({
      version: 1,
      type: 'hkb.weread.ack',
      id: 'selection-2',
      status: 'invalid',
      reason: 'invalid_message',
    })
    expect(await receive(page, selection({ id: 'selection-3', text: 'x'.repeat(2_001) }))).toEqual({
      version: 1,
      type: 'hkb.weread.ack',
      id: 'selection-3',
      status: 'invalid',
      reason: 'invalid_message',
    })

    await page.goto('/#route=explore')
    await expect(page.evaluate(() => window.__hkbCompanionTest)).resolves.toBeUndefined()
  })

  test('公开 sample 只做本地临时联动且不持久化选区正文', async ({ page }) => {
    await page.goto('/?companion=1#route=explore')
    await page.getByRole('button', { name: /打开《安史之乱：历史、宣传与神话》公开演示/ }).click()

    const ack = await receive(page, selection({ id: 'sample-selection' }))
    expect(ack).toEqual({
      version: 1,
      type: 'hkb.weread.ack',
      id: 'sample-selection',
      status: 'local_only',
    })
    await expect(page.locator('.explore-bar')).toContainText('仅本地临时联动')
    await expect.poll(() => page.evaluate(() => ({
      anchor: window.__hkbExploration.selectedAnchorId,
      excerpt: window.__hkbExploration.webPastedExcerpt,
      notice: window.__hkbExploration.composerNotice,
      storage: Object.values(localStorage).join('\n'),
    }))).toEqual({
      anchor: 'web-bridge',
      excerpt: SHARED_CONTRACT.text,
      notice: '公开演示只做本地临时联动，未写入服务端',
      storage: expect.not.stringContaining(SHARED_CONTRACT.text),
    })
  })

  test('窄侧边栏默认展示论证，并保留时空与出处切换', async ({ page }) => {
    await page.setViewportSize({ width: 420, height: 800 })
    await page.goto('/?companion=1#route=explore')
    await page.getByRole('button', { name: /打开《安史之乱：历史、宣传与神话》公开演示/ }).click()

    await expect(page.getByRole('button', { name: '论证' })).toBeVisible()
    await expect(page.getByRole('button', { name: '时空' })).toBeVisible()
    await expect(page.getByRole('button', { name: '出处' })).toBeVisible()
    await expect(page.getByRole('button', { name: '阅读窗口' })).toHaveCount(0)
    await expect(page.locator('.companion-center .logic')).toBeVisible()
  })

  test('私人工作区写入真实 revision、使用消息 URL，并可按 id 在同一后端进程恢复', async ({ page }) => {
    const mutationPayloads = []
    await page.route('**/api/explorations/*/mutations', async (route) => {
      mutationPayloads.push(route.request().postDataJSON())
      await route.continue()
    })
    await page.goto('/?companion=1#route=explore')
    await page.getByRole('button', { name: '上传本地书籍' }).click()
    const uploadDialog = page.getByRole('dialog', { name: '上传本地书籍' })
    await uploadDialog.locator('.file-picker input').setInputFiles({
      name: 'companion-test.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from(`# Companion test\n\n${PRIVATE_TEXT}`),
    })
    await uploadDialog.getByRole('button', { name: '导入并进入阅读器' }).click()
    await expect.poll(() => page.evaluate(() => window.__hkbExploration.snapshot?.id || null))
      .not.toBeNull()
    const explorationId = await page.evaluate(() => window.__hkbExploration.snapshot.id)

    const ack = await receive(page, selection({
      id: 'private-selection',
      url: 'https://weread.qq.com/web/reader/private-book',
      title: '私人材料关联章节',
      locator: '第五章 · 61%',
      text: '只由用户主动发送的选区。',
    }))
    expect(ack).toMatchObject({
      version: 1,
      type: 'hkb.weread.ack',
      id: 'private-selection',
      status: 'synced',
      revision: 2,
    })
    expect(JSON.stringify(ack)).not.toContain('只由用户主动发送的选区')
    expect(mutationPayloads).toHaveLength(1)
    expect(mutationPayloads[0]).toMatchObject({
      type: 'sync_external_reading_progress',
      base_revision: 1,
      provider: 'weread',
      url: 'https://weread.qq.com/web/reader/private-book',
      external_locator: '第五章 · 61%',
      user_provided_excerpt: '只由用户主动发送的选区。',
    })
    const replayAck = await receive(page, selection({
      id: 'private-selection',
      url: 'https://weread.qq.com/web/reader/private-book',
      title: '私人材料关联章节',
      locator: '第五章 · 61%',
      text: '只由用户主动发送的选区。',
    }))
    expect(replayAck).toEqual(ack)
    expect(mutationPayloads).toHaveLength(1)

    const persisted = await page.evaluate(() => localStorage.getItem('history-kb-exploration-v1'))
    expect(persisted).toContain(explorationId)
    expect(persisted).not.toContain(PRIVATE_TEXT)
    expect(persisted).not.toContain('只由用户主动发送的选区。')

    let restoredByGet = false
    await page.route(`**/api/explorations/${explorationId}`, async (route) => {
      if (route.request().method() === 'GET') restoredByGet = true
      await route.continue()
    })
    await page.evaluate(() => sessionStorage.setItem('hkb-e2e-preserve-storage', '1'))
    await page.reload()
    await expect.poll(() => restoredByGet).toBe(true)
    await expect.poll(() => page.evaluate(() => window.__hkbExploration && ({
      kind: window.__hkbExploration.workspaceKind,
      id: window.__hkbExploration.snapshot?.id,
      revision: window.__hkbExploration.snapshot?.revision,
    }))).toEqual({
      kind: 'document',
      id: explorationId,
      revision: 2,
    })
    await expect(page.locator('.explore-bar')).toContainText('companion-test')
  })

  test('404 会清理失效的私人 exploration id', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('history-kb-exploration-v1', JSON.stringify({
        workspaceKind: 'document',
        privateExplorationId: 'missing-private-workspace',
      }))
    })
    await page.route('**/api/explorations/missing-private-workspace', (route) => route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'not found' }),
    }))
    await page.goto('/?companion=1#route=explore')
    await expect(page.getByTestId('exploration-entry')).toBeVisible()
    await expect.poll(() => page.evaluate(() => {
      const persisted = JSON.parse(localStorage.getItem('history-kb-exploration-v1') || '{}')
      return persisted.privateExplorationId ?? null
    })).toBeNull()
  })
})
