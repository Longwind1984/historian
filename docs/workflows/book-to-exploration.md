# v5「拆书 → 历史探索」工作流

> 状态：v5 工程合同；Prompt 范围脚手架、TXT / Markdown / EPUB 私人解析与阅读进度已进入生产代码，《安史之乱》受限 Demo 已形成一份静态公开投影；**LLM、持久化、PDF / OCR 与通用公开投影流水线尚未接入**
>
> 适用输入：一个历史问题，或用户有权在私人环境使用的 TXT / Markdown / EPUB / 带文本层 PDF
>
> 产物合同：[`book-to-exploration.schema.json`](./book-to-exploration.schema.json)
>
> 私有结构验证：[`book-to-exploration.private-validation.json`](./book-to-exploration.private-validation.json)

## 1. 目标

把一个模糊问题或一本书，逐步变成可回到来源、可在时间与地图上播放、可暴露争议和证据缺口、可由人复核的 Exploration。

工作流不负责把模型输出包装成历史真相。它必须持续回答四个问题：

1. 这句话来自原文、作者判断、平台推断还是外部证据？
2. 它能回到哪个来源和定位？
3. 它是候选、已复核，还是尚缺证据？
4. 它能否进入私人探索、公开衍生分析，或正式知识库？

## 2. 当前实现与 v5 目标的边界

| 能力 | 当前生产切片 | 后续目标 |
|---|---|---|
| 输入 | Prompt、TXT、Markdown、EPUB | 带文本层 PDF / OCR |
| 保存 | 后端进程内，6 小时失效 | 本地原文 + 可版本化分析产物 |
| 章节 / 段落 | TXT 标题/空行；EPUB OPF / spine / href / 段落锚点 | TOC 层级、CFI、按需章节 API |
| LLM | 未接入；composer 与分析请求只记录 | 分阶段提议、可取消、可恢复 |
| Claim | 《安史之乱》九个受限公开锚点及原创衍生分析，或私人输入的空结构 | 四种来源角色的运行时强制分层 |
| Scene | 九幕 Demo；私人输入不猜地点 | 证据化 Scene 候选 + 人工复核 |
| 外部材料 | Chrome Companion 主动选区桥 + 手动位置/摘录兜底 | 固定扩展 ID、账户隔离、公开隐私披露 |
| 公开分享 | 未实现 | 默认只导出衍生分析，不带原书 |

生产 `ExplorationSnapshot` 是当前私人阅读会话的运行态：它会把解析后的当前书籍段落返回给上传者的阅读器，但只存在后端进程内。本文 Schema 则定义可版本化的分析产物，不复制正文。两者用途不同，不能把运行态响应当成可公开分享的分析包。

## 3. 总流程

```text
empty
  ├─ Prompt ─→ scope_draft ─→ scope_confirmed ─→ source_packets
  └─ 书籍   ─→ input_ready ─→ scope_draft ─→ scope_confirmed
                                      └──────→ chapters / paragraphs
                                                   │
                                                   ▼
作者论点 → 事实候选 → 时间 / 地点 / 人物 → Scene / 证据关系
                                                   │
                                                   ▼
                                     反证检查 / 证据缺口
                                                   │
                                                   ▼
                                             人工复核
                                      ┌────────────┴────────────┐
                                      ▼                         ▼
                                ready_private       publishable_derivative
```

Prompt 路径没有书，不得伪造「章节」。范围确认后，它建立按来源分组的 `source_packets` 和 `source_record` 锚点；书籍路径才建立真实章节、段落和 EPUB CFI。两条路径在「可定位来源锚点」处汇合。

## 4. 生命周期状态

| 状态 | 进入条件 | 可见结果 | 不允许发生 |
|---|---|---|---|
| `empty` | 没有 Prompt 或书 | 空白工作台 | 展示示范书判断 |
| `input_ready` | 文件基本格式可读 | 元数据、隐私提示 | 把包内日期冒充纸书版次 |
| `scope_draft` | 已有问题或书籍元数据 | 可编辑问题、时间、空间、主线 | 自动开始全书分析 |
| `scope_confirmed` | 用户确认范围 | 固定 revision 基线 | 静默扩大章节或外部来源 |
| `structure_indexed` | 章节 / 来源记录已定位 | 目录、统计、解析警告 | 写入模型生成的伪页码 |
| `analysis_proposed` | 已产出 Claim / 实体 / Scene 候选 | 待核结构 | 把提议写回正式 YAML |
| `evidence_audited` | 完成来源与冲突检查 | 关系、缺口、阻塞项 | 机械填充正反观点 |
| `human_review` | 有待人工决定对象 | 逐项接受、驳回、改写 | 批量将作者判断升格为事实 |
| `ready_private` | 私人探索可用 | 本地可读、可播放 | 默认对外分享原书内容 |
| `publishable_derivative` | 公开投影全部通过 | 衍生分析包 | 包含 EPUB、私有路径、Cookie、可重构全文的摘要 |
| `paused` | 用户取消或等待来源 | 已完成 checkpoint | 清空已完成结构 |
| `failed` | 当前阶段不可恢复 | 失败阶段与错误 | 伪造成功或跳过质量闸门 |

合同强制以下组合：

- `empty` 只能使用 `input.mode=none`、`research_scope.status=draft` 和 `structure_kind=none`；
- `input_ready / scope_draft` 的研究范围只能是 `draft`；
- 从 `scope_confirmed` 到公开衍生状态，研究范围必须是 `confirmed`，问题和 `allowed_source_sets` 不能为空；
- Prompt 在 `structure_indexed` 以后必须有至少一个 `source_packet`，且永远不能出现 book chapters；
- 书籍在 `structure_indexed` 以后必须有至少一个 chapter，且永远不能出现 `source_packets`；
- `paused / failed` 保留进入前的研究范围状态，避免失败处理改写业务事实。

## 5. 分步执行

### 5.1 隐私预检

在读取正文前完成：

1. 识别输入类型与存储位置；
2. 默认 `raw_source_retention=local_only`；
3. 默认 `raw_source_in_artifact=false`；
4. 明示本轮会发送给模型的章节或段落；
5. 不保存网页登录凭据、Cookie、授权头或本机绝对路径；
6. 给本轮产物分配独立 `exploration_id` 与 revision。

`model_send_policy` 只管理书籍片段和外部来源材料，不管理用户主动输入的 Prompt。Prompt 使用独立的 `prompt_send_policy`：

- `not_sent`：只在本地记录，不调用模型；
- `send_when_model_invoked`：用户触发范围整理或编织时，把 Prompt 作为请求输入发送。

因此，`model_send_policy=none` 不等于 Prompt 不能发送；它只表示不附带书籍或外部材料。若两者都不发送，只执行本地记录和结构索引。

### 5.2 接收 Prompt 或书籍

#### Prompt

- 保存用户原话；
- 只提出一轮高价值澄清；
- 不生成书名、章节或作者；
- 范围确认时确定 `allowed_source_sets`；
- `scope_confirmed` 可以暂时没有来源包；
- 进入 `structure_indexed` 前，按研究子问题建立至少一个 `source_packet`。

#### 书籍

- 读取容器元数据、目录、spine 与文本可用性；
- `title / author / language` 只记为包内元数据；
- `edition_label` 只有用户提供或有可核版本证据时才填写；
- 解析警告必须进入 `document_structure.parse_warnings`；
- 原始文件不进入 Git、日志、探索 JSON 或公开包。

### 5.3 确认研究范围

产出 `research_scope`：

- 核心问题；
- 时间范围与精度；
- 地理范围；
- 重点人物 / 组织 / 事件；
- 2–4 条优先主线；
- 包含项；
- 明确排除项；
- `allowed_source_sets`：只允许 `original_text / platform_kb / user_supplied_external / public_external` 中被用户确认的集合。

用户确认后进入 `scope_confirmed`。改变章节范围、问题主线或来源边界必须增加 revision；只改选中 Scene 不增加研究范围 revision。

### 5.4 建章节、段落与来源锚点

书籍路径按以下顺序解析：

1. package / manifest；
2. spine 阅读顺序；
3. TOC 层级；
4. 章节与小节；
5. 可恢复的段落锚点；
6. EPUB 优先使用 CFI；无法生成时使用明确标注的段落索引。

Prompt 路径建立：

1. 按研究子问题建立 `source_packet`，不是把所有检索结果平铺；
2. 每个 packet 保存 `id / title / purpose / status`；
3. packet 的 `source_ids` 指向来源，`anchor_ids` 指向这些来源中的具体记录；
4. 每条来源记录使用 URL fragment、正式库 ID 或用户材料段落定位；
5. packet 可处于 `planned / indexing / ready / failed`，失败不删除已完成 packet；
6. 不把来源包伪装成书籍目录。

锚点只保存 locator；正文由本地 source resolver 按需取得。JSON 中不复制整段正文。确有必要的短摘录最多 280 个字符，并标为 `private_only` 或 `rights_review_required`；这不是法律安全线，公开时仍需人工权利审查。

### 5.5 提取作者论点

逐章节、逐小节分批处理，禁止一次性把整本长书发送给模型。

每个 Claim 必须属于以下一种：

| `kind` | 含义 | 必需字段 | 禁止 |
|---|---|---|---|
| `source_statement` | 原文明确陈述 | 原文锚点、来源主体 | 改写成无来源事实 |
| `author_judgment` | 作者的解释、评价或因果判断 | 作者主体、原文锚点 | 去掉「作者认为」 |
| `platform_inference` | 平台对多个材料提出的结构 | 被推导 Claim ID、待复核 | 伪装成作者原意 |
| `external_evidence` | 外部材料的陈述或判断 | 外部来源 ID、定位 | 混入原书来源列表 |

提取时先找作者正在回答的问题，再找作者怎样组织证据；不要把所有句子都拆成平级卡片。

### 5.6 形成事实候选

作者写到某事，不代表它已经成为平台事实。

`fact_candidate` 只表示「值得核查的历史命题」，必须：

- 指向一个或多个 Claim；
- 保留时间、地点、人物的候选引用；
- 初始 `review_status=pending_review`；
- 不因句式肯定就自动变成 `accepted`；
- 不因多个段落重复就自动视为多源互证。

同一本书的多次重复仍是单一来源；`multi_source` 要求来源独立。

### 5.7 解析时间、地点与人物

#### 时间

- 保留原文时间标签；
- 同时记录标准化候选和精度；
- 「约」「此前」「同年」等不能伪装成精确日期；
- 跨章节代词回指必须可追溯。

#### 地点

- 优先链接正式地点实体；
- 同名地名保留 `candidate_match`；
- 无可靠坐标时 `geometry_status=ambiguous|none`；
- 不从人物籍贯、现代行政区或常识猜事件坐标。

#### 人物与组织

- 候选链接先比对时间、别名、关系和来源；
- `candidate_match` 不得自动合并；
- 只有证据建立唯一性时才链接正式实体；
- 书中概念和作者术语可留在 Exploration，不强行实体化。

### 5.8 编成 Scene 与证据关系

Scene 是可播放的最小叙事单元，不是每段一个 Scene。

一个 Scene 至少包含：

- 标题与衍生摘要；
- 相关 Claim / fact candidate；
- 时间引用；
- 地点引用；
- 当时相关人物；
- 证据关系；
- 地图状态；
- 人工复核状态。

关系语义限于：

- `chronology / participation`；
- `supports / corroborates / supplements`；
- `different_scope / method_difference / narrows`；
- `contradicts`；
- `causal_proposal / author_interprets / model_infers`。

只有同一命题的真值不能同时成立时，才能标 `contradicts`。先后出现不是因果；讨论层级不同不是反方。

### 5.9 检查反证与证据缺口

按 Claim，而不是按页面栏位检查：

1. 是否有独立来源支持？
2. 是否有来源限制其适用范围？
3. 是否存在直接冲突？
4. 是否只是方法或观察尺度不同？
5. 是否没有找到能判断的材料？

没有反证时，写入 `gap.kind=counterevidence_not_found`，界面显示「当前未发现直接冲突材料」。不要创建空洞的反方人物、反方观点或虚假引文。

外部调用失败时保留失败来源和缺口；同一 URL 不循环重试。

### 5.10 人工复核

人工决定面向单个 Claim、fact candidate、关系或 Scene：

- `accept`；
- `reject`；
- `request_evidence`；
- `revise`；
- `accept_as_limit`。

复核动作写入不可变 `review.events`，对象状态随 revision 更新。接受作者判断只表示「忠实表达了作者」，不表示接受其历史结论。

正式知识库晋升是另一条流程：必须重新执行来源、去重、引用完整性和数据验证；本工作流不直接改 YAML / GeoJSON。

## 6. JSON 产物合同

`book-to-exploration.schema.json` 定义一个可暂停、可恢复、可做公开投影的 Exploration Artifact。

### 6.1 主要对象

| 对象 | 用途 |
|---|---|
| `input` | Prompt 或私人书籍引用，不含原文件 |
| `privacy` | 原文留存、模型发送和公开默认策略 |
| `research_scope` | 用户确认的研究约定 |
| `corpus.sources` | 原书、正式库、用户外部材料、公开外部来源 |
| `document_structure` | 章节 / 段落或来源包锚点 |
| `document_structure.source_packets` | Prompt 路径按子问题分组的来源包；书籍路径必须为空 |
| `analysis_plan` | 分阶段深度分析计划与 checkpoint |
| `claims` | 四种来源角色明确的可检验陈述 |
| `fact_candidates` | 尚待证实的历史命题 |
| `entities / time_refs / location_refs` | 可链接、可保持歧义的时空实体 |
| `scenes` | 可播放、可复核的叙事单元 |
| `evidence_relations` | 材料之间的非机械关系 |
| `gaps` | 缺来源、缺定位、歧义、未找到反证、权利未知 |
| `review` | 人工决定记录 |
| `reader_bridge` | 微信读书等外部阅读器的真实能力状态 |
| `release_projection` | 私人产物到公开衍生分析的过滤结果 |

### 6.2 Schema 之外仍须检查的引用完整性

JSON Schema 能验证字段和枚举，但不能独自证明跨数组引用有效。实现必须另外检查：

1. 所有 `*_id` 指向存在对象；
2. ID 在整个 artifact 内唯一；
3. `source_statement / author_judgment` 至少有一个原文锚点；
4. `platform_inference` 至少有一个被推导 Claim；
5. `external_evidence` 至少有一个外部 source；
6. `geometry_status=verified` 才允许非空坐标；
7. `contradicts` 两端作用于同一可比较 Claim；
8. `gap.target_type` 与 `target_id` 必须共同指向合法对象类型；
9. `publishable_derivative` 的 release checks 必须全部为 `pass`。

`gap.target_id` 可以指向 exploration、source、source packet、anchor、Claim、fact candidate、entity、time / location ref、Scene、evidence relation 或 release projection。Schema 校验 `target_type` 枚举；跨 ID 校验器必须再证明该 ID 真实存在于对应集合，不能只因为字符串格式合法就通过。

## 7. 私有 EPUB 验证

本轮对本机《红太阳是怎样升起的：延安整风运动的来龙去脉》EPUB 做了只读结构验证：

- 包内元数据：书名、作者高华、语言 `zh`；
- 45 个 spine 项、71 个归档条目；
- 正文目录识别出 15 章、76 个小节；
- 章节子树共 30 个内容单元；
- 章节范围统计到 487,694 个去空白可见字符、3,428 个段落标签；
- 每章标题、章节级字符数、段落数和小节数记录在私有验证 JSON；
- 以章节级 locator 提议了五条作者论证主线：权力重组、解释权、组织 / 教育技术、审干与抢救、1945 年制度化收束；
- 形成 5 个 `author_judgment`、1 个 `platform_inference`、5 个待核 fact candidates、5 个待核 Scene 和 9 个缺口；
- 没有保存文件路径、文件 UUID、正文、长引文或段落内容；
- 所有内容分析均为原创摘要，绑定章节级 locator，统一 `pending_review`；段落 CFI、独立外证和反证检索仍是阻塞项；
- 包内 `dc:date` 只视为转换包元数据，未据此声称纸书版次。

这次历史验证证明合同能表达「结构索引 → 深度分析候选 → Scene / 缺口」。EPUB 解析器此后已经进入私人工作区，但这份验证仍不证明任何作者判断或事实候选已经成为历史事实。

### 7.1 《安史之乱》前向验证与公开投影

本轮继续用本机《安史之乱：历史、宣传与神话》EPUB 做只读前向验证。原文件、绝对路径、包内 href、哈希和正文均未写入仓库；仓库只记录以下不可逆推出原文的结构统计与原创衍生结果：

- 识别书名、作者张诗坪 / 胡可奇与 29 章目录结构；
- 69 个 spine 文档、2,086 个段落锚点、约 38 万正文字符；
- 形成结构条件、战场与政治、财政后勤、联盟政治、内部重组、历史记忆 6 组分析主题；
- 收敛为河北 / 范阳、洛阳、潼关 / 灵宝、马嵬、太原、两京、睢阳、邺城、河阳 / 邙山 9 个 Scene；
- 只使用仓库已有地点实体的坐标；潼关 / 灵宝与河阳 / 邙山因缺可靠地点引用保持 `location=null`；
- EPUB 上传压缩体上限从 12 MiB 调整为 16 MiB，并补齐 schema、服务端预检和边界测试，使这一本地样本能通过正常导入合同；ZIP 展开体、条目数和单项限制不变。

公开投影不复制上述私人段落锚点，而是另建 9 个稳定公开 ID。每个公开锚点只包含 Scene、时间、地点标签、原创摘要、分析框架、权利状态和“章节级定位”；不包含原文、私有 locator 或可还原阅读顺序的内容。

公开阅读窗口的上限为 10 页，但当前 0 页通过权利审查，因此全部锚点为 `restricted`。论证节点仍可一键回到相应受限锚点；这是功能完整的定位，不是用打码遮住已下发正文。任何将来的 `excerpt_visible` 晋升都必须经过逐页权利审查，并在发布检查中留下明确记录。

## 8. 版权、隐私与公开发布

### 8.1 私人工作区

- 用户选择的 EPUB 保留在本机或明确的临时进程；
- EPUB、全文索引、全文 embedding、绝对路径不进入仓库；
- 模型只接收用户确认范围内的片段；
- 私人探索可保存本地 anchor、衍生摘要与关系，但默认不可公开；
- 「用户持有文件」不自动等于「平台可公开再分发文件」。

### 8.2 可公开的衍生分析

默认可以进入公开候选：

- 书目元数据；
- 平台原创的非重构性分析；
- 经复核的历史事实候选及其公开来源；
- 不含原书内容的时间、地点、人物、Scene 与关系拓扑；
- 指向合法公开来源的引用；
- 由用户明确选择且完成权利审查的短引文。

默认排除：

- EPUB / PDF / TXT 原文件；
- 连续正文、长引文、可按顺序重构原书的章节摘要；
- 私有 anchor 的绝对路径、CFI 对应原文内容或文件指纹；
- 微信读书 Cookie、登录态、用户书架与阅读记录；
- 权利不明的图片、全文索引和外部材料副本。

不存在通用的「多少字一定安全」规则。公开投影默认不带引文；确需引文时进入人工权利审查，记录来源、用途和所用版本。

### 8.3 发布闸门

发布检查不是布尔值，而是：

- `pass`：已经检查并通过；
- `fail`：已经检查且不通过；
- `unknown`：尚未检查或证据不足；
- `not_applicable`：当前产物确实不适用，必须能说明原因。

早期阶段不得用 `false` 冒充「尚未检查」。`release_projection.status=derivative_ready` 前必须确认：

- `no_raw_source=pass`；
- `no_private_locator=pass`；
- `no_credentials=pass`；
- `no_reconstructive_summary=pass`；
- `external_rights_recorded=pass`；
- `human_approved=pass`。

任一项为 `fail / unknown / not_applicable`，都不能进入 `derivative_ready`；它只能保持 `private_ready` 或 `blocked`。

## 9. 微信读书与 Chrome Companion 状态

跨站 iframe 已经从产品路径移除。微信读书保持 Chrome 顶层第一方页面，history-kb 运行在 Side Panel。

| 状态 | 产品含义 | 可以做 | 不可以声称 |
|---|---|---|---|
| `external_open_only` | 只在原站顶层打开 | 使用微信读书自身登录与阅读 | history-kb 持有登录态 |
| `companion_capture_ready` | 扩展可用但没有读取内容 | 等待用户主动读取 | 后台同步正文 |
| `companion_preview` | 当前选区只在 Side Panel 内存预览 | 用户确认或取消 | 已写入探索 |
| `companion_synced` | 用户二次确认且 revision 写入成功 | 在论证 / 时空 / 出处中继续探索 | 自动读取后续章节 |
| `local_only` | 公开示例临时接收选区 | 当前浏览器会话内联动 | 已写服务端 |
| `no_workspace / failed` | 没有可接收工作区或写入失败 | 建立工作区或重试 | 同步成功 |
| `manual_progress_bridge` | 用户手动确认章节或百分比 | 记录章节标签、进度、映射到本地章节 | 后台实时同步 |

扩展内容脚本只接受本扩展 Side Panel 发出的捕获请求；页面加载、滚动和切 tab 都不会读取或发送内容。捕获包严格限定为 `https://weread.qq.com/*`，正文最多 2,000 Unicode 字符；同一 packet ID 在当前页面会话内只产生一次 mutation。扩展不读取 Cookie、书架或后台全文，终态回执后清除选区内存。

手动进度桥接只保存：

- provider；
- 用户输入的章节标签；
- 可选进度百分比；
- 可选本地章节 ID；
- `user_confirmed=true`；
- 记录时间由产品运行态保存。

它不保存 Cookie，不请求微信读书权限，不从页面偷偷抓取，不把模糊章节名自动映射为精确段落。

## 10. Acceptance Matrix

| ID | 场景 | 操作 | 必须断言 |
|---|---|---|---|
| A01 | 空工作台 | 新建 Exploration | `lifecycle_state=empty`、`input.mode=none`、scope=draft；没有示范 claims / scenes |
| A02 | Prompt 输入 | 输入历史问题并确认范围 | Prompt 与 book_ref 互斥；不产生伪章节；`scope_confirmed` 可暂为 `structure_kind=none` |
| A02b | Prompt 来源包 | 推进到 `structure_indexed` | 至少一个 `source_packet`，含 purpose / source IDs / anchor IDs；chapters 为空 |
| A02c | 书籍输入 | 同时注入 Prompt 字段 | Schema 拒绝；book 路径的 `source_packets` 必须为空 |
| A03 | EPUB 输入 | 读取 TOC / spine | 原文件不进 JSON；章节顺序稳定；解析警告可见 |
| A04 | 版次未知 | 只有包内日期 | `edition_label=null`；不得把 `dc:date` 显示为纸书版次 |
| A05 | 段落定位 | 生成书籍 Claim | `source_statement` 或 `author_judgment` 至少一个 anchor |
| A06 | 作者判断 | 提取作者因果解释 | `kind=author_judgment`，speaker 为作者，不显示为平台事实 |
| A07 | 平台推断 | 从多个 Claim 提议结构 | `kind=platform_inference`；至少一个 `derived_from_claim_ids` |
| A08 | 外部证据 | 添加另一研究 | 独立 source ID、rights status、locator；不混入原书来源 |
| A09 | 事实候选 | 从作者陈述提取事件 | 初始 `pending_review`；重复段落不自动变多源互证 |
| A10 | 地点歧义 | 文本只有同名地名 | `geometry_status=ambiguous`；坐标为空；Scene `partial|no_location` |
| A11 | 无地点 Scene | 播放 Scene | 时间与论证可播；地图不继承上一 Scene 高亮 |
| A12 | 非冲突材料 | 两材料讨论不同层级 | 用 `different_scope|supplements`；不生成 `contradicts` |
| A13 | 未找到反证 | 外部检索无结果 | 生成 `counterevidence_not_found` gap；没有占位反方卡 |
| A14 | 真冲突 | 同一 Claim 有不可并存材料 | 两端来源和定位齐全后才允许 `contradicts` |
| A15 | 取消分析 | 在章节批次中取消 | 进入 `paused`；保留已完成 pass 与 revision |
| A16 | Schema | 校验私有结构样例 | JSON 语法与 2020-12 Schema 均通过 |
| A17 | 引用完整性 | 删除被 Scene 引用的 Claim | 自定义引用校验失败，不允许发布 |
| A18 | 私人导出 | 导出 `ready_private` | 无 EPUB、正文、绝对路径、Cookie |
| A19 | 早期发布检查 | 尚未进行权利或重构性检查 | 使用 `unknown / not_applicable`，不能用 false 假装已检查 |
| A19b | 公开投影 | 任一 release check 不是 `pass` | 不得进入 `publishable_derivative` |
| A20 | Companion 捕获 | 点击读取当前选区 | 只生成内存预览；0 mutation；上限 2,000 字 |
| A21 | Companion 确认 | 再点加入当前探索 | 恰好 1 次 mutation；ACK 无正文；同 ID 重放不重复写入 |
| A22 | 手动进度 | 用户输入章节与百分比 | `manual_progress_bridge`；只有用户确认后绑定本地章节 |
| A23 | 人工复核 | 接受作者判断 | 只确认「忠实表达作者」；不自动晋升正式事实 |
| A24 | 正式库晋升 | 选择已复核候选 | 另走来源、去重、引用、数据验证；本流程不写 YAML |

## 11. 最小上下文前向测试

把以下三项交给一个没有本项目历史的执行者：

1. 本工作流；
2. JSON Schema；
3. 私有结构验证 JSON。

给它两个任务：

- 将一个无书籍 Prompt 推进到 `scope_confirmed`；
- 审计私有验证 JSON 是否可以进入 `evidence_audited` 或 `publishable_derivative`。

预期它应得出：

- Prompt 在 `scope_confirmed` 可以暂时没有结构；推进到 `structure_indexed` 后使用至少一个 `source_packet`，不会编造章节；
- `model_send_policy` 不覆盖 Prompt；是否发送 Prompt 由 `prompt_send_policy` 单独决定；
- 私有 EPUB 仍为 `local_only`，JSON 不加入正文；
- 五条作者主线只处于章节级 `author_judgment`，五个 Scene 仍为 `pending_review`；
- 平台编排明确是 `platform_inference`，不是作者明示的五阶段模型；
- 缺段落 locator、独立来源与反证检索，所以不能进入 `evidence_audited`；
- 公开投影不能变成 `derivative_ready`。

如果执行者需要仓库代码、用户隐含意图或全文才能做出这些判断，说明工作流仍不自足，应先补合同，不开始编码。

## 12. 验证命令

```bash
python3 -m json.tool docs/workflows/book-to-exploration.schema.json >/dev/null
python3 -m json.tool docs/workflows/book-to-exploration.private-validation.json >/dev/null
python3 - <<'PY'
import json
from jsonschema import Draft202012Validator
schema = json.load(open("docs/workflows/book-to-exploration.schema.json"))
artifact = json.load(open("docs/workflows/book-to-exploration.private-validation.json"))
Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(artifact)
print("schema + private validation: passed")
PY
```

正式工程实现还需增加跨 ID 引用校验；仅通过 JSON Schema 不等于历史内容通过复核。

## 13. 论证图生成合同（`book_argument_graph.v1`）

深度分析不再只排一个无结构的“待模型处理”标记。服务端在 `request_deep_analysis` 时生成可审计的 Prompt 合同，但当前不会发起模型请求：

1. 从当前探索的有效 anchor 解析 `SourceLocator`，去重但保留顺序；
2. 队列项保存 `request_text`、`requested_views`、locator、guardrails 和 `ArgumentGraph` JSON Schema；
3. 私人正文不进入队列快照。未来模型运行时必须按 `source_text_by_anchor_id` 临时注入用户授权文本；
4. 输出至少包含问题、材料观察、推理机制、行动或转折、后果、限制六类节点；
5. 每个节点必须声明认识论层级和至少一个可解析 anchor；每条边必须引用图中节点；
6. 不得把作者判断改写成无主体事实，不得根据模型常识补地点、坐标、路线、日期精度、人物动机或因果强度；
7. 没有同一命题的明确冲突材料时，不生成 `contradicts`；证据不足时用 `limitation` 降低结论强度。

队列项的当前边界固定为：

```text
processing_status = needs_model
invocation_status = not_called
candidate_output = null
source_payload_state = requires_runtime_injection | missing_source
```

只有未来真实模型返回的 JSON 同时通过 Pydantic 图结构校验、anchor 引用校验和人工复核，才能写入 `argument_graphs`。`needs_model` 不是成功生成，也不能作为对外历史结论。

## 14. 地图顺序与时间参照投影

书籍 Scene 在两个正交投影中复用同一选择状态：

- **地图全览**读取已复核 Scene 坐标，绘制编号点和叙事顺序曲线；无坐标 Scene 只保留清单位置。任何曲线都写入 `sequence_not_route`，不从章节顺序推断行军路线。
- **时间双轨**把 Scene 放在主轨，把正式知识库中已有明确年份的事件、人物和帝王放在参照轨。参照轨数据必须记录实体 ID、类型、年份字段和源 YAML 路径；不能用人物在世区间或叙事常识生成时间点。
- 点击 Scene 更新 `selectedSceneId`、锚点、地图与证据；点击参照实体只更新正式时间与实体选择，仍停留在 Explore 路由。两者不得互相覆盖为同一种节点。

当前《安史之乱》公开 Demo 有 9 幕，其中 7 幕具备仓库内可核坐标；地图总览绘制 7 个点与 6 段相邻已定位 Scene 曲线，另外 2 幕明确标为未定位。这个数字是当前内容状态，不是通用算法假设。
