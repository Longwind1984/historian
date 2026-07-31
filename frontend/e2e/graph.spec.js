import { test, expect } from '@playwright/test'

// 谱系星图（StarmapView）壳 + 图谱 2D 视图（T3.1）
// 前置：dev server 已跑在 http://127.0.0.1:5174（vite 代理 /api -> 127.0.0.1:8002）
// DEV 下 WebGraph 暴露 window.__starmapDebug = { mode, nodeCount, pathFound } 供状态断言

async function installSpacetimeGate(page) {
  let releaseGate
  let markStarted
  let markDelivered
  let firstRequest = true
  const started = new Promise((resolve) => { markStarted = resolve })
  const released = new Promise((resolve) => { releaseGate = resolve })
  const delivered = new Promise((resolve) => { markDelivered = resolve })
  const pattern = '**/api/graph/spacetime**'
  const handler = async (route) => {
    // 切回 web 也会发 spacetime 请求；只门控目标 3D mount 发出的第一条，后续照常走。
    if (!firstRequest) {
      await route.continue()
      return
    }
    firstRequest = false
    markStarted()
    await released
    try {
      const response = await route.fetch()
      await route.fulfill({ response })
    } finally {
      markDelivered()
    }
  }
  await page.route(pattern, handler)
  return {
    started,
    delivered,
    release: releaseGate,
    dispose: () => page.unroute(pattern, handler),
  }
}

test.describe('谱系星图 · 图谱视图', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#year=750&route=graph')
    // 壳懒加载完成：标题「谱系星图」出现
    await expect(page.locator('.sm-title')).toContainText('谱系星图', { timeout: 15_000 })
  })

  test('B1 壳与三 tab 存在 + tab 状态进 URL', async ({ page }) => {
    const loaded3dResources = () => page.evaluate(() => {
      const targets = [
        '/src/starmap/engine/threePalette.js',
        '/src/starmap/engine/mount.js',
        '/node_modules/.vite/deps/three.js',
      ]
      return performance.getEntriesByType('resource')
        .map((entry) => new URL(entry.name, location.href).pathname)
        .filter((pathname) => targets.some((target) => pathname.endsWith(target)))
    })

    // 三 tab
    await expect(page.locator('.sm-tab[data-tab="web"]')).toContainText('图谱')
    await expect(page.locator('.sm-tab[data-tab="nebula"]')).toContainText('星云')
    await expect(page.locator('.sm-tab[data-tab="column"]')).toContainText('时空柱')
    // 默认 web 激活
    await expect(page.locator('.sm-tab[data-tab="web"]')).toHaveClass(/active/)
    await expect(page.locator('canvas.wg-canvas')).toBeVisible({ timeout: 15_000 })
    // Vite 会给模块 URL 追加 query；只比较 pathname，避免依赖预构建 hash。
    // 默认 2D 图谱不能预取 Three 适配器或 3D mount。
    await expect.poll(loaded3dResources).toEqual([])

    // 切到星云 -> 3D 画布出现 + URL 记忆 view=nebula
    await page.locator('.sm-tab[data-tab="nebula"]').click()
    await expect(page.locator('canvas.nebula-canvas')).toBeVisible({ timeout: 20_000 })
    // 正向钉子：进入星云后同一匹配器必须命中，证明上面的空集不是 URL 匹配失效。
    await expect.poll(async () => (await loaded3dResources()).length).toBeGreaterThan(0)
    await expect(page).toHaveURL(/view=nebula/)

    // 时空柱同理：3D 画布出现 + URL 记忆 view=column
    await page.locator('.sm-tab[data-tab="column"]').click()
    await expect(page.locator('canvas.column-canvas')).toBeVisible({ timeout: 25_000 })
    await expect(page).toHaveURL(/view=column/)

    // 切回图谱 -> 画布出现
    await page.locator('.sm-tab[data-tab="web"]').click()
    await expect(page.locator('canvas.wg-canvas')).toBeVisible({ timeout: 10_000 })
  })

  test('B2 图谱画布尺寸 ≥300×600', async ({ page }) => {
    const canvas = page.locator('canvas.wg-canvas')
    await expect(canvas).toBeVisible({ timeout: 15_000 })
    // 等画布有非零布局尺寸（ResizeObserver 已生效）
    await expect.poll(async () => {
      const b = await canvas.boundingBox()
      return b ? b.width : 0
    }, { timeout: 10_000 }).toBeGreaterThanOrEqual(600)
    const box = await canvas.boundingBox()
    expect(box.height).toBeGreaterThanOrEqual(300)
    expect(box.width).toBeGreaterThanOrEqual(600)
  })

  test('B3 选中实体后局部图渲染（canvas + 深度滑杆可操作）', async ({ page }) => {
    // URL 选中李白 -> 局部模式。
    // hash-only 变更不触发整页重载，而 App.vue 的 loadFromUrl 仅在挂载时跑一次，
    // 故先跳 about:blank 强制换文档，再导航到带 entity 的 URL，保证 loadFromUrl 生效。
    await page.goto('about:blank')
    await page.goto('/#year=750&route=graph&entity=p_li_bai')
    await expect(page.locator('.sm-title')).toContainText('谱系星图', { timeout: 15_000 })

    // debug.mode === 'local'
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.mode),
      { timeout: 15_000 },
    ).toBe('local')

    // canvas 存在且节点已渲染
    await expect(page.locator('canvas.wg-canvas')).toBeVisible()
    await expect.poll(
      () => page.evaluate(() => (window.__starmapDebug?.nodeCount || 0) > 0),
      { timeout: 15_000 },
    ).toBeTruthy()

    // EntityDetail 档案卡真正加载出内容（回归钉子：曾因 immediate watch 在 ref
    // 声明前触发 TDZ，整卡卡死"加载中"，而此前无用例断言卡内容故潜伏多个里程碑）
    await expect(page.locator('.ep-name')).toContainText('李白', { timeout: 15_000 })

    // 深度滑杆可见、可用、默认 1 跳
    const slider = page.locator('[data-testid="depth-slider"]')
    await expect(slider).toBeVisible()
    await expect(slider).toBeEnabled()
    await expect(slider).toHaveValue('1')

    // 键盘操作：ArrowRight 1->2，证明可操作
    await slider.focus()
    await slider.press('ArrowRight')
    await expect(slider).toHaveValue('2')
  })

  test('B4 路径查询 李白->岳飞 出现路径高亮状态', async ({ page }) => {
    // 打开路径面板(D1:裸 id 输入已升级为联想检索选实体)
    await page.locator('.wg-chip', { hasText: '路径' }).click()
    await expect(page.locator('[data-testid="path-from-input"]')).toBeVisible()

    // 起点:输入检索 -> 联想点选 -> chip 落定
    await page.locator('[data-testid="path-from-input"]').fill('李白')
    await page.locator('.wg-sugg li', { hasText: '李白' }).first().click()
    await expect(page.locator('.wg-pick-chip', { hasText: '李白' })).toBeVisible()
    // 终点同理
    await page.locator('[data-testid="path-to-input"]').fill('岳飞')
    await page.locator('.wg-sugg li', { hasText: '岳飞' }).first().click()
    await expect(page.locator('.wg-pick-chip', { hasText: '岳飞' })).toBeVisible()
    await page.locator('.wg-path button', { hasText: '查路径' }).click()

    // pathFound === true（结构化关系最短路 ≤4 跳存在）
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.pathFound),
      { timeout: 20_000 },
    ).toBeTruthy()
    // mode 进入 'path'
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.mode),
      { timeout: 10_000 },
    ).toBe('path')
    // 路径消息出现跳数
    await expect(page.locator('.wg-path-msg')).toContainText(/跳路径/)
  })

  test('B5 星云 tab -> webgl canvas + nebulaReady + stars>500', async ({ page }) => {
    // 切星云 tab：three 引擎懒加载、画布(webgl) 出现
    await page.locator('.sm-tab[data-tab="nebula"]').click()
    await expect(page.locator('canvas.nebula-canvas')).toBeVisible({ timeout: 25_000 })

    // 引擎就绪：layout 沉降 + reveal 完成
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.nebulaReady),
      { timeout: 30_000 },
    ).toBe(true)

    // 入图星数 > 500（spacetime 全量 links≥1 实体，约 1100）
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.nebulaStars || 0),
      { timeout: 10_000 },
    ).toBeGreaterThan(500)
  })

  test('B5a 星云与时空柱画布填满宽屏可用高度', async ({ page }) => {
    // 真机问题出现在 1988×1280 一类宽屏：3D 内容只占上半屏，下半屏留空。
    // 几何验收以 StarmapView 的内容区为基准，工具条之外的 stage/canvas 应一直
    // 延伸到内容区底部；这同时钉住 tab 切换后异步组件的尺寸重算。
    await page.setViewportSize({ width: 1988, height: 1280 })
    await page.reload()
    await expect(page.locator('.sm-title')).toContainText('谱系星图', { timeout: 15_000 })

    for (const view of [
      { tab: 'nebula', stage: '.nv-stage', canvas: 'canvas.nebula-canvas' },
      { tab: 'column', stage: '.cv-stage', canvas: 'canvas.column-canvas' },
    ]) {
      await page.locator(`.sm-tab[data-tab="${view.tab}"]`).click()
      const canvas = page.locator(view.canvas)
      await expect(canvas).toBeVisible({ timeout: 30_000 })
      const geometry = async () => {
        const [appBodyBox, bodyBox, stageBox, canvasBox] = await Promise.all([
          page.locator('.app-body-graph').boundingBox(),
          page.locator('.sm-body').boundingBox(),
          page.locator(view.stage).boundingBox(),
          canvas.boundingBox(),
        ])
        if (!appBodyBox || !bodyBox || !stageBox || !canvasBox) return null
        return {
          appBodyBottomGap: Math.abs(1280 - (appBodyBox.y + appBodyBox.height)),
          bodyViewportRatio: bodyBox.height / 1280,
          stageBodyRatio: stageBox.height / bodyBox.height,
          stageBottomGap: Math.abs(stageBox.y + stageBox.height - (bodyBox.y + bodyBox.height)),
          canvasTopGap: Math.abs(canvasBox.y - stageBox.y),
          canvasBottomGap: Math.abs(canvasBox.y + canvasBox.height - (stageBox.y + stageBox.height)),
        }
      }
      await expect.poll(async () => (await geometry())?.appBodyBottomGap ?? Infinity,
        { timeout: 10_000 }).toBeLessThanOrEqual(1)
      await expect.poll(async () => (await geometry())?.bodyViewportRatio ?? 0,
        { timeout: 10_000 }).toBeGreaterThanOrEqual(0.75)
      await expect.poll(async () => (await geometry())?.stageBottomGap ?? Infinity,
        { timeout: 10_000 }).toBeLessThanOrEqual(1)
      await expect.poll(async () => (await geometry())?.canvasTopGap ?? Infinity,
        { timeout: 10_000 }).toBeLessThanOrEqual(1)
      await expect.poll(async () => (await geometry())?.canvasBottomGap ?? Infinity,
        { timeout: 10_000 }).toBeLessThanOrEqual(1)
      await expect.poll(async () => (await geometry())?.stageBodyRatio ?? 0,
        { timeout: 10_000 }).toBeGreaterThanOrEqual(0.85)
    }
  })

  test('B5c 星云与时空柱装配中切走会释放晚到控制器', async ({ page }) => {
    await expect(page.locator('canvas.wg-canvas')).toBeVisible({ timeout: 15_000 })
    await page.evaluate(() => {
      // 测试侧只记录 DEV 生命周期事件；组件不会为验证污染正常 Vue/debug 状态。
      window.__starmapLateDisposals = []
      window.addEventListener('starmap:late-dispose', (event) => {
        window.__starmapLateDisposals.push(event.detail?.view)
      })

      // WebGraph 重挂载会整体替换 __starmapDebug。代理每一代对象，记录 ready 字段
      // 在“已切回 web”之后是否仍被 3D 组件晚到写入。
      const readyWrites = []
      const wrap = (value) => new Proxy(value || {}, {
        set(target, key, next) {
          if (key === 'nebulaReady' || key === 'columnReady') readyWrites.push({ key, value: next })
          return Reflect.set(target, key, next)
        },
      })
      let current = wrap(window.__starmapDebug)
      Object.defineProperty(window, '__starmapDebug', {
        configurable: true,
        get: () => current,
        set: (value) => { current = wrap(value) },
      })
      window.__starmapReadyWrites = readyWrites
    })

    for (const view of [
      { tab: 'nebula', canvas: 'canvas.nebula-canvas', readyKey: 'nebulaReady' },
      { tab: 'column', canvas: 'canvas.column-canvas', readyKey: 'columnReady' },
    ]) {
      const gate = await installSpacetimeGate(page)
      const globalGraphReady = view.tab === 'nebula'
        ? page.waitForResponse((response) => response.url().includes('/api/links/global') && response.status() === 200)
        : Promise.resolve()

      await page.locator(`.sm-tab[data-tab="${view.tab}"]`).click()
      // 请求已经进入 mount await；星云另一份并行数据也先到齐，确保放行后必走晚到 controller 分支。
      await Promise.all([gate.started, globalGraphReady])
      await page.locator('.sm-tab[data-tab="web"]').click()
      await expect(page.locator('canvas.wg-canvas')).toBeVisible({ timeout: 15_000 })

      // 清掉 onBeforeUnmount 合法写入的 false；此后任何 ready 写入都属于晚到副作用。
      await page.evaluate(() => { window.__starmapReadyWrites.length = 0 })
      gate.release()
      await gate.delivered

      // 事件由“晚到控制器已 dispose”分支同步发出，是受控完成信号，不以 sleep 猜测异步状态。
      await expect.poll(
        () => page.evaluate((tab) => window.__starmapLateDisposals.filter((v) => v === tab).length, view.tab),
        { timeout: 15_000 },
      ).toBe(1)
      await expect(page.locator(view.canvas)).toHaveCount(0)
      expect(await page.evaluate((key) => window.__starmapDebug?.[key], view.readyKey)).not.toBe(true)
      expect(await page.evaluate((key) => window.__starmapReadyWrites.filter((w) => w.key === key), view.readyKey)).toEqual([])
      await gate.dispose()
    }
  })

  test('B5b 朝代颜色与雾环扇区按稳定 id 映射,不受 API 数组下标影响', async ({ page }) => {
    const result = await page.evaluate(async () => {
      const m = await import('/src/starmap/engine/inkPalette.js')
      const threePalette = await import('/src/starmap/engine/threePalette.js')
      const column = await import('/src/starmap/engine/columnMount.js')
      const hex = (c) => `#${c.getHexString()}`
      return {
        colors: {
          qin: m.dynastyHexById('d_qin'),
          song: m.dynastyHexById('d_song'),
          qing: m.dynastyHexById('d_qing'),
          xia: m.dynastyHexById('d_xia'),
          neutral: m.NEUTRAL_DYNASTY_HEX,
        },
        sectors: {
          qin: m.dynastySectorIndexById('d_qin'),
          song: m.dynastySectorIndexById('d_song'),
          qing: m.dynastySectorIndexById('d_qing'),
          xia: m.dynastySectorIndexById('d_xia'),
        },
        fog: {
          qin: column.fogAngleForNode('same_entity', 'd_qin'),
          xia: column.fogAngleForNode('same_entity', 'd_xia'),
          xiaAgain: column.fogAngleForNode('same_entity', 'd_xia'),
        },
        // 故意给秦一个错误的数组 idx=3；着色必须只认 dynasty id。
        qinFromNode: hex(threePalette.dynastyColorFn({ dynasty: 'd_qin', dynastyIdx: 3 })),
      }
    })
    expect(result.colors.qin).toBe('#c4a25f')
    expect(result.colors.song).toBe('#81b446')
    expect(result.colors.qing).toBe('#844aa5')
    expect(result.qinFromNode).toBe(result.colors.qin)
    expect(result.colors.xia).toBe(result.colors.neutral)
    expect(result.sectors).toEqual({ qin: 0, song: 9, qing: 13, xia: null })
    expect(result.fog.xia).toBe(result.fog.xiaAgain)
    expect(result.fog.xia).toBeGreaterThanOrEqual(0)
    expect(result.fog.xia).toBeLessThan(Math.PI * 2)
    expect(result.fog.qin).toBeGreaterThan(-Math.PI / 14)
    expect(result.fog.qin).toBeLessThan(Math.PI / 14)
  })

  test('B6 时空柱 tab -> columnReady + columnThreads>2000', async ({ page }) => {
    // 切时空柱 tab：three 引擎懒加载、画布(webgl) 出现
    await page.locator('.sm-tab[data-tab="column"]').click()
    await expect(page.locator('canvas.column-canvas')).toBeVisible({ timeout: 25_000 })

    // 引擎就绪（场景搭建 + 首帧渲染）
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.columnReady),
      { timeout: 30_000 },
    ).toBe(true)

    // 光丝总数 > 2000（有坐标的 Person，spacetime with_geo≈78.6%）
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.columnThreads || 0),
      { timeout: 10_000 },
    ).toBeGreaterThan(2000)

    // T3.5：关联弧计数桩（选中弧 + 常态脉络弧，恒 ≥0）
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.columnArcs ?? -1),
      { timeout: 10_000 },
    ).toBeGreaterThanOrEqual(0)

    // T3.5：左下角图例存在（光丝/环/点 三行）
    await expect(page.locator('.cv-legend')).toBeVisible()

    // 时空柱的盘/光丝颜色也必须走同一份 id 映射，不再拿 API 顺序当色板顺序。
    const colors = await page.evaluate(() => window.__starmapDebug?.columnDynastyColors)
    expect(colors.d_qin).toBe('#c4a25f')
    expect(colors.d_song).toBe('#81b446')
    expect(colors.d_qing).toBe('#844aa5')
    expect(colors.d_xia).toBe('#9aa4b2')
  })

  test('B7 时空柱装配期年份变化不丢失,柱外年份隐藏扫描环并诚实提示', async ({ page }) => {
    await page.locator('.sm-tab[data-tab="column"]').click()
    // 在 three 动态 import / API 装配尚未完成时改变年份，复现旧 watch 注册过晚的窗口。
    await page.evaluate(() => {
      window.location.hash = '#year=1600&route=graph&view=column'
    })
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.columnReady),
      { timeout: 30_000 },
    ).toBe(true)
    await expect(page.locator('.cv-count')).toContainText('1600')
    await expect(page.locator('.cv-outside')).toHaveCount(0)
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.columnScan?.visible),
    ).toBe(true)

    await page.evaluate(() => {
      window.location.hash = '#year=-2100&route=graph&view=column'
    })
    await expect(page.locator('.cv-count')).toContainText('-2100')
    await expect(page.locator('.cv-outside')).toContainText('柱轴范围外')
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.columnScan?.visible),
    ).toBe(false)

    await page.evaluate(() => {
      window.location.hash = '#year=1600&route=graph&view=column'
    })
    await expect(page.locator('.cv-outside')).toHaveCount(0)
    await expect.poll(
      () => page.evaluate(() => window.__starmapDebug?.columnScan?.visible),
    ).toBe(true)
  })
})
