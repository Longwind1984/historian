# 2026-07-23 · 高密度界面优化视觉验收

## 验收范围

本轮核对用户点名的 8 项桌面与移动端交互：悬停误触、地图默认值与折叠控件、澄/夜主题、时间尺度、图标、搜索入口、人物筛选，以及星云/时空柱的下半屏留白。参考图不是重做视觉风格的目标，而是问题发生时的画面；验收保持现有纸墨、印章与古地图语言，只判断交互和布局是否收口。

## 视觉证据

- 问题参考图：`docs/design-qa/source-nebula-height-issue.png`
- 当前同状态实现：`docs/design-qa/implementation-nebula-full-height.jpg`
- 同视口并排图：`docs/design-qa/comparison-nebula-height.png`
- 时间柱默认折叠态：`docs/design-qa/implementation-timeline-controls.jpg`
- 390×844 移动端默认态：`docs/design-qa/implementation-mobile-drawer.jpg`

源图为 2940×1846 Retina 截图，比较前归一到 1470×923；实现截图为 1470×923 CSS 视口、device scale factor 1。两边均为澄主题、谱系星图 → 星云、1637 年、选中“联蒙灭金”并打开右侧档案。

## Findings

- 已关闭 P1：星图内容区曾自动排到 Grid 的第二行 `auto` 轨道，3D stage 只占上半屏。当前 `.app-body` 固定在第三行并允许收缩；实测 app body、stage 与 canvas 底部均到达 923px 视口底部，星云与时空柱的宽屏 E2E 同时覆盖。
- 已关闭 P1：悬停曾会误换右侧档案。当前 hover/focus 只更新跨区视觉高亮，click/Enter/Space 才改变正式选中；程序滚动期与落定后 400ms 仍抑制误触高亮。
- 已关闭 P2：地图图层、人物类型与时间尺度长期占位。三者默认折叠；“重点人物”、当前“帝王”尺度和地图展开键保留在外层。地图工具在左上、MapLibre 缩放控件在左下，实测重叠面积为 0。
- 已关闭 P2：问号、感叹号、搜索与地图“放”字的字形质量不一。当前统一使用已安装的 Lucide SVG 深导入；关键圆形按钮中心偏差不超过 1px，地图展开按钮不再含“放”字。
- 已关闭 P2：移动端首屏控制拥挤且隐藏地图仍付加载成本。390px 下保持一行顶部与折叠筛选，时间柱为主屏，详情为底部抽屉；首次主动展开前不请求 MapLibre，之后复用同一实例。

## 五项视觉面复核

- 字体与层级：沿用现有宋体/系统字体组合，标题、正文、微型控件的字重和行高未漂移；没有出现新的截断或错行。
- 间距与布局：桌面 1470×923、宽屏 1988×1280、移动 390×844 均完成实拍或几何回归；星图、地图和底部抽屉没有溢出视口。
- 颜色与 token：只保留澄/夜两套；系统深浅色变化会实时同步，缺少 `matchMedia` 时按本地 06:00/18:00 降级。明暗两态浏览器控制台均无 error/warning。
- 图像与图标：谭其骧图集保持原始栅格；UI 图标全部来自现有 Lucide 库，不用文字、emoji 或手工 SVG 冒充。
- 文案与内容：按钮可访问名称保留完整动作语义；界面本身不增加“悬停预览”等解释性文案。

## 交互与可访问性验证

已实际操作主题切换、返回时间柱、折叠控件、实体选中与移动端响应式切换，并检查浏览器控制台。键盘路径、搜索 combobox、时间柱人物、地图图例、底部抽屉与弹层焦点由完整 E2E 覆盖。截图只能证明可见状态，不能单独证明屏幕阅读器完整兼容；这里不声称全站 WCAG 合规。

## 比较历史

1. 参考图：星图 stage 在约半屏处结束，下方为大块空白。
2. 修复：主内容固定到 Grid 第三行，3D 容器继续使用 ResizeObserver 适配可用高度。
3. 复核：1470×923 实拍中 stage/canvas 到达视口底部；1988×1280 下星云与时空柱几何回归通过。没有剩余 P0/P1/P2。

## Follow-up Polish

- 选中星体时非邻域节点会按既有 focus 模式淡至 8%；这是谱系星图设计中的主动聚焦，不属于本轮留白缺陷。若以后要调整，应以独立可见草案比较 8% / 12% / 16%，不要混入本次高度修复。

## 2026-07-23 · 地图历史播放增量验收

- 桌面 1440×900：`docs/design-qa/implementation-map-story-desktop.jpg`
- 移动 390×844：`docs/design-qa/implementation-map-story-mobile.jpg`

桌面主体态中，播放条位于地图底部中央，简介卡位于右下；与左下缩放控件、右上年份图例和右下署名均无重叠。移动抽屉的地图净高较小，首版四行摘要使年份眉题被顶部裁切；最终移动样式保留完整年份、标题、单行简介与来源，播放条和缩放控件仍可见，桌面继续保留四行简介。两张截图均为 751 年「怛罗斯之战」播放态；可见状态之外的 5.2 秒自动推进、左轴联动和暂停边界由 `frontend/e2e/map-story.spec.js` 证明。

final result: passed

# 2026-07-27 · v4 书籍探索生产实现验收

## 验收对象与同视口证据

批准原型与生产实现均由应用内浏览器在相同 CSS 视口、device scale factor 1 下截取，并置入同一张比较图复核，不以单张截图代替比较：

- 1117 × 837 原型：`prototypes/exploration-v4/qa-annotation-round-1117-final.png`
- 1117 × 837 实现：`docs/design-qa/exploration-v4-production/implementation-1117x837.jpg`
- 1117 × 837 并排：`docs/design-qa/exploration-v4-production/comparison-1117x837.png`
- 1440 × 1024 原型：`prototypes/exploration-v4/qa-annotation-round-1440-final.png`
- 1440 × 1024 实现：`docs/design-qa/exploration-v4-production/implementation-1440x1024.jpg`
- 1440 × 1024 并排：`docs/design-qa/exploration-v4-production/comparison-1440x1024.png`
- 1440 × 1024 夜色：`docs/design-qa/exploration-v4-production/implementation-night-1440x1024.jpg`
- 390 × 844 移动时空视图：`docs/design-qa/exploration-v4-production/implementation-mobile-map-390x844.jpg`

不另截局部图：三栏、论证链、地图、浮窗、证据区和 composer 在两张并排全屏图中已经同时可见；交互后的逻辑详情、播放面板与私人导入空态由 E2E 状态证据覆盖。

## 五项视觉面复核

- 字体与层级：沿用现有宋体、系统字体、印章与纸墨 token；全局导航和书籍工作栏共两行，没有恢复被否决的模式栏、Presenter Card 或产品讲稿。
- 间距与布局：1117 与 1440 桌面均保持阅读 / 中央叙事 / 关系证据三栏；分隔边界清晰但不抢视觉。390 移动端改为阅读 / 时空 / 出处三视图，地图吸收剩余高度，没有桌面 composer 或导入编排挤入窄屏。
- 颜色与主题：澄 / 夜两态均保留同一信息层级；夜色中的历史栅格降低亮度与不透明度，文字、当前地点、Scene 浮窗和地图控件仍可辨认。
- 地图与关系：生产版没有使用原型生成的静态背景图，而是复用 MapLibre 和现有 1908 配准历史图层，明确标注「历史地理参考 · 1908 · 非当前疆界」。材料关系使用中性材料 hub 向地点分别发散的连续双层 Bézier，不用直虚线、箭头或地点串联；safe profile 在构建期完全移除该历史图层 source。
- 文案与内容：示范书所有段落都标明作者论证摘要 / 版本待绑定；导入任意 TXT / Markdown 后，时间、地点、论证与证据回到未结构化空态，不沿用延安样本，也不生成伪页码或伪引文。

## 交互、可访问性与状态

- 逻辑节点可展开详情并返回绑定段落；左栏正文 / 锚点 / 时间·事件柱 / 网页来源共享同一选择。
- 播放入口默认退在地图内；展开后可播放、暂停、步进、变速，Scene、顶部纪年与时间状态同步，拖图立即暂停；无地点 Scene 清除地点与关系覆盖层并保留最近有效视野。
- 两条分栏可用鼠标、方向键、Home / End 和双击复位；移动端不挂载隐藏地图，只有进入「时空」才加载。
- 右栏 `+ / 输入 / 发送` 只在真实私人导入后记录问题；当前明确显示未调用模型。API revision 冲突返回 409，不静默覆盖。
- 1117、1440、390 与夜色状态的浏览器 console 最终均为 error 0、warning 0；本轮不声称未经独立审计的全站 WCAG 合规。

## 比较结论与有意差异

生产实现保留了获批原型的页面定位、两行顶部、三栏职责、论证链、常驻地图、地图内次级播放和证据 composer。可见差异主要来自工程真实化：原型静态地图替换为可缩放的真实历史参考层；生产端只展示有本地坐标依据的地点，并把未复核关系明确标为材料关系；导入与 composer 从模拟控件变成真实后端会话。未发现剩余 P0 / P1 / P2 视觉缺陷。

final result: passed

# 2026-07-27 · v5 探索双入口、EPUB 与深度示例验收

## 验收对象与视觉证据

本轮解决的不是给既有书籍页补一个上传按钮，而是纠正产品默认前提：探索不再假定用户已经有书。生产入口现在从「历史问题」和「本地材料」两条等价路径开始，既有探索只作为可继续项出现。

- 改造前强制书籍态：`docs/design-qa/exploration-v5/01-current-book-state.jpg`
- 1440 × 1024 真空入口：`docs/design-qa/exploration-v5/02-empty-state-1440x1024.jpg`
- 1440 × 1024 Prompt 范围已确认态：`docs/design-qa/exploration-v5/03-prompt-scope-1440x1024.jpg`
- 1440 × 1024《红太阳》深度衍生示例：`docs/design-qa/exploration-v5/04-red-sun-demo-1440x1024.jpg`
- 390 × 844 示例移动阅读态：`docs/design-qa/exploration-v5/05-red-sun-mobile-390x844.jpg`
- 改造前后并排：`docs/design-qa/exploration-v5/06-before-after-1440x1024.jpg`

## 产品状态复核

- 真空入口：没有书时可直接写历史问题；有 TXT、Markdown 或 EPUB 时可本地导入；示例是第三入口，不再冒充用户当前书籍。
- Prompt 路径：服务端先建立范围合同与证据缺口，不调用模型。用户确认时间、空间与主线后，顶栏、Brief、关系栏和地图 Scene 同帧显示「范围已确认」；无可靠地点时不猜坐标。
- EPUB 路径：浏览器按二进制读取并提交独立 EPUB adapter；后端解析容器、OPF/spine、章节和段落锚点。阅读器只渲染当前章节，滚动或点段落以串行 revision mutation 更新阅读位置。
- 微信读书：第三方页面默认不加载；用户主动打开后才尝试 iframe。跨域环境不读取正文、选区或滚动进度，章节/百分比和可选摘录通过用户确认的手动桥接写入当前探索，不声称自动实时同步。
- 深度示例：示例只保留五条章节级作者判断主线、六幕平台 Scene 编排、关系候选与证据缺口，并明确显示「内置衍生示例 / 不含原书」。作者判断和平台编排分层，版本、页码、段落与独立材料未核前不伪装成已审计事实。

## 视觉与交互复核

- 入口仍使用现有纸墨、印章和澄/夜 token，不新增产品说明页；两条主入口用同等卡片层级，主要动作一眼可见。
- 问题态左栏承担研究问题，中央承担结构与 Scene，右栏承担范围合同和后续追问；确认后没有残留「等待范围确认」的冲突状态。
- 示例桌面保留获批的可调三栏、逻辑节点回跳、MapLibre 历史参考图、连续柔性材料关系和地图内次级播放；移动端保持阅读 / 时空 / 出处三视图。
- EPUB 章节切换不会把 4,445 段全文同时挂到 DOM；滚动热路径使用段落索引缓存，不随每次事件重新展平整本书。
- 应用内浏览器不支持自动化文件选择，因此真实本机 EPUB 由后端 opt-in 测试验证；浏览器端二进制 adapter、章节窗口和进度联动由隔离 E2E 验证。两层证据不互相冒充。

## 验收结论

1440 × 1024 与 390 × 844 实拍均无页面横向溢出；Prompt 的 confirmed 状态、示例工作台和移动阅读层级一致。最终专项 E2E 覆盖真空入口、失败草案、Prompt hydration、EPUB adapter、微信读书手动桥接、深度示例、逻辑回跳、播放和移动视图。未发现剩余 P0 / P1 / P2 视觉缺陷。

final result: passed

# 2026-07-27 · v6 探索入口与动态工作区验收

## 同视口比较证据

本轮直接以用户批注发生时的生产页面为参考，在应用内浏览器用同一 1280 × 720 CSS 视口、device scale factor 1 复核；单张截图只证明状态，最终判断来自并排图：

- 入口改造前：`docs/design-qa/exploration-v6/01-before-entry-1280x720.png`
- 工作台改造前：`docs/design-qa/exploration-v6/02-before-workspace-1280x720.png`
- 单一问题入口：`docs/design-qa/exploration-v6/03-after-entry-1280x720.png`
- 上传本地书籍弹层：`docs/design-qa/exploration-v6/04-after-upload-dialog-1280x720.png`
- 动态工作区默认态：`docs/design-qa/exploration-v6/05-after-workspace-default-1280x720.png`
- 论证区展开态：`docs/design-qa/exploration-v6/06-after-workspace-logic-expanded-1280x720.png`
- 入口前后并排：`docs/design-qa/exploration-v6/07-compare-entry-1280x720.jpg`
- 工作台与论证展开态并排：`docs/design-qa/exploration-v6/08-compare-workspace-expanded-1280x720.jpg`

## 可见结果与状态边界

- 入口从两张等权大卡收敛为一个问题输入区；“上传本地书籍”与主 CTA 同排常驻，格式缩到按钮下方，点击后进入独立 `aria-modal` 弹层。Esc、遮罩、取消和关闭按钮都能退出；上传没有被藏进 `+`。
- 探索入口的全局纪年区只显示“探索”。返回入口时不再把上一份工作区的“内置衍生示例 / 不含原书”状态带进空状态；示例工作台也删除无助于操作的“不含原书”短句，内容边界仍由“内置衍生示例”和版本待绑定文案承担。
- 中央默认实测为 Brief 约 92px、论证约 154px、地图约 354px；两条横向分隔器都可拖动、键盘调整、记忆比例和双击复位。论证区拉到最大时约 268px，地图容器仍保留 240px；非对称最小值在恰好相等的边界上有专项回归。
- 地图 Scene 浮窗标题从 17px 收到 12px，与工作台标题层级一致；地图、缩放控件、浮窗和播放入口在默认态与最小高度态均未互相遮挡。

## 视觉、交互与性能复核

- 纸墨色、宋体层级、印章、边框和现有 Lucide 图标保持不变；未新增说明页、独立产品模式或装饰资产。
- E2E 覆盖 Prompt hydration、上传弹层、EPUB 二进制导入、微信读书手动桥接、示例论证回跳、地图播放、移动三视图，以及两条横向分隔器的键盘变化和地图最小高度。
- 第一轮边界测试真实暴露：非对称分栏恰好落在 `hi === lo` 时被误判为“容器过窄”，地图只剩 190px。修正比较条件后同一测试通过；没有改断言或降低 240px 产品边界。
- 最终构建仍为 213 modules / 1.46s；`ExplorationView` 为 38.17 kB / gzip 14.77 kB，较 v5 增加约 1.32 kB / gzip 0.44 kB。新增运行开销仅为探索桌面工作台内两个 ResizeObserver，没有新增依赖，也不改变 MapLibre 按需加载。

未发现剩余 P0 / P1 / P2 视觉缺陷。

final result: passed

# 2026-07-27 · v7 微信读书网页栏收敛验收

## 同视口与状态证据

- 参考真值：本轮 Browser Comment 1—3 所附 1195 × 719 页面截图。
- 默认收起：`docs/design-qa/exploration-v7/implementation-1195x719-collapsed.png`
- 展开态：`docs/design-qa/exploration-v7/implementation-1195x719-expanded.png`
- 参考与实现均为 1195 × 719 CSS / 物理像素、device scale factor 1；内置示例、网页 tab 与已展开 iframe 状态一致。

同一轮多模态比较中同时检查了用户附图和实现截图。全屏足以辨认本次涉及的左栏字体、间距、边框、真实网页资产和全部文案；展开截图同时承担 focused state 证据。

## 发现、修复与复验

- 参考态有三个 P2：手动同步表单常驻压缩阅读面积；来源头与状态条重复解释能力边界；iframe 底部再次重复跨域说明。
- 修复后来源头、状态条和 iframe 跨域说明均不存在；“在原站打开”收进阅读窗口右下；“同步阅读位置”默认 `aria-expanded=false` 且表单不在 DOM，点击后展开并保持真实同步能力。
- 纸墨 token、宋体 / 系统字层级、边框节奏和真实微信读书 iframe 均保持；新入口只使用现有 Lucide 图标。默认态增加连续阅读面积，展开态仍局限在左栏滚动区，不改变三栏宽度或中央纵向比例。
- 1195 × 719 默认 / 展开两态均未发现剩余 P0 / P1 / P2。浏览器 console error 0。

## 自动验证

- `npm run build`：212 modules，1.62s；`ExplorationView` 37.75 kB / gzip 14.58 kB。
- `npm run test:e2e -- exploration-v5.spec.js`：4 passed，8.6s；覆盖旧文案缺席、默认折叠、ARIA 展开、真实手动 bridge mutation 和同步后保持展开。

final result: passed

# 2026-07-27 · v8 顶部控件与网页阅读高度验收

## 同视口与状态证据

- 参考真值：本轮 Browser Comment 1—3 所附 1195 × 719 页面截图。
- 满高默认态：`docs/design-qa/exploration-v8/implementation-1195x719-default.png`
- 同步展开态：`docs/design-qa/exploration-v8/implementation-1195x719-expanded.png`
- 参考与实现均为 1195 × 719 CSS / 物理像素、device scale factor 1；内置示例、网页 tab 与已加载 iframe 状态一致。

同一轮多模态比较中同时检查了用户附图和实现截图。全屏足以辨认顶部 3 个工具、左栏阅读窗口、同步 disclosure 和水平高度分隔；展开截图同时承担 focused state 证据。

## 发现、修复与复验

- 参考态有三个 P2：问号 / 感叹号圆钮质感与语义均弱；两枚主题色块含义不清；网页阅读窗口固定高度，无法利用或重新分配左栏空间。
- 修复后帮助 / 来源改为键盘与资料库 Lucide 图标，统一 28px 软方钮；澄 / 夜合并为一个显示当前状态的日月按钮。网页阅读默认占满左栏剩余高度，展开同步工具后才出现 6px 水平分隔。
- 分隔支持 pointer capture、ArrowUp / ArrowDown、Home / End、双击复位和比例记忆；折叠后恢复满高，同一 iframe DOM 保持不变。
- 初验发现网页 tab 的 `Globe` 组件缺少深导入并产生 Vue warning；补回后再拍，后续没有新的 console warning / error。
- 1195 × 719 默认 / 展开两态均未发现剩余 P0 / P1 / P2。

## 自动验证

- `npm run build`：214 modules，1.43s；`ExplorationView` 40.83 kB / gzip 15.65 kB。
- `npm run test:e2e -- ui-controls.spec.js exploration-v5.spec.js`：9 passed，13.4s；覆盖单一主题按钮、SVG 居中、系统主题回退、满高阅读、水平分隔、键盘调节、比例折叠恢复与 iframe 不重挂载。

final result: passed

# 2026-07-27 · v9《安史之乱》公开受限 Demo 验收

## 同视口比较证据

- 改造前《红太阳》阅读态：`docs/design-qa/exploration-v9/history-kb-anshi-source-reader-1280x720.png`
- 改造后《安史之乱》受限阅读态：`docs/design-qa/exploration-v9/history-kb-anshi-implementation-1280x720.png`
- 1280 × 720 并排比较：`docs/design-qa/exploration-v9/history-kb-anshi-comparison-2564x720.png`

三张证据均为夜色主题、桌面工作台、阅读 tab、首幕 Scene。多模态并排复核覆盖顶部书目状态、阅读窗口、论证链、地图卡片、证据栏和播放入口；没有用不同视口或不同 UI 状态掩盖版面差异。

## 产品与视觉复核

- Demo 已从地理移动弱、公开传播风险较高的旧示例，切换为跨河北、两京、河洛展开的安史之乱九幕时空叙事。
- 阅读栏完整保留九个稳定定位，但当前不显示任何原文；每个定位以“章节级定位 / 原文未公开”呈现，避免把无权公开的正文用 CSS 假打码。
- 论证节点可展开并一键回到对应受限锚点；同一次选择同步更新 Scene、顶部年份、地图、证据栏和播放次序。
- 地图只采用仓库已有且可核的地点坐标。潼关—灵宝、河阳—邙山保持无坐标状态，清除前一幕高亮并显示“地点待核”，没有画未经核实的行军线。
- 右栏不机械填充正反观点；“历史结构 / 材料互证 / 不同解释”是透镜，不等于每幕必须存在冲突材料。
- 1280 × 720 下三栏没有横向溢出，逻辑链和地图仍保有可读高度，阅读列表可独立滚动。与改造前相比，信息密度相近，但 Demo 的时间与空间推进更明显。

## 交互与安全复验

- 点击论证摘要后出现节点详情；点击“回到定位”返回“阅读窗口”，激活 `anshi-anchor-hebei`，`data-access-state=restricted`。
- 时间 tab 切至第三幕后，顶部年份与地图标题同步为 756；无可靠坐标的 Scene 显示明确空态，不残留人物移动或路线文案。
- 浏览器正文、Pinia 状态、localStorage 与网络断言均检查原书路径、包内 href、原文和私有分析标识为零泄露。
- 最终刷新后浏览器 console 无新增 warning / error。

## 自动验证

- `npm run build`：215 modules，1.50s；状态收口后 `ExplorationView` 43.40 kB / gzip 16.30 kB。相较初版重复状态实现减少 2.37 kB / gzip 0.67 kB；MapLibre 仍为按需 chunk。
- 后端：217 passed，1 skipped；数据校验 `errors=0`。
- 探索专项：7 passed；覆盖公开身份、受限回跳、Scene / 年份 / 地图联动、播放、移动端和私人 / 公开状态隔离。
- 全量 E2E：110 passed，1 skipped / 4.8m；既有时间柱、地图、谱系、移动端与 safe profile 合同没有回归。
- `VITE_RESTRICTED_MAPS=0` safe 专项：1 passed / 10.8s；不暴露 CHGIS / 谭图入口，也不泄露公开 Demo 原文。

未发现剩余 P0 / P1 / P2 视觉或交互缺陷。当前 0 / 10 页通过权利审查是有意发布边界，不是缺失的 UI。

final result: passed

# 2026-07-28 · v10 地图全览、时间参照轴与论证图验收

## 1195 × 719 实拍证据

- 地图全览：`docs/design-qa/exploration-v10/map-overview.png`
- 纵向时间双轨：`docs/design-qa/exploration-v10/timeline-context.png`
- 论证节点详情：`docs/design-qa/exploration-v10/argument-detail.png`

三张图均来自当前 `http://127.0.0.1:5173/#route=explore` 的夜色工作台，不使用静态原型或替代地图。地图图同时可见编号地点、柔性叙事线、九幕清单、“未定位”状态和 `全览 / 聚焦` 控件；时间图同时可见 755—763 主轨与仓库实体参照轨；论证图展示认识论层级、章节级来源边界和回跳动作。

## 发现、修复与复验

- 用户批注指出逐幕地图无法形成发展脉络。实现后默认全览 7 个可核地点，点击再聚焦；2 个无可靠坐标的 Scene 仍在九幕顺序中，但不上地图。
- 叙事线改为 MapLibre GeoJSON 采样 Bézier 双层连续线，属性明确声明“叙事顺序，非行军路线”；没有直虚线、箭头或猜测坐标。
- 左栏时间 tab 扩成纵向双轨，以 Scene 为主轨，以仓库中可核年份的事件、人物、帝王为参照轨；点击参照项真实联动时间和实体选择。
- 研究 Brief 下方五个无消费方的主题按钮已删除；“返回探索入口”收敛为“返回”，“网页”改为“微信读书”。
- 九幕各有六类论证节点、七条显式语义关系和可展开详情；后端 Prompt 合同要求作者视角、认识论分层、locator 绑定、不得强造反方或猜测地点/因果。当前明确是 `needs_model / not_called`，没有用静态 Demo 冒充真实模型输出。
- 联合测试初次暴露两个真实整合缺陷：中央外层分栏少算 50px 导致地图最低只有 190px；MapLibre 参考瓦片加载期错误阻断 Scene 清空。分别把下层最小值修正为 436px，并以 GeoJSON source 可用性代替全样式加载状态后，原合同与新合同均通过。

## 自动验证

- `npm run build`：218 modules / 1.45s；`ExplorationView` 50.03 kB / gzip 18.45 kB，MapLibre 仍为独立按需 chunk，无新增依赖。
- 后端聚焦验证：23 passed，1 skipped；覆盖六类节点、边引用、Prompt 边界、私有正文不进入合同。
- 探索联合 E2E：13 passed / 32.2s；覆盖旧入口/EPUB/微信读书合同、地图总览、未定位清空、播放保持、时间参照联动、九幕论证图和来源回跳。
- 当前应用内浏览器未出现新的 console warning / error。

本轮未做全量 110 项回归、数据全量校验或 safe profile 重构建，因为改动只触及探索 UI、探索 API schema / service 和局部测试；现有正式 YAML / GeoJSON、地图资产、部署配置均未修改。未发布。

final result: passed

# 2026-07-28 · Chrome Companion 本地 beta 验收

## 产品收口

- 同一真实 Chrome 中，微信读书顶层页能保持登录，而跨站 iframe 仍停留在登录态；OAuth 回调还触发了 sandbox 顶层导航拒绝。放宽导航既不能保证共享 Cookie / Storage，又会把父站交给第三方控制，因此 iframe 正式退场。
- 微信读书改为顶层阅读面；`extensions/weread-companion/` 以 Manifest V3 Side Panel 承载 history-kb。当前本地 beta 只连接 `127.0.0.1:5173`，不显示尚未可用的线上入口。
- Side Panel 420 × 800 实拍复核中，工作台默认进入「论证」，并保留「时空 / 出处」；没有在窄栏里再复制一套阅读器。
- 主站“微信读书”tab 只保留顶层打开与默认收起的手动同步兜底，不再出现“在本站尝试嵌入 / 登录卡住 / 重新载入”死路。

## 安全与交互

- 权限只有 `sidePanel` 与 `https://weread.qq.com/*`；无 Cookie、网络拦截、全站、剪贴板或外部连接权限。
- 用户必须先点「读取当前选区」得到内存预览，再点「加入当前探索」才发送；上限 2,000 Unicode 字符。
- 环境变化或终态 ACK 后清除选区 DOM 与内存；ACK 使用精确字段白名单，不回传正文。
- 网页桥校验 companion query、父窗口 source、开发期合法 extension origin、生产精确 allowlist、微信读书 HTTPS URL 与字段长度；同 ID 并发或重放只产生一次 mutation。
- 私人会话只在 companion 模式持久化 exploration ID；后端 GET 成功才恢复，404 清理失效 ID。正文和用户选区不进入 localStorage。

## 自动验证与未尽事项

- Extension Node：12 passed；另有 manifest、CSP、sandbox、sender、跨环境清理与精确 ACK 合同断言。
- Companion + 探索 v5 Playwright：9 passed / 35.4s；覆盖共享生产/消费 fixture、无工作区、公开 local-only、窄侧栏论证默认态、私人 revision/恢复/防重放与 404，且旧 iframe 入口缺席、手动位置同步仍真实写入 revision。
- 前端生产构建：218 modules / 4.66s；`ExplorationView` 48.23 kB / gzip 17.99 kB，无新增依赖；既有 `seed` / `maplibre-gl` 大 chunk warning 未变化。
- 自动化无法代替用户在 `chrome://extensions` 的“加载已解压扩展程序”动作；这一步需按扩展 README 手动完成。固定扩展 ID、生产 `VITE_WEREAD_COMPANION_ORIGIN`、`frame-ancestors`、账户隔离和隐私披露仍是公开发布闸门。

final result: local beta passed; Chrome unpacked installation remains manual
