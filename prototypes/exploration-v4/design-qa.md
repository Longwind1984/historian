# Exploration v4 浏览器批注轮 · 设计 QA

## 对照与归一化

- 源视觉真相：`/Users/rick/ZCodeProject/history-kb/prototypes/exploration-v4/qa-book-only-flow-fanout-1440-final.png`，即用户本轮九条浏览器批注所针对的上一版书籍工作台。
- 批注原视口实现：`/Users/rick/ZCodeProject/history-kb/prototypes/exploration-v4/qa-annotation-round-1117-final.png`。
- 宽屏实现：`/Users/rick/ZCodeProject/history-kb/prototypes/exploration-v4/qa-annotation-round-1440-final.png`。
- 全视图并排证据：`/Users/rick/ZCodeProject/history-kb/prototypes/exploration-v4/qa-compare-annotation-round.png`，左为上一版，右为本轮实现。
- 聚焦对照：`/Users/rick/ZCodeProject/history-kb/prototypes/exploration-v4/qa-compare-annotation-round-focus.png`，检查顶部行数与右下输入区。
- 关键状态：`/Users/rick/ZCodeProject/history-kb/prototypes/exploration-v4/qa-annotation-round-logic-open-1440.png`、`/Users/rick/ZCodeProject/history-kb/prototypes/exploration-v4/qa-annotation-round-player-open-1440.png`。
- 源图与宽屏实现均为 1440 × 1024 px，CSS viewport 1440 × 1024，deviceScaleFactor 1，无密度换算。
- 用户批注视口为 1117 × 837 px，实现截图、CSS viewport 与像素尺寸均为 1117 × 837，deviceScaleFactor 1。
- 对照状态：澄主题、内置阅读器、正文、第一段、1942.02 Scene、地图播放收起、产品旁注关闭。

## Findings

最终轮没有遗留可行动的 P0 / P1 / P2。

### 已修复

- [P2] 无地点 Scene 继承高亮上一地点。
  - 位置：左栏「时间 · 事件柱」选择 1944「材料核对与经验总结」后。
  - 首轮证据：顶部和地图已切到 1944，但 `.map-point.active` 仍为 1，延安会被误读为本场景地点。
  - 修复：无可靠地点的 Scene 保留上一视野与文字说明，但不激活任何地点。
  - 复验：`.map-point.active=0`；地图浮窗明确显示“本 Scene 没有单一可靠地点，地图没有猜测落点”。

- [P2] 正文段落不可通过 Tab 直接到达。
  - 位置：内置阅读器正文。
  - 首轮证据：三个段落按钮均为 `tabIndex=-1`。
  - 修复：恢复原生按钮 Tab 顺序，同时保留逻辑节点回跳后的程序化聚焦。
  - 复验：三个段落 `tabIndex` 均为 0；逻辑节点“回到原文”后，目标段落得到焦点并高亮。

- [P2] 分栏拖动可能丢失 pointerup 前的末段位移。
  - 位置：两条 `role=separator` 分栏边界。
  - 修复：pointerup 消费最终 `clientX` 与上次事件之间的差值；键盘与双击复位保留。
  - 复验：键盘 ArrowRight 把阅读栏 280 → 292 px，中央 525 → 513 px，页面宽度仍为 1117；双击恢复 280 px。浏览器自动化的低层拖动事件没有提供稳定的连续 pointermove，真实鼠标拖动仍需人工补验。

## 全视图比较

- 顶部从三行压成两行：全局导航下只保留一条书籍工作栏。上一版独立的“书籍探索 / 当前研究 / 已自动保存”行被删除，书名、范围、本地状态与保存动作合并到书籍栏。
- 常驻播放 dock 完全退出页面流；地图吸收释放出的高度。默认只露出“播放脉络”次级入口，主动展开时控制停留在地图左下，不改变三栏骨架。
- 左栏由“两种来源”升级为“内置阅读器 / 网页来源 / 时间 · 事件柱”，内置阅读器再提供“正文 / 锚点”二级切换。
- 右栏删掉重复的当前段落摘要和提问说明，底部改为 `+ / 输入 / 发送` 一体式 composer；证据列表获得稳定滚动区。
- 两条 6 px 分栏边界把三栏从固定比例改成可调整阅读视野；1117 × 837 与 1440 × 1024 均无页面级横向或纵向溢出。

## 聚焦区域比较

- 逻辑结构：所有节点都是可操作按钮。展开层明确显示“作者论证摘要 / 作者观察 / 待复核 Scene / 实体集合”等认识论状态，并提供“回到原文”；展开层覆盖论证区，不挤压地图和三栏。
- 阅读器：正文保持连续排版和段落锚点，不再把锚点元信息作为独立空行常驻；锚点视图按时间、论点列出三个定位入口，选择后回到正文并同步 Scene。
- 时间事件柱：点击 1944 后，左栏当前项、顶部时间、地图标题和浮窗同帧更新；无地点时没有继承高亮点。
- 地图播放：默认无常驻控制；打开后具备收起、上一步、播放/暂停/重播、下一步、0.5× / 1× / 1.5× 和当前进度。1.5× 从第 5 幕推进到第 6 幕后，顶部、地图与左栏事件柱一致显示 1945.04，并进入重播状态。
- Composer：`+` 菜单包含添加摘录、添加外部材料、关联人物事件；“添加摘录”会切回内置阅读器、把当前论点写入输入框并聚焦，提交后清空输入。
- 文案：地图只保留“材料关联”，完整“非移动路线”语义进入 `title` 与 `aria-label`；输入区不再显示“向这本书提出一个历史问题”等自解释文案。

## 必查表面

- 字体与排版：继续使用 Noto Serif SC / Songti SC / STSong / SimSun 回退；书名、论证标题、地图 Scene、证据标题和正文层级未漂移。1117 宽度的左栏 tab 和状态仍完整可读。
- 间距与布局：保留纸本式高密度、细分隔线、小圆角和低阴影；顶部少一行后工作空间起点从 y=174 提升到 y=108。1117 下默认栏宽为 280 / 525 / 300，1440 下为 280 / 848 / 300。
- 颜色与 token：米白、墨灰、朱砂、青灰和绿色状态沿用上一版；夜主题往返后背景 `rgb(21,25,29)`、正文 `rgb(235,228,216)`，无溢出或控件消失。
- 图片质量：继续使用同一书封与历史 raster 地图；1440 截图中书封 naturalWidth=72，地图清晰填满剩余舞台。没有用 CSS 假地图、内联 SVG 或占位插图代替资产。
- 文案与内容：删除模式解释、地图长说明、重复段落摘要和 composer 标签；保留“作者论证摘要 / 版本待绑定”等真实性边界。
- 图标：使用已安装的 Phosphor 2.1.10；Plus、Quotes、Link、UsersThree、TextAlignLeft、ListBullets、ClockCounterClockwise 与既有搜索、播放、主题图标同族，纯图标按钮均有可访问名称。
- 状态与交互：正文 / 锚点、三来源 tab、逻辑详情、原文回跳、时间事件柱、地图播放、composer 菜单与发送、澄 / 夜均实际操作。
- 可访问性：分栏为有名称的垂直 separator，支持方向键和焦点态；正文段落、逻辑节点、播放、来源、composer 菜单都可通过语义控件到达。
- 响应性：1117 × 837 的 `scrollWidth/scrollHeight` 与 viewport 完全相等；1440 × 1024 同样无页面溢出。低于 980 px 不属于本隔离桌面原型范围。

## 构建、浏览器与性能

- `npm run build`：最终复跑通过；Vite 6.4.2，4570 modules，1.21s。
- 产物：JS 326.29 kB / gzip 99.23 kB；CSS 44.47 kB / gzip 8.45 kB。
- `npm run test:sites`：4 / 4 通过。
- 浏览器 console：最终 error 0、warning 0。
- 没有新增依赖或网络请求。新增状态均为局部 React state；Canvas 仍只在容器尺寸、DPR 或路线方案变化时重绘，不运行常驻逐帧动画。

## 比较历史

1. 第一轮完成两行顶栏、阅读器/事件柱、逻辑回跳、地图次级播放、可调三栏与 composer；同视口首次实看发现无地点继承高亮、正文 Tab 不可达和拖动末段位移风险。
2. 第二轮修复上述三项；1117 复验确认无地点 active pin 为 0、正文段落 Tab 可达、分栏键盘调整与双击复位生效。
3. 最终全视图和顶栏/composer 聚焦对照没有遗留 P0 / P1 / P2；关键展开状态单独截图确认，没有以默认态截图代替交互验收。

## Follow-up Polish

- P3：若生产需要覆盖 980 px 以下桌面或平板，应另做紧凑布局，不继续压缩当前三栏。
- P3：在生产 E2E 中用真实 PointerEvent 序列补一条分栏拖动回归；当前浏览器验收已覆盖键盘调整与复位。
- P3：真实正文导入后，用版本、章节、段落 ID 和页码替换原型摘要；在此之前继续公开“版本待绑定”。

final result: passed
