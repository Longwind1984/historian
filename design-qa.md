# 探索 v9 ·《安史之乱》公开受限 Demo 设计验收

## 对照真值与实现证据

- 改造前《红太阳》阅读态：`docs/design-qa/exploration-v9/history-kb-anshi-source-reader-1280x720.png`
- 改造后《安史之乱》受限阅读态：`docs/design-qa/exploration-v9/history-kb-anshi-implementation-1280x720.png`
- 同视口并排：`docs/design-qa/exploration-v9/history-kb-anshi-comparison-2564x720.png`

参考与实现均为 1280 × 720、夜色主题、桌面三栏、阅读 tab、首幕 Scene。并排图同时包含书目状态、阅读窗口、论证链、地图、证据栏和播放入口，不以不同视口或不同交互状态替代比较。

## Findings

- P0：0
- P1：0
- P2：0

公开示例已从地理推进不明显、传播风险更高的旧书切换为安史之乱九幕时空叙事。视觉密度维持原工作台尺度，新增内容没有挤压地图或打破三栏层级。

## 五项视觉面与交互复核

- 字体：书名、论证标题和 Scene 标题继续使用既有宋体层级；地图浮窗标题没有重新放大成突兀的独立字号。
- 间距：阅读栏独立滚动，九个定位不会拉长整页；中央 Brief、论证和地图仍可调，1280 × 720 下地图保持可读高度。
- 颜色：沿用澄 / 夜 token；`restricted` 只以克制标签提示，不用大片遮罩或马赛克制造视觉噪声。
- 资产：地图继续复用 MapLibre 与 1908 历史参考层；地点不足的 Scene 不绘制假坐标或直虚线。
- 文案：界面明确区分“原创衍生摘要”“章节级定位”“原文未公开”，右栏不机械制造正反观点。
- 交互：论证节点可展开并回到对应受限锚点；Scene 选择同步年份、地图、证据和播放。潼关—灵宝等无坐标 Scene 会清除上一幕高亮。

## 安全边界

- 当前 `0 / 10` 页通过权利审查；10 页只是未来公开窗口上限，不是法律安全线。
- 原文、私有 locator、包内 href、哈希和本机路径不进入 DOM、Pinia、localStorage、网络响应或构建数据。
- “打码”通过数据不下发实现，不靠 CSS 隐藏已经传到浏览器的正文。

## 验证

- `npm run build`：215 modules，1.50s；`ExplorationView` 43.40 kB / gzip 16.30 kB。
- 后端：217 passed，1 skipped；数据：`errors=0`。
- 探索专项：7 passed；全量 E2E：110 passed，1 skipped。
- safe profile 专项：1 passed；受限地图入口、图集请求和公开 Demo 原文均未泄露。
- 应用内浏览器：论证回跳、受限锚点、无坐标 Scene 与刷新后 console 复验通过。

final result: passed
