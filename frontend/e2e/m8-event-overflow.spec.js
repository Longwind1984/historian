import { test, expect } from '@playwright/test'

// M8 事件溢出可见性 —— T8.0 钉子先行(施工前应按预期失败)
// 覆盖:分桶计数徽标与 API 复算一致(T8.1)、hover 桶弹迷你清单且条目可点选 +
//      click 桶平滑放大回列(T8.2)、M7 人物聚合道名单升级为同一套可点选清单(T8.2)、
//      柱缘密度指示条(T8.3)
// 前置:dev server 已跑在 http://127.0.0.1:5174(vite 代理 /api -> 127.0.0.1:8002)
// 复算钩子:TimeColumn 暴露 window.__hkbTimeline(与 __hkbMap 同款 DEV 先例):
//   { eventsTotal, placed, overflowTotal, overflowIds, zoom,
//     buckets: [{key, count, yearLo, yearHi, ids, names}] }

// 进 L0 朝代档并等布局钩子就绪
async function gotoL0(page) {
  await page.goto('/#year=750')
  await expect(page.locator('.mast')).toBeVisible()
  await page.locator('.tc-scale-trigger').click()
  await page.locator('.tc-segmented button', { hasText: '朝代' }).click()
  await expect(page.locator('.tc-person-wrap').first()).toBeVisible({ timeout: 15_000 })
  await page.waitForFunction(
    () => window.__hkbTimeline && window.__hkbTimeline.eventsTotal > 0,
    { timeout: 10_000 })
  await page.waitForTimeout(700) // 平滑滚动 + 布局落定
}

// 与前端同口径从 API 复算事件总数(Event+Battle,有 date.year 才上轴)
async function apiEventCount(page) {
  return page.evaluate(async () => {
    const q = 'limit=500&fields=id,name,date'
    const [ev, bt] = await Promise.all([
      fetch(`/api/entities?type=Event&${q}`).then((r) => r.json()),
      fetch(`/api/entities?type=Battle&${q}`).then((r) => r.json()),
    ])
    return [...ev.items, ...bt.items].filter((e) => e.date && e.date.year != null).length
  })
}

// 从钩子里挑一只视口附近(唐段 600–900)的桶,prefer 计数小的(放大后回列最稳)
async function pickBucket(page, minCount = 2) {
  const buckets = await page.evaluate(() => window.__hkbTimeline.buckets)
  const near = buckets
    .filter((b) => b.count >= minCount && b.yearHi > 600 && b.yearLo < 900)
    .sort((a, b) => a.count - b.count)
  return near[0] || buckets.filter((b) => b.count >= minCount).sort((a, b) => a.count - b.count)[0]
}

test.describe('M8 事件溢出可见性', () => {
  test('T8.1 溢出处有计数徽标,数字与 API 复算一致', async ({ page }) => {
    await gotoL0(page)

    // ① API 复算:列上卡片 + 溢出 == API 实有事件数(不静默丢弃)
    const apiCount = await apiEventCount(page)
    const hook = await page.evaluate(() => window.__hkbTimeline)
    expect(hook.placed + hook.overflowTotal, '卡片+溢出 应等于 API 事件总数').toBe(apiCount)

    // ② 桶守恒:各桶计数之和 == 溢出总数
    const bucketSum = hook.buckets.reduce((s, b) => s + b.count, 0)
    expect(bucketSum, 'Σ桶计数 应等于溢出总数').toBe(hook.overflowTotal)

    // ③ DOM:多事件桶渲染 +N 徽标,且数字与钩子逐桶一致
    const target = await pickBucket(page, 2)
    expect(target, 'L0 下应存在 count≥2 的溢出桶').toBeTruthy()
    const badge = page.locator(`[data-bucket-key="${target.key}"]`)
    await expect(badge).toBeVisible()
    await expect(badge).toHaveText(`+${target.count}`)

    // ④ 徽标不再同 x 叠放:已渲染徽标两两纵向间距 ≥10px(不再是 184 枚 7x2px 叠一根虚线尺)
    const boxes = await page.locator('.tc-overflow-badge').evaluateAll(
      (els) => els.map((el) => el.getBoundingClientRect().y + el.getBoundingClientRect().height / 2))
    expect(boxes.length).toBeGreaterThan(0)
    boxes.sort((a, b) => a - b)
    for (let i = 1; i < boxes.length; i++) {
      expect(boxes[i] - boxes[i - 1], `相邻徽标间距 ${(boxes[i] - boxes[i - 1]).toFixed(1)}px`).toBeGreaterThanOrEqual(10)
    }
  })

  test('T8.2 hover 桶弹出该桶事件迷你清单,条目可点选(selectEntity 通道)', async ({ page }) => {
    await gotoL0(page)

    const target = await pickBucket(page, 2)
    const badge = page.locator(`[data-bucket-key="${target.key}"]`)
    await expect(badge).toBeVisible()
    await badge.hover()

    // 迷你清单:共享组件 .tc-agg-pop,逐条列名,数量 ≤ 桶计数
    const pop = page.locator('.tc-agg-pop')
    await expect(pop).toBeVisible()
    // 浮层与触发徽标在几何上分离，鼠标可从徽标移入清单且不遮住徽标。
    const [badgeBox, popBox] = await Promise.all([badge.boundingBox(), pop.boundingBox()])
    const separated = popBox.x + popBox.width + 4 <= badgeBox.x
      || badgeBox.x + badgeBox.width + 4 <= popBox.x
    expect(separated, '桶浮层不应覆盖触发徽标').toBe(true)
    const items = pop.locator('.tc-agg-pop-name')
    const n = await items.count()
    expect(n).toBeGreaterThan(0)
    expect(n).toBeLessThanOrEqual(target.count)

    // 条目可点选:点第一条 → 既有 selectEntity 通道 → 右栏档案卡换成该事件
    const firstName = (await items.first().locator('.tc-agg-pop-nm').innerText()).trim()
    expect(target.names).toContain(firstName)
    await items.first().click()
    await expect(page.locator('.ep-name')).toContainText(firstName, { timeout: 10_000 })
  })

  test('T8.2 click 桶平滑放大,原溢出事件回列', async ({ page }) => {
    await gotoL0(page)

    const before = await page.evaluate(() => window.__hkbTimeline)
    // 选一只能全列回列的桶:全列回列 ⇔ 与桶相交的任何 cols+1 件事件年距 ≥ 卡高行距
    // (区间图定理),换算所需 k 不超 K_MAX(12) 即容量可达。超过最大缩放容量的紧密簇
    // (如 755/756/757 连续三年、列宽仅 2)本就回列不尽 —— 那是容量上限,不是本条验收
    const ROW = 25
    const needK = (b) => {
      const ys = [...before.eventYears].sort((x, y) => x - y)
      let need = 0
      for (let i = 0; i + before.cols < ys.length; i++) {
        if (ys[i] > b.yearHi || ys[i + before.cols] < b.yearLo) continue
        need = Math.max(need, ROW / Math.max(ys[i + before.cols] - ys[i], 0.01))
      }
      return need
    }
    const candidates = before.buckets
      .filter((b) => b.count >= 2)
      .map((b) => ({ b, need: needK(b) }))
      .filter((x) => x.need > 0 && x.need <= 8)   // 容量可达且给分数序贪心留余量
      .sort((x, y) => x.need - y.need || y.b.count - x.b.count)
    const target = candidates[0] && candidates[0].b
    expect(target, '应存在可全列回列的桶').toBeTruthy()

    await page.locator(`[data-bucket-key="${target.key}"]`).click()
    await page.waitForTimeout(900) // 放大 + 平滑滚动落定

    const after = await page.evaluate(() => window.__hkbTimeline)
    // 确有放大
    expect(after.zoom, 'click 桶后 zoomLevel 应上升').toBeGreaterThan(before.zoom + 0.1)
    // 镜头落在桶区间(钳高度 bug 曾让 L0→L2 的点击飞去年 -1939;
    // store.year 是视口上沿年,锚点在其下 240/k 年处,容差照此给)
    const kk = 0.42 * Math.pow(12 / 0.42, after.zoom / 2)
    const mid = (target.yearLo + target.yearHi) / 2
    const tol = (target.yearHi - target.yearLo) + 240 / kk + 5
    expect(Math.abs(after.year - mid), `镜头应落在桶区间 ${target.yearLo}..${target.yearHi} 附近`).toBeLessThan(tol)
    // 原桶成员全部回列(不再处于溢出)
    for (const id of target.ids) {
      expect(after.overflowIds, `${id} 应已回列`).not.toContain(id)
    }
    // 整体溢出也随之缓解
    expect(after.overflowTotal, '溢出总数应下降').toBeLessThan(before.overflowTotal)
  })

  test('T8.2 人物聚合道名单升级为同一套可点选清单(M7 交互语言统一)', async ({ page }) => {
    await gotoL0(page)

    const badge = page.locator('.tc-agg-badge')
    await expect(badge).toBeVisible()
    await badge.hover()

    // 与事件桶同一组件同一类名;条目可点选 → selectEntity → 档案卡切换
    const pop = page.locator('.tc-agg-pop')
    await expect(pop).toBeVisible()
    const items = pop.locator('.tc-agg-pop-name')
    expect(await items.count()).toBeGreaterThan(0)
    const firstName = (await items.first().locator('.tc-agg-pop-nm').innerText()).trim()
    await items.first().click()
    await expect(page.locator('.ep-name')).toContainText(firstName, { timeout: 10_000 })
  })

  test('T8.3 柱缘密度指示条:全轴热区一瞥可见,刷年掠过有响应', async ({ page }) => {
    await gotoL0(page)

    // 薄条贴柱缘渲染,分桶 ≥60,热区对比可读
    const strip = page.locator('.tc-density')
    await expect(strip).toBeVisible()
    const bins = page.locator('.tc-density-bin')
    expect(await bins.count()).toBeGreaterThanOrEqual(60)
    const ops = await bins.evaluateAll(
      (els) => els.map((el) => parseFloat(getComputedStyle(el).opacity)))
    expect(Math.max(...ops) - Math.min(...ops), '密度热区应有可读对比').toBeGreaterThan(0.3)

    // 刷年响应:当前年标记随年份移动(点击条上 1/4 处跳年 → 标记跟到 1/4 处)
    const now = page.locator('.tc-density-now')
    await expect(now).toBeVisible()
    // 密度条覆盖在主滚动区边缘，wheel 必须转发给主轴，不能形成滚动死带。
    const scroll = page.locator('.tc-scroll')
    const scrollTop0 = await scroll.evaluate((el) => el.scrollTop)
    await strip.hover()
    await page.mouse.wheel(0, 260)
    await expect.poll(() => scroll.evaluate((el) => el.scrollTop)).toBeGreaterThan(scrollTop0 + 100)

    const box = await strip.boundingBox()
    await page.mouse.click(box.x + box.width / 2, box.y + box.height * 0.25)
    await page.waitForTimeout(900)
    const topPct = parseFloat(await now.evaluate((el) => el.style.top))
    expect(Math.abs(topPct - 25), `当前年标记应在 25% 附近,实测 ${topPct}%`).toBeLessThan(3)
  })
})
