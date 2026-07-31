import { test, expect } from '@playwright/test'

const linkRequestsByPage = new WeakMap()

test.describe('关键非原生交互的键盘与语义', () => {
  test.beforeEach(async ({ page }) => {
    const linkRequests = []
    linkRequestsByPage.set(page, linkRequests)
    page.on('request', (request) => {
      if (new URL(request.url()).pathname.startsWith('/api/links/')) {
        linkRequests.push(request.url())
      }
    })
    await page.goto('/#year=750')
    await expect(page.locator('.mast')).toBeVisible()
    await expect(page.locator('.mp-chip').first()).toBeVisible({ timeout: 15_000 })
  })

  test('搜索建议遵循 combobox/listbox 语义并可用键盘选中', async ({ page }) => {
    const search = page.getByRole('combobox', { name: '搜索历史实体' })
    await expect(search).toHaveAttribute('aria-expanded', 'false')
    await search.fill('苏轼')

    const option = page.getByRole('option', { name: /苏轼/ }).first()
    await expect(option).toBeVisible()
    await expect(search).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByRole('listbox', { name: '搜索建议' })).toBeVisible()
    await expect(search).toHaveAttribute('aria-activedescendant', await option.getAttribute('id'))

    await search.press('Enter')
    await expect(page.locator('.ep-name')).toContainText('苏轼')
    await expect(search).toHaveAttribute('aria-expanded', 'false')
  })

  test('资料来源弹层可用键盘打开、约束焦点并关闭', async ({ page }) => {
    const trigger = page.getByRole('button', { name: '打开资料来源与致谢' })
    await trigger.focus()
    await page.keyboard.press('Enter')

    const dialog = page.getByRole('dialog', { name: '资料来源与致谢' })
    await expect(dialog).toBeVisible()
    await expect(trigger).toHaveAttribute('aria-expanded', 'true')
    await expect(dialog).toBeFocused()
    await expect(page.locator('#app')).toHaveAttribute('inert', '')
    await expect(dialog.getByRole('link', { name: /中国历代人物传记资料库/ })).toBeVisible()
    await expect(dialog.getByText(/CC BY-NC-SA 4\.0/).first()).toBeVisible()
    await expect(dialog.getByText(/CHGIS Version 5/)).toBeVisible()
    await expect(dialog.getByText(/版本 v\d+\.\d+\.\d+ · [\w.+-]+/)).toBeVisible()

    await page.keyboard.press('Tab')
    await expect(dialog.getByRole('button', { name: '关闭' })).toBeFocused()

    await dialog.focus()
    await page.keyboard.press('Shift+Tab')
    await expect(dialog.getByRole('link', { name: 'Wikimedia Commons' })).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(page.locator('#app')).not.toHaveAttribute('inert', '')
    await expect(trigger).toBeFocused()
    await expect(trigger).toHaveAttribute('aria-expanded', 'false')
  })

  test('在世人物与时间柱人物可用 Space/Enter 激活并暴露选中态', async ({ page }) => {
    const chip = page.getByRole('button', { name: /查看李白.*档案/ }).first()
    await expect(chip).toHaveAttribute('tabindex', '0')
    await chip.focus()
    await chip.press('Space')
    await expect(chip).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.ep-name')).toContainText('李白')
    await expect(page.locator('.tc-lens-playing')).toHaveCount(0)
    expect(linkRequestsByPage.get(page), '未打开链接 tab 不应触发全库 mention 图冷建').toEqual([])

    const person = page.locator('.tc-person-wrap[title^="杜甫 "]').first()
    await expect(person).toHaveAttribute('role', 'button')
    await expect(person).toHaveAttribute('tabindex', '0')
    await person.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('.ep-name')).toContainText('杜甫')
  })

  test('链接 tab 保持惰性，首次主动打开后完成真实出入链加载', async ({ page }) => {
    const chip = page.getByRole('button', { name: /查看李白.*档案/ }).first()
    await chip.click()
    await expect(page.locator('.ep-name')).toContainText('李白')
    expect(linkRequestsByPage.get(page), '主动打开前不应冷建 mention 图').toEqual([])

    await page.getByRole('button', { name: /^链接/ }).click()
    await expect.poll(
      () => linkRequestsByPage.get(page).length,
      { timeout: 15_000, message: '主动打开链接 tab 后应请求 links API' },
    ).toBeGreaterThanOrEqual(3)
    await expect(page.locator('.ep-tab-body:visible .ep-ph')).toHaveCount(0, { timeout: 15_000 })
    await expect(page.locator('.ep-tab-body:visible .ep-link-group').first()).toBeVisible()
  })

  test('时间柱事件与地图政权图例可用键盘激活', async ({ page }) => {
    const eventCard = page.locator('.tc-event-card').first()
    await expect(eventCard).toBeVisible({ timeout: 15_000 })
    const eventName = (await eventCard.locator('.tc-event-name').textContent()).trim()
    const eventLabel = await eventCard.getAttribute('aria-label')
    const stableEventCard = page.getByRole('button', { name: eventLabel, exact: true })
    await expect(eventCard).toHaveAttribute('role', 'button')
    await stableEventCard.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('.ep-name')).toContainText(eventName)

    // 750 年只有中性 CHGIS 行政记录；1050 年另有确属政权疆域的辽峰值矢量。
    await page.goto('/#year=1050')
    await expect(page.locator('.mast-year-sub')).toContainText('1050', { timeout: 15_000 })
    const polity = page.locator('.map-legend-polity[role="button"]').first()
    await expect(polity).toBeVisible({ timeout: 15_000 })
    const polityName = (await polity.locator('span').nth(1).textContent()).split(' · ')[0].trim()
    await polity.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('.ep-name')).toContainText(polityName)
    await expect(polity).toHaveAttribute('aria-pressed', 'true')
  })

  test('聚合名单和密度滑杆提供完整键盘路径', async ({ page }) => {
    await page.locator('.tc-scale-trigger').click()
    await page.getByRole('button', { name: '朝代', exact: true }).click()
    const badge = page.locator('.tc-agg-badge')
    await expect(badge).toBeVisible({ timeout: 15_000 })
    await badge.focus()

    const pop = page.locator('.tc-agg-pop[role="group"]')
    await expect(pop).toBeVisible()
    const item = pop.getByRole('button').first()
    const personName = (await item.locator('.tc-agg-pop-nm').textContent()).trim()
    const density = page.getByRole('slider', { name: '全史事件密度' })
    const yearBeforePersonAnchor = Number(await density.getAttribute('aria-valuenow'))
    await item.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('.ep-name')).toContainText(personName)

    await expect(density).toHaveAttribute('aria-orientation', 'vertical')
    // 档案加载早于 650ms 锚定动画结束；先等人物年份真正落到 slider，避免拿旧 750
    // 与 ArrowDown 后的“人物年份 + 一格”比较而误报（荀况实例为 -313 → -267）。
    await expect.poll(async () => Number(await density.getAttribute('aria-valuenow')))
      .not.toBe(yearBeforePersonAnchor)
    const before = Number(await density.getAttribute('aria-valuenow'))
    await density.focus()
    await page.keyboard.press('ArrowDown')
    await expect.poll(async () => Number(await density.getAttribute('aria-valuenow')),
      { timeout: 5_000 }).toBeGreaterThan(before)
  })
})
