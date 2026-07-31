
## 2026-07-11 · 接手重构：架构分层 + Bug 修复 + 性能优化

### 做了什么
从 ZCode 接手 history-kb 项目，完成全量架构重构。三个核心 bug 全部修复，后端和前端代码结构重新分层，首屏体积下降 88%。

### Bug 修复
1. **"此刻在世 0 人"**：后端新增 `prefer_seed=true` 参数，种子人物（李白、李隆基等）优先于 CBDB 学术数据返回。750 年现在正确显示 16 人在世。
2. **"无疆域数据"**：原代码 `paintTerritories` 依赖 `isStyleLoaded()` 轮询，底图瓦片被代理拦截后永远不返回 true。改为 `styledata` 事件后直接绘制疆域 GeoJSON（疆域数据来自本地后端，不依赖外网瓦片）。
3. **MapLibre Failed to fetch**：系统代理 127.0.0.1:7897 拦截瓦片请求。添加 `transformRequest` 配置（但 OS 级代理无法用 JS 绕过，此为环境限制，非代码问题）。

### 架构重构
**后端**：
- `core/data.py`：预建 `EntityIndex`（by_id / by_type / persons_by_year 二分查找）和 `RelationIndex`（邻接表 + BFS），查询从 O(N) 降到 O(1)/O(log N)
- 新增 `services/` 层：entity_service, graph_service, territory_service, timeline_service
- API 路由变薄，只做参数校验 + 调 service
- 原来每次请求扫描 7022 个 YAML 文件（有 mtime 缓存但仍 O(N)），现在启动时建索引

**前端**：
- 单体 `stores/app.js` 拆分为 `useDataStore` / `useTimeStore` / `useSelectionStore` / `useUIStore`
- 组件按职责分目录：`shared/`（SearchBar/Seal/Avatar/WikiLinkText）、`timeline/`（TimeColumn/MomentPanel）、`map/`（MapPanel）、`graph/`（GraphPanel/EntityDetail）
- 新增 `composables/useEntityDetail.js` 统一实体详情加载逻辑
- API client 加实体缓存（同一实体不重复请求）
- MapPanel 和 GraphView 改为 `defineAsyncComponent` 懒加载

### 性能优化结果
| 指标 | 重构前 | 重构后 |
|---|---|---|
| 首屏 JS | ~1338KB | ~134KB（-88%）|
| MomentPanel chunk | 817KB（含 MapLibre）| 9.5KB（纯逻辑）|
| MapLibre | 首屏同步加载 | 按需加载（807KB 独立 chunk）|
| 后端实体查询 | O(N) 扫描 7022 YAML | O(1)/O(log N) 索引 |
| 实体详情请求 | 每次重新 fetch | 内存缓存 |
| 构建 | - | 109 模块, 1.59s |

### 关键决策与被否决的备选
- **保留旧 store 兼容层 vs 直接删除**：选了直接删除。旧 `useAppStore` 解构后不响应式，留着是隐患。新代码已全部改用具体 store。
- **瓦片代理修复方案**：考虑过 (a) 换国内瓦片源 (b) 后端代理转发 (c) transformRequest。选了 (c)，因为疆域 GeoJSON 不依赖底图瓦片，瓦片只影响背景美观，不值得为它加后端代理增加复杂度。
- **TimeColumn 虚拟滚动**：暂未实现。当前人物列表渲染性能可接受，等数据量增长再优化。

### 当前状态
- 后端 `:8000` 运行中，前端 `:5173` 运行中
- 两个路由都验证通过：时间柱（人物在世+疆域+详情）、谱系星图（Cytoscape 关系图）
- 构建通过，git 已提交（b48b7af）
- 已知限制：MapLibre 底图瓦片因系统代理无法加载（疆域不受影响）

### 未尽事项
- TimeColumn 虚拟滚动（人物多时优化）
- 疆域 GeoJSON properties 为空（原数据问题，`polity`/`name` 字段缺失）
- README.md 需更新反映新架构
- 后端测试覆盖（当前无自动化测试）

### 文件级变更清单
- 修改：backend/app/core/data.py, backend/app/api/*.py (6 files), frontend/src/App.vue, frontend/src/api/client.js, frontend/src/views/GraphView.vue
- 新增：backend/app/services/*.py (4 files), frontend/src/stores/{useDataStore,useTimeStore,useSelectionStore,useUIStore,index}.js, frontend/src/composables/useEntityDetail.js, frontend/src/components/{shared,timeline,map,graph}/*.vue (10 files)
- 删除：frontend/src/components/{Avatar,EntityDetail,GraphPanel,MapPanel,MomentPanel,Seal,SearchBar,TimeColumn,TimelinePanel,WikiLinkText}.vue, frontend/src/stores/app.js

---

## 2026-07-11 · T1.4 移除 Neo4j 图数据库

### 做了什么
移除了从未实测的 Neo4j 图数据库路径--driver 单例、幂等导入脚本、docker-compose 服务、`neo4j==5.24.0` 依赖、`NEO4J_*` 配置项。后端现在纯靠启动时构建的 YAML 内存索引提供服务，7,011 实体规模下查询无影响。决策归档至 `docs/decisions.md`（ADR-001）。

### 关键决策与被否决的备选
- **.gitignore 的 neo4j_data/neo4j_logs**：删除（更干净）vs 保留（无害）。选删除，volumes 已不存在。
- **.env.example**：原仅含 `NEO4J_PASSWORD`，移除后改为列出可覆盖的可选变量（DATA_DIR/SCHEMA_DIR/CORS_ORIGINS），避免空置。
- **PROGRESS.md "Known limitations #6"**：原记"Neo4j 路径未实测"，移除后该限制不成立，删除该条并 #7 顺延为 #6。
- **registry.py**：检查后确认其 docstring 与实现均不含 Cypher 逻辑（只生成 data-dictionary + TS stubs），无需改动。
- **恢复路径**：导入脚本与 driver 保留在 git 历史，需要时从 v1.0.0 之前提交检出重建。

### 当前状态
- `from app.main import app` 成功（`app ok`）
- pytest 套件 32 passed（12.37s），1 个无关的 Starlette/httpx 弃用警告
- 全仓 grep neo4j（.py/.txt/.yml/.yaml/.example，排除 decisions/WORKLOG/PROGRESS/roadmap）= 无残留引用

### 未尽事项
- 无

### 文件级变更清单
- 删除：backend/app/core/neo4j.py, backend/scripts/import_to_neo4j.py
- 新增：docs/decisions.md
- 修改：backend/requirements.txt, backend/app/main.py, backend/app/core/config.py, backend/tests/test_smoke.py, docker-compose.yml, .env.example, .gitignore, schema/_registry.md, README.md, PROGRESS.md

## 2026-07-11 · T1.2-r2 数据校验器修 BCE 年份比较

### 做了什么
数据校验器 `scripts/validate_data.py` 的 3 条 E_YEAR 误报全部消除，全量 ERROR 从 5 降到 2（仅剩 pl_kaifeng id 重复、p_cbdb_563091 born>died 两个真实数据 bug），exit=1 不变。修复 BCE 年份比较的两个根因，未改任何 data/** 数据。

### 数据年份编码方式（读 YAML 的发现）
- 手写实体（qin_han 等朝代目录）：BCE = `year` 存**正数** + 正文文本字段含 "BC&lt;n&gt;" 标记（如 "BC154"、"BC209"）；CE = 正数，无 BC 标记或含 "AD&lt;n&gt;" 标记。全库 58 个实体文件含 BC 标记。
- CBDB 关系（data/relations/cbdb.yaml）：BCE = `year` 存**负数**（signed 约定，4681 处，多为 `year: -1`）。
- 手写关系：BCE = `since`/`until` 存正数，**自身字段无任何 BCE 标记**（note 只是"主导"等）。
- 全库仅 1 个实体横跨 BCE/CE：`p_wang_mang`（bio 同时含 "BC1" 与 "AD9"/"AD23"）--这正是误报 #3 的根因。
- 关键含义：手写关系无法仅凭自身字段判定 BCE，必须借助端点实体；但不能盲信单个端点（王莽的 BC 标记把 CE 关系拉成了 BCE）。

### BCE 修复实现说明
换算规则一句话：**BCE 正数年份比较前取负换算成天文学年（year_astro = -year），月份不参与正负翻转，之后与 CE/signed 统一按 (year, month) 元组数值比较（大=晚）。**
- `year_hardship` 的 bce 分支改为 `ya,yb = -ya,-yb` 后走统一比较，修正"同一 BCE 年内月份大=晚"被旧逻辑反转的 bug（e_qiguo_zhiluan BC154-1 vs BC154-3 不再误报）。
- `detect_relation_era` 改为：since/until 含负年份→signed；否则仅当所有「非横跨」端点均为 bce/signed 才判 bce；任一端点为 ce 或横跨→ce。新增 `_entity_spans_bce_ce`（正文同时含 BC+AD 标记）识别横跨实体并排除其参与 bce 推断，使王莽改革 9-22（CE）不再被误判为 bce。
- 同时保全 15 条跨年 BCE 关系（楚汉 BC206-202、武帝 BC141-87、张骞 BC138-114 等）：两端点均纯 BCE→仍判 bce→取负后 -206 &lt; -202 不报。

### 关键决策与被否决的备选
- **"era 只来自记录自身字段"的严格解读 vs 保留端点推断**：严格解读（手写关系无自身 BCE 标记→一律 ce）会令 15 条跨年 BCE 关系全变误报（206&gt;202 等）。选了保留端点推断但加约束（横跨实体排除 + 所有非横跨端点须一致为 BCE）。理由：数据编码决定手写关系无法自证 BCE，端点推断是唯一可用信号，但必须防住王莽这类横跨实体。
- **横跨实体识别用 "BC+AD 双标记" vs "born/died 跨元前元后"**：选前者。born/died 是正数无 era 标注，无法判定哪个是 BCE；正文 BC/AD 标记是数据里唯一的 era 线索，且全库恰好只命中王莽 1 个，信号干净。

### 验收输出
`/Users/rick/ZCodeProject/.venv/bin/python scripts/validate_data.py --json /tmp/validate-after.json; echo "exit=$?"`
```
--- ERROR (2 条) ---
[ERROR] data/entities/places/kaifeng.yaml pl_kaifeng  E_DUP_ID: id 重复（首次见于 data/entities/places/core_places.yaml）
[ERROR] data/entities/persons/p_cbdb_563091.yaml p_cbdb_563091  E_YEAR: 年份硬伤 born({'year': 1209}) > died({'year': 1172}) [ce]
总览: entities=7010 relations=9909 errors=2 warnings=5677  耗时 3.09s
```
exit=1。双链覆盖 12.6%（与基线一致）。3 条误报（e_qiguo_zhiluan 实体、qiguo 关系、wang_mang_gaige 关系）均已消失。

### 当前状态
- `scripts/validate_data.py` 可直接跑：`/Users/rick/ZCodeProject/.venv/bin/python scripts/validate_data.py --json /tmp/validate-after.json`
- 全量 7010 实体 / 9909 关系，3.09s 跑完，exit=1（2 条真实数据 bug 待数据侧修复）

### 未尽事项 / 遗留问题
- 2 条真实数据 bug 未修（本任务边界禁止改 data/**）：pl_kaifeng id 重复（kaifeng.yaml 与 core_places.yaml 各定义一份）；p_cbdb_563091 born(1209)&gt;died(1172)（CBDB 桩数据年份错乱）。
- 潜在局限：横跨实体的「自身 born&gt;died」校验仍走 bce 取负逻辑。对王莽（BC45 vs AD23）恰好正确（-45 &lt; -23），但若出现 born=BCE、died=CE 且 died 年份绝对值更大的横跨实体，取负会误判。当前全库仅王莽 1 个横跨实体且不触发，未引入额外抽象。
- 手写关系 BCE 判定仍依赖端点实体推断（数据编码所限），非"纯自身字段"。若后续给关系增加显式 era 字段可彻底消除该依赖。

### 文件级变更清单
- 修改：scripts/validate_data.py（year_hardship bce 分支取负换算；新增 _AD_DIGIT_RE 与 _entity_spans_bce_ce；重写 detect_relation_era；更新 era 段注释）

## 2026-07-11 · v2.0 M1 落地：P0 修复 + 工程地基（GLM 工人流水线首战）

### 做了什么
v2.0 方案获批后完成 M0+M1 全部 9 项任务。两个 P0 显示 bug 修复（谱系星图打不开、地图疆域不显示），
工程闸门建立（32 个后端测试、5 个 E2E 用例、数据校验器），Neo4j 移除，README 重写，数据基线 2 个 bug 修复。
**执行模式首次验证成功：全部编码由 GLM-5.2（火山方舟 Coding Plan，Claude Code 无头壳）完成，
Claude 只写任务书、审 diff、跑验收**——9 个任务 12 次工人运行，2 次打回返工，1 次 API 中断重发。

### 关键决策与被否决的备选
- **星图 P0 根因**：不是数据问题（用户猜双链覆盖率），而是 .graph-panel 缺 flex 骨架 + EntityDetail
  height:100% 抢占全高 → 画布 0 高。数据侧确实覆盖率低（12.6%），归 M4。
- **疆域 P0 根因**：paintTerritories 被 isStyleLoaded() 门禁卡死（代理拦瓦片→永不就绪）。
  r1 用 style.load 事件仍竞态（内联 style 同步解析，监听挂上前已错过）；r2 改确定性三路触发。
- **Neo4j 移除**（ADR-001，docs/decisions.md）：从未实测过的死重；恢复路径 git show v1.0.0:...
- **验证环境教训**：内嵌浏览器面板 rAF 饿死，maplibre style 永不解析——此类验证一律走
  Playwright + 系统 Chrome（channel:'chrome'，免下载 chromium）。
- **CBDB 数据修复方法论**：不猜年份，回查 CBDB SQLite 源，用 c_index_year 证明 born/died 调换。

### 当前状态
- 分支 v2/m1-foundation 全绿：pytest 32 passed / validate errors=0 / build 1.4s / E2E 5 passed
- 现状 tag v1.0.0；工人流水线 scripts/glm/run-task.sh + 任务书在 scripts/glm/tasks/
- 运行：scripts/dev.sh 或 README Quick start

### 未尽事项（M2 起点）
- TimeColumn 虚拟滚动（5,311 人）、/api/links/global 每请求全量扫描 2.6s 无缓存
- 疆域 fill 层被历史 beforeId 插在瓦片层之下，瓦片可用时会被遮挡（T2.5）
- 关系缺 note 1099 例、双链覆盖 12.6%（M4 内容规范起点基线）
- GLM 工人须知：命令白名单勿用 venv 绝对路径以外的写法（已扩白名单）；README 声称的命令都已实测

### 文件级变更清单（M0+M1，10 commits）
- 新增：docs/roadmap-v2.md, docs/decisions.md, scripts/glm/{run-task.sh,tasks/*.md ×10},
  scripts/{dev.sh,validate_data.py}, backend/tests/*.py ×10, frontend/e2e/*.spec.js ×2,
  frontend/playwright.config.js, frontend/.gitignore
- 修改：frontend/src/components/graph/{GraphPanel,EntityDetail}.vue, frontend/src/styles/main.css,
  frontend/src/components/map/MapPanel.vue, backend/{requirements.txt,app/main.py,app/core/config.py},
  docker-compose.yml, .env.example, .gitignore, schema/_registry.md, README.md, PROGRESS.md,
  frontend/package.json(-vis-timeline/-vis-data), scripts/{up.sh,up-no-docker.sh,dev-backend.sh},
  data/entities/persons/p_cbdb_563091.yaml, data/entities/places/kaifeng.yaml
- 删除：backend/app/core/neo4j.py, backend/scripts/import_to_neo4j.py,
  data/entities/places/core_places.yaml, frontend/test-results/.last-run.json(出跟踪)

## 2026-07-11 · M2 性能规模 + M3 谱系星图完全重构（Galaxy 三视图）

### 做了什么
M2 六项：links 缓存热请求 2.6s→3ms、列表载荷 -54.6%、TimeColumn 虚拟化 DOM -37%、
疆域 hover tooltip、「素」本地古风底图（默认，零网络零报错）+ 疆域图层顺序修正、星图朝代聚合（后被 M3 取代）。
M3 按 Rick 钦定范式将谱系星图推倒重构为三视图：
- **图谱 2D**（Obsidian Graph View 范式：局部图深度滑杆/hover 聚焦/拖拽钉住/物理滑杆/类型筛选/路径模式）
- **星云 3D**（移植 Rick 自研 galaxy web 引擎：Worker 力导向/电影相机/Focus/六度飞行控件，1076 星）
- **时空柱 3D**（原创：Z=年代+14 朝代盘带、XY=方位投影、2284 根人物光丝 10 draw calls、
  当前年扫描环↔时间柱双向联动、俯瞰/巡航/跟随一生三相机）
数据地基：/api/graph/spacetime 端点（地理覆盖 78.6%）+ 补齐秦/汉/三国/晋/南北朝/五代十国 6 朝代实体。
Cytoscape 退役。全程 GLM-5.2 工人执行（含 1M 上下文档位跑大任务），Claude 审查验收。

### 关键决策与被否决的备选
- 3D 技术：直接移植 rick-homepage 的裸 three 引擎（vendor 入库再适配），否决引入 3d-force-graph 整库
- 2D 技术：d3-force + Canvas 自绘，否决继续用 Cytoscape（已退役）
- 光丝渲染：InstancedMesh box（可控粗细+raycast 命中），否决 LineSegments（linewidth 平台失效）
- 朝代色：14 雅色单一来源 inkPalette，三视图同源
- 流水线事故与根治：工人自认规划者递归分发（roadmap 分工描述误导）→ run-task.sh 注入角色声明；
  环境变量前缀命令被白名单拦 → 统一 `env VAR=... cmd` 写法并加白

### 当前状态
- v2/m3-starmap 分支全绿：pytest 37 / E2E 8 / validate errors=0 / build 主 chunk 133.75KB（红线 140KB）
- three 独立懒加载 chunk；实体 7016（含 14 朝代）
- 运行：scripts/dev.sh；谱系星图 → 三 tab

### 未尽事项
- 星云打磨：Wander 漫游未接、纸色模式渲染风格（大颗柔边圆盘偏粉彩）待 Rick 真机定夺
- 时空柱：非线性 Z 轴（稠密段放大）为一期后评估项；关系跨丝弧未实装
- 方舟套餐 5 小时配额今日曾打满一次（21:16 重置后恢复）；M5 批量任务需注意配额节奏
- M4（时间轴 zoom/分栏拖拽/帝王世系/事件关联/身份筛选）与 M5 内容规范未启动

### 文件级变更清单（M2+M3 主要项）
- 新增：frontend/src/views/StarmapView.vue, frontend/src/components/starmap/{WebGraph,NebulaView,ColumnView}.vue,
  frontend/src/starmap/engine/*（15 模块）, backend /api/graph/spacetime, data/entities/dynasties/×6,
  docs/starmap-redesign.md, scripts/glm/tasks/t2.*~t3.*
- 修改：backend/app/api/{links,entities,graph}.py+services, frontend TimeColumn/MapPanel/SearchBar/MomentPanel,
  useUIStore(view 字段), e2e 全套(8 用例), README
- 删除：frontend/src/{views/GraphView.vue, components/graph/GraphPanel.vue}, cytoscape 依赖, engine-ref/

## 2026-07-12 · M4 交互与玩法（Rick 点名项全部落地）+ 缓存根因修复

### 做了什么
M4 完成 Rick 点名的全部交互项，均合并 main：
- **时间轴多级缩放**（Ctrl/⌘+滚轮，朝代→帝王在位段→逐年三级 LOD，光标锚定）
- **帝王世系二级导航**（点帝王段跳在位年；43 帝补真实在位年，正史出处，唐玄宗 712–756 非生卒）
- **左右分栏拖拽**（通用 SplitPane，双击复位，比例记忆）
- **人物身份/重要性筛选**（roles[12]+importance；FilterBar 12 chip+重点人物开关；时间柱与图谱共用）
- **跨年事件条带**（61 事件画时间带随缩放伸缩）
- **事件因果关联**（caused_by/led_to 等 24 条带出处，详情卡"前因→后果"链）

### 关键修复（端到端验证抓出，只信工人报告会漏）
- **EntityIndex 改数据不重建**（根因）：_ensure_index 只构建一次，改 YAML 须重启后端。加 TTL(2s) 签名失效自动重建。踩坑 3 次后根治，也解决用户"改数据看不到"。
- **EntityDetail 卡死（潜伏多个里程碑）**：immediate watch 在 relations/causal 等 const 声明前触发 TDZ，星图详情卡一直卡"加载中"，因 E2E 从不断言卡内容而漏网。watch 移至声明后 + 加回归钉子。
- **selectionStore 残留 hover 覆盖选中**：搜索选中后档案卡显示鼠标途经实体。选中清 hover + 350ms 抑制窗口。
- **帝王段用生卒冒充在位**：补真实在位年修正。

### 当前状态
- main 全绿：pytest 40 / E2E 8(含详情卡回归钉子) / validate 0 err / 实体 7016 关系 9934
- 流水线：方舟配额打满自动降级 Anthropic(opus/sonnet)；工人 prompt 注入角色声明

### 未尽事项
- M4 剩余（非 Rick 点名，可选）：人物详情页深化、事件长河第三视图、路径讲解卡+分享
- M5 内容重扫（回应"内容过简"大头）：关系补 note 关联逻辑、生平结构化 life_events、事件/战役扩容、CBDB 关系补语义——未启动
- 星云纸色模式渲染风格待 Rick 定夺（粉彩感）；Wander 未接；时空柱关系弧未实装

## 2026-07-12 · M5 内容重扫 + 通史贯通(秦汉BCE→2008) + 对抗核查流水线

### 做了什么
从 Rick 报的一个"吕雉跨纪元/公元前事件为空"显示 bug 出发，本会话把知识库从"止于清 1912、公元前错乱"扩成一部**从秦汉 BCE 到 2008 的完整通史**，并建立了一套内容质量流水线。全部合并 main。

**修 bug + 扩通史**：
- BCE 年份归一化：秦汉 BCE 实体年份存正数、前端按 signed 绘制→BCE 被画到 CE 区。迁移 50 实体年份取负(scripts/migrations/2026-07-12-bce-normalize.py)。吕雉/汉武帝/12 个 BCE 事件已正确落公元前。
- 时间轴 1912→2026，ERAS(在 palettes.js)加民國/共和國带 + d_minguo/d_prc 朝代实体。
- 近代(1912-1949)：46 人+20 事件+55 关系(孙中山/蒋介石/鲁迅/辛亥/五四/抗战…)。
- 现代(1949-2008)：22 人+14 事件(毛泽东/邓小平/钱学森 + 建国/改革开放/港澳回归/北京奥运)。

**内容质量流水线(Ultracode 模式)**：GLM 便宜生成 → validate_data.py content linter + --strict-seed 闸门 → Anthropic 多 agent 对抗核查(史实+中性) → 修正 → 提交。
- T5.3 种子关系补关联逻辑 235 条：核查 223 clean，揪出 12 个**潜伏在原始数据里**的错误(后金/后晋实体混用、冯道仕后梁伪造边、章邯归属秦二世、李光弼收复两京张冠李戴、succeeded_by 方向不一致)→ T5.4 全修。
- 近代内容核查：96/123 clean，27 问题(19 史实错+6 POV+2)→ T5.7b 全修(冯国璋非留德、孔祥熙"四大家族"/汪精卫"汪伪"/九一八不抵抗归因等 POV 中性化)。
- 现代内容(审查方自撰,因 GLM 拒绝敏感生成)核查：39/41 clean，2 处任期年份错(毛泽东主席任期1945非1949)已修，0 POV。

### 关键决策
- **BCE 编码统一为负数(signed)**：与朝代实体/前端轴一致，弃"正数+文本BC标记"。
- **现代史审查方自撰**：GLM coding 端点对当代政治史空产出(20 轮 2014 token)，审查方按严格中性自写，但**同样过对抗核查**(不因自撰免检，果然揪出 2 个自身错误)。
- **对抗核查值 4.5M+ token**：两轮共揪 60+ 真错，含 12 个原始数据潜伏错误+若干 POV 立场词——只看工人报告绝对发现不了；历史准确性/中性是此项目立身之本，token 不是约束(Ultracode)。

### 当前状态
- main 全绿：validate errors=0(7123 实体/9993 关系)、pytest 40、E2E 9、首屏 JS 达标
- 通史时间轴 秦汉BCE(前221)→2008，各段有人物/事件/关系；内容经生成+对抗核查双关
- 运行：scripts/dev.sh 或 README；改数据后端自动失效(无需重启)

### 未尽事项
- 现代段仅到 2008，人物 22/事件 14 为核心集(可扩)；在世当代政治人物未做(中性顾虑)
- 公元前事件仍可扩(现 12 个,先秦更早段薄)；CBDB 4892 桩 bio 未升级(方案A外)
- 内容规范 content-spec 的 life_events 结构化尚未全量铺开(仅 schema 就绪)
- 星云纸色渲染偏粉彩、Wander/时空柱关系弧等 M3 打磨项挂起

### 文件级变更(M5,主要)
- 新增：docs/content-spec.md, scripts/audit_content.py, scripts/migrations/2026-07-12-{bce-normalize,contemporary-gen}.py,
  data/entities/dynasties/{minguo,prc}.yaml, data/entities/persons/×68(近代+现代), data/entities/events/×34,
  data/relations/{modern,contemporary}.yaml, scripts/glm/tasks/t5.*
- 修改：50 实体 BCE 年份取负, scripts/validate_data.py(content linter), frontend TimeColumn/palettes.js(轴 2026),
  data/relations/(种子补 note + 12 修复), data/entities/polities/houjin.yaml(后金→后晋)

---

## 2026-07-15 · M6 通史纵深：先秦回溯 + 帝王轴兼容 + 事件分类落库（进行中）

Rick 追加四点优化（时间覆盖太窄不含先秦/人物事件密度不足/事件分类粗且互相压盖/缺事件因果线索）。本会话完成先秦前段与配套前端，其余分期推进。

### 做了什么
- **事件分类 5 族 14 类定稿**（军事 battle·conquest·rebellion｜权力 coup·succession·purge｜治理 reform·institution｜对外 diplomacy·treaty·territory｜文明 culture·religion·disaster + other 兜底），写入 schema/event.yaml。
- **先秦回溯**（此前全库最早止于范增 -277，零夏商周）：
  - 三代(夏商西周)：20 人 + 3 朝代 + 3 政权 + 2 战役 + 8 事件 + 4 地点 + 关系；夏商模糊纪年 + ext.disputed，共和元年(前841)起精确。
  - 东周春秋：东周 + 齐晋楚秦燕鲁宋郑吴越 10 诸侯国(割据政权) + 霸主诸子 17 人。
  - 战国：韩赵魏 + 变法纵横名将诸子（GLM 生成中）。
- **时间轴前端配套**：轴原点 -221→-2100（先秦可上轴）；ERAS + 跳转 chip 加夏商西周春秋战国；帝王段取数改"在位优先、生卒回退"，兼容只有在位年、无生卒的上古帝王(武丁/成王/厉王等现可上轴)；新增 monarch(君主)身份供诸侯国君标注；修复事件因果线 overlay(getNeighbors 漏 import 致静默失效)与事件悬浮置顶。
- **对抗核查**：每批 3 路 sonnet skeptic 逐条查(史实/出处/中性/格式)。三代修 13、春秋修 18——多为**出处张冠李戴**(史记细节误引左传等)、托名之作(孙子兵法/墨子/道德经)加"旧题/相传"、老子身份存疑、卧薪尝胆据史记订为尝胆、菼执→鸠浅。

### 关键决策
- **回溯下界=夏商(模糊纪年)**：Rick 定，商及以前"约前N世纪"+disputed，前841 后精确。
- **上古帝王只有在位年**：前端原逻辑硬要生卒→上古帝王全被丢弃(正对应"帝王坐标系不全")。改为 reign 优先。单端点在位年(禹/汤/盘庚/帝辛)暂作细标记，待 t6.2 帝王世系全补时补在位区间。
- **manifest 约束式任务书**：Claude(opus)定 roster+日期+信息源清单，GLM 只填 bio/格式，把幻觉面压到最小——三代/春秋各仅需 13/18 处修正，较 M5 显著更干净。
- **surgical 前端亲自做**：轴原点等高爆破半径核心改动 Claude 直接改 + Playwright(系统 Chrome)实测，不走 GLM 往返(既存 in-app 浏览器因 maplibre 抢 rAF 卡死)。

### 当前状态
- 分支 v2/m5-content：validate errors=0(7201 实体/10053 关系)、pytest 40 通过。
- 预览 http://localhost:59834（本 worktree 前端 → :8002 worktree 后端）；时间轴现从前2000+ 起，夏商西周事件/帝王段正确落轴。
- 提交：fdffce0(三代)、1636607(前端轴+帝王段+monarch)、cfe79bf(春秋)；均对抗核查后。

### 未尽事项
- **战国批** GLM 生成中(task b8qn1tzzb)，待核查→提交。
- **帝王世系全补(t6.2)**：现仅 43 emperor 有在位年，唐缺李世民/晋 0/汉 3-of-29；单端点上古帝王待补区间。
- **现当代加密**：Rick 明示个人用途、不做政治正确避讳、中性事实广覆盖(GLM 拒答段 Claude 亲写)。
- **阶段2**：156 事件重扫归 14 类 + battle/war 野值与 34 Battle 实体收口 + 前端 category→配色(族)/图标(类)。
- **阶段3**：事件因果线索(含燕云割让→收复)，preceded_by(51 条野类型)归并。
- **阶段4**：帝王分道去压盖、事件单点/跨年统一视觉、事件碰撞避让、右栏"此刻在世"改随游标年份(现随选中实体，前950 仍显李白同代)。
- **先秦谋臣**(妇好/姜尚/周公等无纪年)缺 floruit 锚点上不了人物轴；starmap inkPalette.js 未延至先秦。

### 文件级变更(M6 本会话)
- schema：event.yaml(14 类枚举+family)、person.yaml(monarch 身份)
- 新增数据：dynasties/{xia,shang,zhou}、polities/{xia,shang,xizhou + dongzhou,qi/jin/chu/qin/yan/lu/song/zheng/wu/yue_state}、persons ×37(三代 20+春秋 17)、events ×13、battles ×4、places ×4、relations/{preqin_sandai,preqin_chunqiu}.yaml
- 前端：TimeColumn.vue(ORIGIN 轴原点/帝王段 reign 优先/eraChips 先秦/getNeighbors import/hover z-index)、palettes.js(ERAS 先秦带)、FilterBar.vue(monarch)
- 任务书：scripts/glm/tasks/t6.1{a,b,c}
- .gitignore(.playwright-mcp/)、.claude/launch.json(前端代理 :8002，本地未入库)

---

## 2026-07-15/16 · M6 通史纵深：分类落到视觉、因果线索、地图专项，以及一串「静默丢弃」

### 做了什么
把 Rick 提的 4 点优化从数据一路做到界面，中途查出并修掉了一批**用户看不见、系统也不报错**的丢数据缺陷——它们才是这两天最大的收获。

给非开发者的一句话：**时间轴上原本"没有"的东西，多半不是没收录，而是被前端悄悄滤掉了**。秦始皇、关羽、张良、萧何、卫青、白起、屠呦呦、胡锦涛……一个都不在人物轴上，库里却都有。

### 关键决策与被否决的备选

**1. 事件分类：17 类 → 18 类，且不用「亂」**
- `rebellion` 定为「民变·起义」，印章取「民」而非「亂」——「乱」是治者视角（辛亥革命非乱），「义」是举事者视角，「民变」只陈述发动者、不预判正当性。
- 后来发现挂着 `rebellion` 的 20 条里有 5 条是军政集团内战（安史/七国/侯景/二次革命/护国）——给安禄山盖「民」章同样是错的。**没有新增类**：八王之乱、靖难之役早已归 `war`，按先例归位即可。
- 配色上线后暴露「治世」无处可归（贞观之治被标成 `reform` 变法，是事实性错误）→ 经 Rick 拍板加第 18 类 `prosperity`。

**2. 族色：否决「复用实体色」，改专设**
- 复用方案里军事(31°)/权力(12°)/治理(47°) 三个色相全挤在暖色带、亮度还都是 L≈40-45，而这恰是最大的三族（占 71% 事件）——「族」这层粗读等于没有。
- 改为 5 族专设 `--fam-*`，最小色相间隔 **59°**（原 16°）；军事仍锚在 H=31 以保住 Battle 实体的视觉收口。

**3. 因果 vs 线索：否决「把割让与收复连成因果」**
- Rick 要「燕云十六州的割让与收复」相连。但二者隔 432 年、无因果路径——明北伐终结了燕云问题，并非被割让所「导致」。硬连一条跨 432 年的 `led_to` 是史学家不会写的陈述。
- 故分成两套正交机制：**因果**(`led_to`) 答「谁引发了谁」，**线索**(`ext.threads`) 答「哪些事同属一个历史问题」。选中时取并集：割燕云 → 串出 11 环、跨 432 年，终点是 1368 明北伐克大都。

**4. 行军箭头：先补数据，不编方向**
- Battle 原有 combatants/commanders，但无行军起讫。**没有数据而画箭头即是编造方向**，故先加 `march` 字段（逐段 from→to + 出处），只补史载明确的 5 役 6 段。
- 明北伐本为四步（山东→河南→潼关→大都），但「山东」「潼关」无 Place 实体——**不为画箭头而编 id**，只落两段有实体可依的。迁移脚本护栏当场拦下了我编的 `pl_shandong_ming`。

**5. 现当代：直书，不用委婉语**
- 四五运动写明当局「出动民兵、警察与卫戍部队清场抓人」、定性「反革命政治事件」，**同时写 1978 年平反为「完全的革命行动」**——定性与平反都摆出，读者自行判断。
- 庐山会议 → 大饥荒 是这批因果里最重的一条：**压下正确的批评本身就是死因之一**。

### 一类反复出现的缺陷：静默丢弃
同一个 filter 的某个方向没人查过，数据就人间蒸发，且不报错。逐个撞上来的，共 6 处：

| 缺陷 | 影响 |
|---|---|
| `/api/entities` limit 上限 2000，而 4892 个 CBDB 人物吃光配额 | 种子人物只剩 301/583 上轴 |
| filter 要 born+died 俱全，在世者无卒年 | 屠呦呦/胡锦涛等 7 人消失 |
| 同上，卒年已知而生年不可考者 | **91 人消失，含秦始皇、关羽、张良、萧何、卫青、白起、李斯、管仲、赵高** |
| 同上，只有在位年的上古君主 | 禹/汤/武丁/齐桓公/秦穆公等 21 人消失 |
| `reign_start/end` 每人一组，装不下重祚 | 1457-1464(明英宗天顺)、710-712(唐睿宗复位) 帝王带是空的 |
| fields 白名单漏列 `reign_start` | filter 条件恒为 false，上一条修了也不生效 |

**教训**：新增派生状态要堵住所有绕过它的赋值口（`loadFromUrl` 直接赋 `year` 就绕过了 `settledYear`）；同一 filter 的两个方向要一起查。

### 我在诊断中犯的错（都已纠正，记下防再犯）
- 用 `window.fetch` 计数，而 api/client 走 axios(XHR) → 测得「0 请求」
- 用 performance resource entries 计数，而被 CORS 拦截的请求不计入 → 又一次「0 请求」
- `--noproxy *` 未加引号被 zsh 展开成文件名 → 误判「直连无响应」
- 据小图目测称箭头方位角错 → 用变换矩阵反解，夹角 0°，是我看岔
- 手工裁定时凭记忆猜 id（`e_zhoushizong_gaige` 实为 `e_zhou_reform`）→ 护栏静默失效

**共性：0 或异常值先怀疑探针；目测不算证据。**

### 当前状态：能跑什么
- 前端 `.claude/launch.json` 的 frontend 配置（已带 `VITE_DEV_PROXY_TARGET=:8002`）；后端 :8002 服本 worktree 数据
- **时间轴**：719 种子人物全部可上轴（此前 301）；261 帝王、47 政权，十朝在位链连续；251 事件/战役分 5 族 18 类，族=配色、类=印章字形；四档缩放 0 重叠
- **线索**：选中事件串因果链+线索（燕云 11 环跨 432 年；庐山会议 11 环 1957→1978）
- **地图**：占比可拖、「放」键一键放大为主体（9.2%→51.8%）；选中事件落族色印章 + 行军箭头（5 役）
- 验证：`python3 scripts/validate_data.py`(errors=0, 7442 实体)、`uv run --with pytest ... pytest -q`(44 passed)、`cd frontend && npx vite build`

### 未尽事项与已知问题
- **谭其骧底图待 Rick 在真 Chrome 确认**：Playwright 的 Chromium 不走系统代理，`tile.osgeo.cn` 需经代理才可达；curl 走代理 HTTP 200 正常。OSM/CARTO/Esri 在自动化里可达。
- **:8002 未带 `--reload`**，且该端口挂着 3 个 uvicorn 遗留进程——搜索排序等后端改动在浏览器里看不到，需 Rick 重启。
- **`march` 仅 5 役**（军事族共 109 事件）：铺开需逐条查史料补起讫，纯内容活。
- **因果覆盖 132/251 孤立**；`ext.threads` 仅燕云一条。
- **事件无 importance 字段**：全景只显 85/251，选谁靠「因果度数+描述长度」代理。
- **Place 重复**：41 组纯种子同名（洛阳 6 / 长安 4 / 沛县 4——每有一人籍贯在此就新建一个）+ 182 组 CBDB 内部重复。不在 Rick 的 4 点内，未动。
- **十大大将缺 4 位**（谭政/张云逸/王树声/许光达）。
- 「后唐庄宗伶人乱政」挂 `institution`（印「制」）不准——它是衰政，而 prosperity 无反面；全库仅此 1 条，为 n=1 加第 19 类不值。
- starmap `inkPalette.js` 未延至先秦；谱系星图节点在无 GPU 浏览器黑屏（待 Rick 用真实浏览器确认）。

### 文件级变更（本会话 37 个提交）
- **schema**：event.yaml(18 类 + prosperity + march)、battle.yaml(category + march)、person.yaml(floruit_start/end)、relations.yaml(禁用 preceded_by 表事件因果)
- **前端**：TimeColumn.vue(碰撞避让/溢出槽/卡片 22px/线索轨道/四态时间锚/人物名贪心)、MapPanel.vue(事件标注/行军箭头/占比/maplibre CSS/CORS)、MomentPanel.vue(纵向分栏/settledYear/关系 key)、SplitPane.vue(泛化 vertical)、palettes.js(EVENT_CATS 18 类 + FAMILY_HUE 专设族色)、useTimeStore.js(settledYear 防抖)、useUIStore.js(mapExpanded)、client.js(getRelations)、main.css(族色默认值)
- **后端**：entity_service.py(搜索相关性排序)、tests/test_search_rank.py(4 条回归钉子)
- **数据**：+18 现当代人物、+12 现当代事件、+2 明代事件、22 人先秦纪年、91 人 deathOnly 上轴、258 帝王、事件全量重扫 18 类、燕云线索 9 成员、march 5 役
- **迁移脚本**（scripts/migrations/）：retag-round2、merge-dup-battles、causal-unify、thread-yanyun、preqin-floruit、march-routes —— 均幂等，多数带「id 未命中即 exit(1)」护栏

## 2026-07-16 全库外键完整性：70 处引用指向虚空，而验证器报 errors=0

### 做了什么
把「实体之间的引用」这条链从头查了一遍，之前从没人查过。发现验证器只检查
`relations/*.yaml` 里的关系两端，却完全不看实体内部写的引用——比如「隋的都城是哪里」
「陆九渊的籍贯是哪里」「赤壁之战有哪些政权参战」。于是这些引用指向不存在的东西多年，
总览始终报「错误 0」。这不是验证器写错了，是它从没被要求查这个方向。

修完的账：

| 指标 | 本轮前 | 本轮后 |
|---|---|---|
| 悬空外键（指向不存在的实体） | 70 | 0 |
| 类型不符（如「亡于哪个政权」填了个朝代） | 23 | 0 |
| 同名重复地点组 | 53 | 3（坐标不同，同名未必同地，留人工判） |
| 同名重复人物组 | 22 | 0 |
| 政权数 | 74 | 86 |

新建 24 个实体：8 人（袁崇焕、丁汝昌、也先、杨镐、伊东祐亨、冉闵、姚苌、冒顿单于）、
12 政权（匈奴、瓦剌、日本、英国、冉魏、后秦、陈友谅的汉、朱元璋的吴，及曹操/刘备/
孙权/袁绍四个军政集团）、4 地点。这些不是凭空加的——它们的引用早就写在事件档里，
只是实体一直没建。

### 关键决策与被否决的备选

**重复地点只并「同名且同坐标」的。** 53 组重复的根因是建模错误：`category: birthplace`
把「人和地的关系」写成了「地点的属性」。洛阳本来是都城，有人要拿它当籍贯，发现类型不对，
于是新建一个「籍贯类」的洛阳——每来一个人就多一个同名洛阳。实测 163 个 birthplace
地点中 149 个只被 `person.birthplace` 引用。已从 schema 删除该枚举值并写入根因注释防再犯。
剩下 3 组（巨鹿/建州/涿郡）坐标不同，可能确非一地，没并。

**重复人物取并集而非二选一。** 22 组的模式极整齐：每组必是「一条有在位年、无月份」+
「一条有卒月、无在位年」，全是五代十国/辽/金 君主——两批导入各写各的，id 约定还不同
（`p_liu_chong` vs `p_liuchong`），谁也不知道对方存在。所以合并是把两边的字段合起来，
不是挑一个留下。另有一组不同名同人：徐知诰即李昪（937 代吴建齐，939 复姓李）。

**四个军政集团建成 Polity，代价记在明处。** `k_caowei_pre` 这类 `_pre` id 是一套没写完的
约定，指政权正式立国前的势力（曹操 192-220 是汉丞相，曹魏 220 才立国）。备选是把
赤壁之战的参战方填成「东汉 vs 东汉」——名义正确但等于没说。选择建为 Polity，起止取其
作为独立军政实体的存续期，用描述写明其非独立政权。**Polity 目前没有字段能区分
「立国政权」与「军政集团」，这个分野只能靠文字承载**，是已知缺陷。

**顺带修了三处史实错误**（不是笔误，是内容错）：
- 西晋「亡于」东晋——东晋是继承者不是终结者，西晋 316 亡于刘曜的前赵
- 鄱阳湖之战的参战方里有元——1363 年是朱元璋灭陈友谅，元不在场
- 白马驿之祸（905）的涉事政权填了后梁——后梁 907 才立国，当时朱温还是唐臣
- 李从珂卒年 937-01 而后唐亡于 936-11——他是随后唐灭亡自焚的，同一件事。全库政权链
  （后汉 951-01 → 后周 951-02）用的是农历口径，937-01 是公历换算混进来的，已统一

**验证器新规则的反证。** 故意把隋的都城改成不存在的 id、把「亡于哪个人」填成一个政权，
两种违规都被抓住（E_DANGLING_REF / E_REF_TYPE），还原后回到 0。不做这步的话，
新加的检查可能只是个装饰。

### 当前状态
- `python3 scripts/validate_data.py` → entities=7368 errors=0 warnings=20395
- `uv run --with pytest --with httpx --with fastapi --with pyyaml pytest -q` → 44 passed
- `cd frontend && npx vite build` → 通过

### 未尽事项
- **`Faction.core_members` 存人名而非 id（123 处）**，与已存在的 `member_of`/`leader_of`
  关系（54 条）是同一事实的两套表达。正解是迁进 relations 并删掉该字段，但其中 35 个
  人名在库中尚无 Person 实体（顾宪成、杨涟、左光斗、高攀龙、胡林翼、彭玉麟、韦昌辉…），
  **先删字段就是丢信息，须先补人再迁移**。现降级为具名 WARN 记在验证器的
  `_REF_PENDING_MIGRATION`，补完人即移除，该项自动变回 ERROR。
- **`EntityDetail.vue:106` 的「核心成员」是死链**——它把人名当 id 渲染成可点链接，
  点了没反应。名字能看见，所以不算白屏，但点击无效。随上一条一起修。
- **Polity/Dynasty 同名并存 12 组**。不全是冗余：`d_song`（宋）罩着 `k_beisong`+`k_nansong`
  两个政权，是「朝代 ⊃ 政权」的合理层级；但 `d_jin_jurchen` 与 `k_jin` 起止完全相同
  （1115-1234），纯冗余。需连同「Polity 缺『立国/集团』字段」一起定，是同一族结构问题。
- **农历/公历口径在库中混用**。本轮只修了李从珂一处（因其与政权链直接冲突），
  同类问题规模未测。
- Faction 自身也有重复：`f_heshuo`/`f_heshuo_3_zhen`（河朔三镇）、`f_eunuch_tang`/
  `f_late_tang_eunuchs`（晚唐宦官集团）；`p_yangwu_group` 是 Faction 却挂 `p_` 前缀。
- 南京有 4 个地点实体（金陵/建康/建业/应天府）——同城异代名，是该合并还是该保留
  历时性，未定。本轮的合并规则（同名同坐标）碰不到它们。
- 探针错误又中一次：用 `\bpl_[A-Za-z0-9_]+\b` 抓 id，吃不进 `pl_yan'an_han` 的撇号，
  于是把 `pl_yan` 报成悬空。**0 或异常值先怀疑探针**——这次是「凭空多出一个悬空」。
  该 id 已改为 `pl_yanan_han`（全库唯一一个带撇号的 id）。
- 护栏两次当场拦住我猜的 id（`pl_ye` 实为 `pl_yecheng`、`e_baimayi_zhihuo` 实为
  `e_baima_yi`）。「裁定 key 未命中即 exit(1)」这条继续保留。

### 文件级变更清单
- **schema**：place.yaml（删 birthplace 枚举值 + 根因注释）
- **scripts**：validate_data.py（新增 `ref_fields()` + 内嵌外键检查 E_DANGLING_REF /
  E_REF_TYPE + `_REF_PENDING_MIGRATION` 具名 WARN）
- **迁移脚本**（scripts/migrations/）：2026-07-16-merge-dup-places、-fix-inline-refs、
  -fix-inline-refs-2、-merge-dup-persons —— 均幂等，带「裁定 key 未命中即 exit(1)」护栏
- **数据**：新建 24 实体（persons/{yuanchonghuan,dingruchang,yexian,yanghao,ito_sukeyuki,
  ranmin,yaochang,maodun}、polities/{caowei_pre,shuhan_pre,dongwu_pre,yuanshao_pre,ranwei,
  houqin,xiongnu,waci,riben,britain,wu_zhu,han_chen}、places/{jiangnan,jinxi_fuzhou,
  dongguan_yuan,lujiang_ding}）；删除 75 个重复地点 + 23 个重复人物；约 420 个文件重指

## 2026-07-16（续）Faction 成员：123 个人名里 32 个查无此人，而界面把人名当链接

### 做了什么
还上一轮记下的债。`Faction.core_members` 存的是人名字符串（「周敦颐」「杨涟」），
schema 却声明它是「指向 Person 的引用」。两个后果：

1. **123 个名字里 32 个在库中根本没有对应的人**，而库自己不知道——因为没人查过。
2. **界面把人名当 id 渲染成可点链接**：在理学派详情里点「周敦颐」，什么也不会发生。
   名字能看见，所以不像坏了，但点击一直是死的。

这一轮补齐了那 32 人，把成员关系迁进受校验的 `member_of`/`leader_of`，删掉了这个字段，
并让详情页的「核心成员」改由关系驱动——现在点得动了。

| 指标 | 本轮前 | 本轮后 |
|---|---|---|
| Faction 带 core_members 字段 | 26 | 0（字段已删） |
| 成员关系（member_of + leader_of） | 54 | 126 |
| 同名重复 Faction 组 | 2 | 0 |
| 种子人物 | 704 | 736 |

新建 32 人：顾宪成、杨涟、高攀龙、崔呈秀、田令孜、杨复恭、俱文珍、王守澄、郑覃、李弼、
罗绍威、孟楷、葛从周、述律平、和凝、李崧、宋齐丘、冯延巳、孙晟、韩熙载、徐温、李继勋、
王审琦、韩重赟、黄庭坚、张浚、汤和、张玉、朱能、韦昌辉、胡林翼、彭玉麟。

### 关键决策与被否决的备选

**为什么不直接把人名改成 id 就完事。** 那是十行的活，也能立刻修好死链。否决的理由是它会
把「同一事实两套表达」这件事坐实：`member_of` 关系已经存在 54 条，其中 44 条与
core_members 完全重合。关系那套受校验、能带 note 与起讫年；字段那套不受校验。留两套，
下次照样分叉。所以选择关系归 relations，删字段。

**为什么先补人再删字段，而不是反过来。** 那 32 个名字是真实历史人物，先删字段就是把
它们丢了。上一轮把这条债降级成验证器里一条具名 WARN 而不是让它变绿，就是为了这个顺序。
现在补完了，验证器的豁免（`_REF_PENDING_MIGRATION`）已整个删除，不留残留。

**成员关系不写 since/until。** 成员起讫年多不可考，编不如缺。既有关系带 since/until 的
不动。迁移脚本设了硬护栏：任何一条解析不出人、或缺 note，整体拒绝迁移——不留半拉子。

**顺带清掉的重复**：两个「晚唐宦官集团」（f_eunuch_tang 750-905 / f_late_tang_eunuchs
758-903）与两个「河朔三镇」是近乎逐字的复制，已合并（成员取并集）。`p_yangwu_group`
是个 Faction 却挂着 `p_` 前缀（`p_` 是 Person 的），已改。义社十兄弟的「韩重斌」是
「韩重赟」之误（宋史·韩重赟传），已改。

### 当前状态
- `python3 scripts/validate_data.py` → entities=7398 relations=10182 errors=0 warnings=20301
- `uv run --with pytest --with httpx --with fastapi --with pyyaml pytest -q` → 44 passed
- `cd frontend && npx vite build` → 通过
- **浏览器实测**（这是死链修复，只看构建不算数）：打开东林党详情 → 「核心成员」列出
  顾宪成（加粗，领袖）/杨涟/左光斗/高攀龙，note 进 tooltip → **点「杨涟」跳转到其详情
  （生卒 1572–1625、生平「劾魏忠贤二十四大罪」）**，控制台无报错。
  另见：袁崇焕、顾宪成、高攀龙、杨涟 已出现在 1600 年的「此刻在世」——上一轮与本轮
  新建的人物确实上了时间轴。

### 未尽事项与已知问题
- **本地起后端必须显式给 `DATA_DIR`/`SCHEMA_DIR`**。默认值是 `/app/data`（容器内路径），
  本地不设就静默加载 0 个实体、API 全返回空。这次差点误判成自己的改动出错。
  验证命令：`DATA_DIR=$PWD/data SCHEMA_DIR=$PWD/schema uvicorn backend.app.main:app --port 8002 --reload`
- **谱系星图里年份显示为 −2100**，而 URL 与时间柱都是 1600。本轮顺手看到，未查，
  与本轮改动无关。
- Polity/Dynasty 同名并存 12 组、Polity 缺「立国/集团」字段——两者同族，仍待一并定。
- 农历/公历口径混用，规模未测。
- 南京 4 个地点实体（金陵/建康/建业/应天府）同城异代名，合并与否未定。
- 3 组坐标不同的同名地点（巨鹿/建州/涿郡）留人工判。

### 文件级变更清单
- **schema**：faction.yaml（删 core_members 字段 + 根因注释）
- **scripts**：validate_data.py（撤销 `_REF_PENDING_MIGRATION` 豁免及其 WARN 管道）
- **迁移脚本**（scripts/migrations/）：2026-07-16-merge-dup-factions、-add-faction-members、
  -core-members-to-relations —— 均带护栏（新建 id 冲突、同名已在库、roles 越界、
  未解析项即整体拒绝）
- **前端**：EntityDetail.vue（核心成员改由 member_of/leader_of 关系驱动，领袖加粗，
  note 进 tooltip，Faction 进详情即预取关系）、types/schema.ts（删 core_members 声明）
- **数据**：+32 人物；+71 条成员关系（data/relations/faction_members.yaml）；
  合并 2 组重复 Faction；26 个 Faction 删 core_members 字段

## 2026-07-16（续二）朝代着色把 748 个北宋人涂成了辽人

### 做了什么
本来是去处理「Polity 与 Dynasty 同名并存 12 组」这个结构问题，查着查着发现它不是冗余：
Dynasty 是**断代骨架**（19 个，覆盖夏→共和国，含三国/晋/南北朝/五代十国这类"时期"），
`includes` 关系（Dynasty → Polity）是它的索引机制，后端 `DynastyIndex` 靠它给人物归朝代、
驱动星图的「朝代着色」。类型没问题，问题在别处——

**归属是按「年份落在哪个朝代的起止区间」算的，而这些区间彼此重叠。**
辽 916~1125 与宋 960~1279 重叠 165 年，因为它俩本来就并存。匹配逻辑是「按 founded 升序
取首个命中」，辽（916）排在宋（960）前面，于是 **960~1125 年出生的人全被判成辽人**。

实测：「辽」分到 **748 人**，是最大的一档，超过唐（553）和宋（427）。
而这库里真正的辽人只有 32 个。另有 13 人落在空档（如 1234 金亡~1271 元立）而无朝代。

根子在于：**1050 年的人是辽是宋，取决于他在哪，不取决于他在何时。年份判不了。**

答案本来就在数据里：4804 个人物带着 `dynasty_ref`，指向其实际政权（北宋 2611、唐 1333、
明 467、清 131、元 96、契丹/辽 32）。但这个字段**从未在 schema 里声明**——所以不受校验、
悬空了 21 处也没人知道，更没人拿它来算归属。

| 指标 | 本轮前 | 本轮后 |
|---|---|---|
| 「辽」分到的人物 | 748 | 32（= dynasty_ref 里真辽人数） |
| 「宋」分到的人物 | 427 | 2709 |
| 未分类人物 | 2894 | 99 |
| includes（Dynasty→Polity） | 14（覆盖 9/19 朝代） | 84（覆盖全部 Polity） |
| 悬空 dynasty_ref | 21 | 0 |
| 同名重复 Polity 组 | 2 | 0 |

### 关键决策与被否决的备选

**否决「把辽/金从 Dynasty 里删掉」。** 那样年份区间就不重叠了，一劳永逸。但辽史/金史是正史，
删掉它们是拿实现方便去改历史。改的是实现：归属优先查 `dynasty_ref`，年份只作回落。

**否决「按正统排序」。** 让宋"赢"过辽听起来像在判正统——那是立场，不是我该塞进代码的东西。
实际做的是：并存朝代（辽/金）在**年份回落**匹配时排到最后再试。这修的是「先到先得」这个
实现细节，不是历史判断——真正的辽人都带 dynasty_ref，走查表，根本走不到回落那条路。
排序只影响那些没有 dynasty_ref、只能靠年份猜的人，此时取多数情形是唯一诚实的选择。

**否决「前端改 DYNASTY_RANGES 的顺序」。** 那是最省事的镜像修法，但该数组的下标与
DYNASTY_COLORS 对齐（设计上"时间相近者视觉相近"），改序会连带改色。改的是判定逻辑：
前端也走 dynasty_ref → includes 查表，年份两轮回落（先非并存、再并存）。
映射从 `/api/relations?type=includes` 取，不在前端另抄一份——那是漂移的开始。

**顺带清掉**：重复 Polity 两组（北周 d_zhou_north/k_bei_zhou、陈 k_chen/k_nan_chen，
起止只差月份精度）；三个 id 前缀与 type 不符（`d_zhou_north`/`d_zhou_wu` 是 Polity 却挂
Dynasty 的 `d_`；`e_beijing_bao_wei` 是 Battle 却挂 Event 的 `e_`）。
前两轮查过重复地点、人物、Faction，**唯独没查过重复 Polity**——又一个"没人查过的方向"。

### 当前状态
- `python3 scripts/validate_data.py` → entities=7396 relations=10254 errors=0 warnings=20283
- `uv run --with pytest --with httpx --with fastapi --with pyyaml pytest -q` → **48 passed**
  （44 + 新增 4 条朝代归属钉子）
- `cd frontend && npx vite build` → 通过
- **反证**（钉子不证明会响就只是装饰）：把修复退回（恢复先到先得 + 忽略 dynasty_ref），
  测试当场报 `AssertionError: 辽 分到 748 人 —— 它又把并存的宋人吞了`；还原后 48 passed。
- **浏览器实测**：星图开「朝代着色」，苏轼（1037–1101）描边为竹青（宋）而非苔绿（辽）。
  但两色都偏绿，肉眼不算证据，故另在页面内跑判定逻辑对照：
  1000/1050/1100/1120 年均由「辽」纠正为「宋」，而 `k_liao → 辽`、`k_jin → 金` 查表不变。

### 未尽事项与已知问题
- **前端只有 14 个朝代的色板**（秦…清），夏/商/周/民国/共和国无色，落灰。故政权→朝代
  查表在前端只命中 65/84。这是既有设计，未改。
- **`k_nanbeichao`（南北朝 420~589）是"时期"却被建成 Polity**，与 `d_nanbeichao` 重复；
  `k_song`（宋 960~1279）与 `k_beisong`+`k_nansong` 表达同一段。本轮暂各归其断代，
  该不该留作 Polity 未定。
- **`dynasty_ref` 名字有误导性**：它指向的是 Polity 不是 Dynasty。4804 个人物在用，
  改名的代价大于收益，故在 schema 注释里写明。
- **长安有多个地点实体**（`pl_chang_an` / `pl_chang_an_pre_tang` / `pl_chang_an_xiwei` /
  `pl_daxing`），本轮合并重复 Polity 时撞见。同城异代名，与南京那组（金陵/建康/建业/
  应天府）是同一个问题：地名的历时性该合还是该分，未定。
- 谱系星图右上角年份显示 −2100（URL 与时间柱都是 1600），上一轮记下的，仍未查。
- Polity 仍缺「立国政权 / 军政集团」的区分字段（曹操集团之属只能靠描述文字承载）。
- 农历/公历口径混用，规模未测。

### 文件级变更清单
- **schema**：person.yaml（声明 `dynasty_ref: ref → Polity` + 注释说明其名与实不符）
- **后端**：api/links.py（`_build_polity_dynasty()` 查表；`DynastyIndex.build` 改为
  dynasty_ref 优先、年份回落；`_COEXISTING_DYNASTIES` 并存朝代降级排序）
- **测试**：backend/tests/test_dynasty_assign.py（4 条钉子，已反证会响）
- **前端**：starmap/engine/inkPalette.js（`COEXISTING_DYNASTY_IDX`、`DYNASTY_NAME_TO_IDX`
  + 区间重叠的说明）、components/starmap/WebGraph.vue（`dynastyIdxOf` 改为查表优先、
  两轮年份回落；personMeta 增补 dynasty_ref 与 includes 查表）
- **迁移脚本**：2026-07-16-merge-dup-polities、-dynasty-includes
- **数据**：data/relations/dynasty_includes.yaml（84 条）；修 21 处悬空 dynasty_ref；
  合并 2 组重复 Polity；改 2 个错误 id 前缀

## 2026-07-16（续三）97 个 agent 并行勘察：45 条发现被推翻 38 条，活下来的三条都是用户当面看到的假话

### 做了什么
派了 6 名调查员分头查剩余结构问题，每条发现再派 2 名怀疑者从「事实」与「价值」两个角度
**尝试推翻它**。45 条发现里 38 条被推翻（84%）——推翻的多半不是因为数字错，而是因为
「零用户可见面」「建议的修法会造出更大的问题」。活下来 7 条，本轮做了其中三条最伤人的。

**另有一条最严重的，不在任何原发现里**——是综合 agent 在查证 territory 时自己撞见的，
它诚实标注了「没经过任何人证伪」。我独立复现后确认，且发现比它报的还糟。

| 修的问题 | 修前 | 修后 |
|---|---|---|
| 1115–1127 地图上的北宋 | **不存在**（被金顶掉） | 回来了 |
| 1050 年「此刻在世」头六人 | 耶律宗真(34岁)…苏轼(13岁) | 范仲淹、毕昇、包拯、富弼、欧阳修、韩琦 |
| 1127 年靖康之变的当事人 | 宗泽/李纲/赵佶 **不可达** | 都在面板里 |
| 搜「建康」 | 1 条 | 3 条（建康/建业/金陵） |
| 搜「建邺」 | **0 条** | 1 条 |
| `total`（该年在世人数） | 230（截断池子大小） | 372（真实值） |
| 测试 | 44 passed | **57 passed** |

### 三件事，逐个说清

**一、金把北宋从地图上顶掉了 13 年（含靖康之变那一年）。**
两层叠加：
- **代码**：`territory_service.py` 在 `load_geojson()` 返回的**进程内共享缓存对象**上原地
  盖 `polity_id/name/color`，再 `features.extend()` 按引用外扩。同一次调用里 k_beisong 先跑、
  k_jin 后跑（两者都指 `chgis_beisong.geojson`），后者把前者**已经推进结果的那 10 个对象**
  一起改写了。实测 year=1120 返回 305 个 feature 而唯一对象只有 295 个。
- **数据**：`jin.yaml` 让金用北宋的图，note 写「金朝版图主要源自北宋故土」。但那张图实际
  只有 10 块**南方**州军：汀州、邵武军、兴化军、广德军、太平州、池州、**吉阳军（海南）**、
  连州、岳州、兴国军。金在任何年份都没到过这些地方。

代码那半边是纯 bug（没人打算让北宋消失），已修：逐个浅拷贝再盖章。
数据那半边我按「求真高于中性」删掉了金的 territory——**画一条假疆域比留白更坏**。
金 1115–1234 现在不上图，理由记在 `jin.yaml` 的 `ext.territory_note` 里，免得下一个人
再拿别人的图来填。

**这个「共享 geojson + 原地盖章」不止这一处**：`chgis_wudai.geojson` 由后梁/后晋/后汉/后周
四家共用，眼下只因 951 年后周先命中了 `houzhou_peak.geojson` 才没撞上。现在堵死了。

**二、「此刻在世」先截断后排序，丢的永远是最年长的那批。**
`persons_alive_at` 从**生年最晚者**往回扫，凑够 230 就 break；而 `prefer_seed` 排序发生在
截断**之后**——没进池子的救不回来。规律：越年长越先蒸发，而年长者恰恰最可能是当年的
重量级人物。1050 年因此丢掉范仲淹、毕昇、包拯、富弼、欧阳修、韩琦六人，面板里却排着
13 岁的苏轼、5 岁的黄庭坚、3 岁的蔡京。1127 年丢掉宗泽、耶律延禧、完颜晟、完颜吴乞买。

改成全量取→排序→再切片。**代价实测 0.13ms → 0.20ms**——省下的 0.07ms 换掉了范仲淹和
包拯，这买卖不划算。

**三、地点别名对主搜索框 100% 死。**
Person/Event 的 schema 声明的是 `alias`（542 个实体），Place 的声明的是 `aliases`
（58 个实体 81 条），而搜索的 `_rank` 只读 `alias`。`_rank` 返回 None 即被滤掉——
所以那 81 条别名不是排得靠后，是彻底搜不到。同仓库 `api/links.py:117` 早就
`for key in ("alias", "aliases")` 两个都吃，**可见这是键名错配而非取舍**。

### 反证（钉子不证明会响就只是装饰）
- 池子退回先截断后排序 → `AssertionError: 1050 年面板里没有范仲淹`、`1127 年面板里没有宗泽`
- 别名退回只读 alias → `AssertionError: 只召回 1 条 —— aliases 键又被漏读了`
- 还原后 57 passed

### 当前状态
- `python3 scripts/validate_data.py` → entities=7396 relations=10254 errors=0 warnings=20283
- `pytest -q` → **57 passed**（44 + 13 条新钉子）
- **浏览器实测**：1050 年面板 = 范仲淹 61岁 / 毕昇 60岁 / 包拯 51岁 / 富弼 46岁 /
  欧阳修 43岁 / 韩琦 42岁…；地图图例「契丹/辽 285 · 北宋 10」。

### 未尽事项与已知问题

**新发现的大坑（本轮没修，需要内容工程）**：
- **`chgis_beisong.geojson` 只有 10 个 feature**，而唐 871、辽 285、南宋 240、明 254。
  北宋有三百余州——**这张图是个残缺导入**（`data/geo/originals/` 里的原始下载也只有 10 个，
  所以是当初就抓错了，不是本地弄丢的）。后果：1050 年地图上北宋 10 块 vs 辽 285 块，
  北宋看着像个附庸。这条**两批 agent 都没点破**（综合 agent 只说「金不该用它」）。
  修它要重新导 CHGIS 北宋数据，属内容工程。

**需要 Rick 决策的（我已按默认动作执行/搁置，可推翻）**：
1. **金的疆域**：我已删（选项 a）。备选 b＝把 valid_from 收到 1127（北宋回来但金仍画在
   海南）、c＝导入真正的金代 geojson（`data/geo/originals/` 里没有）。
2. **地图按年出图是否按 feature 自带的 `beg_yr`/`end_yr` 过滤**：**默认动作＝不动**。
   实测 430 年 API 返回 290 个 feature，按 CHGIS 自己的记录只有 29 个当时存在（虚增 9 倍）；
   18 张图全有此病。代码约 10 行，但会让每张按年出的地图明显变稀疏——这是「地图在声称
   什么」的问题。按仓库惯例我会出 430/500/750/1000/1500 五个年份的**前后对比图**给你选，
   不用文字请示。
3. **搜索是否纳入 `modern_name`**：**默认动作＝不动**。实测 `q=南京` 会从 4 条变 11 条，
   多带进黄天荡（一个水战战场）、天京、六合。这是搜索语义变更，不该混在 bug fix 里。

**存活但本轮没做的发现**：
- Place 的关系面 99% 是 inline 字段（`person.birthplace` 3892 处），进不了图谱：
  `/entities/pl_jianye_han/neighbors` → 0 条边。规模约 4054 条新增关系，且**前置未决**——
  地名历时性该合还是该分（南京 9 个实体、长安 5 个）。先定合并再迁移，否则要改两次。
- 刘承祐 `reign_end 951` > `died {950,12}`：校验器**早就在报**（`validate_data.py:613`
  的 `reign_bounds` WARN 桶，T4.1b 引入），真实增量是 WARN→ERROR 提级约 2 行。
  但往哪边改取决于历法口径（后汉 ended {951,1} 是公历口径），且「乾祐三年十一月廿二
  = 公历 951-01-02」这个换算**未经查证**，落地前须核《资治通鉴·卷289》。
- `columnMount.js:184` 的 `yearToZ(initYear)` 无 clamp，柱身只覆盖 -221..1912，
  时间轴 4126 年量程里 48% 落在柱外（-2100 → z=-2114，柱高才 2400）。
  **但这解释不了 WORKLOG 记的「星图 -2100 / URL 与时间柱 1600」三方分歧**——
  那个报告仍未定位，别把 clamp 当它的结案。

**明确判定「不该做」的**（每条都有人认真论证过，结论是别碰）：
- **CBDB 地点去重（186 组 / 238 个可消除实体）**：探针错了。那 186 组里 184~185 组每个成员
  带互不相同的 `first_year`/`last_year`——CBDB 用「同名+时段」编码地名历时性。長安
  618–907 / 703–747 / 748–959 / 960–1126 是四条断代切片，不是重复。合并会把北宋人的籍贯
  改指到明代行政单位：模拟跑出来 dynasty_ref 错配 10 → **222**。这个「修复」会亲手造出
  它声称要避免的失真。
- **给 Place 的 `first_year`/`last_year` 加 year 过滤**：那是 CBDB 的**行政建置记录窗口**
  （众数全落在 960/1368/1644 这些朝代边界），不是「地方存在的年限」。按它过滤会造出
  「元代黑洞」：272 个地名在 1279 存在、1300 消失、1400 又冒出来。
- **给 `year_month` 写死「农历口径」声明**：569 个带 month 的值里至少 76 个按史实必然是
  公历——共和国 founded {1949,10}、辛亥革命 {1911,10}、五四 {1919,5}、七七、九一八，
  以公历日期命名的事件其 month 与名字全部相符。写死农历 = 在 schema 里编码一句假话。
- **加「正文农历月 vs 结构化月不符」检查**：真阳性率约 0。农历正月初一落在公历 1/21–2/20，
  所以农历 N 月 → 公历 N+1 月是**换算正确的签名**。玄武门 626-07、马嵬驿 756-07 全是对的。
- **给 Polity 加 `nature`/`is_period` 分类字段、把 4 个 `*_pre` 军政集团迁成 Faction**：
  零用户可见面（`polities_involved` 全前端不渲染；4 条无 territory 不上图；0 个人物靠它们
  归朝代）。而迁移实测把 errors 从 0 打到 5~9（赤壁/官渡的 `polities_involved` 声明是
  `ref → Polity`），要清掉只能删掉库里最著名两场战役的交战方。**上一轮记的这个待办，
  结论是别做。**
- **删 `k_nanbeichao`**：它是 420–580 这 160 年地图上**唯一**有疆域的实体（同代 9 个真政权
  territory 全为 0）。删了 = 170 年全黑。且那张图的 290 个 feature 里没有任何政权归属字段，
  机械拆不开。（另：实测那是一份**纯南朝**数据集，bbox lat 18.16–34.94，北魏到约 41°N
  根本不在里面。）**上一轮记的这个待办，结论也是别做。**
- **给 territory / geojson 缓存加目录签名失效**：`git log --all -- 'data/geo/*.geojson'`
  全仓库只有 1 个 commit，改过 0 次，生产不 reload；加 `rglob("*")` 实测让 2s TTL 热路径
  从 176ms 涨到 245ms（+39%）。**但缓存的可变引用是真 bug，已在本轮修掉**——
  真问题从来不是缓存不失效，是缓存可变。
- **给 `/api/relations` 加 offset**：「1942 条取不到」是假的，`from`/`to`/`year` 也是过滤器
  且在截断前先筛，全库最大 from 桶 1209 条 < 5000 上限，10254 条关系当前全部可达。

### 文件级变更清单
- **后端**：services/territory_service.py（逐 feature 浅拷贝再盖章，不再污染共享缓存；
  `polity_territory` 同样不交出缓存对象）、services/entity_service.py（在世池子取全量再排序；
  `_rank` 两个别名键都读）、core/data.py（`persons_alive_at` 支持 `limit=None` 不截断）
- **测试**：backend/tests/test_alive_pool.py（4 条）、test_alias_keys.py（5 条），均已反证会响
- **数据**：data/entities/polities/jin.yaml（删 territory，记 ext.territory_note）
- **勘察产物**：97 个 agent / 45 条发现 / 38 条被推翻，完整计划存于
  scratchpad/plan.md（本会话内有效）

## 2026-07-16（续四）历史底图专项：谭其骧地图集整套都在，按年换幅已接通；但我把瓦片服务打限流了

### 做了什么
补 Rick 点3 的后半：「可以选择绘制好的非互动的底图来表达特定年代的事情，比如说像五代十国
某一个时代的某一个时间节点的割据状况」。这条是长程执行里被漏掉的——之前只做了地图放大与
占比可调，底图这半边一直没动。

**现有的「古」底图是摆设**：它写死了一张 `mp0302`，与年份无关。而 `mp0302` 实际是
「原始社会遗址分布图」——所以不管看哪个年代，底下都垫着一张史前遗址图。

查清了三件事：
1. **`tile.osgeo.cn` 是个 MapProxy，上面挂着整套谭其骧《中国历史地图集》**，已配准成
   webmercator 瓦片。这正是 Rick 说的「绘制好的非互动底图」，而且早就在项目里了，
   只是没人知道它不止一张。
2. **图层 id 无任何元数据可查**：WMTS 能力文档里 10714 个图层的 Title 就是 id 本身、
   Abstract 空、bbox 全是全球默认；demo 目录页只列 id 不列名，且 `mp0302` 根本不在其中。
   所以年代归属只能**逐幅取瓦片看图认**。
3. **`mp03xx` 段 177 个图层是地图集第一至五册**（先秦→唐），`mp05xx` 段是第六册起
   （宋辽金→清）；`mp04xx` 是另一套现代专题图（气候/植被/人口/夜光），不相干。

认出并接线 14 幅（依据写在代码注释里，都是直接读图上的地名）：
原始社会遗址 `mp0302` / 夏 `mp0305`（有仍·有虞·安邑）/ **商 `mp0306`**（亳·奄·鬼方·土方·
林方）/ 西周 `mp0308`（宗周·成周·曲沃·严允）/ 春秋 `mp030b`（林胡·义渠·绵诸）/
战国 `mp0311` / 秦 `mp031f`（内史·陇西郡·咸阳）/ 前秦 `mp0373` / 北魏 `mp0391`（沃野·武川·
怀朔·薄骨律 六镇）/ 西魏 `mp0393` / 隋 `mp03c9` / 唐 `mp03dc`（关内道·节度使）/
**五代十国 `mp0500`**（定难·党项）/ 宋·西夏 `mp051b`（兴庆府·永兴军路·秦凤路）。

商代那幅正好也补上 Rick 点1 要的「商代这类没有明确编年的历史」。

### 顺带修掉一个既有 bug
`switchBasemap` 全程假设 style 已加载完。地图初始化约 1s，这段窗口里点底图按钮，
maplibre 抛 `Style is not done loading`，异常从 onClick 冒出去，**整个切换半途而废——
底图停在空白，而按钮已显示为选中**。用户看到的是「点了「古」但地图什么都没有」。
已加 `whenStyleReady()`：所有改样式的操作等 style 就绪后再做。

### 当前状态：**未完成，且我自己造成了阻塞**
- `npx vite build` → 通过
- **Playwright 实测确认换幅逻辑正确**：year=-1200 时应用确实发出
  `wmts/mp0306/webmercator/5/25/12.png` 的请求（mp0306 = 商）——**选幅是对的**。
- **但那些请求全部 `net::ERR_CONNECTION_CLOSED`。** 原因是我在勘察阶段连打了约 530 个
  瓦片请求（177 + 205 + 151 三段全量探测），**把 `tile.osgeo.cn` 打到限流/临时封 IP**。
  等待 80 秒后 curl 仍 `HTTP 000`（exit 35，SSL 连接错误）。勘察开始时它是 HTTP 200 /
  0.1s 正常的。
- 所以：**代码正确，服务被我打挂，出图未能亲眼验证**。

### 未尽事项
- **等 tile.osgeo.cn 解封后重验出图**。这是下一轮第一件事。
- **这暴露了这个方案的真实风险**：单点依赖一个第三方免费服务，它会限流。若要正经用，
  应把认定的十几幅瓦片**自己缓存下来**（涉及下载文件到仓库，需 Rick 点头），
  或至少加上失败退避（现有 errCount 机制已有，但被上面那个 style bug 挡住了）。
- **另一件已澄清的旧账**：WORKLOG 早前记「谭其骧底图待 Rick 在真 Chrome 确认，
  `tile.osgeo.cn` 需经代理才可达」——**这条是错的**。实测 `curl --noproxy '*'` 直连
  HTTP 200，不需要代理。（限流前测的。）
- 汉/三国/东晋/南朝/元/明/清 的图幅尚未认（落到兜底幅）。`mp05xx` 段 70 个有效图幅
  只看了第一批 24 个。
- 五代十国那幅 `mp0500` 的把握低于其他——图上有「定难/党项/京兆府/凤翔府」，
  定难军是五代建制，但也可能是宋初图。**需复核**。

### 文件级变更清单
- **前端**：components/map/MapPanel.vue
  - 新增 `ATLAS_SHEETS`（14 幅年代图 + 逐条认图依据）、`atlasSheetFor()`、`applyAtlasSheet()`
  - 「古」底图改为随 `settledYear` 换幅；只在图幅 id 真变时才 setTiles（同朝代内滑动零请求）
  - 图例显示当前图幅名（`· 图集「商」`）
  - 修 `switchBasemap` 的 style 未就绪即改样式（拆出 `whenStyleReady` / `applyBasemapNow`）

## 2026-07-17 历史底图自托管：所谓「我把服务打限流了」是误诊，真因是 CORS

### 先纠正上一轮的错误诊断
上一轮结尾我报告「我在勘察时连打约 530 个请求，把 tile.osgeo.cn 打到限流/封 IP」。
**这是错的，而且错得典型**——我拿到 4 次 `HTTP 000` 就套用了「大概是被限流了」这个
现成解释，没取证。Rick 说「先寻找解决限流的最优方案，而不是一味地去等待重试」，
一查就翻案了：

- 直连 × 3 全部 HTTP 200；经代理 × 3 全部 200；连打 12 次成功率 12/12
- 试抓一整幅（172 个瓦片）零失败，5 秒完成
- 那 4 次 `HTTP 000` 是**瞬时抖动**，不是限流

**真因是 CORS**：Chromium 里 maplibre 取瓦片必报
`blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present`，
而 curl 无论 GET 还是 OPTIONS、无论直连还是走代理，那台 nginx 都稳定返回
`Access-control-allow-origin: *`。同一浏览器、同一 URL：裸 `<img>` 加载
30~121ms 成功（img 不校验 CORS），maplibre 的 fetch 全灭。差异不在可达性，在 CORS，
而那台服务器我们控制不了，这个差异也无从在外部诊断到底。

（这解释了 WORKLOG 早前那条「谭其骧底图需经代理才可达」——它需要的从来不是网络可达，
是 CORS 头。我上一轮又草率地推翻了那条记录，说「不需要代理」。两次都错在没取证到底。）

### 做了什么
既然底图是产品功能，就不该挂在一个既控制不了、又诊断不清的第三方服务上。**改自托管**：

- `scripts/fetch_atlas_tiles.py`：把 14 幅 × z2-6 = **2408 个瓦片（56MB）**抓到
  `data/geo/atlas_tiles/`。幂等、并发 4、失败重试 1 次。实测 96 秒、**零失败**。
- `backend/app/main.py`：`app.mount("/tiles/atlas", StaticFiles(...))` 自己服。
- `frontend`：`atlasTileUrl` 改为 `/tiles/atlas/{id}/{z}/{x}/{y}.png`（相对路径）；
  `vite.config.js` 的 proxy 增加 `/tiles` 转发。**同源，没有 CORS 这回事。**

### 顺带修的 bug
`activeSheet` 只在 `settledYear` 变化时才算，于是首屏切到「古」时图例显示
「该年代图幅未认」，而实际早该匹配上（实测 750 年停在商幅，因为 settledYear 从未变过）。
watch 加 `immediate: true`。

### 当前状态：跑通，端到端已验证
- `pytest -q` → 57 passed；`validate_data.py` → errors=0
- **Playwright 实测**（真 Chromium，不走系统代理）：滑过五个年份，图幅逐个跟上，
  且**真的发出了对应瓦片请求**（不只是标签对）：

  | 年份 | 图例 | 实际取的图幅 |
  |---|---|---|
  | 750 | 图集「唐」 | mp03dc ✓ |
  | 1050 | 图集「宋 · 西夏」 | mp051b ✓ |
  | 920 | 图集「五代十国」 | mp0500 ✓ |
  | 600 | 图集「隋」 | mp03c9 ✓ |
  | -221 | 图集「秦」 | ✓ |

  网络面板：全部 `200 OK`，**零 tile.osgeo.cn 请求**，控制台零 CORS 错误
  （此前是 9 条）。

- **Rick 已确认**瓦片提交进 git（`data/geo` 87MB → 143MB）。先例：`originals/` 的
  18 个 CHGIS 文件（87MB）早已入库。

### 未尽事项
- **`#year=` hash 不生效**：URL 是 `#year=750` 而页面停在默认年，`loadFromUrl` 那条路
  有问题。本轮绕开它（直接调 `store.setYear`）完成了验证，但这是个真 bug，未修。
- **汉/三国/东晋/南朝/元/明/清 的图幅尚未认**，落到兜底幅（原始社会遗址图 —— 纯地理
  底图无政权界，用在任何年代都不说假话）。`mp05xx` 段 70 个有效图幅只看了 24 个。
- **`mp0500`（五代十国）的把握低于其他**：图上有「定难/党项/京兆府/凤翔府」，
  定难军是五代建制，但也可能是宋初图。**需复核**。
- z 只抓到 6（全国到省级够用）。z7 要 +112MB、z8 要 +415MB，放大到县级会糊——
  但那时底图会显示为空白而非报错（无该级瓦片）。
- **in-app Browser pane 验不了地图**：maplibre 在其中渲染不起来（`isStyleLoaded` 恒 false、
  图层不存在），`performance` 也抓不到瓦片请求。地图验证一律用 Playwright。

### 文件级变更清单
- **新增**：`scripts/fetch_atlas_tiles.py`（抓取脚本，含认图依据注释）
- **新增**：`data/geo/atlas_tiles/`（14 幅 × 2408 个 PNG，56MB）
- **后端**：`main.py`（mount `/tiles/atlas` 静态目录 + 为什么不直连的完整说明）
- **前端**：`MapPanel.vue`（`atlasTileUrl` 改自托管路径；watch 加 immediate）、
  `vite.config.js`（proxy 增加 `/tiles`）

---

## 2026-07-17 · M6 前端交互质量批（PRD 全量落地）

> 依据 `docs/prd-frontend-interaction.html`（Rick 已批准，「确定性非常高，都可以直接修」）。
> 执行：Kimi 主代理规划 + 子代理分波施工 + 集群收尾；分支 `v2/m6-interaction-prd`，9 个提交。

### 做了什么（A/B/C/D 四批 19 条全落地）
- **A 批 P0 断点**：星图 CTA 调错 store 抛 TypeError → 改 `ui.setRoute`；两处「地图定位」空操作 → `locateRequest{id,type,nonce}` 显式定位通道（同 id 重发也触发）；「在关系图中展开」死旗标 → 兑现并删 `pathHighlight`；URL 恢复失效（见下「根因纠正」）；底图双源 → `ui.basemap` 单源 + 进 URL/localStorage（死值 `'osgeo'` 删除）。
- **B 批闭环**：搜索选中 → `repYear`（`utils/repYear.js`）→ setYear → 柱平滑滚动 + lens 脉冲；星云/时空柱响应外部选中（`selectEntity` 第三参 origin 防环，星云飞近复用 star-click 路径，时空柱 Person 触发「跟随一生」预设）；在世 chips ⇄ 柱生命条双向 hover 高亮。
- **C 批效率**：全局快捷键（`composables/useHotkeys.js`：`/` `←→` `Space` 播放 `g` 跳年 `1/2/3` `t` `Esc` `?`）+ HotkeyHelp/YearJump 组件；SearchBar 重写（键盘导航/类型 chips/今名徽章/空态）+ **后端 modern_name 入搜索**（rank 5/6，排在 name/alias 之后——原 handoff open_question#3 就此关闭）；顶部朝代 chips 删除并入 gutter（title + ⌕ 跳年钮）。WebGraph Space→`f`。
- **D 批呈现**：文案三层规则入 content-spec §8（品牌从繁/数据从史/UI 从简），CE 后缀等英文残留清除；年谱「生于」拼接 bug 修复 + `life_events[]` 渲染位（无数据显式「年谱待补 · 仅录生卒」）；疆域 `territory-label` 标注层真正 addLayer（coalesce(name_ch,name_ft,name)、zoom 插值、面积 60 分位阈值、古图集下 0.45 透明）；EmptyState 组件统一全站空态 + 地图配色跟随 palette；WebGraph 路径 id 输入 → 联想选择器；**两套档案卡合并为 `shared/EntityProfile.vue`**（tab 并集：详情/关系/链接/年谱/同代/史料；MomentPanel 552→224 行、EntityDetail 823→37 行各剩壳；`useEntityDetail.js` 复活为加载层）；死样式/死代码清扫（main.css 遗产 -165 行、`.sm-empty*`、`relatedIds` stub、`activePolity` stub、`zoom/setZoom`、vue-router 依赖）。

### 验证（全部实测通过）
- `npx vite build` ✓；`pytest -q` → **58 passed**（57 + modern_name 召回新钉）；`validate_data.py` → errors=0（基线不动）
- **Playwright 全量 26/26 通过**（真 Chrome，dev server 手起手停）：a/b/c/d-batch + timeline + graph

### 根因纠正与教训（重要，别信旧文档想当然）
- **A4 `#year=` 失效根因不是 year→scroll 缺失**——05e416c 已有 watch 与防抖 guard。真断点三条：①全站无 `hashchange` 监听（贴链接进已打开页面毫无反应，750 又恰是默认年所以冷启动看不出）；②`loadFromUrl` 在 `dataStore.init()` 之后才跑，有时序窗；③entity 参数丢 type。handoff 的「loadFromUrl 那条路有问题」方向对但未定位，本轮钉死。
- **并行施工竞态**：D2 合并档案卡改了 DOM 类名，并行做 e2e 静态巡检的代理拿到的是旧 DOM——`.mp-dossier-*` 全灭却报「一致」。教训：多代理并行时，静态巡检必须排在所有 DOM 变更之后；最终只能信真浏览器跑出来的结果。
- **B1 脉冲 e2e 误报**：350ms 瞬态类的断言放在网络断言之后必错过窗口——失败的是断言时序不是功能（页面快照证实年份已到 1037）。瞬态 UI 的断言要前移或加测试钩子。

### 有意的偏差（Rick 知悉即可，不改）
- URL 恢复的 basemap **不写回 localStorage**：分享链接不覆盖对方本地偏好。
- Event/Battle 有 `march` 数据也算有地理锚点（MapPanel 本来就会 fitToLegs）。
- 星云 B2 外部选中只自动「跟随一生」Person；Event/Battle 保持高亮不自动飞（8 秒强制爬升对每次搜索太吵）。

### 未尽事项
- **E 批（响应式布局 / 新手引导）**：PRD 定为 v2.1 单独立项，本期不动。
- e2e 需手动起 dev server（backend :8002 + frontend :5174，见 `playwright.config.js` 头注）；CI 化未做。
- handoff 遗留数据层缺陷照旧排队：北宋疆域 10 feature、金无疆域、星图年份 -2100（均未在本批范围）。
- 谭其骧图集未认图幅、march-A 类箭头：仍等 Rick 拍板（与本批无冲突）。

### 提交线（main..v2/m6-interaction-prd）
`2731caf` PRD 文档 → `98cbf3f` A批 → `0622e85` B批 → `64ceb4e` C批 → `c991fea` D批大部 → `8eb64cd` D5 余项 → `e7df6f1` TimeColumn 清扫 → `a2ab965` D2 档案卡合并 → `a06d740` e2e 选择器修正

---

## 2026-07-18 · v3 M9 图集线快修包（T9.0/T9.1/T9.4 三项，工程前置）

> 分支 `v3/m9-atlas`。拍板口径（Rick 授权）：z7 不补、收 maxzoom（零成本）；过渡态显式注明、不说假话；
> 351-580 单政权视角维持现状 + 界面注明。本轮不碰 TimeColumn.vue（M7 战场），未起 dev server / 未跑 Playwright（端口归 M7）。

### T9.0 收 maxzoom：zoom 7+ 从「404 退避灰显」变「栅格过采样」
- 根因：自托管瓦片只到 z6，而「古」source maxzoom=10 → 放大到 z7+ 必请求不存在的瓦片，
  连续 404 × 5 触发退避，UI 灰显「瓦片不可达」——说假话（瓦片不是不可达，是根本不存在）。
- 修法：`BASEMAPS.古` 新增 `sourceMaxzoom: 6`（地图本体仍可放到 10：过采样放大扫描图反而能读小字）。
  生效处共两处，都已接上：`buildStyle` 的 source 定义（只在挂载时跑一次）+
  `switchBasemap` 里同步 `src.maxzoom`（不同步则「古」继承挂载时那家底图的 maxzoom，404 依旧）。
  `RasterTileSource.maxzoom` 是 maplibre-gl 4.7.1 d.ts 声明的公开属性，SourceCache 每次取覆盖瓦片实时读它。
- 「素」底图 tiles 为空、无网络请求，不动。

### T9.1 fetch_atlas_tiles.py 增强
- `--sheets mp051b,mp0500`：只抓指定幅（逗号分隔，未知 id 报错 exit 1 并列出已登记 id），默认仍全表。
- `--probe <sid>`：探针模式。抓该幅 z5 中国 BBOX 瓦片（35 个），PIL 拼 1792×1280 预览存
  `/tmp/atlas_probe/<sid>_z5.png`，打印 内容片(≥2KB)/近空白(<2KB)/无片 统计。
  sid 不限于已登记表（勘察新幅正是用途）；瓦片走同一个 `fetch()` 落盘，幂等复用。
  用法：`uv run --with pillow python3 scripts/fetch_atlas_tiles.py --probe mp051b`。
- 实测：`--sheets mp051b,mp0500` → 344 个全「已有」0s；`--sheets mp9999` → exit 1 报错正确；
  `--probe mp051b` / `--probe mp0500` 均出图（mp051b：内容片 4/35，区域图实锤；mp0500：35/35 全覆盖）。

### T9.4 mp051b 更正 + 过渡态注明 + mp0500 定谳
- **T9.4a mp051b 收窄**：实测 156/172 瓦片 <2KB、内容只在河套（z6 x51-52/y23-24），是「西夏」区域图
  不是宋全图。`ATLAS_SHEETS` 区间 960-1279 → **1038-1227**，label「宋 · 西夏」→「西夏 · 区域图」；
  960-1037 与 1228-1279 落兜底。脚本 SHEETS 注释同步更正。
- **T9.4b 图例诚实化（两处，纯文案无新组件）**：
  ① 落兜底幅 mp0302 时图例从含糊的「该年代图幅未认」改为明示 `图集「原始社会遗址 · 该年代图幅待补」`
  （告诉你铺的是哪张 + 该年代待补）；② mp0373 前秦/mp0391 北魏/mp0393 西魏 label 加「· 区域政权图」
  后缀（351-580 单政权视角的界面注明，兑现拍板口径）；mp051b label 自带「区域图」字样。
- **T9.4c mp0500 定谳 = 五代（后晋天福八年 943），保留**：
  探针预览亲读 —— 图幅图例纪年行「（后）晋天福八年（943 年）」（天福为后晋独有年号）；
  河套清楚可见「定难（军）」「党项」+ 夏州/绥州/延州，行政区全是府州名（京兆府/凤翔府/太原府），
  **无任何宋代路名**（永兴军路等不存于 943）；北为辽（上京临潢府/辽阳府/黄龙府），江南为南唐。
  旧注「把握低于其他，待复核」删除，MapPanel 与脚本两处注释已写硬依据。
  预览图：`/tmp/atlas_probe/mp0500_z5.png`（及 mp051b_z5.png）。

### 验证（本分支实测）
- `pytest -q` → **58 passed**；`validate_data.py` → **errors=0 / warnings=20283**（基线不动）；
  `npx vite build` ✓（>500kB chunk 警告是既有的）
- e2e/Playwright 未跑（端口 8002/5174 归 M7 代理独占）；图例文案与 maxzoom 行为改动待 M7/M10 回归时真机确认。

### 未尽事项
- z7 补抓（+5712 瓦片/+112MB）仍等 §6 磁盘预算拍板；不补则现状已是终态。
- 北宋/南宋/辽/金全图、汉、元明清图幅仍未认（mp05xx 46 幅、mp03xx ~165 幅勘察属 T9.2/T9.3，别的线在做）。
- 960-1037 / 1228-1279 现为兜底 + 待补注明的过渡态，待 T9.2 认出宋全图后转正。

### 文件级变更清单
- **前端**：`frontend/src/components/map/MapPanel.vue`
  （BASEMAPS.古 +sourceMaxzoom、buildStyle/switchBasemap 同步 maxzoom、ATLAS_SHEETS 三条 label 后缀 +
  mp051b 收窄 + mp0500 定谳注释、图例兜底文案、stale 注释清理）
- **脚本**：`scripts/fetch_atlas_tiles.py`（--sheets/--probe 参数 + probe()、mp0500/mp051b 注释更正、docstring 用法）


---

## 2026-07-19 · M7 时间柱人物区可读性重构(v3.0 第一里程碑)

> 依据 `docs/roadmap-v3.md` §3-M7;超容策略为 §5-1 方向甲「容量封顶 + 聚合溢出道」(Rick 已拍板)。
> 执行:Kimi 子代理独立施工;分支 `v3/m7-person-lanes`,worktree `.claude/worktrees/v3-m7`。

### 做了什么(T7.0-T7.4 全落地)
- **T7.0 钉子先行**:新增 `frontend/e2e/m7-person-lanes.spec.js` 4 用例(道距/拖栏重算/选中聚光/连线几何),施工前 4 红且条条命中诊断(0.45px 道距、拖栏不变、opacity=1、x=62.87% 百分比残留)。
- **T7.1 ResizeObserver 接上 viewW**:scrollRef 尺寸变化即 syncViewTop,拖 SplitPane/窗口缩放实时重算布局(车道/事件列),不再等下一次滚动。
- **T7.2 车道双自适应(核心)**:laneCount 由「全史最大并发」全局常数(L0 实测 97)改为 `min(可见窗并发数, floor(区宽/最小道距 10px))`;区宽策略重定——`PERSON_RIGHT` 0.30→0.47、地板 pxA+44→pxA+88、上限给事件区留至少一列(实测 720px 下事件区仍保 2 列)。超容人物并入最右一条**聚合溢出道**:按生年落刻度示密度(视口虚拟化)、「+N」徽标随滚动跟随视口、hover 弹名单(前 24 人 + 等 N 人)、click 以点击处年份为锚平滑放大——窗内并发下降后人物自然回列。
- **T7.4 年代窗自适应**:车道索引按可见年代窗(视口±缓冲)分配,不再背全史峰值,稀疏年代自然摊开。窗界按 **100 年桶量化**:滚动途中桶界不变则分道结果跨帧稳定,否则每帧全量重分道会把主线程在 650ms 动画里占满(实测见下)。
- **T7.3 选中聚光 + 连线几何**:选中人物在轴上时 `.tc-inner` 挂 `tc-dim` 类,非选中条 CSS 淡出 0.25(hovered 除外);关系连线 x 改为 `laneX` 同款 px 几何——旧公式 `60+lane*24/count+'%'` 是更早百分比布局残留,连线错落到事件卡区(e2e 钉死),对端在聚合道时落在聚合道位上。
- **提升集(自保设计,任务书外补的)**:选中 + 在世 chips 必占车道、不入聚合。起因是实测复算:默认 720px 容量仅 7-12 道,**杜甫(cap≤12 时)必入聚合道**,M6 B3「chips⇄柱条双向 hover」会静默破灭(chip 有、柱上无条)。故在世名单单源化为 `composables/useAlivePeople.js`(MomentPanel 与 TimeColumn 共用一份,取数逻辑原样),chips 上的人柱上必有条。

### 实测证据(全部本分支真机跑过)
- `pytest -q` → **58 passed**(基线不动);`validate_data.py` → **errors=0**(warnings=20283 基线不动);`npx vite build` ✓
- **Playwright 全量 30/30**(既有 26 + 新钉 4,真 Chrome;b-batch 连跑 4 次全绿排除 B1 闪烁)
- 截图自证 4 张(`.m7-tmp/m7-{1..4}-*.png`):L0 全景人物区(车道摊开 + 「+110」聚合徽标)/ 拖分栏实时重算(拉宽后聚合道 +3 就地回列消失)/ 选中聚光(李白朱红,余条 0.25,连线落在人物区内)/ 聚合道 hover 名单弹层

### 根因纠正与教训
- **B1 lens 脉冲断言丢失的真相**:不是功能坏了,是滚动动画全程 ~650ms 里主线程被逐帧重渲染占满(单帧皆低于 longtask 阈值,PerformanceObserver 抓不到,但 CDP 断言会被饿着),Playwright 首次采样整段错过 350ms 脉冲窗。修法:脉冲类名挂 350→900ms(=动画全程+断言余量,观感不变) + 车道窗桶量化 + 聚合刻度虚拟化 + dim 走 CSS 类开关(不重建 400 条内联样式)。教训:**瞬态断言的窗口要比主线程饱和期更长**,别再只盯断言时序。
- **hover 劫持**:搜索选中后柱体平滑飞行,事件卡滑到静止光标下,Chrome 落定后补发 mouseenter,hover 预览把刚选中的档案顶成「割燕云十六州」(B1 连挂 4 次,elementFromPoint 实证)。store 的 350ms 抑制窗盖不住滚动全程。修法:`setHoverGuarded` —— scrollToYear/zoomAt 动画期 + 落定后 400ms 尾窗内柱内 hover-in 一律忽略(清空放行)。
- **hover 不入提升集**:hover 是高频动作,每次 hover 全量重分道纯属自找抖动;chips 已覆盖双向 hover 的互高亮对象。

### 未尽事项
- 提升集超容(>maxLanes)时道距可收紧到 ~5-7px(chips 上限 16 故有界),未做二次压缩;极窄 pane(<400px)下事件列仍会溢出视口(M6 遗留,v3.1 E 批范围)。
- 聚合道名单浮层只读(pointer-events:none),名单内人名不可点选——与 M8 事件分桶的「hover 清单可点选」交互语言待 M8 统一。
- `momentPins` CSS left 仍是 56% 百分比(与本次连线同源旧残留),功能无恙,未动。

### 提交线(main..v3/m7-person-lanes)
`eb8e93c` T7.0 钉子(红)→ `4954cf9` T7.1 ResizeObserver → `1bfce2b` T7.2-T7.4 核心重构 + B1 两连修

## 2026-07-19 · M8 事件溢出可见性(v3.0 第二里程碑)

> 依据 `docs/roadmap-v3.md` §3-M8;与 M7 交接备注的「交互语言待 M8 统一」一并收口。
> 执行:Kimi 子代理独立施工;分支 `v3/m8-event-overflow`(自 v3/m7-person-lanes 切出),worktree `.claude/worktrees/v3-m8`。

### 做了什么(T8.0-T8.3 全落地)
- **T8.0 钉子先行**:新增 `frontend/e2e/m8-event-overflow.spec.js` 5 用例(徽标与 API 复算/hover 清单可点选/click 放大回列/人物名单统一/密度条),施工前 5 红且条条命中缺口。
- **T8.1 分桶聚合**:184 枚 7x2px 同 x 叠放的溢出刻度按 y 距 16px 并桶(`overflowBuckets`),多事件桶渲染「+N」计数徽标(族色继承既有调色——取桶内 importance 最要者的族色描边),单事件桶保持旧刻度行为(悬停见名、点选定位)。相邻桶质心距 ≥16px,徽标物理上不再互叠。
- **T8.2 统一可点选清单**:新组件 `timeline/AggPopList.vue` —— 事件溢出桶与 M7 人物聚合道共用同一套 hover 迷你清单,条目可点选走既有 `selectEntity` 通道;M7 只读名单就此升级(M7 交接的待统一项收口)。徽标 hover 开、140ms 宽限关(徽标→浮层短距移动不闪关)。**click 桶 → 平滑放大**:所需 k 按「邻域事件全列回列」精确反推——卡片等高等距,全列回列 ⇔ 任何 cols+1 件的年距 ≥ 卡高行距(区间图定理),取与桶相交全部窗口所需最大 k,×1.15 余量(分数序贪心略劣于最优),封顶 K_MAX;只放大不缩小,锚定点击处。
- **T8.3 柱缘密度指示条**:全轴(-2100..2026)90 桶事件密度热区薄条(7px)贴柱右缘,与缩放无关,任一 zoomLevel 一瞥「哪里有戏」;当前年刻痕随刷年掠过响应,点击条面跳年。

### 施工中发现并修掉的两个真 bug
- **回列反推不能只数桶内**:首版按桶内 6 件反推只放大到 0.82,实测 4/6 件仍被邻段事件(安史之乱等已列卡)挤在溢出。改为区间图定理的精确容量条件(e2e 钉子同步学会:超过最大缩放容量的紧密簇——如 755/756/757 连续三年、列宽仅 2——本就回列不尽,钉子只选容量可达的桶断言全列回列,那是容量上限不是缺陷)。
- **`zoomAt` 钳高度 bug(影响面超出 M8)**:同步设 `scrollTop` 时 `innerHeight` 尚未随 zoom flush,目标超出旧 DOM 内高被浏览器钳住——L0 直跳 L2 目标 35881 被钳成 1833,镜头飞到年 -1939(截图实证)。M7 的聚合道 click(+0.6 同款路径)对 -454 以后的目标同样中招,只是当时无钉无截图未暴露。修法:rAF 复核补设(小步滚轮缩放下为 no-op)。e2e 钉子新增「镜头落在桶区间」断言锁死回归。

### 实测证据(全部本分支真机跑过)
- `pytest -q` → **58 passed**(基线不动);`validate_data.py` → **errors=0**(warnings=20283 基线不动);`npx vite build` ✓
- **Playwright 全量 35/35**(既有 30 + 新钉 5,真 Chrome;含一轮 M7 T7.2 红后修——openPop 误套 hover 守卫挡住测试的刻意悬停,浮层不写 selection store 无需守卫,误开也会随徽标滑走自关)
- 截图自证 4 张(`.m8-tmp/m8-{1..4}-*.png`):L0 计数徽标(+12/+46/+44 沿柱可读)/ hover 桶弹 46 件迷你清单 / click 桶后镜头落在五代十国 909、原溢出事件全列回列 / 柱缘密度条特写

### 未尽事项
- 密度条 7px 命中区不转发滚轮(停其上滚动失效);bin 悬停已有 title 读数,未做更大交互面。
- 桶徽标与最左事件列边缘有 ≤7px 视觉交叠(徽标 z-index 浮于卡上),实测无碍读数。
- M7 遗留照旧:momentPins CSS left 56% 百分比残留未动;提升集超容道距收紧未做二次压缩。

### 提交线(main..v3/m8-event-overflow,自 v3/m7-person-lanes 起)
`9d7652a` T8.0 钉子(红)→ `58e124b` T8.1-T8.3 核心实现 + 回列反推/zoomAt 钳高度两修复

---

## 2026-07-19 · v3 M9 图幅注册波 —— 十五幅新注册、唐三幅分期、清两幅定年（年代表 14 → 28 幅）

> 分支 `v3/m9-atlas`。五路勘察代理出候选 → 本代理对关键幅逐张 ReadMediaFile 亲读复核后才注册
> （证据优先；勘察结论三处被实测推翻，见下）。预览图均在 `/tmp/atlas_probe/`。
> 本轮未起 dev server、未跑 Playwright（8002/5174 归 M8）；e2e 钉子写好待 M8/M10 跑。

### 注册清单与区间（ATLAS_SHEETS；脚本 SHEETS 同步）

| 幅 | 区间 | 认图依据（亲读，≥2 地名） |
|---|---|---|
| mp0324 西汉 | -206~8 | 图例都城=**长安**；西域都护府/匈奴/乌孙 |
| mp0334 东汉 | 25~220 | 图例都城=**雒阳**（东汉写法）；西域长史府/鲜卑/夫余 |
| mp0346 三国 | 220~280 | 图例纪年「魏景元三年、蜀汉景耀五年、吴永安五年（262年）」；魏/蜀/吴 |
| mp035a 西晋 | 281~316 | 图例纪年「**太康二年（281年）**」、都城=洛阳；西域长史府/鲜卑/高昌戊己校尉 |
| mp0375 东晋·十六国 | 317~350 | 图题纪年「…光初十年、…建兴十五年（327年）」；晋/赵/成/凉/代 |
| mp0394 北周·北齐·陈 | 558~580 | 图例纪年「陈太建四年、齐武平三年、周建德元年（572年）」；齐/周/陈/突厥/吐谷浑 |
| mp03db 唐·前期 | 618~704 | 图例纪年「**总章二年（669年）**」；单于都护府/安西四镇（焉耆镇/龟兹镇）/吐蕃/大非川 |
| mp03dc 唐·中期 | 705~755 | 都城=西京、道级驻所=河南府、碎叶；**突厥牙帐**+回纥/同罗/契苾/仆骨（后突厥期）→ 开元741 期 |
| mp03dd 唐·后期 | 756~906 | 图例纪年「元和十五年（820年）」、都城=上都、节度使/观察使/经略使；回鹘牙帐/契丹/奚/西受降城 |
| mp0503 北宋·辽 | 960~1126 | 东京开封府/北京大名府/契丹(辽)/西夏/定难军/太原府 |
| mp053d 金·南宋 | 1127~1175 | 图例纪年「金皇统二年、南宋绍兴十二年（1142年）」；金/西夏兴庆府/开封府/归德府 |
| mp053e 金·南宋 | 1176~1279 | 图例纪年「金泰和八年、南宋嘉定元年（1208年）」；金/西夏/南京路 |
| mp0589 明·前期 | 1368~1499 | 图例纪年「宣德八年（1433年）」；鞑靼/瓦剌/奴儿干都司/亦力把里 |
| mp058a 明·后期 | 1500~1643 | 图例纪年「万历十年（1582年）」；鞑靼土默特部/亦力把里 |
| mp05c1 清·前期 | 1644~1857 | 图例纪年「嘉庆二十五年（1820年）」（外东北/台湾府完整） |
| mp05d1 清·晚期 | 1858~1911 | 图例纪年「光绪三十四年（1908年）」（外东北已失/台湾已割） |

区间衔接说明：西汉起 -206 接秦（-207）；220 归东汉（十月曹丕篡汉）；三国止 280、西晋起 281；
mp0393 西魏收窄 535-580→**535-557**（557 西魏亡/北周立）；唐 dd 止 **906**（原任务书 907 与五代
mp0500 起年重叠，907 归五代）；明 058a 止 **1643**（避免与清 1644 重叠）；清分界 1858（瑷珲条约，
外东北割让起点）。新莽 9-24 与元 1280-1367 无图落兜底 + 「该年代图幅待补」注明。

### 勘察结论被实测推翻的三处（证据优先，均已更正注册）
1. **mp035a ≠ 西汉重复幅**：勘察标「同为西汉全图·与 mp0324 去重取一」。亲读图例：都城=**洛阳**、
   纪年「**太康二年（281年）**」、西域**长史**府（非都护府）→ 实为**西晋全图**，新注册 281-316。
   mp0324 无竞争入西汉。
2. **mp03db ≠ 开元741**：勘察标「图上纪年开元二十九年 741」。亲读图例两次均为「**总章二年（669年）**」；
   图上是单于都护府+安西四镇（北庭都护府 702 年才置，不在图上）→ 初唐极盛幅，注册 618-704。
3. **mp053d/mp053e ≠ 同期重复**：勘察标「同期重复版取一」。亲读图例：053d=皇统二年/绍兴十二年
   （**1142**）、053e=泰和八年/嘉定元年（**1208**）→ 金南宋（一）（二）两期，均注册并拆区间。

### mp03dc 复核结论（任务书第 6 条）
dc 与 dd **不同期**，不移除：dc 北方是**突厥牙帐**+回纥/同罗/契苾/仆骨（后突厥期的铁勒诸部），
dd 北方是**回鹘牙帐**（突厥已亡）；dc 图例都城=西京、道级驻所（河南府）、碎叶，无节度使行；
dd 图例都城=上都、明列节度使/观察使/经略使。dc 定**开元二十九年（741）**盛唐期，由独扛 618-906
改挂 **705-755**。注：dc 图例纪年行在本地 z6 拼图裁幅之外未能亲读，741 由「突厥牙帐+回纥诸部并存
+道级驻所」与 dd（元和820）互斥推定——其余两期（669/820）均已由 db/dd 图例纪年钉死，741 是唯一
剩余位置。

### 清两幅定年（任务书第 11 条）
z6 台湾（53/27）/外东北（55/23）探针因服务器 SSL 断连取回 760B 暗片，**判读失败**；改读 z5 预览的
图例纪年行（证据更硬）：mp05c1=「嘉庆二十五年（1820年）」、mp05d1=「光绪三十四年（1908年）」。
定年成功 → 拆 1644~1857 / 1858~1911，两幅均注册（不走「只注册 05c1」的降级预案）。

### 元全图缺位（任务书第 12 条）
S1+S2 合并结论：mp05xx 段**不存在**元时期全图（只有分省/宣政院/西域区域图）→ 元全图候选已穷尽，
1280-1367 显式留兜底 + 图例「该年代图幅待补」，不说假话。

### mp051b 移出年代表（任务书第 9 条）
西夏区域图（1038-1227）：960-1279 已被 mp0503/053d/053e 三幅全图覆盖 → 从 ATLAS_SHEETS 移除；
脚本 SHEETS 保留条目并注明「西夏区域图·不入年代表」备查。区域图不入年代表的纪律不动；
mp0373/0391/0393 的「区域政权图」后缀保持（351-580 单政权视角的既有注明）。

### mp0302 注释更正（任务书第 13 条）
MapPanel.vue 旧注「demo 目录页只列 id 不列名，且 mp0302 根本不在其中」实测不成立：demo 页含
mp0302 ×10、mp03 段 177 个 id 与 GetCapabilities 完全一致。已改写（目录页不给年代，认图仍靠读图）。

### 未注册的存疑幅（勘察代理自标存疑/中，本轮不注册）
mp03b4（北魏东部，北魏末 vs 东魏存疑）、mp03b8（北镇阴山）、mp03e5（点圈主题图，缺图例）、
mp03f2/f5/f6/fb/fc（z5 无内容、z4 局部，五代小政权/渤海候选）；mp03c5/c7（梁东魏西魏全图分块，
疑同图分幅，已有 mp0393 覆盖该期）。mp01xx/mp02xx/mp06xx+ 段位未勘探（T9.5）。

### 瓦片入库
**服务器 SSL 断连，本波只入种子 187 片，剩余量放弃（两轮 15min 冷却探活均 http=000，curl rc=35）。**

- **已入库（5 幅部分层）**：mp03db z5×35、mp03dd z5×35、mp0503 z5×35+z6×4、mp053d z5×35+z6×4、
  mp053e z5×35+z6×4（勘察代理探针遗产 `/tmp/atlas_probe/tiles/` 拷入，共 187 片）。
- **0 片（10 幅全缺 z2-z6）**：mp0324、mp0334、mp0346、mp035a、mp0375、mp0394、mp0589、mp058a、
  mp05c1、mp05d1。
- **缺层（3+2 幅）**：mp03db/mp03dd 缺 z2/z3/z4/z6；mp0503/mp053d/mp053e 缺 z2/z3/z4 及 z6 大部。
- **断连时间线**：15:32 首抓 mp0324 172/172 全失败（失败率 100% 自停）；16:06/16:21/16:37/16:40/
  16:55/17:10/17:01/17:17 八次探活均 000。按收尾指令两轮冷却后放弃。
- **前端表现（已注册未抓齐的年份）**：「古」底图请求 /tiles/atlas/<id>/z/x/y.png 404 → 既有退避机制
  灰显「瓦片不可达」——诚实降级、不说假话；种子幅在 z5/z6 层已有真内容。补抓只需服务器恢复后
  重跑 `python3 scripts/fetch_atlas_tiles.py --sheets mp0324,mp0334,mp0346,mp035a,mp0375,mp0394,mp03db,mp03dd,mp0503,mp053d,mp053e,mp0589,mp058a,mp05c1,mp05d1`（幂等）。

### 验证（本分支实测）
- `pytest -q` → **58 passed**；`validate_data.py` → **errors=0 / warnings=20283**（基线不动）；
  `npx vite build` ✓（>500kB chunk 警告是既有的）
- 新增 `frontend/e2e/atlas-sheets.spec.js`（跳年看图例：-100西汉/100东汉/262三国/281西晋/330东晋/
  669·750·850唐/1050北宋/1142·1200金/1450·1600明/1750·1900清 + 9·1300 兜底待补）。**写好未跑**
  （端口归 M8），待 M8/M10 真机回归。

### 文件级变更清单
- **前端**：`frontend/src/components/map/MapPanel.vue`（ATLAS_SHEETS 14→26 幅 + mp0302 注释更正 +
  mp0393 收窄 + mp051b 移除 + 唐三幅/金两幅/清两幅分期注释）
- **脚本**：`scripts/fetch_atlas_tiles.py`（SHEETS 同步 15 幅新登记 + mp051b「不入年代表」注释 +
  mp03dc 复核结论注释）
- **测试**：`frontend/e2e/atlas-sheets.spec.js`（新增，17 用例，未跑）
- **数据**：`data/geo/atlas_tiles/` 新增 5 幅种子瓦片 187 片（mp03db/dd/0503/053d/053e；其余 10 幅 0 片待补，见「瓦片入库」）
---

## 2026-07-19 · M10 收版集成（v3.0 最后里程碑）

> 分支 `v3/release`（自 v3/m8-event-overflow 切出，merge v3/m9-atlas），worktree `.claude/worktrees/v3-release`。
> 铁律执行：不 merge main、不 push、不打 tag；提交按路径显式 add（worktree 内 frontend/node_modules 是符号链接）。

### 合并与冲突
- `git merge --no-ff v3/m9-atlas`：唯一冲突 = WORKLOG.md 尾部双追加（m8 侧 M7+M8 段 / m9 侧两段 M9）。
  按时间序解：M9 快修包(07-18) → M7 → M8 → M9 注册波(07-19)，四段全保，无功能冲突（m9 不碰 TimeColumn，m7/m8 不碰 MapPanel）。

### 瓦片补抓：服务器仍断，两轮冷却后放弃（环境项）
- 探活 `tile.osgeo.cn`（known-good wmts/mp0302/webmercator/5/25/12.png）四次：09:36 / 11:00 / 11:05 / 11:17 UTC
  全部 `curl rc=35 LibreSSL SSL_connect: SSL_ERROR_SYSCALL`（http=000，~5s 超时）。两轮 ≥15min 冷却完成，按任务书放弃。
- 齐缺清单（每幅齐=172 片 z2-z6）：**0 片（10 幅）** mp0324/mp0334/mp0346/mp035a/mp0375/mp0394/mp0589/mp058a/mp05c1/mp05d1；
  **部分（5 幅）** mp03db 35(z5)、mp03dd 35(z5)、mp0503 39(z5×35+z6×4)、mp053d 39、mp053e 39（M9 探针遗产种子）。
  原有 14 幅全齐（含 mp03dc/mp0302/mp0500）。
- 补抓命令（服务器恢复后幂等重跑）：
  `uv run python3 scripts/fetch_atlas_tiles.py --sheets mp0324,mp0334,mp0346,mp035a,mp0375,mp0394,mp0589,mp058a,mp05c1,mp05d1`
  再 `--sheets mp03db,mp03dd,mp0503,mp053d,mp053e` 补缺层（每 ~300 请求停 60s）。

### 集成逮到两个真 bug（均已修复复验）
1. **TDZ：图例永落兜底（M9 引入）**。`activeSheet`/`appliedSheetId` 声明在 `watch(settledYear, immediate)` 之后，
   immediate 回调同步执行撞 TDZ（`Cannot access 'activeSheet' before initialization`，被 Vue 错误通道吞掉）。
   默认年 750 直开 `#year=750` 时 settledYear 不再变化 → 图例永显示「原始社会遗址 · 该年代图幅待补」。
   M9 未跑 e2e（端口归 M8）故未暴露；M10 全量首跑 7 红逮到（750 确定性红，另 6 个在负载下年份先落定而 flaky 红）。
   修法：声明前移（MapPanel.vue）。修后 atlas-sheets 17/17、全量 52/52。
2. **直开 `#year=1050&basemap=古` 先铺唐图再自愈（既有竞态，集成实测放大）**。URL 恢复在 App setup 完成
   （year=1050），但 settledYear 有 180ms 消抖仍是默认 750 → 建图按 750 取 mp03dc，几秒后自愈。
   实测 5 次直开 3 次首发 mp03dc（请求日志实证）。修法：onMounted 按**即时 year**（`store.year ?? store.settledYear`）
   取幅——消抖为刷年节流而设，一次性初取不受其限。修后 6/6 直开首发即 mp0503，无过渡态。
- **勘误 M9 WORKLOG 一处机制描述**：「瓦片 404 → 退避灰显」不成立。实测 maplibre 把瓦片 404 当「无数据」
  静默处理（探针：-100 年 68 个瓦片 404，map `error` 事件 6 秒 0 次）；退避（连续 5 次 → 隐藏图层 + 按钮灰显）
  只对非 404 网络错误生效。缺片年份真实表现 = 空白底图 + 正确图例 + 疆域叠加层，不造假、无报错。

### 回归（全部本分支真机实测）
- `pytest -q` → **58 passed**（基线不动）；`validate_data.py` → **errors=0 / warnings=20283**（基线不动）；
  `npx vite build` ✓（>500kB chunk 警告既有）
- **Playwright 全量 52/52**（35 既有 + atlas-sheets 17；真 Chrome；首跑 7 红=上述 TDZ，修后两轮全绿）

### 性能（轻量）
- 首屏 entry chunk：v3/release 151,256B vs main 基线 151,215B（**+41B**，git archive main 实测构建对比，非凭记忆）；
  MapPanel chunk 817,406→818,335B（+929B）；TimeColumn chunk 23,363→30,206B（+6.8KB，M7/M8 逻辑，懒加载不阻首屏）；
  inkPalette 不变。
- 后端热接口 `/api/entities?limit=50` ×5：0.0965/0.0015/0.0013/0.0013/0.0012s → **中位 1.3ms**（首调用 96ms 为冷启动）。

### §1 完成定义逐条核对（截图存 `.m10-tmp/`，勿入库）
1. L0 人物区道距 ≥4px 或聚合态可读 + 拖 SplitPane 实时重算 ✓（m10-1：L0 车道摊开 +「+110」聚合徽标；
   m10-2：右拖 200px 后 left 全变、聚合徽标 +110→+73 就地回列，全程未滚动）
2. 选中聚光淡出 + 连线落人物区 ✓（m10-3：李白选中条朱红、余条淡出、右栏档案卡为李白；e2e T7.3 断言 opacity ≤0.3 + 连线 px 几何）
3. 事件溢出计数徽标 + hover 清单 + click 回列 ✓（m10-4：+6 徽标弹「6 件收起于此」可点选清单；
   m10-5：click 后镜头落 732、神龙革命/怛罗斯之战等全列回列）
4. 960-1279 不再空白 ✓ 有条件达成（m10-6：1050 北宋·辽**真图**——mp0503 z5 种子片；z2-z4 缺层待补抓）。
   汉/元明清段：汉 -100 图例「西汉」正确但 0 片 → 空白底图（环境项）；**元 1300 显式兜底**（m10-7b：mp0302 真图 +「该年代图幅待补」）✓；
   明清 1450/1750 图例正确、0 片空白底图（环境项，同补抓清单）
5. zoom 7+ 不再 404 退避 ✓（m10-8：750 唐 zoom 7.5 = z6 过采样，「金州」大字可读，无退避无 404 请求）
6. e2e 52/52 ✓、pytest 58 ✓、validate errors=0 ✓

### 未尽事项（移交 Rick）
- 10 幅 0 片 + 5 幅缺层瓦片待 tile.osgeo.cn 恢复后补抓（命令见上）；补齐前汉/三国/晋/北周/明/清段「古」底图为空白（图例正确）。
- mp03dc 视口边缘 4 片越出抓取 BBOX 的 404（z4 x10 / z5 x21）——既有现象 main 同，低于退避阈值无感知。
- 元全图不存在（勘察穷尽）与新莽 9-24 为永久兜底态；z7 补抓按拍板不补。
- e2e 需手起 dev server（backend :8002 + frontend :5174），CI 化未做（沿 M6 遗留）。

### 提交线（v3/release）
`5013ad6` merge m9 → `（本段随文档与两修复一并入库，见 git log）`

---

## 2026-07-20 · v3.1「看得细」——点选锚定 / 月日粒度 / 真实图像与外链

### 做了什么（写给非开发者）

四件事，都已落地并跑通验证：

1. **清完上一版的尾巴**：分支与 worktree 全部已并入 main（无待整合项），handoff 里唯一遗留的
   「补抓 15 幅地图瓦片」趁 tile.osgeo.cn 短暂恢复补下 10 幅（1720 片），西汉/东汉/三国/西晋/
   东晋/北周/明×2/清×2 段的历史地图从此有底图。剩 5 幅服务器再次断连未竟。
2. **点谁就看谁的时代**：以前点时间轴上的事件，右边地图和人物名单纹丝不动——点了安史之乱，
   右边还是天宝九载的疆域。现在点一个事件（或人物），整条时间轴会滑动，把它送到那条红色锚定
   横线上，右边的疆域图、在世人物随之切到那一年。锚线不动、轴动（Rick 指定的方案二）。
3. **时间轴从「年」细到「月/日」**：新增「月」「日」两档。同一年里的事件第一次能分开——
   1937 年的七七事变（7月7日）与南京大屠杀（12月13日）在旧的「编年」档下必然重叠（其中一件被
   挤进溢出槽），月档下相隔 82 像素各就各位。近现代史梳理因果需要的月份分辨率，现在有了。
4. **人物有了真实画像，条目有了延伸阅读**：全站头像此前大多是空白（详见下方「查出来的事」），
   现在 736 位种子人物里 439 位配上了 Wikidata/Commons 上的真实历史画像（含许可与作者署名），
   696 位挂上了中文维基百科与 Wikidata 外链，收在档案卡的「史料」页里。

### 查出来的事（都是取证得来，不是推断）

- **头像不是「有些没配图」，是大多数是空的**。库里 102 个 image 字段是早期脚本按「中文名 →
  Commons 文件名」硬编码猜的，从未核对；实测李白、杜甫皆 404，整体失效率约 78%。而前端图加载
  失败时把 `<img>` 藏起来、占位字符又是 `v-else` 永不出现 —— 于是头像位变成一个空的纯色块。
- **「日粒度不可行」是错的**。上一轮调研判定日档需要 1206 万像素的容器高度、不可行。实测
  Chrome 单元素高度上限 33,554,428px（2^25），且 scrollTop=12,000,000 精确生效，余量 2.8 倍。
  日档实测 62fps、DOM 仅 119 节点。**标注「需实测」的数字，用之前必须真去测**。
- **月/日数据一直都在**，只是被前端丢掉了：210 个事件里 101 个带 month、41 个战役里 31 个带，
  10 个带 day（全部是 1912–1945，公历口径无歧义）。后端一直原样传到前端，只在时间柱取
  `year: e.date.year` 那一行被主动丢弃。
- **浏览器把 scrollTop 量化成整像素**。750 年在「帝王」档（k=2.245）下期望 scrollTop=6398.234，
  实存 6398，反算回来是 749.896 —— 误差 0.104 年。原先的 `Math.round` 一直在掩盖它，一改
  `floor` 首屏立刻错一年、11 条测试变红。这不是浮点 eps 能救的，量级差五个数量级。

### 关键决策与被否决的备选

| 决策 | 选了什么 | 为什么不选另一个 |
|---|---|---|
| 锚定方式 | 轴动、锚线不动（方案二） | Rick 指定；且锚线追事件会让「一年一世界」的参照系本身漂移 |
| 人物锚到哪一年 | 生命段起点（= `utils/repYear` 的四态优先级） | 另立一套优先级会让同一个人「从搜索进」和「从柱上点进」落在不同年 |
| 缩放曲线 | 分段指数，`lv∈[0,2]` 原样保留 | 并成一条曲线会改掉既有三档的 px/年，而 M7 车道容量、M8 回列反推与其 e2e 断言全部标定在那三个值上 |
| 日粒度形态 | 几何分离到日，但**不出逐日刻度** | 农历月长 29/30 不等且置闰、公历 28~31，一把等分尺画到日就是在宣称它撑不起的精确 |
| 历法口径 | 原载不换算 + 字形区分（农历「十二月」/ 公历「7月7日」）+ 常驻口径注记 | 换算需逐条核朔闰；没核就换算等于凭空造精确。含糊不标则默认读者以为已换算 |
| 小数年放哪 | 组件本地 ref，不进 store | 进 store 会让 App 的 watch 每帧写一次 URL（settledYear 的消抖挡得住地图，挡不住 URL） |
| 4892 个 CBDB 人物 | 不配图，只取 QID 做外链 | 实测带 P497 的 41.3 万条 Wikidata item 里只有 2381 条带 P18（0.58%），请求几乎全部落空 |
| 延伸阅读放哪 | 「史料」tab 内分节，不另开 tab | 分节标题足以立「史料本身 vs 后人编的参考」这道界，不必让 tab 条变成七个 |
| 收哪些站点 | 中文维基百科 + Wikidata | 百度百科词条可任意改写且无版本溯源；ctext/维基文库价值更高但需「书名→urn」映射表，等第二个真实用例 |

### 当前状态：能跑什么、怎么跑

```bash
cd frontend && npm run dev          # 一体化：自动拉起后端，开 http://localhost:5173
```
时间轴右上角现在是五档：朝代 / 帝王 / 编年 / 月 / 日。点任意事件卡或人物条即锚定。
月档起左上角出现历法口径注记。档案卡「史料」页含典籍出处 / 延伸阅读 / 图像出处三节。

验证基线（全部本次实跑）：**e2e 63/63**（既有 52 + M11 5 + M12 6）、**pytest 58**、
**validate errors=0 / warnings=20283**（与基线一致）、**vite build ✓**。

### 未尽事项与已知问题

- **5 幅瓦片仍缺**（mp03db/mp03dd/mp0503/mp053d/mp053e）。tile.osgeo.cn 抓到中途再次 SSL 断连
  （rc=35 / HTTP=000）。取证确认非图幅问题：断连期连已成功的 mp0324 同样连不上。服务器恢复后跑
  `uv run python3 scripts/fetch_atlas_tiles.py --sheets mp03db,mp03dd,mp0503,mp053d,mp053e`
- **键盘 ←/→ 在月/日档仍按「年」步进**。store.year 是整数口径，改月步进要动 store 结构，本次未做。
  月/日档下用滚轮或点选导航。
- **YearJump（g 键）只认整数年**，不支持「755年七月」这类输入。
- **9 位人物匹配歧义（AMBIG）未写入**，25 位未匹配（NONE，多为上古/传说人物，Wikidata 上
  未标 P31=Q5）。对账表 `data/_align/wikidata_align.csv` 可抽样复核，含匹配方式与置信依据。
- **事件/战役/政权尚未配图**。「赤壁之战该配哪张画」是编辑判断不是检索问题，自动化容易张冠李戴，
  与「求真高于中性」冲突，故未做。
- **陈旧后端进程会 404 新瓦片**：Starlette 的 StaticFiles 对启动后新增的子目录返 404，
  抓完瓦片必须重启后端才看得到（本次因此误诊过一次，已取证纠正）。

### 文件级变更清单

- `frontend/src/components/timeline/TimeColumn.vue` —— M11 锚定通道（anchorTo/selectAndAnchor，
  接入 8 处点选）+ M12 全部几何改造（五档缩放/tYear 小数年/月刻度/像素容差取整/口径注记）
- `frontend/src/styles/palettes.js` —— `fmtYM` / `fmtMD` / `isGregorian` / `GREGORIAN_FROM`
- `frontend/src/components/shared/EntityProfile.vue` —— 头像兜底旗 + 史料 tab 三节 + 延伸阅读
- `frontend/e2e/m11-event-anchor.spec.js`（新，5 钉）、`frontend/e2e/m12-sub-year.spec.js`（新，6 钉）
- `schema/person.yaml` —— image_credit / image_license / image_source_page / wikidata_id / wikipedia_zh
- `scripts/align_wikidata.py`（新）—— 四段式 Wikidata 对齐流水线
- `data/entities/persons/*.yaml` —— 702 个文件写入外部标识与图像
- `data/_align/` —— 对账物（jsonl + csv），可复现可抽查
- `data/geo/atlas_tiles/mp0324|mp0334|mp0346|mp035a|mp0375|mp0394|mp0589|mp058a|mp05c1|mp05d1` —— 1720 片
- `.gitignore` —— 忽略 test-results/

---

## 2026-07-21 · 西汉之前疆域 —— 接入谭图 + 补 CHGIS 空档 + 修直开竞态（M14）

### 做了什么（写给非开发者）

Rick 报「西汉之前的疆域数据都是空的」。取证后发现这不是一个问题，是三件事叠加，逐一处理：

1. **先秦的矢量疆域，权威源里根本不存在**。郡县制是秦朝的发明，CHGIS（哈佛+复旦，我们唯一的
   矢量疆域数据源）最早只到公元前 224 年——春秋 0 个府、战国全期仅 4 个（还都是秦国前身的郡）。
   战国/春秋/商周的行政疆界数据，任何权威源都没有；凭空捏造违背「求真高于中性」。
   **但谭其骧图集有先秦的权威地图**，就在 app 的「古」底图里（夏到秦六幅，瓦片俱全）。
   用户看到的「空」，是默认「素」底图只画矢量层的空，不是真没权威资料。
2. 于是**把「古」图集接成先秦的答案**：素底空白时给一键「切古」入口并标注该年图幅（如「战国」），
   古底图上把误导的「无疆域数据」改成「本图即谭其骧图集『战国』·矢量疆域无源」。真正无图幅的
   年份（如现代 1950，谭图止于 1911）才仍显「无疆域数据」。
3. **补上 CHGIS 能填的真实空档**：秦朝疆域此前被截断成 7/10 个府，补齐缺的 3 个（鄣郡/会稽郡/
   象郡）→ 前215 年疆域 10 块。
4. **顺手逮到一个真 bug**：直接打开先秦年份的链接会残留上一朝代的疆域（实测闪现「唐 871」）——
   异步竞态，慢的旧请求后返回覆盖了快的新请求。加请求时序守卫修掉。

### 关键决策与被否决的备选

- **不给先秦画矢量疆界**（求真高于中性）。学界对先秦疆界本身就存疑，CHGIS 也没有——捏造即造假。
  权威答案是谭其骧的印刷图（栅格），已在「古」底图，接进来即可，零虚构。
- **楚汉阶段（前206–前203）的 9 块 CHGIS 过渡郡不做矢量填充**。楚汉分治，把这 9 块硬塞给西汉或
  西楚都是张冠李戴，同样违背求真。交由「古」图集的西汉幅（覆盖 -206..8）呈现。
- **切古用一键入口而非自动切换**：自动切会覆盖用户的底图选择与本地偏好，一键入口尊重用户控制。

### 当前状态

已提交 main（`e53bea8`，未 tag——版本号留待 Rick）。预览在 http://localhost:5173。
先秦年份：素底见「切古」入口，古底见谭图 + 「本图即疆域」说明；秦朝疆域 10 块。
验证：新增 e2e m14 5 钉；全量回归 **68/68**（既有 63 + m14 5）；pytest **58**；
validate **errors=0 / warnings=20283**（基线一致）；vite build ✓。

### 未尽事项与已知问题

- **先秦矢量疆域仍为空**（有意为之，非缺陷）。若将来要让素底也上色，唯一诚实的路径是人工把谭其骧
  先秦图描成矢量多边形——工作量大、边界学界存疑、精度风险高，本次按求真原则未做。
- 楚汉阶段（前206–前203）矢量层仍空，同上，交由古图。

### 文件级变更清单

- `scripts/extract_chgis.py`（新）—— CHGIS 府级 polygon 按年窗抽取为 GeoJSON 的可复用脚本
- `data/geo/chgis_qin.geojson` —— 补齐 3 块（7→10）
- `frontend/src/components/map/MapPanel.vue` —— 空态古图接入（yearSheet + 切古入口/本图即疆域）+ paintTerritories 请求时序守卫
- `frontend/e2e/m14-pre-han-territory.spec.js`（新，5 钉）

---

## 2026-07-22 · Codex 接手盘点与 M14 复验

### 做了什么（写给非开发者）

从 Claude Code 切换到 Codex 后，对仓库目标、架构、提交线、全部本地 refs、reflog、worktree 与交接文档做了只读盘点，并重新跑了完整验证。结论是：没有遗留的未完成 branch 或 worktree；v3.1 已合入并发布 `v1.2.0`，M14 也已在 `main` 收口并发布 `v1.2.1`。本轮没有继续臆造一条开发线，只校正会误导后续接手者的文档。

### 关键决策与被否决的备选

- 以本地 refs / reflog / tag / 工作区状态为分支事实源，不采信 `handoff.json` 里仍写着的“v3.1 待验收并 main”；后者是 2026-07-20 的过期快照。
- 不开启新功能迭代。北宋/金矢量疆域虽然是当前最明显的内容缺口，但它属于下一轮产品方向，不是 Claude 留下的未完成 worktree。
- `PROGRESS.md` 保留为历史构建日志，不重写旧阶段数字；在顶部明确当前口径，避免破坏可追溯过程。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
```

本轮实跑：后端 `pytest` **58 passed**；数据校验 **7,396 实体 / 10,254 关系 / errors=0 / warnings=20283**；Vite production build 通过（仍有既有的 >500kB 懒加载 chunk 警告）；Playwright 系统 Chrome 全量 **68/68 passed**。M14 的完成状态由当前代码复验确认，不只依赖旧日志。

### 未尽事项与已知问题

- `handoff.json` 已滚到 M14，但其中大量 v3.1 施工细节作为历史证据保留；下一轮应在选定产品方向后继续滚动，而不是另建一次性交接文档。
- 父目录 `/Users/rick/ZCodeProject/AGENTS.md` 描述的是另一个“个人投资副驾”项目，与本仓库不符；仓库内目前没有自己的 `AGENTS.md`，后续代理必须以本仓库 README / WORKLOG / handoff 取代其项目事实。
- `frontend/package.json` 版本仍为 `1.1.0`，而最新仓库 tag 为 `v1.2.1`；本轮未改发布元数据，避免在已打 tag 后制造新的未发布版本状态。
- 当前最高严重度的内容缺口仍是北宋疆域 GeoJSON 只有 10 个 feature；是否进入 M15 需先核 CHGIS 原始数据能力。另有 5 幅图集瓦片缺层、月/日档键盘步进仍按年等已知项，详见 `handoff.json`。

### 文件级变更清单

- `README.md` —— 关系图架构由过期的 Cytoscape 更正为实际的 d3-force + Canvas。
- `PROGRESS.md` —— 标明它是 phase 16 历史构建日志，并指向当前规模口径。
- `handoff.json` —— 分支/worktree、版本、验证基线与下一任务状态滚到 M14 / v1.2.1。
- `WORKLOG.md` —— 追加本次 Codex 接手盘点与复验记录。

---

## 2026-07-22 · Codex 连续优化收口——历史语义、时间导航、性能与自包含验证

### 做了什么（写给非开发者）

在确认没有遗留 branch/worktree 后，继续处理盘点时可见的工程缺陷与高置信内容缺口：

1. **纠正历史地图的语义与坐标**：CHGIS 原始府级数据从高斯投影正确转换到 WGS84；每条建置记录按自身起止年过滤、重复记录合并但保留真实 multipart。它们现在明确显示为“府级行政建置记录”，不再按文件名冒充辽、宋等政权疆域。全库 3,062 条可去重记录仍在，1050 年的福州、泉州、杭州也不会再被误标为辽。
2. **补齐时间导航闭环**：跳年支持 `755年七月`、`755-07`、`前221年三月`；方向键按当前年/月/日粒度步进；精确跳转会自动进入月档，同时保持全局年份、URL 与地图仍是整数年口径。星图时空柱的异步竞态、柱外年份误导、朝代归属与颜色错位一并修正。
3. **把开发与验收变成仓库自包含**：后端启动统一走仓库环境或锁定 requirements，运行依赖与测试依赖分离；Playwright 自己冷启动并回收隔离前后端，不再依赖手工常驻进程，也不再有 Vite 同端口重复拉后端的竞态。
4. **补高置信内容，不靠猜测清零**：新增 4 个军事实体、6 段有史料依据的行军路线；新增 8 条因果关系和 1 条事件层级关系；修正刘承祐、黄天荡、长平等可核事实；脱贫攻坚条目改用国家统计局与外交部乡村振兴衔接材料。仍缺证据或存在地望争议的项目明确留空或标 `needs-verification`。
5. **补齐五幅历史图砖**：mp03db、mp03dd、mp0503、mp053d、mp053e 均含标准 BBOX 172 片及 7 片边缘扩展，共各 179 片。全库现为 29 个目录、5,023 个 PNG，文件签名扫描无异常；抓取器增加 8 秒单请求超时、单 URL 不重试和主机熔断。
6. **消除两个随数据规模放大的热点**：CHGIS 首次聚合从约 18.26 秒降至 250.95 毫秒（约 72 倍），原因是 GeoJSON 改用 JSON 解析并加有界缓存；李白一层关系查询从约 3.19 毫秒/次降至 0.17 毫秒/次（约 18.8 倍），改用保持全局顺序的邻接索引。

### 关键决策与被否决的备选

- CHGIS 只表达行政建置，不表达政权疆界。拒绝按文件名给 3,062 条记录强塞 `polity_id`；北宋/金政治边界继续等待权威分国矢量源或人工数字化审校。
- 不为降低审计数字机械补因果边或行军线。当前 23/105 个军事/政变/改革事件仍无因果关系，18 个核心行军候选仍需史料核验；“诚实留空”优于时间相邻即判因果。
- 不把 test/httpx 留在生产依赖，也不借父项目虚拟环境；测试版本精确锁定在 `backend/requirements-dev.txt`。
- 不把精确月写进全局整数年状态，避免 URL、地图与既有年度查询契约随滚动每帧抖动；月/日只作为一次性导航请求与时间柱局部精度。
- Docker/Nginx/一键启动草案修复了 lockfile 构建、同源 `/tiles` 和 smoke 失败仍返回成功的问题，但它们属于部署配置，依协议在 Rick 明确确认前不定稿、不提交。

### 当前状态：现在能跑什么、怎么跑

```bash
cd frontend && npm run dev
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
cd frontend && npm run build
cd frontend && npm run test:e2e
```

冻结工作区实测：后端 **77/77 passed（9.96s）**；数据校验 **7,396 实体 / 10,263 关系 / errors=0 / warnings=20,278（3.81s）**；Vite 构建 **197 modules / 1.40s**；Playwright 冷启动全量 **76/76 passed / 4.5m**，`VITE_BACKEND_AUTOSTART=0` 生效且结束后 `:8002`、`:5174` 均回收。Shell 语法、handoff JSON、版本一致性、Vite/Playwright 配置导入、Docker 静态合同与 `git diff --check` 全部通过。

### 未尽事项与已知问题

- **等待 Rick 确认部署配置**：`docker-compose.yml`、`frontend/Dockerfile`、`frontend/nginx.conf`、`scripts/up.sh` 及配套 `.dockerignore` 仍是未提交草案。本机只有 Docker 29.6.1 客户端、没有 `docker compose` 子命令，因此只能静态检查，不能声称容器实跑通过。
- **内容核验仍需人工判断**：23 个因果缺口、18 个行军候选、刘承祐相关事件/政权的农历与公历口径、9 例 Wikidata AMBIG、25 例 NONE，以及事件/战役/政权配图，均不能自动猜测。
- **北宋/金政治边界仍无可信矢量源**；现有 CHGIS 无 polity 字段，只能中性展示府级建置，谭其骧栅格底图仍是当前可信展示。
- **Place 内联关系约 4,054 条未批量物化**：直接转成普通关系会改变最短路径与图谱权重，需先确认关系语义。
- 前端仍有两个既有的大型懒加载 chunk 警告：`inkPalette` 523.73kB、`MapPanel` 818.63kB；本轮没有为了消除警告预制抽象或改变加载行为。
- 响应式布局、新手引导及夏商周/民国/共和国的新色板属于用户可见设计，需先给可预览方向再定稿。

### 文件级变更清单

- 工程与文档：`AGENTS.md`、`README.md`、`handoff.json`、`backend/requirements.txt`、`backend/requirements-dev.txt`、`scripts/run-backend.sh`、`scripts/dev.sh`、`scripts/dev-backend.sh`、`frontend/package.json`、`frontend/package-lock.json`、`frontend/playwright.config.js`、`frontend/vite.config.js`。
- 后端：`backend/app/api/relations.py`、`backend/app/core/data.py`、`backend/app/main.py`、`backend/app/services/graph_service.py`、`backend/app/services/territory_service.py`、`backend/scripts/import_chgis.py`。
- 后端测试：`backend/tests/test_api_entities.py`、`test_api_graph.py`、`test_api_relations.py`、`test_api_territories.py`、`test_audit_content.py`、`test_fetch_atlas_tiles.py`、`test_index_relation.py`。
- 前端：`frontend/src/api/client.js`、`components/map/MapPanel.vue`、`components/shared/HotkeyHelp.vue`、`components/shared/YearJump.vue`、`components/starmap/ColumnView.vue`、`components/timeline/TimeColumn.vue`、`composables/useHotkeys.js`、`starmap/engine/columnMount.js`、`dataAdapter.js`、`inkPalette.js`、`stores/useTimeStore.js`、`utils/timeNavigation.js`。
- E2E：`frontend/e2e/graph.spec.js`、`m8-event-overflow.spec.js`、`m13-time-navigation.spec.js`、`m14-pre-han-territory.spec.js`、`march-routes.spec.js`。
- 内容与数据：`data/entities/battles/{changping,huangtiandang,shanhai_guan}.yaml`、`data/entities/events/{an_lushan_rebellion,jingkang_zhibian,sui_mie_chen,tuopin_gongjian}.yaml`、`data/entities/persons/liuchengyou.yaml`、`data/relations/all.yaml`、`data/relations/event_causal.yaml`、`data/geo/chgis_qin.geojson`、五个 `data/geo/atlas_tiles/<sheet>/` 图砖目录。
- 内容工具：`scripts/audit_content.py`、`scripts/extract_chgis.py`、`scripts/fetch_atlas_tiles.py`、`scripts/requirements-chgis.txt`、`scripts/validate_data.py`、`docs/march-routes.md`。
- 待确认部署草案：`docker-compose.yml`、`backend/.dockerignore`、`frontend/.dockerignore`、`frontend/Dockerfile`、`frontend/nginx.conf`、`scripts/up.sh`。

### 同日后续 · 窄屏取证、键盘可达与地图首屏竞态

继续从实际运行态复核，而不是只扫源码。桌面首屏在 1280×720 下仍能清楚表达“时间柱—此刻—地图—人物”；切到 390×844 后，页面没有响应式断点，桌面双栏被硬裁切，品牌标题挤成竖排、地图与人物档案只能看到一半。基于这两张真实截图生成了两种移动端草案：①时间柱主屏 + 可拉起地图抽屉；②时间 / 地图 / 人物单画布切换。依用户可见设计须确认的约定，生产 UI 尚未按任一草案修改。

不改变视觉方向的可访问性缺陷已直接修复：时间柱的朝代、帝王、人物、事件、聚合与年谱，右侧在世人物，搜索建议/类型筛选，以及地图底图和真实政权图例都能通过 Tab 聚焦、Enter/Space 激活并向读屏暴露状态；事件密度条提供垂直 slider 语义及方向键、PageUp/Down、Home/End。全局 Space 播放不再与人物控件冲突，同时保留月/日档方向键导航。

全量回归还抓到一个与可访问性无关、此前被时序掩盖的真缺陷：安史之乱已选中时，MapPanel 可能尚未挂载，或较慢的旧人物定位随后清掉新路线；地图的 `idle` 也可能因 source 状态长期不触发。现在挂载后补消费当前选中实体，以单调 `locateSeq` 拒绝过期异步结果，并用 style 结构就绪 + `styledata` / 800ms 有界重检替代无限等 `idle`。MapLibre 4.7.1 文档同时确认 `querySourceFeatures` 会因内部切 tile 返回拆分/重复要素，测试因此改用公开 `GeoJSONSource.serialize()` 精确核对原始 2 段，仍保留 2 个箭头和两条路线标题断言；重复 5/5 通过。

最终实跑：Playwright 全量 **80/80 passed（4.7m）**，行军路线重复 **5/5**，Vite production build **197 modules / 1.48s**，`git diff --check` 通过，`:8002` / `:5174` 均已回收。两个大 chunk 的实测体积为 MapPanel 819,477B / gzip 223,315B、Three 共享块 523,767B / gzip 132,102B；二者已有路由/组件懒加载，当前没有用户侧性能回归证据，故未用纯拆包制造更多请求来消除警告数字。

本段新增或继续修改：`frontend/src/components/shared/SearchBar.vue`、`frontend/src/components/timeline/{TimeColumn,MomentPanel,AggPopList}.vue`、`frontend/src/components/map/MapPanel.vue`、`frontend/src/composables/useHotkeys.js`、`frontend/e2e/accessibility-keyboard.spec.js`、`frontend/e2e/march-routes.spec.js`、`handoff.json`、`WORKLOG.md`。

## 2026-07-22 · 内容对抗复核与全量回归收口

### 做了什么（结果）

把内容审计从“只有总数”改成可直接定位实体 ID，并完成一轮高置信补录与反向审稿：黄巢起义新增 880 年洛阳至长安的两都阶段路线；齐都临淄、日本都东京补入现有可复用地点；荆轲因现有 13 类角色没有“刺客/使者”的诚实映射继续留空，桂陵地望与黄天荡胜者也不为清零而猜。对抗复核同时撤回了时间倒置、同年事件强判因果、重叠事件互相导致及未经证实的“桂陵=长垣”等弱结论，因此军事/政变/改革事件无因果数仍为 23/105——数字没有变漂亮，但数据更可靠。

刘承祐—郭威—后周链按《资治通鉴》卷289、290统一为农历月份：950 年十一月刘承祐遇害，十二月郭威监国，951 年正月即位并建立后周；人物、事件、政权与关系全部对齐，并新增两条回归测试。安禄山行军线纠正为幽州—洛阳（东都）—长安，避免把涿州县级地点和后世洛阳地点混入唐代路线。

全量 E2E 首轮暴露“未打开链接页也会为角标冷建全库提及图”：首屏 `stats` 被 CPU 竞争拖过 10 秒，且并发请求可能重复构建。现已取消 eager 预取，只有首次打开链接 tab 才加载；后端用 `RLock` single-flight，三线程冷启动只建一次。进一步 profile 发现旧扫描对 7,663 个文本字段执行约 6,745 万次 `str.find`；无依赖字符 trie 按原名字排名稳定回排，全库逐字段与旧实现精确相等。图构建从 3.46 秒降至约 0.02 秒，独立进程完整单冷从 5.970 秒降至 2.433 秒（-59.2%）；余下主要是 YAML/NameIndex 加载，不再阻塞首屏。

图集西缘缺片也从模糊现象收敛为精确坐标：默认李白定位碎叶时每幅缺 `4/10/{5,6}`、`5/21/{11,12}`、`6/43/{22,23,24}` 共 7 块；UI 使用 28 幅，最多缺 196 个文件。远端首个请求 3 秒 SSL 超时后按主机熔断，未重试，标记 `needs-verification`；本地 5,023 个 PNG 签名均正常，标准 4,988 片计划幂等无新增、无失败。

### 关键决策与被否决的备选

- 内容边只有时间先后、并发或主题相关时，不提升为因果；角色、地望、胜者存在枚举不匹配或史实歧义时保留空值。
- 关系角标不值得阻塞首屏；改成按需加载，并发安全由后端 single-flight 保证。扫描优化只接受全库逐字段与旧实现完全相等的方案，不能缩小扫描范围或放宽测试。
- 图集外部主机首探超时后立即熔断，不对同一 URL 重试；没有拿到文件就不声称补齐。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
cd frontend && npm run build
cd frontend && npm run test:e2e
```

冻结工作区实测：后端 **83/83 passed（10.40s）**；数据校验 **7,396 实体 / 10,263 关系 / errors=0 / warnings=20,278（4.38s）**；Vite production build **197 modules / 1.47s**；Playwright 全量 **81/81 passed（4.9m）**，相关可访问性/链接 spec 另重复 **25/25**。`git diff --check`、handoff JSON 与 shell 语法检查通过；仓库仍只有 `main`、单 worktree、无未合分支。

### 未尽事项与已知问题

- 390×844 响应式方向仍等 Rick 在“时间柱主屏+地图抽屉”和“时间/地图/人物单画布切换”两张草案中选择；确认前不改生产 UI。
- Docker/Compose/Nginx/up.sh 仍是待确认部署草案；本机无 `docker compose`，只有静态合同检查，确认前不定稿、不提交。
- 首次主动打开链接页在独立进程仍有约 2.433 秒 YAML/索引冷加载；Place 内联关系约 4,054 条、内容规范草案的大批 note/bio/life_events 缺口，以及北宋/金政治边界仍需单独决策或可信来源。
- 图集西缘 196 个候选文件尚未补抓，外部源状态需择机验证。

### 文件级变更清单

- 审计与测试：`scripts/audit_content.py`、`backend/tests/test_audit_content.py`、`backend/tests/test_later_han_zhou_calendar.py`、`backend/tests/test_api_links.py`。
- 内容数据：`data/entities/events/{an_lushan_rebellion,guo_weizhou,huangchao_qiyi}.yaml`、`data/entities/persons/{guowei,liuchengyou}.yaml`、`data/entities/places/{caishiji,gaoping}.yaml`、`data/entities/polities/{houzhou,qi_state,riben}.yaml`、`data/relations/{all,event_causal}.yaml`、`docs/march-routes.md`。
- 链接性能与回归：`backend/app/api/links.py`、`frontend/src/components/shared/EntityProfile.vue`、`frontend/src/composables/useEntityDetail.js`、`frontend/e2e/{accessibility-keyboard,march-routes}.spec.js`。
- 文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-22 · 第二轮自主收尾——出处可定位、代表都城与 YAML 冷加载

### 做了什么（结果）

在移动端、部署和系统性内容迁移仍等 Rick 拍板期间，继续完成不改变产品方向的明确待办。内容审计现在会把空 source 直接列出实体 ID，并把空字符串视为“缺来源”而不是字段完整；据此修复开禧北伐、隆兴北伐两条目的空来源，同时把误写成书名的 impact 改成真实历史影响，空 source 从 2 降到 0。

22 个缺都城政权逐项核对后，只为楚、韩、魏、赵、郑补入现有且年代语义可成立的代表都城，缺口降至 17。集团、时代总称、游牧联盟、多次迁都政权及现有 Place 明显错代的项目继续留空。事件关系只新增两条上下文：隋征高句丽与隋末起义为同期交叠，唐灭东突厥属于贞观时期；两者都没有冒充直接因果，因此 23/105 的因果缺口未被虚假清零，完全孤立项由 20 降至 18。

链接页剩余冷启动经 profile 确认为 7,425 个 YAML 的 Python 解析成本。当前 PyYAML 6.0.2 带 LibYAML，改用安全语义相同的 `CSafeLoader`，无 LibYAML 平台自动回退；全库逐文件对比值、标量类型和键顺序 0 差异。独立进程完整单冷由 2.433 秒降至约 1.04 秒，后端全量测试对照由 16.07 秒降至 11.74 秒。合并目录签名的第二方案收益不足 10% 且会增加失效耦合，未实施。

### 关键决策与被否决的备选

- `capital` 只填能由现有精确 Place 与政权史源支撑的代表都城；多都迁徙或错代地点不为降低数字硬填。
- 事件存在同期或时期从属时使用 `concurrent_with` / `part_of`，不升级成 `led_to`；白登、侯景、开禧、邺都、雍正、回鹘等缺精确端点继续标 `needs-verification`。
- YAML 加速必须逐文件等价且保留目录签名热更新；不足 20% 或增加一致性风险的路径不落地。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
uv run --with-requirements backend/requirements.txt python scripts/audit_content.py
cd frontend && npm run test:e2e -- accessibility-keyboard.spec.js
```

本轮实测：后端 **86/86 passed（10.72s）**；数据校验 **7,396 实体 / 10,265 关系 / errors=0 / warnings=20,278（4.4s）**；内容审计空 source **0**、都城缺口 **17/84**、因果缺口仍 **23/105**；加载器变更后的链接/键盘 E2E **5/5 passed（20.6s）**，mention graph 日志 **0.02s**。

### 未尽事项与已知问题

- 移动端、部署草案、系统性内容迁移仍按默认边界等待 Rick 选择；未替用户定稿。
- 17 个都城空值均有具体留空理由；18 个完全孤立战乱/改革事件仍需新建精确端点或进一步史源，不适合按时间相邻补边。
- 外部图集西缘 196 个候选缺片仍受源站 SSL 超时阻挡，保持 `needs-verification`。

### 文件级变更清单

- 审计与测试：`scripts/audit_content.py`、`backend/tests/test_audit_content.py`。
- 内容：`data/entities/events/{kaixi_beifa,longxing_beifa}.yaml`、`data/entities/polities/{chu_state,han_state,wei_state,zhao_state,zheng_state}.yaml`、`data/relations/event_causal.yaml`。
- 性能与回归：`backend/app/core/data.py`、`backend/tests/test_api_links.py`。
- 文档：`README.md`、`handoff.json`、`WORKLOG.md`。

### 同日最终终审 · 事件端点与争议战役字段

最后一轮只新增一条 `concurrent_with`：第一个五年计划（1953—1957）与社会主义改造（1953—1956）在过渡时期总路线下并行推进；不把其中任一方写成另一方的单一原因。其余 11 个事件没有粒度相当、时间与史源都成立的现有端点，全部保留 `needs-verification`。审计结果为 6 个已有上下文 counterpart、17 个完全孤立项，直接因果缺口仍为 23/105。

桂陵、马陵的古战场地望均有重大分歧，仓库也没有可无争议复用的精确 Place；黄天荡则同时存在金军最终突围、宋军长期阻遏效果，单值 `victor` 会把战术结果与战略影响压成假定论。三项字段因此继续留空；马陵说明中原先单列的“今山东莘县一带”改为“具体地望有多说”，使文本与空 location 一致。

最终实测：后端 **86/86 passed（10.46s）**；数据校验 **7,396 实体 / 10,266 关系 / errors=0 / warnings=20,277（4.6s）**；内容审计空 source **0**、都城缺口 **17/84**、完全孤立战乱/改革事件 **17**。本段只新增/修改 `data/relations/event_causal.yaml`、`data/entities/battles/maling.yaml`、`handoff.json`、`README.md`、`WORKLOG.md`。

## 2026-07-22 · 本轮最后收口——Wikidata 官方消歧与当前态文档

### 做了什么（结果）

Wikidata 对齐的最后 9 例官方实体级人工消歧已全部收口：对账结果现为 **0 AMBIG / 9 MANUAL / 25 NONE**，736 行中 **711** 行有 `wikidata_id`、**705** 行有 `wikipedia_zh`。人物 YAML 保留此前已经逐项核过 Commons 许可与作者链的 **439** 份媒体；本轮新发现的 P18 没有完整许可与作者链，因此只写 QID 和中文维基条目，不新增图片，也不把“有 P18”误写成“可合规使用”。

同时修正文档当前态漂移：`PROGRESS.md` 顶部当前关系数从 10,254 更新为 **10,266**，但 phase 16 历史正文原样保留；`docs/prd-frontend-interaction.html` 页眉从“草案 v1 · 待评审”改为“历史方案 · A–D 已落地 · E 未立项”，方案正文不追改。README 与 handoff 现写当前 Wikidata 数量；handoff 仍保留历史 commit `3b4e194` 的原始“439 图像 + 696 外链”记录，不用今天的结果篡改当时交付。

独立审计再次确认仓库仍只有 `main`、单一已注册 worktree、没有未合 branch；按 A/B/C/D 分类，A 类当前工程收口项已经清零，剩余均是需要产品选择、外部可信来源或另行立项的 B/C/D 项，不存在应继续追赶的隐藏施工线。

### 关键决策与被否决的备选

- 只把 Wikidata 官方实体级证据足够的 9 例改为 `MANUAL`；25 例 NONE 不猜。
- P18 不是使用授权。缺 Commons 许可、作者与来源链时不写图片字段，宁可保留已有 439 份合规媒体。
- 历史日志与当前摘要分层：更新 README/handoff/PROGRESS 顶部当前口径，但不倒改旧 commit 数字与历史施工正文。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
cd frontend && npm run build
cd frontend && npm run test:e2e
```

本次最后收口实跑：后端全量 **86 passed / 11.22s**；生产构建 **197 modules / 1.48s**，通过，仍只有既有两个 >500kB 懒加载 chunk 警告；数据校验 **7,396 实体 / 10,266 关系 / errors=0 / warnings=20,277 / 3.97s**。CSV、JSONL 与人物 YAML 的 QID/中文条目逐项一致；重新生成 report 与现有 CSV **逐字节一致**；`scripts/align_wikidata.py` 通过 `py_compile`；handoff JSON 与文档文本检查通过。CSV 保持 report 要求的 CRLF，使用 `git -c core.whitespace=cr-at-eol diff --check` 检查通过。完整 E2E 本段未重跑，继续沿用此前 **81/81** 的冻结基线，不把旧结果写成这一步的新验证。

### 未尽事项与已知问题

- 25 例 NONE 继续诚实留空；事件、战役、政权配图仍需要逐图编辑与许可审查。
- 移动端方案、部署草案、行军 A/B/C 规则与 Place 历时性仍是 B/C/D 类待决项，本轮不越权定稿。

### 文件级变更清单

- 同轮 A2 文档修正：`PROGRESS.md`、`docs/prd-frontend-interaction.html`。
- Wikidata 对账与人物字段：`data/_align/wikidata_align.{csv,jsonl}`、对应 9 个人物 YAML（仅 QID/中文条目，无新增图片）。

### 同日交接 checkpoint · 非部署成果已本地提交

本轮非部署成果已建立本地 checkpoint：`6d1be95 Complete post-M14 hardening wave`，共 **806 files**，其中 **708 PNG**。提交明确排除了 6 个仍待 Rick 决定的部署草案：`docker-compose.yml`、`frontend/Dockerfile`、`frontend/nginx.conf`、`scripts/up.sh`、`backend/.dockerignore`、`frontend/.dockerignore`；用户维护的 `AGENTS.md` 也未纳入。当前没有 remote/upstream，本 checkpoint **未 push**。

本段只同步提交与工作区状态，没有重跑测试；验证沿用上一段本轮收口：pytest **86/86 / 11.22s**、validate **7,396 / 10,266 / errors=0 / warnings=20,277 / 3.97s**、build **197 modules / 1.48s**，E2E 沿用此前 **81/81** 冻结基线。当前工作区只剩上述 6 个部署草案、用户 `AGENTS.md`，以及本次待单独提交的 `handoff.json` / `WORKLOG.md` 交接同步。

## 2026-07-22 · 部署 A 定稿与真实容器验收

### 做了什么（结果）

Rick 确认保留部署方案后，将 6 个部署文件定稿并建立本地提交 `9b5b38f Finalize container deployment`（未 push、未发布）。Compose 现在构建生产镜像：后端不再把 `./backend` 覆盖挂进 `/app`，也不再用 `uvicorn --reload`；运行时只读挂载 `data/` 与 `schema/`，backend 健康后才启动 frontend。前端采用 Node 22 + lockfile `npm ci` 构建静态产物，由 Nginx 同源代理 `/api` 与 `/tiles`。

本机没有 Compose plugin/legacy `docker-compose`，因此按 Compose 的同一 network、挂载和环境变量合同，用独立 backend/frontend 容器做了等价隔离拓扑真测。后端 `/api/meta/stats` 返回 **7,396 实体 / 10,266 关系**，schema 与 entities 端点通过；前端 Nginx 配置检查通过，同源 API 返回同一统计，瓦片代理返回真实 PNG。测试结束后临时容器、镜像和 network 已清理。

### 关键决策与被否决的备选

- 首次真实构建暴露 `node:20-alpine` 实际为 Node v20.20.2，而锁定依赖 `@mapbox/jsonlint-lines-primitives@2.0.3` 要求 Node >=22；宿主也是 Node v22.23.1，因此构建镜像升级到 `node:22-alpine`，没有忽略 engine 警告。
- 旧 `docker compose exec backend python tests/test_smoke.py` 在镜像 `/app/tests` 布局下会错误推导 `/data`、`/schema`，与实际 `/app/data`、`/app/schema` 不同。没有改测试或伪造路径，而是改成有 deadline、失败即退出的真实 HTTP smoke：stats / schema / entities、前端 API 代理与 PNG 瓦片。
- 没有为了本机缺 Compose 而改写部署模型；`scripts/up.sh` 依次检测 Compose plugin 与 legacy 命令，均不存在时清晰失败。真实验收使用等价隔离拓扑，不把它说成 Compose 命令实跑。

### 当前状态：现在能跑什么、怎么跑

具备 Compose 的环境运行 `scripts/up.sh`：脚本构建镜像、启动服务、等待 health gate，并执行有界 HTTP smoke。当前机器 Docker CLI **29.6.1** / server **29.5.2** 可用，但没有 Compose plugin、legacy `docker-compose` 或 buildx，因此脚本会在创建 `.env` 或容器前清晰退出。

真实容器验收结果：frontend production build **197 modules / 2.67s**，通过，仍只有既有两个 >500kB 懒加载 chunk warning；backend stats **7,396 / 10,266**；`/api/meta/schema`、`/api/entities?limit=1`、Nginx `-t`、同源 `/api`、`/tiles/...png` 均通过。Compose YAML、`bash -n`、只读挂载、health dependency、无 reload/bind mount、bounded smoke 与 `git diff --check` 静态合同均通过。

### 未尽事项与已知问题

- 本机缺 Compose plugin/legacy 命令与 buildx，不能直接运行 `scripts/up.sh`；这是当前机器的使用限制，不是部署配置未定稿。需在具备 Compose 的环境补一次脚本原命令验收。
- 部署提交只在本地 main，未 push、未发布。移动端与内容语义范围仍等待 Rick 决定。

### 文件级变更清单

- 部署提交：`docker-compose.yml`、`backend/.dockerignore`、`frontend/.dockerignore`、`frontend/Dockerfile`、`frontend/nginx.conf`、`scripts/up.sh`。
- 本段当前态同步：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-22 · 移动端方案一定稿与真实浏览器验收

### 做了什么（结果）

Rick 选择「时间柱主屏 + 底部地图抽屉」后，≤720px 不再硬裁桌面双栏：时间柱占满首屏，顶部与身份筛选压成单行；此刻读数、真实 MapLibre 年代地图和在世人物进入底部抽屉。抽屉收起时保留读数预览，展开高度约占内容区 41%，支持点击、ArrowUp/ArrowDown、Home/End 以及 pointer 上下拖拽。移动地图保持当年中国概览，不再因默认选中李白而先飞往人物地理锚点；桌面仍沿用原双栏、档案与地图定位行为。

按 390×844 参考图做了同尺寸左右对照，最终结果写入 `design-qa.md`，P0/P1/P2 均为 0。生产界面保留现有搜索输入和两个路由直达按钮，没有为了像素照抄而牺牲既有功能；地图仍按 CHGIS 真数据中性显示行政建置，没有把参考图的红色理想分区冒充政权疆域。

容器部署草案已在此前 `9b5b38f` 定稿并提交，本段没有再改 CI、部署平台或对外发布，也没有 push；用户维护的 `AGENTS.md` 继续不纳入。共享工作区同时出现另一会话的 EdgeOne/来源致谢草案（backend create_app、AttributionDialog 等）；它与已确认的容器部署不是同一方案，仍处于脏工作区，因此本提交只暂存移动端相关 hunk，不替并行会话半途提交。

### 关键决策与被否决的备选

- 抽屉不做全屏：参考图和「时间柱为主」都要求保留年代上下文，最终展开顶边约 y=539，而不是覆盖到页面顶部。
- 移动 MomentPanel 只保留读数、地图和在世人物；桌面长档案不塞进窄抽屉，点选与深度浏览仍可走桌面或谱系星图。
- 移动/桌面地图使用不同的分栏存储键，避免桌面历史比例把移动地图挤到看不见人物名单。
- 未引入新图标库、布局依赖或第二套路由；响应式边界只新增一个职责单一的移动布局壳。

### 当前状态：现在能跑什么、怎么跑

```bash
cd frontend && npm run build
cd frontend && npm run test:e2e -- mobile-layout.spec.js
```

本段实跑 `npm run build`：**199 modules / 1.67s，通过**，仍只有既有两个 >500kB 懒加载 chunk 警告。Codex 应用内浏览器在 **390×844** 实测：顶部无横向溢出、筛选可横滚、时间柱 390×745、抽屉点击/键盘/上下拖拽、真实地图与在世人物均通过；在 **1440×900** 复验移动容器为 0、TimeColumn 与 MomentPanel 各 1，桌面结构未回退；控制台无 error/warning。新增 `mobile-layout.spec.js`，但本段遵循已选应用内浏览器，没有另起 Playwright CLI；此前全量 **81/81** 只作为冻结基线，不冒充本段新结果。

### 未尽事项与已知问题

- 内容工程是否从「高置信维护」升级为「系统迁移」仍待 Rick 选择；这不是代码失败，见本次交付说明。
- 新手引导仍未做；本轮只兑现已确认的响应式结构。
- 本机依旧没有 Compose plugin/buildx；容器方案状态与 `9b5b38f` 记录一致，未发布。
- 并行共享会话的 EdgeOne/来源致谢草案仍未完成独立验证与提交；本轮保留其工作区改动，没有混入移动端提交。

### 文件级变更清单

- 移动布局：`frontend/src/App.vue`、`frontend/src/components/timeline/MobileTimelineLayout.vue`、`frontend/src/components/timeline/MomentPanel.vue`、`frontend/src/components/timeline/TimeColumn.vue`。
- 响应式与地图：`frontend/src/components/shared/FilterBar.vue`、`frontend/src/components/shared/SearchBar.vue`、`frontend/src/components/map/MapPanel.vue`。
- 验收与文档：`frontend/e2e/mobile-layout.spec.js`、`design-qa.md`、`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-22 · EdgeOne 混合部署上线与来源致谢

### 做了什么（结果）

历史全景知识台已发布到正式地址 `https://history.ricksi.com/`。EdgeOne 负责静态前端、5,023 张地图瓦片和云函数 API；域名 CNAME 指向 `history.ricksi.com.pages.dnsoe6.com`，免费 RSA 2048 证书已部署并自动续期。应用右上角新增 `!` 来源与致谢入口，明确项目仅用于个人研究、学习和作品展示，并保留 CBDB 的非商业、署名与相同方式共享义务及其他资源各自许可。

### 关键决策与被否决的备选

- 采用 EdgeOne 混合方案，而不是把 245 MB 数据与 FastAPI 查询复制成纯静态页面；前端和瓦片走边缘缓存，查询由云函数按需运行。
- 数据在构建期编译为只读 JSON 随部署发布，不从 GitHub 运行时逐请求拉取；避免延迟、限流、可用性和版本不一致问题。
- 正式入口只使用自定义 HTTPS 域名，不向主页暴露带访问令牌的临时预览地址。

### 当前状态：现在能跑什么、怎么跑

- 线上首页 `https://history.ricksi.com/` 返回 200；`/api/meta/stats` 返回 200 与 7,396 实体 / 10,266 关系；抽样地图瓦片返回 PNG。
- 公网 DNS 解析器 `119.29.29.29` 与 `8.8.8.8` 均返回 EdgeOne CNAME；控制台证书状态为“已部署”，到期时间 2026-10-20 07:59:59，已启用自动更新。
- 前端生产构建通过，后端 pytest 86/86，通过来源致谢键盘可访问性定向 E2E 6/6；EdgeOne 紧凑 API 与部署产物数据/瓦片哈希核对通过。

### 未尽事项与已知问题

- CHGIS V5 随库 EULA 禁止未经书面协议的电子再分发；当前云函数包包含经筛选、去除误导性政权字段的 CHGIS 几何，但是否落入允许的“研究出版物中的部分数据”仍需书面许可确认。补足固定署名和修改说明不等于消除该分发边界风险。
- OSGeo 中国站公开提供配准瓦片，但页面未给出允许第三方完整镜像再分发的明确许可。本轮不能把“公开可访问”推定为“允许自托管”。
- 古地图瓦片、图片与开源软件仍分别受原始许可约束；若未来改为收费产品，需要重新做逐项商业许可审查。
- EdgeOne 云函数首次冷请求实测约 2.7 秒，热缓存后的页面和静态瓦片均为亚秒级；后续有真实访问量后再决定是否增加预热或常驻后端。

### 文件级变更清单

- EdgeOne：`edgeone.json`、`package.json`、`scripts/build_edgeone.py`、`cloud-functions/`、`backend/app/core/data.py`、`backend/app/main.py`、`.gitignore`。`edgeone-dist/` 是可由上述入口重建的 134 MB 发布产物，明确忽略、不进入 Git。
- 来源与致谢：`frontend/src/App.vue`、`frontend/src/components/shared/AttributionDialog.vue`、`frontend/e2e/accessibility-keyboard.spec.js`、`README.md`、`WORKLOG.md`。

## 2026-07-23 · EdgeOne 源码收口、发布闸门与许可审计

### 做了什么（结果）

将共享工作区里已上线但未入 Git 的 EdgeOne 构建、云函数 API 和来源致谢实现收成可复现源码。根 `npm run build` 现在先执行数据校验，只有 `errors=0` 才构建前端并生成发布包；云函数在编译 JSON 缺文件或实体/关系数与 manifest 不一致时直接失败，不再静默回落为空库。`edgeone-dist/` 为 134 MB / 5,113 文件的可再生产物，已加入忽略规则，不重复提交 5,023 张已跟踪瓦片。

重新探测正式地址：首页 200，`/api/meta/stats` 200 并返回 7,396 / 10,266，仓库真实瓦片 `mp0302/2/2/1.png` 返回 200、`image/png`、256×256。首次误用不存在的 `tang/0/0/0.png` 得到 404，核对真实文件路径后纠正，没有把这次探测错误归因于线上故障。

### 关键决策与被否决的备选

- 不提交 `edgeone-dist/`：它完整重复前端构建、云函数复制和 116.68 MB 瓦片，可由源文件确定性重建；提交只会放大仓库且制造源码/产物漂移。
- 不让发布构建绕过数据红线：根构建明确串联 `validate_data.py`，没有因为 warning 数量大而隐藏、降级或删掉既有检查。
- 来源弹层补上 CHGIS 固定引用和本站变换说明，并把背景设为 `inert`；但明确否决“加了致谢就等于取得再分发许可”的错误结论。
- 移动抽屉全量 E2E 暴露净位移比合同少约 7px；修复产品的折叠露出高度 112→104px，没有放宽 `>200px` 断言。

### 当前状态：现在能跑什么、怎么跑

```bash
npm run build
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
cd frontend && npm run test:e2e
```

本段验证：数据 **7,396 / 10,266 / errors=0 / warnings=20,277 / 8.42s**；根构建 **201 modules / 1.73s**，发布包 **5,113 files / 134.08 MB**；pytest **90/90 / 11.03s**；只安装云函数 requirements、确认无 PyYAML 的隔离 smoke 返回 **7,396 / 10,266**；完整 E2E 首跑 **84/85**，修产品几何后定向 **3/3**，最终全量复跑 **85/85 / 4.9m**。`git diff --check` 通过。

### 未尽事项与已知问题

- **公开再分发许可未解决**：CHGIS V5 随库 EULA 要求固定引用、说明修改，并禁止未经书面协议的电子再分发；OSGeo 页面说明瓦片源自《中国历史地图集》，但未提供允许第三方完整镜像的明确许可。当前正式站点已经公开这两类内容；需 Rick 提供书面许可，或确认下线相关图层/站点。未经确认不再次发布。
- 内容系统迁移继续按 C1 保守维护；Place 关系、人物生平和路线批量迁移没有在许可问题后面被偷偷启动。
- 两个 >500 kB 懒加载 chunk warning 仍在，均为已有 MapLibre/地图配色重块；本轮没有因部署收口引入新的首屏同步依赖。

### 文件级变更清单

- 部署与运行时：`.gitignore`、`edgeone.json`、`package.json`、`scripts/build_edgeone.py`、`cloud-functions/`、`backend/app/core/data.py`、`backend/app/main.py`。
- 回归：`backend/tests/test_edgeone_runtime.py`、`frontend/e2e/accessibility-keyboard.spec.js`。
- 界面与响应式：`frontend/src/App.vue`、`frontend/src/components/shared/AttributionDialog.vue`、`frontend/src/components/timeline/MobileTimelineLayout.vue`。
- 文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 许可安全分发 profile 预备完成

### 做了什么（结果）

在不改动当前线上站点的前提下，新增可逆的 EdgeOne `safe` 分发 profile。`npm run build:safe` 会生成独立的 `edgeone-dist-safe/`：保留 7,396 个实体、10,266 条关系、16 个手工政权 GeoJSON 与完整 API，排除 18 个 `chgis_*.geojson`、5,023 张谭其骧图集镜像瓦片及“古”底图入口。旧 localStorage 或分享链接里的 `basemap=古` 会被归一化为“素”，不会绕过组件从图谱路由保留受限能力；来源弹层继续保留 CHGIS 固定署名和谭图来源记录，并明确 safe 版没有分发对应几何或瓦片。

Vite 产物新增 `distribution-profile.json`，Python 打包器在复制文件前强制核对。实测用 full 前端执行 safe 打包会以 `expected=safe actual=full` 失败，因此不会把陈旧的完整前端混入安全包；反向错配由同一校验与单测覆盖。根 `edgeone.json` 与 `npm run build` 保持 full 默认，当前生产也未变更。

### 关键决策与被否决的备选

- safe profile 只移除尚未确认公网再分发许可的地图几何和镜像，不净化实体里的来源文字；后者是史料追溯信息，完全隐藏 CHGIS 会造成来源链与实际数据不一致。
- 不把 safe 设为根配置默认值：这会在 Rick 尚未决定线上策略时偷偷改变完整研究构建。安全发布必须明确选择预构建的 `edgeone-dist-safe/`。
- 不仅在 MapPanel 隐藏按钮；合法底图集合下沉到 Pinia store 单源，避免图谱路由、旧 URL 或 localStorage 留下“古”状态。
- 不修改 CI、DNS、EdgeOne 项目或线上内容；本轮只准备和验证本地产物。

### 当前状态：现在能跑什么、怎么跑

```bash
npm run build                         # full → edgeone-dist/
npm run build:safe                    # safe → edgeone-dist-safe/
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
```

本段实跑结果：数据 **7,396 / 10,266 / errors=0 / warnings=20,277**；full **34 GeoJSON / 18 CHGIS / 5,023 atlas / 5,114 files / 134.08 MB**；safe **16 GeoJSON / 0 CHGIS / 0 atlas / 73 files / 5.20 MB**。safe 真实 runtime 在 1050 年返回 `chgis_admin_records=0`、`polity_territories=1`。pytest **92/92 / 10.59s**；默认 full E2E **85 passed + safe 1 skipped / 4.9m**；safe 专项 **1/1 / 6.9s**；full/safe 前端错配负向实验按预期失败；`git diff --check` 通过。

### 未尽事项与已知问题

- safe 成品尚未发布；线上仍是包含 CHGIS 几何与自托管谭图瓦片的完整构建。应由 Rick 在“已有书面许可保留 full / 无许可改发 safe / 临时下线”中决定，本轮不越权。
- 根 `edgeone.json` 仍对应 full 源码构建。safe 已验证的是预构建成品直接上传路径；EdgeOne 是否支持一套源码配置选择多 profile 尚未核验。
- 内容工程范围尚未决定：保守维护只修有明确史料证据的单点错误；系统迁移会重构约 4,054 条 Place 内嵌关系，并必须先决定“南京/长安等同一地点的历代名称是合为一个实体，还是按时代拆分”。两者工程量和数据模型影响不同，不能靠默认猜测开工。

### 文件级变更清单

- 构建与测试：`.gitignore`、`package.json`、`scripts/build_edgeone.py`、`backend/tests/test_edgeone_build.py`、`frontend/vite.config.js`、`frontend/e2e/safe-distribution.spec.js`。
- 前端能力边界：`frontend/src/config/distribution.js`、`frontend/src/stores/useUIStore.js`、`frontend/src/components/map/MapPanel.vue`、`frontend/src/components/shared/AttributionDialog.vue`。
- 文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 高密度界面交互收敛与星图全高修复

### 做了什么（结果）

把高频误触和常驻控件密度一起收敛：时间柱、在世人物与图谱之间的悬停仍会互相高亮，但右侧档案只在点击、Enter 或 Space 后切换；时间尺度、人物类型和地图图层改为默认折叠，重点人物、当前“帝王”尺度、跳年与地图展开入口仍留在外层。地图默认底图改为“古”，放大/收起、搜索、帮助、来源和复位等入口统一使用 Lucide SVG 图标；地图图层工具在左上、MapLibre 缩放在左下，不再互相遮挡。

配色删去“青 / 赭”，只保留“澄 / 夜”：浏览器无需权限即可读取 `prefers-color-scheme` 并实时跟随，无法读取时按本地 06:00 / 18:00 近似日夜切换，不请求位置权限。谱系星图的星云/时空柱下半屏留白定位为 App 三行 Grid 自动排布错误；把主内容明确钉到第三行后，两种 3D 画布都延伸到视口底部，没有改 Three 引擎或用固定高度补丁。

### 关键决策与被否决的备选

- 选择“显式选择才换档案”，保留 hover 视觉互高亮；否决 300–450ms 延迟 hover，因为它仍会在高密度区域误换档案，并引入计时状态和闪烁边界。
- 时间尺度与跳年合为同一工具组，搜索输入框的放大镜留在输入框内部；否决把跳年图标继续单独钉在朝代 gutter 上。
- 采用项目依赖 `@lucide/vue` 的一致线性 SVG，不再用 `?`、`!`、`⌕`、`↺`、`放/收`等字符冒充图标。构建期需转换 1,961 个模块，但产物已 tree-shake，构建仍为约 2 秒；地图与星图两个 >500 kB 懒加载 chunk warning 与既有重依赖形态一致。
- 星图只修外层 Grid 行归属；否决在星云/时空柱组件内写 `calc(100vh - …)`，后者会重复编码 header/tab 高度并破坏未来布局调整。

### 当前状态：现在能跑什么、怎么跑

```bash
cd frontend && npm run build
cd frontend && npm run test:e2e
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
```

本段验证：full 与 safe 前端生产构建均通过；完整 E2E **90 passed / 1 skipped（safe 专项在 full profile 下按预期跳过）/ 5.5m**，safe profile 专项 **1/1**；后端 pytest **92/92 / 12.60s**；数据 **7,396 / 10,266 / errors=0 / warnings=20,277 / 5.22s**；新增的主题、折叠、古地图、控件零重叠、图标居中、hover 稳定档案和星图全高定向回归 **16/16**，补充的“无 matchMedia”降级与移动端定向回归 **8/8**。桌面夜色 1280×720 与宽屏 1988×1280 已做浏览器几何和截图复核，`git diff --check` 通过。

### 未尽事项与已知问题

- “日出 / 日落”降级不请求位置权限，因此采用当地时钟 06:00 / 18:00 近似，不是经纬度天文时刻；正常浏览器均直接走无需授权的系统主题状态。
- 已保存的合法底图偏好仍优先于新默认“古”；新用户或无偏好状态默认古，尊重旧用户主动选择，不强行迁移 localStorage。
- npm 仍报告 2 个依赖审计项（1 moderate / 1 high）；本轮未执行可能带来破坏性升级的 `npm audit fix --force`。
- 公开再分发许可与内容工程范围仍沿用前两段记录，本轮未发布、未改部署配置，也未触碰历史数据。

### 文件级变更清单

- 交互与主题：`frontend/src/App.vue`、`frontend/src/stores/useUIStore.js`、`frontend/src/stores/useSelectionStore.js`、`frontend/src/styles/palettes.js`、`frontend/src/styles/main.css`、`frontend/src/components/shared/SearchBar.vue`、`frontend/src/components/shared/FilterBar.vue`、`frontend/src/components/timeline/TimeColumn.vue`、`frontend/src/components/timeline/MomentPanel.vue`。
- 地图与星图：`frontend/src/components/map/MapPanel.vue`、`frontend/src/starmap/engine/inkPalette.js`、`frontend/src/starmap/engine/columnMount.js`。
- 依赖与回归：`frontend/package.json`、`frontend/package-lock.json`、`frontend/e2e/ui-controls.spec.js`、`frontend/e2e/graph.spec.js`、`frontend/e2e/b-batch.spec.js`、`frontend/e2e/c-batch.spec.js`、`frontend/e2e/accessibility-keyboard.spec.js`、`frontend/e2e/mobile-layout.spec.js`、`frontend/e2e/m7-person-lanes.spec.js`、`frontend/e2e/m8-event-overflow.spec.js`、`frontend/e2e/m11-event-anchor.spec.js`、`frontend/e2e/m12-sub-year.spec.js`、`frontend/e2e/m13-time-navigation.spec.js`、`frontend/e2e/m14-pre-han-territory.spec.js`、`frontend/e2e/march-routes.spec.js`。
- 文档：`README.md`、`WORKLOG.md`。

## 2026-07-23 · 当前态文档与 Lucide 构建性能收口

### 做了什么（结果）

把上一段已经验收的界面结果滚入常新文档：README 的前端基线更新为 full profile **91 passed + 1 skipped**、safe profile 专项 **1/1**；handoff 记录当前 `HEAD=f0b88fd`、最新构建/测试数字与仍需用户决定的发布、内容边界，不再让 85 项的旧 E2E 基线冒充当前状态。

同时定位并消除了引入 Lucide 后的构建期无效解析：6 个前端组件不再从 `@lucide/vue` 总入口取图标，改为明确导入实际使用的单图标 ESM 文件。Vite 转换模块数从 **1,961 降至 225**，full production build 从 **1.73s 降至 1.47s**；改动只影响构建期模块发现，不改变组件、图标名称或运行时交互，产物大小与既有大 chunk 形态基本不变。

### 关键决策与被否决的备选

- 不移除 Lucide 或重画 SVG；问题是 barrel import 让 Vite 扫描整个图标包，按图标深导入即可保留同一视觉组件并缩小构建工作集。
- 不为消除两个既有 `>500 kB` warning 人为拆出更多网络请求；本次优化的目标是已被实测放大的构建解析成本，运行时地图与 Three 懒加载边界不变。
- 没有执行会向 npm 审计服务提交 lockfile-derived 依赖图的联网 `npm audit`：当前未获对这类外部提交的明确授权。安装过程曾报告的 **1 moderate / 1 high** 仍缺具体 advisory 与受影响路径，标记 `needs-verification`；在联网审计完成前，不写“已安全”、也不直接执行 `npm audit fix --force`。
- 响应式布局已经落地，不再把整个 E 批写成延期；剩余的新手引导是尚未确认的用户可见方向，既未完成，也不是永久否决项。

### 当前状态：现在能跑什么、怎么跑

```bash
cd frontend && npm run build
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
```

本段 full build 实跑为 **225 modules / 1.47s**。深导入后的完整功能回归为 full E2E **91 passed + 1 skipped / 5.8m**；同轮其余基线为 safe 专项 **1/1 / 7.8s**、pytest **92 passed / 12.60s**、数据 **7,396 / 10,266 / errors=0 / warnings=20,277 / 5.22s**。深导入没有修改产品逻辑或测试合同。

### 未尽事项与已知问题

- 本轮基于 `f0b88fd` 完成 Lucide 深导入与当前态文档收口；精确提交见 `git log -1`。用户维护的 `AGENTS.md` 继续保持未跟踪，不纳入。
- npm 的两项审计提示尚未完成具体 advisory 定位，保持 `needs-verification`；后续只有在允许把依赖图提交给审计服务后，才能判断是开发期还是生产期路径、能否非破坏性修复。
- safe/full 线上选择、地图数据再分发许可、Place 系统迁移与新手引导方向仍需用户或外部证据；本段未发布、未改部署配置、未改历史数据。

### 文件级变更清单

- Lucide 深导入：`frontend/src/App.vue`、`frontend/src/components/map/MapPanel.vue`、`frontend/src/components/shared/FilterBar.vue`、`frontend/src/components/shared/SearchBar.vue`、`frontend/src/components/timeline/MomentPanel.vue`、`frontend/src/components/timeline/TimeColumn.vue`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 谱系星图首载边界收口

### 做了什么（结果）

继续沿产物静态依赖链检查默认「图谱」首载，发现上一段“运行时懒加载边界不变、产物大小基本不变”的判断不成立：`WebGraph` 虽然没有直接使用 Three 渲染，但它导入的 `inkPalette` 为生成 `Color` 对象静态导入了 Three，构建器因此把 3D 依赖提前并入默认 2D 图谱闭包。这个结论来自构建产物与浏览器资源请求证据，不再用源码里的动态 import 位置代替真实首载判断。

现将朝代色值、背景与透明度保留为不依赖 Three 的纯数据 `inkPalette`，把 `Color` 对象适配独立到只供星云/时空柱引擎使用的 `threePalette`。颜色值、节点语义与交互没有改变；默认 WebGraph 静态 JS 闭包由 **724.26 kB 降至 201.94 kB**，gzip 由 **211.83 kB 降至 79.08 kB**，纯数据 `inkPalette` 仅 **1.41 kB**。Three 现在直到首次进入星云或时空柱才加载。

### 关键决策与被否决的备选

- 不接受“组件使用动态 import，所以依赖一定延迟加载”的源码表面判断；验收以产物静态闭包和真实网络请求为准。
- 不复制两套朝代颜色常量。`inkPalette` 继续是色值单源，`threePalette` 只负责把同一色值转换为 Three `Color`，避免 2D 数据模块反向依赖 3D 运行时。
- MapLibre 与 Three 3D 路由仍各自保留 `>500 kB` lazy chunk；它们本来就是进入地图或 3D 视图后才需要的重依赖，本段没有为了消除 warning 数字切碎正常的按需加载边界。
- `npm audit --offline` 返回 0，但本地 advisory 缓存是否完整无法证明，因此不能据此得出依赖安全结论。安装过程曾提示的 **1 moderate / 1 high** 继续标 `needs-verification`，也未执行破坏性修复。

### 当前状态：现在能跑什么、怎么跑

```bash
(cd frontend && npm run test:e2e -- graph.spec.js)
npm run build
npm run build:safe
```

本段定向验证：谱系星图 **9/9 passed**；full 与 safe 根构建均通过，二者前端构建均为 **226 modules**，数据校验均为 **7,396 / 10,266 / errors=0 / warnings=20,277**。浏览器资源检查确认默认 WebGraph 未请求 Three/3D 资源，切换到星云后才确实发起对应请求。没有重跑全量 E2E，本段不把此前 91 项基线冒充新结果。

### 未尽事项与已知问题

- 本轮基于 `c7dbda9` 完成谱系星图首载边界收口，精确提交见 `git log -1`。用户维护的 `AGENTS.md` 保持未跟踪，不纳入。
- npm 两项提示的具体 advisory 与生产可达性仍待获准联网审计后定位，`npm audit --offline` 的 0 项结果不改变 `needs-verification` 状态。
- safe/full 线上选择、地图数据再分发许可、Place 系统迁移与新手引导方向仍需用户或外部证据；本段未发布、未改部署配置、未改历史数据。

### 文件级变更清单

- 星图依赖边界：`frontend/src/starmap/engine/inkPalette.js`、`frontend/src/starmap/engine/threePalette.js`、`frontend/src/starmap/engine/dataAdapter.js`、`frontend/src/starmap/engine/mount.js`、`frontend/src/starmap/engine/renderer.js`。
- 定向回归：`frontend/e2e/graph.spec.js`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 原生 fetch 客户端与依赖面收口

### 做了什么（结果）

沿前端运行依赖继续核对真实使用面：源码中唯一的 Axios import 位于 `frontend/src/api/client.js`，所有业务请求都只调用 `api.get`，没有写请求、拦截器、取消令牌、上传进度或其他 Axios 专属能力。因此用浏览器原生 `fetch` 实现同一窄接口，并从 manifest 与 lockfile 移除 Axios 及其仅由此链路带入的依赖。

适配器继续返回 `{ data, status, headers }`，保留调用方既有的 `api.get(path, { params })` 和解构 `data` 合同；查询参数仍保留 `0` 与空字符串、跳过 `null` / `undefined` 并正确编码中文与保留字符。非 2xx 响应抛出的错误继续带 `name`、`status` 与 `response.data`，`application/*+json` 也按 JSON 解析。新增独立浏览器合同测试，避免依赖替换只靠现有页面间接覆盖。

### 关键决策与被否决的备选

- 不新增另一套请求库。当前客户端是同源、只读 GET 薄层，原生 `fetch` 已覆盖真实需求；保留一个 Axios 兼容形状的窄适配器，比把 `{ data }` 解构与错误读取扩散重写到全站风险更低。
- 不借迁移改变缓存、端点、参数名或错误展示。实体缓存和所有导出函数继续在原位置工作，依赖收口与业务行为解耦。
- 不把删除 Axios 等同于“安全告警清零”。`npm audit --offline` 即使返回 0，也无法证明本地 advisory 缓存完整；既有两项提示的具体 advisory 与生产可达性仍保持 `needs-verification`。

### 当前状态：现在能跑什么、怎么跑

```bash
(cd frontend && npm run test:e2e -- api-client.spec.js)
(cd frontend && npm run test:e2e)
(cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js)
npm run build
npm run build:safe
```

本段验证：原生客户端合同 **1/1 passed**；full E2E **92 passed + 1 skipped / 4.5m**；safe 专项 **1/1 / 6.8s**；full 与 safe 根构建均通过，数据均为 **7,396 / 10,266 / errors=0 / warnings=20,277**。两套前端构建均为 **174 modules**；full index **121.40 kB / gzip 48.61 kB**，safe **121.59 / 48.66 kB**，前一轮为 **167.17 / 65.53 kB**；默认 WebGraph 静态 JS 闭包约由 **201.94 / 79.98 kB** 降至 **156.17 / 63.06 kB**。lockfile package 数从 **160 降至 133**，共移除 27 个节点。

### 未尽事项与已知问题

- 本轮基于 `0add868` 完成原生 fetch 客户端与依赖面收口，精确提交见 `git log -1`。用户维护的 `AGENTS.md` 保持未跟踪，不纳入。
- 离线 audit 的 0 项结果不构成安全证明；未获准提交依赖图做联网审计前，既有两项提示继续标 `needs-verification`。
- safe/full 线上选择、地图数据再分发许可、Place 系统迁移与新手引导方向仍需用户或外部证据；本段未发布、未改部署配置、未改历史数据。

### 文件级变更清单

- API 与依赖：`frontend/src/api/client.js`、`frontend/package.json`、`frontend/package-lock.json`。
- 合同回归：`frontend/e2e/api-client.spec.js`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 移动端地图首次展开加载边界

### 做了什么（结果）

继续核对移动端「时间柱主屏 + 底部抽屉」的真实首载，确认抽屉虽然默认收起，内部 MapPanel 仍会立即触发 MapLibre 下载和地图初始化。现保留收起态可见的此刻读数摘要，只把地图挂载延后到用户首次点击、键盘展开或向上拖拽完成；首次打开后不再卸载，收起再展开复用同一地图实例。桌面端仍立即显示地图。

浏览器资源回归证明：390px 收起首载的 MapPanel 与 `maplibre-gl` 请求均为 0；首次展开后两类资源才出现；再次展开时原始资源条目没有增加，`.maplibregl-map` 始终只有一个。生产产物没有被切碎或隐藏 warning，移动首屏实际延后的地图 JS + CSS 为约 **891.51 kB raw / 235.46 kB gzip**。

### 关键决策与被否决的备选

- 没有延迟整个 MomentPanel。104px 收起区真实露出朝代、年号和在世人数摘要，把整个面板卸载会造成已经定稿的移动信息层级退化。
- 没有在每次收起时销毁地图。MapLibre 初始化成本高，首次主动打开后保留实例，比反复创建更符合抽屉交互与性能目标。
- 没有调高 Vite chunk warning 或为追求数字强拆 MapLibre；这轮修复的是隐藏内容被过早请求的生命周期边界。

### 当前状态：现在能跑什么、怎么跑

```bash
cd frontend && npm run test:e2e -- mobile-layout.spec.js
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
npm run build
npm run build:safe
```

本段定向移动回归 **4/4 passed / 9.6s**；完整回归 **93 passed + 1 skipped / 4.3m**；safe 专项 **1/1 / 7.7s**。full 与 safe 根构建均通过，前端均为 **174 modules**；数据硬闸门两次均为 **7,396 / 10,266 / errors=0 / warnings=20,277**。full 产物 5,114 files / 134.05 MB，safe 产物 73 files / 5.17 MB。

### 未尽事项与已知问题

- MapLibre 仍是 821 kB 级按需 chunk；它现在不再进入移动隐藏首屏，但首次展开仍需下载。继续拆包只有在真实首开指标证明必要时再做。
- safe/full 线上选择、地图数据再分发许可、Place 系统迁移与新手引导方向仍需用户或外部证据；本段未发布、未改部署配置、未改历史数据。
- 用户维护的 `AGENTS.md` 继续保持未跟踪，不纳入项目提交。

### 文件级变更清单

- 移动加载边界：`frontend/src/components/timeline/MobileTimelineLayout.vue`、`frontend/src/components/timeline/MomentPanel.vue`。
- 浏览器回归：`frontend/e2e/mobile-layout.spec.js`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 行军路线第三轮高置信补全

### 做了什么（结果）

继续按「A 类只落明确起讫、B 类只落独立阶段、C 类明确留空」推进 111 个军事候选。先对齐全部实体、`march` 端点与地点坐标，确认原有 10 个实体 / 13 段都能解析到有坐标 Place；其余 101 项中，文档点名但尚未落地的石敬瑭、崖山等仍缺扬武谷、潮阳等关键地点，不能靠终点反推路线。

本批纠正了一处路线归属：洛阳—长安不再挂在 875—884 年的「黄巢起义」父事件，而迁到已有 `part_of` 关系的 880 年「黄巢攻入长安」阶段，父事件 API 有显式无 `march` 护栏。另据《宋史·曹彬传》补入宋灭南唐的江陵—采石矶—金陵两段。当前为 **11 个实体 / 15 段**，15 段全部带出处且端点都有坐标。

### 关键决策与被否决的备选

- 不在父事件和阶段事件复制同一条黄巢路线；复制会让一段进军冒充九年全程，并形成两份会漂移的事实。
- 不把宋灭南唐简化为江陵直连金陵；原文与已有地点实体都支持采石矶这个真实阶段，拆两段更准确。
- 不用晋阳代替扬武谷、不用漳州直连崖山，也不借宋代河南的「永安」画太平天国路线。事件有 `location` 只证明能落印章，不证明它就是行军起点或终点。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
cd frontend && npm run test:e2e -- march-routes.spec.js
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
npm run build
npm run build:safe
```

本段真实地图路线专项 **3/3 passed / 12.1s**；完整后端 **92/92 / 9.84s**；完整 E2E **95 passed + 1 skipped / 4.5m**；safe 专项 **1/1 / 7.0s**。full 与 safe 根构建均通过，前端均为 **174 modules**，数据硬闸门均为 **7,396 / 10,266 / errors=0 / warnings=20,277**。

### 未尽事项与已知问题

- 余下 100 个军事候选中，82 个有事件落点、18 个连落点也没有；`location` 不能机械当路线终点。当前纯本地证据没有更多可直接落地的文档明确 A 类。
- 扬武谷、潮阳、宜阳、平州、横江、京口等地点需要外部史料与坐标核验；复杂战争还需要先拆阶段事件。本段保持 `needs-verification`，没有为提高覆盖率编造路线。
- safe/full 线上选择与 Place 历时模型仍待用户或外部证据；本段未发布、未改部署配置。用户维护的 `AGENTS.md` 继续不纳入提交。

### 文件级变更清单

- 路线数据：`data/entities/events/huangchao_qiyi.yaml`、`data/entities/events/huangchao_zhan_changan.yaml`、`data/entities/battles/song_nantang.yaml`。
- 回归：`backend/tests/test_api_entities.py`、`frontend/e2e/march-routes.spec.js`。
- 当前态文档：`README.md`、`docs/march-routes.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 崖山最后一程与引用校验闭环

### 做了什么（结果）

继续按「只落史载明确起讫」推进进军箭头。本地 CBDB `ADDR_CODES` 的 `c_addr_id=100447` 给出宋元潮阳县（960—1279）及坐标，新增同时代 `Place`；《宋史纪事本末·卷一百八·二王之立》明确张弘范由潮阳港乘舟入海、经甲子门获知宋帝所在后进至崖山，因此崖山海战只补 **潮陽 → 崖山** 这一段最后海路，不把此前漳州、鲍浦寨等沿海战事压成一根直线。当前为 **12 个实体 / 16 段**，全部路线端点有坐标，全部分段带出处。

新增潮陽后，数据校验器把它报成孤儿。取证发现这不是单点例外：孤儿集合只计普通关系端点和正文提及，遗漏已经通过存在性/类型校验的 `location`、`capital` 等顶层内嵌外键，且对象数组 `march` 端点此前没有硬校验。现把所有有效内嵌外键和有效 march 端点计作“被使用”，并把 march 坏结构、悬空端点、非 Place 端点分别纳入硬错误。孤儿实体从误报的 **1159** 收敛到 **185**，总 warning 从 **20,278** 降到 **19,304**；差值 974 全部来自此前漏计的真实引用，没有删除 warning、放宽断言或降低错误等级。

### 关键决策与被否决的备选

- `modern_name` 沿用仓库 CBDB 导入器的保守映射，不擅自写到某个现代街道或县治点；现有证据足以确认历史潮阳县点，但不足以在本批引入更细的现代行政语义。
- 不补漳州 → 潮阳。两段史料之间还夹着鲍浦寨、五坡岭等行动，直接连线会把多阶段战事说成直达路线。
- 扬武谷虽有《资治通鉴》所载“自扬武谷而南，至晋阳”，但现只能定位为原平一带十余公里级线性峡谷，没有可复核单点坐标；不任选谷口、村庄或中点制造虚假精度。
- 没有把新增地点加入一条人为制造的普通关系来压掉孤儿 warning；修的是校验器对既有真实引用的漏计，并用 8 条正反合同测试约束。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
cd frontend && npm run test:e2e -- march-routes.spec.js
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
npm run build
npm run build:safe
```

路线专项 **4/4 passed / 12.7s**；新增校验器合同 **8/8**；完整后端 **100/100 / 9.99s**；完整 E2E 共 97 条，**96 passed + 1 skipped / 5.0m**；safe 专项 **1/1 / 4.4s**。full 与 safe 根构建均通过，前端均为 **174 modules**；数据硬闸门为 **7,397 / 10,266 / errors=0 / warnings=19,304**。full 产物 **5,114 files / 134.05 MB**，safe 产物 **73 files / 5.17 MB**。校验器只随现有实体扫描收集引用并遍历 16 个 march 分段，没有引入新的构建期全量嵌套流程；本轮 full/safe 数据闸门分别为 6.95s / 7.01s。

### 未尽事项与已知问题

- 余下 99 个军事候选中，81 个有事件落点、18 个没有；事件落点仍不能机械视为进军端点。扬武谷保持 `needs-verification`，其他长期战争也须先拆阶段再落线。
- 当前 185 个孤儿实体是在普通关系、正文提及、顶层内嵌外键与 march 端点全部计入后的结果；它们是后续内容审计候选，不应靠自动造关系清零。
- safe/full 线上选择、地图数据再分发许可与 Place 历时模型仍待外部证据或用户决策；本段未发布、未改部署配置。用户维护的 `AGENTS.md` 继续保持未跟踪，不纳入提交。

### 文件级变更清单

- 路线与地点：`data/entities/battles/yashan.yaml`、`data/entities/places/pl_cbdb_100447.yaml`。
- 校验与回归：`scripts/validate_data.py`、`backend/tests/test_validate_data.py`、`backend/tests/test_api_entities.py`、`frontend/e2e/march-routes.spec.js`。
- 当前态文档：`README.md`、`docs/march-routes.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 孤儿判定的关系参与者语义复核

### 做了什么（结果）

上一段把内嵌外键的有效目标计入“非孤儿”后，继续按原始校验任务书复核剩余 185 项，发现普通关系的 `from` / `to` 两端都会被视为关系参与者，但内嵌外键与 march 只计目标、不计持有字段的 owner。结果是定川寨、夹河、潞州、黄海四场已经连着地点、参战方和主帅的战役，以及另外 9 个 Event、5 个 Person，仍被误称为孤儿。

现用单一 `reference_participants()` 规则统一口径：只有至少一个有效目标时，owner 与目标才共同计入；若全部目标悬空、类型错误或结构错误，owner 仍保持孤儿且错误照常上报。修正后孤儿由中间值 **185** 收敛为 **167**，总 warning **19,304 → 19,286**；这 18 项全部已有真实结构化出边，没有新增或修改任何历史事实。

### 关键决策与被否决的备选

- 没有把所有“正文提到别人”的来源实体也自动视为非孤儿；原任务书对正文双链明确采用“被其他实体提及”的入链口径，本轮只修与普通结构化关系端点不一致的部分。
- 没有把存在坏端点的 owner 先算作已连接；否则悬空引用会一边报错、一边替来源实体消掉孤儿 warning，语义自相矛盾。
- 没有为 18 项补造普通关系；校验器应理解已有结构化关系，而不是要求数据重复表达同一事实。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
```

校验器合同 **9/9 / 0.02s**；完整后端 **101/101 / 9.81s**；数据 **7,397 / 10,266 / errors=0 / warnings=19,286 / 3.79s**，其中孤儿实体 167。`git diff --check` 通过。

### 未尽事项与已知问题

- 剩余 167 项仍需区分“合法独立时间轴内容”和“确有缺链”；本轮不以降低数字为目标，不自动补关系。
- safe/full 线上选择、地图数据再分发许可与 Place 历时模型仍待外部证据或用户决策；本段未发布、未改部署配置。用户维护的 `AGENTS.md` 继续保持未跟踪，不纳入提交。

### 文件级变更清单

- 校验与回归：`scripts/validate_data.py`、`backend/tests/test_validate_data.py`。
- 当前态文档：`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 高置信内容缺链最小批次

### 做了什么（结果）

对修正口径后的 167 个孤儿实体做本地证据审计，没有把它们当作待清零 KPI。先落 20 个无需外推的连接点：澳门回归、首颗原子弹、东方红一号、三峡工程、神舟五号、脱贫攻坚、一带一路 7 个正文已明确“中国/中国政府”的事件补 `k_prc`；刘义隆、拓跋焘按各自 `ext.regime` 与正史来源补 `k_liusong` / `k_beiwei`；另补 8 条人物—事件关系与宋庆龄—孙中山、戴季陶—孙中山、唐绍仪—袁世凯 3 条人物关系。唐绍仪关系限定为 1885 年任袁世凯西文翻译、随办洋务委员至 1912 年政见不合辞职，不把边界留成“无限早”，也不暗示终身追随。

11 条新关系全部有实质 note。第一版沿用人物实体里过宽的“中华人民共和国史 / 当代中国史”，事实成立但新增 18 条 source-format warning；本轮没有用净 warning 下降掩盖它，而是逐项换成已核页面的“机构·标题”出处：国家航天局/中国科学院支持孙家栋、于敏，国家国防科技工业局/国防部支持邓稼先，中国军网与地方政府官方页面支持陈赓、刘伯承、徐向前，人民网支持康生，全国政协支持宋庆龄。source-format suspect 最终保持原基线 **1613**，没有新增出处债务。

当前关系 **10,266 → 10,277**，孤儿 **167 → 147**；总 warning **19,286 → 19,266**，下降只来自 20 个真实连接参与者。实体总数保持 7,397。

### 关键决策与被否决的备选

- 不给 COVID-19、SARS 只挂 `k_prc`；它们是跨国疫情，单一政权会表达不完整。
- 不把“某领导人任内发生”写成 `participated_in`，也不把同时代人物、地点或事件互连来追求数字。
- 不给 28 个本地只有独立生平的高优先人物强找事件；他们可由时间轴、人物筛选和搜索到达，“没有关系”不等于“产品不可达”。
- 已确认 `p_wanyan_sheng` 与 `p_wanyanwuqimai` 是同一金太宗，但正确修复需要合并独有字段、迁移引用并删除重复文件；本批不擅自删除用户既有数据，也不造一条“同一人”关系绕过去。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py --strict-seed
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
npm run build
npm run build:safe
```

新增 API 合同 **20/20 / 0.68s**；完整后端 **121/121 / 10.12s**；strict-seed 与普通数据闸门均为 **7,397 / 10,277 / errors=0 / warnings=19,266**，孤儿 147。full / safe 根构建均通过且均为 **174 modules**；full **5,114 files / 134.05 MB**，safe **73 files / 5.17 MB**，只保留既有大 chunk 提示。数据改动没有新增前端运行时代码，构建产物体积保持既有量级。

### 未尽事项与已知问题

- 147 个剩余孤儿中，多数是可独立浏览的现代人物、事件与地点；少数需要外部史料或产品语义，不能自动补链。
- 金太宗明确重复实体需要删除确认；另有 3 组 seed/CBDB 疑似重复（拓跋嗣/31006、耶律璟/43095、耶律宗真/43157），须先迁 CBDB 关系再审。
- safe/full 线上选择、地图数据再分发许可与 Place 历时模型仍待外部证据或用户决策；本段未发布、未改部署配置。用户维护的 `AGENTS.md` 继续保持未跟踪，不纳入提交。

### 文件级变更清单

- 事件政权：`data/entities/events/aomen_huigui.yaml`、`diyike_yuanzidan.yaml`、`dongfanghong1.yaml`、`sanxia_gongcheng.yaml`、`shenzhou5.yaml`、`tuopin_gongjian.yaml`、`yidai_yilu.yaml`。
- 人物政权：`data/entities/persons/liu_yilong.yaml`、`tuoba_tao.yaml`。
- 关系与回归：`data/relations/modern.yaml`、`backend/tests/test_high_confidence_links.py`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 高密度界面 8 项验收收口

### 做了什么（结果）

复核用户点名的悬停、地图、主题、时间尺度、图标、搜索、人物筛选与星图满高 8 项，确认运行时实现已由 `f0b88fd` 落地，本轮没有再造第二套交互。补强两处最容易退化的黑盒合同：时间柱人物 hover/focus 与档案关系 hover 都不得切换右侧正式档案，只有 click/Enter/Space 才选中；地图展开按钮必须含真实 SVG 且不得退回“放”字。TimeColumn 的旧注释同步改为当前事实：滚动期与落定后 400ms 抑制的是误触视觉高亮，不再是防止档案被劫持。

按 Product Design 验收流程保存同视口证据。用户参考图归一到 1470×923 后与当前澄主题、1637 年、星云、选中“联蒙灭金”的实现并排检查：旧图 stage 在上半屏结束，当前 app body 高 865px、星图 body 813px、stage 772.5px，stage/canvas 底部均到达 923px 视口底部。390×844 实拍保持时间柱主屏与底部详情抽屉；系统夜主题与手动澄主题都无浏览器 error/warning。

### 关键决策与被否决的备选

- 不删除所有 hover。双向视觉高亮仍能帮助在世 chips、时间柱和关系项互相定位；删除正式选中副作用并保留 400ms 滚动保护，兼顾可读性与防误触。
- 不把图层、尺度和人物类型永久展开。当前尺度、重点人物和地图展开留在外层，低频选项点击展开，减少遮挡且不牺牲可发现性。
- 不为同视口比较追求逐像素复刻问题截图。截图是留白缺陷证据，不是回退目标；现有纸墨、印章、古地图与实体聚焦行为保持不变。
- 星云选中后非邻域节点淡至 8% 是既有 focus 设计，不与高度修复混改；如需调整，应另出可见草案比较。

### 当前状态：现在能跑什么、怎么跑

```bash
cd frontend && npm run test:e2e -- e2e/ui-controls.spec.js e2e/b-batch.spec.js e2e/accessibility-keyboard.spec.js e2e/mobile-layout.spec.js e2e/graph.spec.js
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
npm run build
npm run build:safe
```

受影响面定向 **27/27 passed / 55.0s**；完整 E2E **96 passed + 1 skipped / 5.2m**；safe 专项 **1/1 / 5.1s**。full / safe 根构建均通过，数据硬闸门两次均为 **7,397 / 10,277 / errors=0 / warnings=19,266**，前端均为 **174 modules**；full **5,114 files / 134.05 MB**，safe **73 files / 5.17 MB**。只有既有 MapLibre / seed 大 chunk 提示，没有调高阈值或新增运行依赖。

### 未尽事项与已知问题

- 本轮 8 项已经实现并通过可见状态、键盘路径、完整回归与构建，不留半成品。
- 线上仍是完整 EdgeOne 构建；公开地图数据再分发许可未解决，safe 成品已验证但未发布。本轮没有改部署配置、没有发布。
- 新手引导仍属未定的用户可见方向；Place 关系迁移与确认重复的金太宗实体仍需产品口径或删除确认，未擅自处理。
- 用户维护的 `AGENTS.md` 继续保持未跟踪，不纳入项目提交。

### 文件级变更清单

- 交互事实与回归：`frontend/src/components/timeline/TimeColumn.vue`、`frontend/e2e/b-batch.spec.js`、`frontend/e2e/ui-controls.spec.js`。
- 视觉验收：`docs/design-qa.md`、`docs/design-qa/source-nebula-height-issue.png`、`implementation-nebula-full-height.jpg`、`comparison-nebula-height.png`、`implementation-timeline-controls.jpg`、`implementation-mobile-drawer.jpg`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 3D 星图装配中切走的资源竞态

### 做了什么（结果）

关闭星云与时空柱在动态加载期间离开页面的资源泄漏窗口。此前两个 View 都先等待 Three 模块和 `/api/graph/spacetime`，卸载时控制器尚为空；请求晚到后仍会在已卸载节点上创建 WebGL、Worker、动画帧、ResizeObserver、事件监听，时空柱还会注册一个无法由组件自动停止的异步 watcher。现在 dynamic import 返回、控制器装配返回与 ready 回调都检查组件是否仍存活；晚到控制器立即调用引擎已有的完整 `dispose()`，不写 Vue 或就绪状态。

时空柱保存并显式停止异步创建的选中 watcher，只有存活控制器才能启动调试采样定时器；星云同时回收联想与 blur 定时器，并阻止六度飞行、联想请求在卸载后改写状态。测试用受控路由门闩截住 spacetime 响应，等两个 3D 视图进入 mount await 后立即切回图谱，再放行响应；两者都必须发出 DEV late-dispose 完成事件、不得晚写 ready，且页面中不留 3D canvas。

### 关键决策与被否决的备选

- 不改 Three 引擎的数据结构或视觉参数；引擎的 `dispose()` 已能完整释放资源，缺口只在 View 的异步生命周期所有权。
- 不用固定 sleep 猜竞态是否结束。测试以“请求已被门控、响应已送达、late-dispose 事件已发出”作为确定性同步点，并重复三轮验证。
- 不为这项引入 AbortController 跨层改造。当前补丁已保证卸载后不保留资源；若以后要连后端计算也提前取消，应作为独立的请求取消合同处理。

### 当前状态：现在能跑什么、怎么跑

```bash
cd frontend && npm run test:e2e -- e2e/graph.spec.js
cd frontend && npx playwright test e2e/graph.spec.js --grep "B5c" --repeat-each=3
cd frontend && npm run build
```

谱系星图规格 **10/10 / 21.2s**；竞态用例重复 **3/3 / 10.6s**；Vite 生产构建 **174 modules / 1.34s**。默认 index 仍为 **121.40 kB / gzip 48.62 kB**，NebulaView **4.92 / 2.26 kB**，ColumnView **3.43 / 1.78 kB**；只有既有 MapLibre / seed 大 chunk 提示，无新依赖。

### 未尽事项与已知问题

- 本项不改变线上部署或许可状态，未发布、未改部署配置。
- 仍待用户决策的金太宗重复实体删除、Place 历时模型与 full/safe 发布选择未越权处理；用户维护的 `AGENTS.md` 继续保持未跟踪。

### 文件级变更清单

- 生命周期：`frontend/src/components/starmap/NebulaView.vue`、`frontend/src/components/starmap/ColumnView.vue`。
- 回归合同：`frontend/e2e/graph.spec.js`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 第二批本地证据引用与四段行军

### 做了什么（结果）

继续处理不需要外部史料、删除或产品口径的结构化缺口。北京奥运会、北京冬奥会、上海世博会的正文均明确为中国主办，补 `polities_involved: [k_prc]`；60 位原本孤立的帝王按各自实体已经同时具备的 `emperor`、`ext.regime`、在位起讫与正史 sources 补 `dynasty_ref`。四个待合并重复实体完颜晟、拓跋嗣、耶律璟、耶律宗真明确排除，不用新增引用掩盖重复问题。

巨鹿之战的 `location` 从“张角籍贯”实体改到专门写明 BC207 巨鹿之战的 `pl_julu_qi`。另为唐朝建立前的晋阳—长安、唐收复两京、高梁河灭北汉后转攻幽州、夹河末期郓州—汴梁各落一段有边界的 march；总计由 12 个实体 / 16 段增至 16 个实体 / 20 段，其中 15 个属于原 111 条军事候选，唐朝建立本身是 `founding`。

首轮候选曾把 `pl_yizhou` 当成幽州保卫战正文的河北易州；实查该实体是“益州 / 成都”。此候选已撤回，迁移预检与 API 反例合同都要求 `b_youzhou917` 保持无 march，直到存在正确的河北易州地点。迁移首跑精确改 68 份实体 YAML，第二次运行 `changed_files=0`。

### 关键决策与被否决的备选

- 不给 SARS、COVID-19 只挂中国政权；它们是跨国疫情。也不把邓小平自己的逝世建模成 `participated_in`。
- 不给四个待合并重复帝王补 `dynasty_ref`；正确动作仍是迁引用、合字段、删重复，需要删除确认。
- 不因同音使用错误地点；易州/益州反例成为永久回归护栏。
- 不把长战争压成一根箭头。四段 march 都只表达条目现有正文明确写出的单一阶段，note 内嵌原有正史出处。
- 不用 `yaml.dump`。幂等迁移逐键插入/替换，写前统一检查实体唯一性、旧值、目标类型、坐标、source 与候选数量，冲突时整批拒绝。

### 当前状态：现在能跑什么、怎么跑

```bash
python3 -B scripts/migrations/2026-07-23-high-confidence-links-round2.py
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py --strict-seed
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
cd frontend && npm run test:e2e -- e2e/march-routes.spec.js
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
npm run build
npm run build:safe
```

新增 API 合同 **69/69 / 0.47s**；完整后端 **190/190 / 10.03s**。strict-seed 与普通数据闸门均为 **7,397 / 10,277 / errors=0 / warnings=19,202**，孤儿 **147→83**，source-format suspect 保持 **1,613**，没有新增普通关系。真实地图专项 **8/8 / 26.6s**；完整 E2E **101 passed + 1 skipped / 5.6m**；safe 专项 **1/1 / 7.3s**。

full / safe 根构建均为 **174 modules**；full **5,114 files / 134.06 MB / 1.36s**，safe **73 files / 5.18 MB / 1.35s**。运行时代码未变，前端 chunk 只因 full/safe 常量产生既有 hash 差异，体积保持原量级；仍只有既有 MapLibre / seed 大 chunk 提示。

### 未尽事项与已知问题

- 剩余 83 个孤儿中，3 个事件是跨国疫情或人物逝世，其他多为可独立浏览的人物与地点；不再把“孤立”机械等同于“错误”。
- 已确认或疑似的重复人物仍需迁引用并删除一份；Place 历时模型、full/safe 发布与地图再分发许可仍需用户或外部证据。
- 余下军事候选为 96 条，其中 78 条有事件落点；落点不等于进军起点，仍按 A 类明确起讫、B 类拆阶段、C 类留空处理。
- 本轮未发布、未改部署配置；用户维护的 `AGENTS.md` 继续保持未跟踪。

### 文件级变更清单

- 事件 / 战役：`beijing_aoyun.yaml`、`beijing_dongao.yaml`、`shanghai_shibo.yaml`、`julu_zhizhan.yaml`、`jian_guo_tang.yaml`、`tang_shoufu_liangjing.yaml`、`gaolianghe.yaml`、`jiahe.yaml`。
- 帝王政权：`data/entities/persons/` 下 60 份 YAML；精确 ID→Polity 映射集中在 `scripts/migrations/2026-07-23-high-confidence-links-round2.py` 的 `DYNASTY_GROUPS`。
- 迁移与合同：`scripts/migrations/2026-07-23-high-confidence-links-round2.py`、`backend/tests/test_high_confidence_links_round2.py`、`frontend/e2e/march-routes.spec.js`。
- 当前态文档：`README.md`、`docs/march-routes.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 交接基线一致性护栏

### 做了什么（结果）

修正 `handoff.json` 项目总览残留的旧数据基线：与同文件验证区统一为 **7,397 个实体 / 10,277 条关系 / errors=0 / warnings=19,202 / 孤儿实体 83**。同时移除分支说明里会随提交立即过时的基准 commit，改为以 `git log -1` 为精确事实源。

新增轻量合同测试，要求项目总览与验证基线中的实体、关系、错误、警告、孤儿五项数字始终一致，避免后续只更新其中一处再次产生自相矛盾的交接状态。

### 关键决策与被否决的备选

- 不重写历史 `WORKLOG` 中当时真实的 19,266 / 147 基线；历史日志保持 append-only。
- 不把 HEAD 哈希硬编码进会与其同批提交的文档，否则每次提交后文档必然落后一版。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests/test_handoff_consistency.py -q
python3 -m json.tool handoff.json
```

### 未尽事项与已知问题

- 此护栏只保证当前态文档内部一致；真实数据是否通过仍由 `scripts/validate_data.py` 的 errors=0 闸门证明。
- 重复人物删除、再分发许可、Place 历时模型等方向性事项不因本轮文档修正而改变。

### 文件级变更清单

- 当前态：`handoff.json`、`WORKLOG.md`。
- 回归合同：`backend/tests/test_handoff_consistency.py`。

## 2026-07-23 · 展开地图的历史播放闭环

### 做了什么（结果）

地图放大为主体后新增播放 / 暂停 / 上一条 / 下一条。按下播放会从左时间轴当前年份起寻找下一条可定位记录，每 5.2 秒自动推进；地图镜头、事件印章或行军路线、左时间轴年份、实体档案和地图内简介浮窗同时切换。浮窗使用 `aria-live=polite`，键盘可直接操作四个原生按钮。拖动、滚轮或点击地图会暂停镜头；手动改选实体或从左轴改年会结束旧故事，避免旧卡与新镜头互相矛盾；收起地图或卸载页面也会停止计时器。开始地图故事前先停旧的 Space 逐年播放，两套定时器不争写年份。

后端新增 `/api/timeline/map-story`，当前返回 **169 条**：163 条已有 `location` 或至少一段完整 `march` 的 Event / Battle，以及 6 条关键人物生平节点。人物节点分别是汤—鸣条、帝辛/姬发—牧野、姬重耳—城濮、白起/廉颇—长平；它们都同时满足“人物与可定位事件有结构化关系、同年、`life_events.event` 明确包含完整事件名”，地图焦点明确指向该事件。

### 关键决策与被否决的备选

- 不把人物生平节点落到出生地或籍贯。当前 importance 1/2 且有年谱的 42 人 / 156 个节点没有独立地点字段；借出生地显示异地战役会制造事实。只有三重合同命中的 6 条进入清单，其余诚实留空。
- 不把播放计时器塞进 MapPanel 局部状态。`useMapStoryStore` 是清单、当前位置和计时器的唯一真相，地图与时间柱只消费 `current`，避免两份 index 漂移。
- 播放控件仅在地图主体态出现。小地图继续留给当年疆域与选中定位，不永久占用三枚低频按钮。
- 不新增依赖；播放图标继续使用已锁定版本的 Lucide 深导入，后端复用现有实体与关系内存索引。

### 当前状态：现在能跑什么、怎么跑

```bash
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
cd frontend && npm run test:e2e -- e2e/map-story.spec.js
cd frontend && npm run test:e2e
cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js
npm run build
npm run build:safe
```

后端 **194/194 / 10.06s**。播放专项 **2/2 / 12.6s**，真实等待证明计时器从 751 怛罗斯自动推进到 755 安史之乱，并覆盖左轴、浮窗、marker、人物年谱、手动拖图和收起暂停；相邻地图/时间轴 **20/20**。完整 E2E **103 passed + 1 skipped / 4.6m**，safe 专项 **1/1 / 6.8s**。

组件抽取后的 full / safe 根构建均为 **181 modules**；full **1.36s、5,114 files / 134.07 MB**，safe **1.35s、73 files / 5.19 MB**。两者数据闸门均保持 **7,397 / 10,277 / errors=0 / warnings=19,202**；safe E2E 继续通过。播放 API 热索引实测三次为 **2.32–2.57ms**；首次独立进程连索引冷建为 **609ms**。主入口仅从 121.40 kB 量级到 **121.54 kB / gzip 48.66 kB**，MapLibre 仍按需加载；只有既有大 chunk 提示。

最终另以 1440×900 与 390×844 实拍验收。桌面播放条、简介卡、缩放与图例互不遮挡；移动首拍发现四行简介把年份眉题裁掉，遂仅在窄屏压成单行简介与单行来源，复拍确认年份、标题、简介和控制条全部完整可见。证据存入 `docs/design-qa/implementation-map-story-*.jpg`。

### 未尽事项与已知问题

- 当前 150 条未进入播放的人物年谱节点不是遗漏：数据模型没有每个节点的地点引用。今后若补，应在 `life_events` 增加经过来源审校的 Place / Event 引用，再自然进入清单，不能从正文抽地名猜坐标。
- 本轮交付的是可实际预览和回归的用户可见草案；播放节奏、浮窗尺寸与控件位置仍需 Rick 真机观看后确认才算视觉定稿。
- 未发布、未 push、未改部署配置；许可、重复人物删除与 Place 历时模型等既有待决项保持原状。用户维护的 `AGENTS.md` 继续不纳入提交。

### 文件级变更清单

- 播放清单 API：`backend/app/services/timeline_service.py`、`backend/app/api/timeline.py`、`backend/tests/test_map_story.py`。
- 前端状态与请求：`frontend/src/stores/useMapStoryStore.js`、`frontend/src/stores/index.js`、`frontend/src/api/client.js`。
- 地图交互与回归：`frontend/src/components/map/MapPanel.vue`、`frontend/src/components/map/MapStoryPlayer.vue`、`frontend/e2e/map-story.spec.js`。
- 当前态文档与视觉证据：`README.md`、`handoff.json`、`WORKLOG.md`、`docs/design-qa.md`、`docs/design-qa/implementation-map-story-desktop.jpg`、`docs/design-qa/implementation-map-story-mobile.jpg`。

## 2026-07-23 · 金太宗重复人物合并

### 做了什么（结果）

将重复表示同一人的 `p_wanyan_sheng` 与 `p_wanyanwuqimai` 合并为唯一实体，保留已有两条人物关系使用的稳定 ID `p_wanyanwuqimai`。保留项原有的“完颜吴乞买”姓名、1135 年 2 月卒、会宁籍贯与更细的两次伐宋表述没有被覆盖；另一份的在位期、帝王角色、重要度、补充事迹、《金史》来源、Q5070、中文维基与 Commons 图像许可字段全部合入，别名并集也保留。

Wikidata JSONL / CSV 与媒体许可对账物同步迁到稳定 ID，旧 ID 和原先的 `NONE` 双记录均删除。旧帝王生成迁移改用稳定 ID，当前高置信政权迁移把该实体纳入金朝：首跑只新增 1 个 `dynasty_ref`，第二次运行 `changed_files=0`，证明不会再次生成重复项或重复写入。

### 关键决策与被否决的备选

- 同一历史人物只保留一个实体；稳定 ID 优先取已有结构化关系引用者，字段取有来源且不冲突的并集。
- 不保留两个“方便以后再看”。重复实体会继续污染搜索、统计和关系展示。
- 不因自动去重授权而降低身份门槛。今后只在别名、生卒、事迹、来源或外部标识足以闭合时自主合并；仅同名或字段互相冲突仍请求确认。
- 不只删除 YAML。迁移脚本与对齐产物一并改指，避免重跑后复发。

### 当前状态：现在能跑什么、怎么跑

```bash
python3 -B scripts/migrations/2026-07-23-high-confidence-links-round2.py
uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py --strict-seed
uv run --with-requirements backend/requirements.txt python scripts/validate_data.py
```

合并后的完整后端先为 **194/194 / 13.11s**；增加 canonical / 旧 ID 404 防回归合同后，最终基线为 **196/196 / 12.98s**。strict-seed 与普通数据闸门均为 **7,396 实体 / 10,277 关系 / errors=0 / warnings=19,201**；Person **5,628→5,627**，关系不变，重复记录原本是孤儿，故孤儿实体 **83→82**。`data/` 中旧 ID 为 **0**，三份对齐物各只保留一条 canonical 记录；JSONL / CSV 均可解析，`git diff --check` 通过。

### 未尽事项与已知问题

- 另有拓跋嗣 / CBDB 31006、耶律璟 / CBDB 43095、耶律宗真 / CBDB 43157 三组疑似重复，需逐组核对关系和字段；新的自主授权允许证据闭合后直接合并，但不允许只凭名字相似处理。
- 本轮未发布、未 push、未改部署配置；用户维护的 `AGENTS.md` 继续保持未跟踪。

### 文件级变更清单

- 唯一实体：`data/entities/persons/wanyanwuqimai.yaml`；删除 `data/entities/persons/wanyan_sheng.yaml`。
- 对齐产物：`data/_align/wikidata_align.jsonl`、`data/_align/wikidata_align.csv`、`data/_align/wikidata_media.jsonl`。
- 防复发迁移：`scripts/migrations/2026-07-15-emperors-b4-wudai-liaojinxixia.py`、`scripts/migrations/2026-07-23-high-confidence-links-round2.py`。
- 当前态文档：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 可复用发布 Skill 与 v1.3.0 版本标识

### 做了什么（结果）

把历史知识台从“人工记住一串命令”收束为全局 Skill `release-history-kb`：统一执行版本升级、数据校验、Vite 构建、EdgeOne 完整 / 安全两种产物打包、Preview / Production 部署和线上验收。Production 必须显式带 `--confirm-production`；Preview 支持 EdgeOne 查询令牌转 Cookie 的访问流程，能核对版本、实体 / 关系统计和真实地图瓦片。构建失败会恢复版本文件，未提交改动会进入可重复的 dirty revision 摘要，避免把不同代码误认成同一版。

应用版本由 `package.json` 单一口径生成，本轮因新增地图历史播放升到 **v1.3.0**。Vite 在每次构建写出不可缓存的 `/release.json`，感叹号“资料来源”弹窗的标题区常驻显示版本和短修订号；移动端无需滚动也可看见。

重新读取最新 `main@2f82d4f` 后，用 full profile 构建并发布到 EdgeOne Preview `dpadrmnr1yp4`。线上验收通过：**7,396 实体 / 10,277 关系**，真实地图瓦片 **26,056 bytes**；正式环境尚未发布。

### 关键决策与被否决的备选

- 版本信息在构建期注入，不让前端启动后再多发一次请求；`release.json` 仅服务部署验收，因此不增加首屏开销。
- 保留 full / safe 两种明确产物，不在运行时按环境猜测受限地图资源是否存在。
- 不把 Production 发布隐藏在常规构建里；对外发布继续保留显式确认闸门。
- 不用减少数据或地图覆盖范围换取部署速度。常规迭代只构建一次，先发 Preview 验收，再复用同一产物发布 Production。

### 当前状态：现在能跑什么、怎么跑

```bash
python3 ~/.codex/skills/release-history-kb/scripts/release.py prepare --bump patch --profile full
python3 ~/.codex/skills/release-history-kb/scripts/release.py deploy --env preview --profile full
python3 ~/.codex/skills/release-history-kb/scripts/release.py verify --base-url '<Preview URL>' --profile full
```

最终回归：后端 **196 passed / 10.80s**；严格数据闸门 **errors=0**；完整 E2E **103 passed + 1 skipped / 5.6m**；弹窗专项复跑 **6 passed / 17.9s**。full 产物 **5,115 files / 140,584,845 bytes**，构建 **9.91s**；Preview 上传与部署 **109.54s**。

### 未尽事项与已知问题

- 正式站仍停留在上一版；需 Rick 明确确认后，才能把已验收的 v1.3.0 产物发布到 Production。
- EdgeOne Preview 的令牌属于短期访问凭据，不写入仓库、日志文档或最终交付说明。
- CBDB 非商业使用与署名要求继续保留；古地图瓦片的公开再分发许可状态未因本轮发布机制改变。

### 文件级变更清单

- 版本与构建元数据：`package.json`、`frontend/package.json`、`frontend/package-lock.json`、`frontend/vite.config.js`、`scripts/build_edgeone.py`。
- 版本展示与回归：`frontend/src/components/shared/AttributionDialog.vue`、`frontend/e2e/accessibility-keyboard.spec.js`。
- 项目文档：`README.md`、`WORKLOG.md`。
- 全局发布能力（仓库外）：`~/.codex/skills/release-history-kb/`。

## 2026-07-23 · v1.3.0 正式发布

### 做了什么（结果）

将 Preview 已验收的同一份 full 产物正式发布到 EdgeOne Production，部署 ID `dpmr9bplyfcq`，上传与平台部署耗时 **118.73 秒**。正式域名 `https://history.ricksi.com/` 已切换到 **v1.3.0 / 52b2f002**；机器回归核对首页、`release.json`、云函数统计与真实地图瓦片均通过，仍为 **7,396 实体 / 10,277 关系**，样例瓦片 **26,056 bytes**。

浏览器真实操作确认：来源弹窗显示版本与 CBDB 署名，关闭后焦点回到感叹号；地图可放大为主体并成功开始 / 停止历史播放；谱系星图可进入，图谱 / 星云 / 时空柱三种模式均在线出现。页面控制台没有 error。

### 关键决策与被否决的备选

- 先上线并验收历史站，再合并主页入口，避免主页先把用户送到旧目标。
- Production 复用 Preview 的同一份内容寻址产物，不重复构建，不减少瓦片或数据覆盖范围。
- 不以 EdgeOne “Deploy Success” 作为完成；只有自定义正式域名的版本、API、瓦片和真实交互全部通过才宣布上线。

### 当前状态：现在能跑什么、怎么跑

```bash
python3 ~/.codex/skills/release-history-kb/scripts/release.py verify \
  --base-url https://history.ricksi.com/ \
  --profile full
```

正式站已可使用，发布版本可由 `/release.json` 或右上角感叹号弹窗确认。

### 未尽事项与已知问题

- 古地图瓦片的公开再分发许可状态未因本轮上线改变；项目继续按已确认的非商业个人展示口径运行，并保留来源与许可说明。
- 当前 150 条没有可靠地点引用的人物年谱节点仍不进入地图播放，等待数据模型补充经过审校的地点引用。

### 文件级变更清单

- 当前发布事实：`README.md`、`WORKLOG.md`。

## 2026-07-23 · 完整版保留决定与许可前提复核

### 做了什么（结果）

Rick 选择 B：继续保留体验最完整的版本，同时明确以前提“能够确认已有书面公网再分发许可”为条件。本轮按发布流程只核许可证据、不重新构建或部署。仓库随附的 `external_data/chgis_v5/v5_time_pref_pgn_README.txt` 明确写明，CHGIS 数据不得通过互联网电子再分发，除非另有 CHGIS 管理委员会书面协议；CHGIS 官方 V5 页面当前也写明“不允许 resale 或 redistribution”。

OSGeo“左图右史”页面说明地图主要来自谭其骧《中国历史地图集》，原始图片从网络取得并经地图纠正后由 WebGIS 发布，但没有列出允许第三方下载、复制和自托管 5,023 张瓦片的许可。仓库也未发现 CHGIS 单独授权书、谭图权利方授权或 OSGeo 向第三方授予镜像权的文件。因此 B 已记录为**有条件选择**，其许可前提当前不能确认。

### 关键决策与被否决的备选

- 保持当前 Production 完整版本不动；本轮不把已验收的 v1.3.0 Preview 发布到 Production。
- 不把“公开可访问”“OSGeo 已经在线展示”“本站有署名”解释成可复制再分发授权。
- 不把 Rick 选择 B 改写成 Rick 已提供许可。只有核验两类书面授权后才关闭阻塞。

### 当前状态：现在能跑什么、怎么跑

完整版与安全版仍可由 `release-history-kb` Skill 重建；Production 继续是此前的完整构建，v1.3.0 仅在隔离 Preview 验收。若取得授权，应把授权文件或可核验的权利方书面许可交给 Codex，核对授权对象、使用范围、互联网再分发、修改/派生、期限与署名要求后，再决定 Production 发布。

### 未尽事项与已知问题

- 缺 CHGIS 管理委员会允许互联网电子再分发的单独书面协议。
- 缺《中国历史地图集》/配准瓦片相关权利方允许本站复制并公开镜像的书面授权。
- 用户维护的 `AGENTS.md` 继续保持未跟踪；本轮未发布、未改部署配置。

### 文件级变更清单

- 当前发布与许可状态：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-23 · 许可发布决策覆盖与 v1.3.0 正式站复验

### 做了什么（结果）

Rick 将本站明确定位为非商业个人研究与作品展示，接受当前未核实到 CHGIS / 谭图单独书面公网再分发授权的现状，并明确要求跳过此前的许可发布阻塞、继续使用 full Production。该决定关闭项目内的发布等待项，但不改写外部许可事实，也不把已有署名解释为已经取得授权。

检查时 EdgeOne Production 已完成一次 v1.3.0 full 发布，因此没有重复上传或制造第二个部署。正式站 `https://history.ricksi.com/` 当前为 **v1.3.0 / 52b2f002**，部署 ID `dpmr9bplyfcq`。发布验证脚本核对首页、`release.json`、云函数统计与真实地图瓦片均通过：**7,396 实体 / 10,277 关系**，样例古地图瓦片 **26,056 bytes**。

浏览器重新实看确认：资料来源弹层显示 v1.3.0 / 52b2f002、CBDB / CHGIS / OSGeo 谭图来源与固定署名；地图历史播放从 **0 / 169** 推进到 **64 / 169**，时间轴联动至 **710 年**，地图浮窗显示“唐隆政变”的时间、简介与《旧唐书·玄宗本纪》出处；谱系星图的图谱、星云、时空柱均能切换并填满主体区域。浏览器控制台 **0 error**。

### 关键决策与被否决的备选

- 按 Rick 的明确风险决策保留并发布 full；safe profile 继续作为可逆替代方案，不删除。
- 不再要求用户提交两类书面授权才继续项目迭代；该项从 `handoff.json` 的下一任务和待决问题中移除。
- 不把“个人示例、非商业、已署名”写成法律授权或“已确认开源许可”；文档如实区分所有者的发布决定与外部权利状态。
- 正式站已经是同一内容寻址产物，否决重复 Production 部署，避免无意义的上传、缓存切换与版本噪音。

### 当前状态：现在能跑什么、怎么跑

```bash
python3 ~/.codex/skills/release-history-kb/scripts/release.py verify \
  --base-url https://history.ricksi.com/ \
  --profile full
```

当前 Production 可直接使用；来源弹层、固定署名、数据变换说明与 safe 构建能力均保留。许可发布阻塞已经关闭，后续迭代回到高置信内容完整性维护。

### 未尽事项与已知问题

- 未核实到 CHGIS 管理委员会或谭图 / 配准瓦片相关权利方的单独书面公网再分发授权；这是保留记录的外部风险，不再是当前项目发布阻塞。
- 150 条没有可靠地点引用的人物年谱节点仍不会进入地图播放；只有补齐经过审校的地点引用后才可纳入。
- Place 历时性合分与是否扩大低置信行军路线范围仍是后续方向问题，不因本次发布决定自动启动。
- 用户维护的 `AGENTS.md` 继续保持未跟踪，不纳入项目提交。

### 文件级变更清单

- 当前发布、风险决策与交接状态：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-26 · v4「探索」Product Spec 与视觉原型

### 做了什么（结果）

为下一大版本完成了不进入业务代码的产品定义与视觉发散：把「探索」定义为一个由历史问题或私人书籍驱动、先确认研究范围，再渐进编织事件 / 人物 / 地点 / 论点 / 证据网络的时空探索装置。新模块不以聊天记录作为最终产物，而以可播放、可追问、可回溯出处、可版本化的「探索层」作为交付；现有静态知识库继续是只读底座。

形成三幅 1440 × 1024 视觉原型：①对话、时空画布与证据透镜均衡的「叙事编织台」；②地图和时间播放占主位的「时空导演台」；③原文、作者观点、支撑材料与反方视角并置的「史料工作坊」。当前产品收敛建议是以 ① 作为通用壳，播放时进入 ② 的视觉重心，书籍模式进入 ③ 的资料布局。

Product Spec 已细化到信息架构、两条用户闭环、探索状态、证据等级、静态库 / 探索层边界、LLM 逻辑步骤、隐私与版权、性能成本、P0–P2 范围和端到端验收。另制作一幅可切换「历史问题 / 私人书籍」的状态流，实际渲染并点选验证两种入口都汇入同一套范围确认、渐进编织、证据复核与时空探索流程。

### 关键决策与被否决的备选

- 推荐「对话只负责表达与改范围，结构化时空画布才是主体」，不在现有右栏外挂永久聊天框。
- 新生成内容先进入可版本化探索层；否决 LLM 直接写正式 YAML，以免临时推断污染已审定事实。
- 书籍模式明确区分史料直述、作者判断、模型推断与真实争议；否决把作者观点改写成无主体的百科共识，也不为形式平衡虚构反方。
- 私人书籍首版推荐本地优先：原文件不默认上云，只把完成当前模型任务所需片段送出；代价是暂不提供跨设备同步。
- 初始编织只生成 6–12 个场景、可见网络建议不超过 20 节点 / 30 关系，展开时按需处理；否决一次生成完整巨图。
- 视觉原型仍是待批准草案；在 Rick 确认通用壳和组合关系之前，不进入业务代码。

### 当前状态：现在能跑什么、怎么跑

- 正式站只作为现有设计语言与交互基线被只读检查，本轮没有修改或发布。
- 产品草案位于 `docs/product-spec-exploration-v4-draft.md`。
- 三幅视觉原型已在本轮 Codex 对话中展示。
- 交互状态流的源文件位于当前 Codex 可视化目录；已渲染为独立页面并验证「私人书籍」点选后，入口文案和证据复核语义会正确切换。
- 文档检查：`git diff --check` 通过；可视化 fragment 已由官方 render 脚本成功包装，浏览器 DOM 与实际截图均无缺失。

### 未尽事项与已知问题

- 待 Rick 批准：是否接受「原型 1 为通用壳、原型 2 为播放态、原型 3 为书籍态」的组合，以及哪一幅决定通用壳的主要空间分配。
- 模型提供方、费用、上下文限额、外部史料检索范围和持久化方式尚未进入技术设计；这些具体数值必须在实现前按实际 API 与部署条件核查。
- 书籍导入的私人文本处理只有产品边界，尚未实现；无账户的公开站点不应直接承担默认云端全文持久化。
- 用户维护的未跟踪 `AGENTS.md` 保持原样，本轮未纳入变更。

### 文件级变更清单

- 产品草案：`docs/product-spec-exploration-v4-draft.md`。
- 工作日志：`WORKLOG.md`。

## 2026-07-28 · 探索 v10：地图全览、历史参照轴与六层论证图

### 做了什么

把《安史之乱》公开受限 Demo 从“逐幕看一个点”扩成可以先看全局、再进入局部的时空探索。地图默认同时展示 7 个有仓库坐标依据的 Scene、9 幕顺序清单和 6 段柔性叙事曲线；另外 2 幕继续诚实标为未定位。点击地图编号或清单项后进入聚焦，Scene、锚点、顶部年份、证据和播放仍共用同一选择状态。

左栏时间 tab 改成 755—763 的纵向双轨：主轨是九幕书籍 Scene，参照轨是正式知识库中已有明确年份字段的事件、人物和帝王。参照项点击后真实联动现有时间与实体选择，不只是装饰标签。“网页”同时改为更明确的“微信读书”，“返回探索入口”收敛为“返回”。

九幕静态四卡概括被替换为可寻址论证图：每幕各有问题、材料观察、推理机制、行动或转折、后果、限制或不确定性六类节点和七条显式关系。节点详情说明认识论层级、章节级来源边界并可回到受限锚点。后端新增 `book_argument_graph.v1` Prompt 合同、Pydantic 图校验和 guardrails；深度分析现在会生成 `needs_model / not_called` 队列项，但不会调用模型或把私人正文写入合同。

### 关键决策与被否决的备选

- 地图曲线固定表达“叙事顺序”，GeoJSON 写入 `sequence_not_route`；否决用直虚线、箭头或章节顺序冒充行军路线。
- 未定位 Scene 保留在九幕清单，但不上地图；否决从地名文本、人物籍贯或相邻节点猜坐标。
- 时间参照轨只使用仓库实体的明确年份字段，并记录 ID、类型、证据字段和源 YAML；否决用人物在世区间或常识补时间点。
- 论证图强制六类节点与认识论分层，但不强制正反观点；只有同一命题存在明确冲突材料和 locator 时才允许 `contradicts`。
- 研究 Brief 下“结构压力 / 战争动员 / 军政决策 / 联盟政治 / 历史记忆”只改变无人消费的 store 字段，没有任何视图联动，直接删除；以后若恢复，必须先定义真实筛选或重编织结果。
- 没有接入真实模型。先把来源注入、输出 Schema、引用边界和状态语义做成可测试合同，避免把人工 Demo 冒充模型链路。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore
```

最终验证：

- `npm run build`：218 modules / 1.45s；`ExplorationView` 50.03 kB / gzip 18.45 kB，`ExploreMapPanel` 16.13 kB / gzip 5.82 kB；没有新增依赖，MapLibre 仍为按需 chunk。
- 后端聚焦测试：23 passed、1 skipped / 0.52s；覆盖六类节点、边引用、Prompt 合同、runtime source slot 和私人正文不进入合同。
- 探索联合 E2E：13 passed / 32.2s；覆盖旧入口、EPUB、微信读书、地图总览、未定位清空、播放保持、时间参照联动、九幕论证图和来源回跳。
- 1195 × 719 应用内浏览器实拍了地图全览、时间双轨和论证节点详情；没有新的 console warning / error。证据见 `docs/design-qa/exploration-v10/`。
- 联合测试首次真实暴露两个整合问题：外层分栏下层最小高度少算 50px，导致地图只剩 190px；MapLibre 参考瓦片加载期把 Scene 清空错误挡住。分别修正为 436px 与按 GeoJSON source 可用性同步后，旧合同 7/7、新旧联合 13/13 通过，没有改断言或降低 240px 地图底线。

### 未尽事项与已知问题

- 真实模型运行时、流式/分批生成、取消与重试、引用审计、成本状态均未实现；当前 `candidate_output` 始终为空。
- 后端探索仍是有界单进程内存会话，没有账户级持久化或跨 worker 恢复。
- 本轮只跑探索联合 13 项和后端聚焦 24 项，没有重跑全量 110 项、数据全量校验或 safe profile 构建；旧基线仍记录在 `handoff.json`。
- 本轮没有改正式 YAML / GeoJSON、地图资产、CI 或部署配置，没有 push 或发布。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 前端：`frontend/src/components/exploration/ExploreMapPanel.vue`、`frontend/src/components/exploration/ExplorationReader.vue`、`frontend/src/views/ExplorationView.vue`。
- 公共 Demo 与时间参照：`frontend/src/data/anshiPublicDemo.js`、`frontend/src/data/anshiTimelineReferences.js`。
- 后端合同：`backend/app/schemas/exploration.py`、`backend/app/services/exploration_service.py`、`backend/app/prompts/__init__.py`、`backend/app/prompts/book_argument_graph.py`。
- 自动验证：`backend/tests/test_exploration_argument_prompt.py`、`frontend/e2e/exploration.spec.js`、`frontend/e2e/exploration-v5.spec.js`、`frontend/e2e/exploration-map-overview.spec.js`、`frontend/e2e/exploration-timeline-context.spec.js`、`frontend/e2e/exploration-argument-graph.spec.js`。
- 产品与验收：`README.md`、`docs/product-spec-exploration-v4.md`、`docs/workflows/book-to-exploration.md`、`docs/design-qa.md`、`docs/design-qa/exploration-v10/`、`handoff.json`。
- 工作日志：`WORKLOG.md`。
- 对话内视觉产物：三幅探索模块视觉原型，以及仓库外的交互状态流。

## 2026-07-26 · v4「探索」交互原型与开发标注定稿

### 做了什么（结果）

把上一轮图片级方向推进为可实际操作、可直接交给开发的桌面网页原型。编织态、播放态、书籍态共享同一探索壳：问题模式可以在对话约定、时间主线、地图场景和证据透镜之间切换；播放模式会把左场景轨、地图聚焦浮窗、解释透镜和底部时间带同步推进；书籍模式以“内置阅读器 + 论证链路 + 常驻地图 + 关系化证据”为主体，并提供微信读书网页来源兼容态。

原型内置 G / W / P / B 编号的开发标注层。每个编号均能打开定位、默认、交互、状态、数据和验收六项说明；顶部状态入口可演示 Loading、Empty、Error，方便开发按同一合同实现，而不是从静态图猜交互。Product Spec 同步补齐了书籍接入、观点关系、生产地图分层、Scene 数据合同和完整状态矩阵。

### 关键决策与被否决的备选

- 书籍态保留常驻地图，段落、论点、人物、地点和证据互相联动；否决把书籍模式做成只有文本与卡片的旁支页面。
- 内置阅读器是首版核心合同；微信读书网页只作为渐进增强与返回原站入口。实测公开阅读页没有直接阻止 iframe 的响应头，但跨域 DOM、选区读取与第三方登录 cookie 仍不能作为稳定接口，因此首版摘录回流采用复制粘贴，扩展桥接留到后续。
- 证据关系按互证、补充、关注层级不同、方法差异、范围限制、直接冲突和证据缺口表达；只有材料真的冲突时才显示冲突，否决为了版式平衡强造正反观点。
- 原型地图使用真实 raster 视觉资产与可交互 DOM 标注层以验证视觉；生产实现沿用 MapLibre，使用已核验 raster 瓦片、GeoJSON line / fill / symbol 层、标签避让和 Scene 镜头合同，否决把原型折线或生成底图直接当生产地理数据。
- 本轮范围严格留在 `prototypes/exploration-v4/`、产品文档和交接文档；没有修改生产 `frontend/` / `backend/`，没有发布。

### 当前状态：现在能跑什么、怎么跑

- 本地预览保持在 `http://127.0.0.1:4173/`，Codex 内置浏览器已保留书籍态交付页。
- `cd prototypes/exploration-v4 && npm run build`：通过；Vite 6.4.2 转换 4570 modules，JS 300.48 kB / gzip 91.49 kB，构建 1.18s。
- `cd prototypes/exploration-v4 && npm run test:sites`：4 / 4 通过。
- 1440 × 1024 浏览器实测：三态切换、播放自动推进至结束、书籍第二段联动、网页来源、B04 六项标注、澄 / 夜、Loading / Empty / Error 均通过；console error 为 0。
- `git diff --check`：通过。由于生产运行时代码未变，本轮未重复执行后端、数据和正式前端全量回归。

### 未尽事项与已知问题

- 需要 Rick 实际操作并确认原型；确认前不进入正式 Explore 路由和后端探索层实现。
- 原型没有真实 LLM、书籍解析或持久化；这些属于生产阶段 2 / 3。
- 微信读书跨域正文和选区不能自动回流；首版需复制粘贴，后续可评估浏览器扩展桥接。
- 地图路线仍是原型级简化；生产需要已核验瓦片、GeoJSON、MapLibre 摄像机和不确定地点合同。
- 本轮只验收 1440px 桌面信息架构，未设计手机或窄平板替代布局。
- 用户维护的未跟踪根 `AGENTS.md` 保持原样，未纳入本轮成果。

### 文件级变更清单

- 产品定稿：`docs/product-spec-exploration-v4.md`。
- 原型：`prototypes/exploration-v4/src/App.jsx`、`src/styles.css`、`public/assets/`、`AGENTS.md`、构建与测试包装。
- 视觉与验收：`prototypes/exploration-v4/design-qa.md`、`qa-*.png`。
- 项目入口与交接：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-26 · v4「探索」最终重做：共享 Exploration 与按需产品旁注

### 做了什么（结果）

将被打回的「常驻 Presenter Mode」彻底撤出 prototype 版面，交付一套默认退场、点击展开的完整产品旁注：默认界面只保留既有工具位中的「产品旁注」开关；开启后，相关标题旁出现无编号蓝灰锚点；点击先看到「解决什么 / 为什么这样排 / 边界」，需要开发依据时再临时展开状态定义、数据合同、开发验收和该区域的真实状态场景。开关前后主工作区同为 1440 × 916，旁注不触发布局重排。

同时修正了上一版更根本的产品矛盾。编织、播放、书籍现在使用同一个「延安整风（1941—1945）」Exploration，所有模式保持挂载并共享 Scene、地点、主线、段落、来源、证据、透镜与播放速度；顶部时间跟随当前 Scene。播放支持 0.5× / 1× / 1.5× 真实计时、暂停、步进、结束和重播；无可靠地点时保留上一范围但不激活任何猜测点。W03 地图、P04 播放、B01 书籍来源的状态演示只从对应完整旁注进入，只改变局部区域。

撤下了未核验的逐字引文、页码、出版社和「史实已核验」标签，改为明确的作者论证摘要、研究摘记、待版本复核与待正式库核验；材料关联线使用无箭头虚线并标明不是行动路线。证据结论默认不出现，只有用户点击已复核关系后才显示「当前材料尚无实质冲突」。

### 关键决策与被否决的备选

- 最终方案自主采用「锚点短旁注 + 临时完整依据」两级渐进披露；不再要求 Rick 在近似视觉选项中做局部产品决策。
- 否决常驻 Presenter Card、章节轨、发布会进度、聚光暗幕、右侧讲稿和全局 Normal / Loading / Empty / Error 演示器；产品经理讲述可以完整，但不能成为 prototype 的第四栏。
- 三态是同一 Exploration 的三种工作姿态，不是三个演示页面；否决切换模式时卸载组件、重置上下文或更换研究题目。
- 状态按区域真实降级并保留最近可用内容；否决「返回正常状态」式评审作弊器。
- 书籍摘要只承载交互与结构验证；没有核验版本与页码时，宁可公开缺口，也不把重构文本包装成原文。
- 本轮严格停在隔离原型、Product Spec 和交接文档；生产 `frontend/` / `backend/`、部署和发布均未启动。

### 当前状态：现在能跑什么、怎么跑

```bash
cd prototypes/exploration-v4
npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
```

最终预览保持在 `http://127.0.0.1:4173/`。验证结果：

- `npm run build`：最终收尾复跑通过；Vite 6.4.2，4570 modules，3.19s；JS 311.44 kB / gzip 94.40 kB，CSS 33.79 kB / gzip 6.92 kB。
- `npm run test:sites`：4 / 4 通过。
- Codex 应用内浏览器 1440 × 1024：旁注关闭/开启零重排、W03 短注/完整依据、Ready/Partial/No location/Tile error、1.5× 播放推进、结束/重播、无地点、B01 三来源状态、第二段到 Scene/结构/地图联动、证据复核后结论、澄/夜均通过。
- 1260 × 900：`scrollWidth=innerWidth=1260`、`scrollHeight=innerHeight=900`，无页面溢出。
- 浏览器 console：0 error，0 warning。
- 同视口视觉 QA：`prototypes/exploration-v4/design-qa.md` 最终为 `passed`，无 P0 / P1 / P2。
- `python3 -m json.tool handoff.json` 与 `git diff --check` 在会话收尾再次执行。

### 未尽事项与已知问题

- 原型没有真实 LLM、持久化、书籍解析或知识库检索；进入生产前仍需 Rick 按最初约定明确批准。
- 原型 raster 地图只定义视觉与交互基线；生产必须使用 MapLibre、已核验瓦片 / GeoJSON、标签避让和 Scene 摄像机合同。
- 书籍摘要仍是明确标识的原型材料；真实内容管线必须绑定用户版本、段落锚点和可核验出处。
- 1260 宽度虽无溢出但已接近高密度桌面下限；若生产要把它作为主要宽度，应定义独立紧凑排版。
- 当前成果保留在工作区，未提交、未发布；与任务无关的既有改动和用户维护的未跟踪根 `AGENTS.md` 均未纳入本轮。

### 文件级变更清单

- 产品规格与现行规则：`docs/product-spec-exploration-v4.md`。
- 原型实现：`prototypes/exploration-v4/src/App.jsx`、`prototypes/exploration-v4/src/styles.css`。
- 原型持久决策：`prototypes/exploration-v4/AGENTS.md`。
- 视觉与验收：`prototypes/exploration-v4/design-qa.md`、`qa-final-*.png`、`qa-compare-*.png`。
- 项目入口与交接：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-26 · v4「探索」收敛为单一书籍工作台与地图曲线重做

### 做了什么（结果）

按 Rick 的明确方向移除了原型中的「编织态 / 播放态 / 书籍态」顶层切换，只保留一套书籍探索工作台。研究 Brief 与论证链成为阅读过程中的页内结构，Scene 播放、步进、速度、地图浮窗和时间轨成为地图下方的页内能力；内置阅读器、网页来源和关系化证据仍在同一三栏页面中。段落、论证、Scene、地点、播放状态和证据继续共用一份 Exploration。

地图彻底删除地点间直虚线。默认 Flow 改为从当前材料浮窗旁的非地理 hub 向延安、西安、重庆分别发散三条双层 cubic Bézier；备选 Beads 沿同一 fan-out 拓扑使用疏朗不等距珠点。两者都不串联城市、没有箭头、不穿过地点标签，并明确写「从当前材料关联到地点 · 不代表移动」。两个可比较入口是 `?route=flow` 和 `?route=beads`。

### 关键决策与被否决的备选

- 书籍探索是唯一页面骨架；否决保留三态入口、默认只选书籍态，以及保留不可达隐藏页面。
- 编织与播放保留为能力而不是模式：前者落在研究约定和论证链，后者落在地图 Scene 浮窗、播放 dock 和时间轨。
- 第一次柔性曲线仍连接城市，PM reviewer 指出会被误读为行动路线；最终改成材料 hub fan-out。否决仅靠「非行动路线」文案修补城市连线语义。
- 默认采用连续 Flow，因为它最清楚表达「一份材料映射多个地点」；Beads 作为图面备选，不在产品里放永久方案选择器。
- 没有核验版本和页码，不把摘要替换成伪原文；继续明确显示「作者论证摘要 / 待按所选版本复核」。
- 产品旁注继续默认退场、点击展开；没有让 PM 讲稿重新占据 prototype 版面。

### 当前状态：现在能跑什么、怎么跑

本地预览保持在：

```text
http://127.0.0.1:4173/?route=flow
http://127.0.0.1:4173/?route=beads
```

最终验证：

- `npm run build`：通过；Vite 6.4.2，4570 modules，1.26s；JS 300.92 kB / gzip 92.68 kB，CSS 37.73 kB / gzip 7.50 kB。
- `npm run test:sites`：4 / 4 通过。
- 1440 × 1024：书籍三栏满高；Flow / Beads Canvas 实际像素可见；材料线避开标签；播放 dock 保持在底部。
- 1260 × 900：`scrollWidth=innerWidth=1260`、`scrollHeight=innerHeight=900`，无页面溢出。
- 1.5× 播放：1942.02 推进到 1942.05，时间轨、地图标题和浮窗同帧；结束后显示重播，重播回到第一幕。
- 点击第二段：左栏段落、1942—1943 论证、1943 Scene 与地图浮窗同步。
- 内置阅读器 / Web limited、产品旁注两级、澄 / 夜均通过；最终热更新后 console error 0、warning 0。
- 同视口与地图局部设计 QA 无 P0 / P1 / P2，`prototypes/exploration-v4/design-qa.md` 最终为 `passed`。
- `python3 -m json.tool handoff.json` 与 `git diff --check` 通过。
- Canvas 不运行常驻动画，只在容器尺寸、DPR 或方案变化时重绘；没有新增依赖或网络请求。

### 未尽事项与已知问题

- 当前仍是隔离原型，没有真实 LLM、书籍解析、持久化或知识库检索；没有修改生产 `frontend/` / `backend/`，没有部署或发布。
- 1260 是高密度桌面下限；生产若覆盖更窄桌面，需要独立紧凑排版。
- 生产地图需把材料 fan-out 的语义、来源与控制点转换为经审校的 GeoJSON，并交给现有 MapLibre GL JS 4.7.x 图层和标签避让；原型 Canvas 坐标不能直接成为地理数据。
- 真实书籍内容必须绑定用户提供的版本、段落锚点和出处；现有文字只用于产品结构验证。
- 当前成果仍在工作区，未提交、未发布；用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 单工作台实现：`prototypes/exploration-v4/src/App.jsx`、`prototypes/exploration-v4/src/styles.css`。
- 原型持久决策与 checkpoint：`prototypes/exploration-v4/AGENTS.md`、`prototypes/exploration-v4/.scratch/book-only-checkpoint.md`。
- 产品规格：`docs/product-spec-exploration-v4.md`。
- 设计验收：`prototypes/exploration-v4/design-qa.md`、`qa-book-only-*.png`、`qa-compare-book-only-flow.png`、`qa-compare-book-map-lines.png`。
- 项目入口与交接：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-26 · 书籍探索九条浏览器批注收口

### 做了什么（结果）

把用户在 1117 × 837 实际页面上标出的九处问题合并为一次工作台收口。顶部由三行压成全局导航与书籍工作栏两行；三栏加入可访问分隔边界；左栏形成「内置阅读器 / 网页来源 / 时间 · 事件柱」三级入口，内置阅读器再分正文与锚点；中央逻辑节点可以展开作者摘要或证据边界，并一键回到对应正文；常驻播放 dock 删除，只在地图左下保留默认收起的次级入口；右栏用 `+ / 输入 / 发送` 一体式 composer 取代重复的段落摘要和提问说明。

原型仍保持单一 Exploration。选择左栏事件时，顶部纪年、地图 Scene、论证段落与左栏当前项同帧更新；无可靠地点的 1944 Scene 保留上一地图视野但不激活任何地点。`+` 菜单可写入当前摘录、外部材料或人物事件关联；地图说明收敛为「材料关联」，完整非移动语义放入 title / aria。

### 关键决策与被否决的备选

- 顶部必要信息只允许进入书籍工作栏；否决为“书籍探索 / 当前研究 / 已自动保存”另设一行。
- 播放是地图的次级能力，默认不占工作台高度；否决把 Scene 轨与控制常驻地图下方。
- 阅读器默认连续正文，锚点与事件柱是可切换的定位方式；否决继续用大块元信息或碎片卡替代阅读。
- 逻辑节点必须可逆地回到来源；没有确切版本时只展示作者论证摘要和证据边界，不伪造原文、页码或出版社。
- 三栏宽度属于个人阅读视野，采用拖动、方向键与双击复位；不引入独立布局设置页。
- 右栏输入只保留一个 composer；`+` 菜单承担材料附加，否决在输入框上方重复解释明显操作。
- 当前批次仍只修改隔离原型、产品文档与交接材料；生产 `frontend/` / `backend/`、部署与发布保持不动。

### 当前状态：现在能跑什么、怎么跑

```bash
cd prototypes/exploration-v4
npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
```

本地预览保持在 `http://127.0.0.1:4173/?route=flow`。

- `npm run build`：通过；Vite 6.4.2，4570 modules，1.21s；JS 326.29 kB / gzip 99.23 kB；CSS 44.47 kB / gzip 8.45 kB。
- `npm run test:sites`：4 / 4 通过。
- 1117 × 837：`scrollWidth=innerWidth=1117`、`scrollHeight=innerHeight=837`；mode bar 与常驻 playback dock 均不存在；默认栏宽 280 / 525 / 300。
- 1440 × 1024：无页面溢出；地图吸收剩余高度；右栏 composer 与左栏正文完整可见。
- 交互实测：正文 / 锚点、三来源 tab、事件柱联动、全部逻辑节点详情与原文回跳、地图播放展开 / 1.5× / 结束 / 重播、`+` 菜单与发送、澄 / 夜均通过。
- 无地点 Scene 复验 `.map-point.active=0`；正文段落 `tabIndex=0`；分栏方向键 280 → 292 px、双击恢复 280 px。
- 浏览器 console：最终 error 0、warning 0。
- 同视口设计 QA 最终无 P0 / P1 / P2，`prototypes/exploration-v4/design-qa.md` 为 `passed`。

### 未尽事项与已知问题

- 当前仍是隔离原型，没有真实 LLM、书籍解析、持久化或知识库检索；进入生产前仍需 Rick 明确批准。
- 浏览器自动化没有稳定提供连续 pointermove，分栏真实鼠标拖动建议在生产 E2E 用 PointerEvent 序列补钉；键盘调整与双击复位已实际验证。
- 低于 980 px 的窄桌面 / 平板不属于本隔离原型范围，生产若覆盖需独立布局。
- 真实正文仍必须绑定用户提供的版本、章节、段落和页码；现有文本只用于产品结构与状态验证。
- 当前成果仍在工作区，未提交、未发布；用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 原型实现：`prototypes/exploration-v4/src/App.jsx`、`prototypes/exploration-v4/src/styles.css`。
- 原型规则与 checkpoint：`prototypes/exploration-v4/AGENTS.md`、`prototypes/exploration-v4/.scratch/annotation-round-checkpoint.md`。
- 产品规格：`docs/product-spec-exploration-v4.md`。
- 设计验收：`prototypes/exploration-v4/design-qa.md`、`qa-annotation-round-*.png`、`qa-compare-annotation-round*.png`。
- 项目入口与交接：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-27 · v4 书籍探索首个生产切片

### 做了什么（结果）

把已经批准的单一书籍探索原型接入现有 Vue / Pinia / FastAPI 产品。全局新增「探索」路由，进入后直接打开同一套书籍工作台：桌面为可调阅读 / 论证地图 / 关系证据三栏，移动端为阅读 / 时空 / 出处三视图；左栏支持正文、锚点、时间·事件柱和网页来源，中央逻辑节点可以展开并回到绑定段落，地图 Scene 浮窗与顶部纪年同步，播放控制默认收在地图内，右栏用 `+ / 输入 / 发送` 记录当前文本问题。

私人 TXT / Markdown 现在会真实提交到后端，解析为章节与段落锚点。会话最多 64 份、6 小时失效、按最近访问淘汰，支持 revision 乐观并发和显式删除；全文不写入仓库、日志或数据库，进程重启即清除。当前问题只记录为 `recorded_no_llm`；待复核 Scene 只会标记 `model_inference / pending_review`，不生成伪页码、伪引文或猜测地点。导入任意文本后，示范书的延安、时间轴、作者判断和证据关系全部退场，界面显示尚未结构化。

生产地图继续使用现有 MapLibre。full profile 复用本地 1908 配准历史图层并明确标注「非当前疆界」，safe profile 从构建期完全移除该 source。材料关系从 Scene 浮窗边缘对应的中性 hub 向延安与待核材料地点分别发散两条双层连续 Bézier；hub 不显示为地理点，线条不连接城市、不加箭头或虚线，拖动、缩放和 resize 时才按可见关系重算。无地点 Scene 清空地点和关系覆盖层，但保留最近有效视野。

### 关键决策与被否决的备选

- 探索一级入口直接进入最近或空白书籍工作台；否决再增加一张只有「提问题 / 导入书」的功能首页。两个动作以后都从工作台内新建并汇入同一 Exploration。
- 私人导入先采用有界进程内会话；否决在没有身份与存储边界时把全文写入正式 YAML、浏览器长期存储或服务器日志。代价是重启和多 worker 不可恢复，已作为下一阶段显式缺口。
- composer 当前只记录、不假装已经接入模型；否决用前端假回复或把结构提议显示成史实。
- 导入文本缺时间、地点与证据关系时保持空结构；否决为了画面完整沿用示范书数据或从文字、籍贯和现代常识猜坐标。
- 地图参考层复用真实配准瓦片；否决把原型生成地图截图当生产底图。safe profile 在构建期删除 source，而不是只把标题或开关隐藏。
- 材料关系以中性 hub fan-out 表达；否决地点间直连、机械虚线、箭头，以及只靠「非移动」文案修补行动路线语义。
- 移动端首版承担阅读、Scene 与出处，不提供导入和复杂编排；避免窄屏复制桌面三栏。
- 本轮不改 CI / 部署配置，不 push、不发布；现网仍是 v1.3.0 / 52b2f002。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore&scene=scene-focus
```

最终验证：

- 后端全量：`205 passed in 11.41s`；新增导入、读取、删除、compose、mutation、revision 冲突、认识论边界、容量与 TTL 合同。
- 数据全量：7,396 实体 / 10,277 关系，`errors=0`、`warnings=19201`，4.31s；没有删除、隐藏或降级既有 warning。
- 前端全量 E2E：`106 passed + 1 skipped`，4.7m；在最终地图视觉微调前已覆盖全站，改动后的探索专项 3/3 和 safe 专项 1/1 再次通过。
- 相关地图、行军、键盘与控件定向回归：21/21，51.1s。
- final full 前端 build：204 modules / 1.59s；ExploreMapPanel 11.81 kB / gzip 4.30 kB，保持按需加载。
- final safe 前端 build：204 modules / 1.48s；ExploreMapPanel 11.09 kB / gzip 4.08 kB；safe runtime 专项 1/1，7.0s，时间柱与探索页均不请求 `/tiles/atlas/`。
- 浏览器实拍：1117 × 837、1440 × 1024、390 × 844 与夜色；两条材料线共享非地点 hub，终点分别绑定地点；逻辑回跳、1.5× 播放、无地点清理、私人导入空态和移动三视图通过；console error 0、warning 0。
- 同视口原型 / 生产并排验收无剩余 P0 / P1 / P2；证据见 `docs/design-qa.md` 与 `docs/design-qa/exploration-v4-production/`。
- `python3 -m json.tool handoff.json`、`git diff --check` 通过。

性能边界：探索地图仍是按需 chunk；移动端只有进入「时空」才挂载 MapLibre。材料曲线只在 Scene、相机或容器尺寸变化时按 2 条 × 33 点重算，不运行常驻动画。现有 `seed` 与 MapLibre 大 chunk 警告未扩大为本轮阻塞。

### 未尽事项与已知问题

- 后端探索会话是单进程内存，不跨重启、worker 或设备恢复；还没有账户身份、加密私人存储、导入导出探索包。
- 真实 LLM 范围确认、渐进编织、现有知识库检索、引用审计和成本/取消状态未接入；当前 composer 的真实语义就是「记录问题」。
- 只支持 TXT / Markdown；EPUB、版本与页码绑定、PDF/OCR、网页选区同步、微信读书桥接与多书对读未做。
- 示范书内容只用于结构与状态验证，所有作者摘要仍需绑定用户实际提供的版本和段落；待核材料地点没有被晋升为正式事实。
- full profile 的 1908 历史图层是参考底图，不代表 1942 疆界；safe profile 保持完全不请求。现网尚未包含本轮代码。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动，不纳入提交。

### 文件级变更清单

- 前端入口与状态：`frontend/src/App.vue`、`frontend/src/stores/index.js`、`frontend/src/stores/useUIStore.js`、`frontend/src/stores/useExplorationStore.js`、`frontend/src/api/client.js`。
- 前端工作台：`frontend/src/views/ExplorationView.vue`、`frontend/src/components/exploration/ExplorationReader.vue`、`ExplorationEvidence.vue`、`ExploreMapPanel.vue`、`frontend/src/components/shared/SplitPane.vue`。
- 后端合同与服务：`backend/app/main.py`、`backend/app/api/explorations.py`、`backend/app/schemas/exploration.py`、`backend/app/schemas/__init__.py`、`backend/app/services/exploration_service.py`。
- 验证：`backend/tests/test_api_explorations.py`、`frontend/e2e/exploration.spec.js`、`frontend/e2e/safe-distribution.spec.js`、`docs/design-qa.md`、`docs/design-qa/exploration-v4-production/`。
- 产品与原型：`docs/product-spec-exploration-v4.md`、`prototypes/exploration-v4/`。
- 项目入口与交接：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-27 · 探索 v5 双入口、EPUB 阅读与书籍拆解工作流

### 做了什么（结果）

把探索页从“默认已经有一本书”的非正常产品前提改成真正的探索入口：用户没有书时，可以直接输入一段历史问题，服务端先建立范围合同和证据缺口，再由用户确认时间、空间与叙事主线；用户有材料时，可以上传 TXT、Markdown 或 EPUB。两条路径最终进入同一套阅读 / 结构 / 地图 / 证据工作台，返回动作也改为“返回探索入口”，不再误导为返回时间柱。

EPUB 现在按二进制导入，不伪装成纯文本。后端验证 ZIP 边界、读取 `container.xml`、OPF 与 spine，生成章节、段落 locator 和阅读进度；前端只渲染当前章节，点击或滚动段落通过串行 revision mutation 同步，避免并发覆盖。本机 Downloads 中的《红太阳是怎样升起的》只用于私有只读验证：解析得到 28 个阅读节、4,445 个段落、541,066 个字符，约 85ms；原书、绝对路径、下载来源和长引文均未进入仓库。

微信读书新增按需网页来源：默认不加载第三方页面，用户主动后才尝试 iframe；跨域环境下不读取正文、选区或滚动进度。用户可以手动确认章节 / 百分比并选择性粘贴当前段落，服务端真实记录这一桥接状态，不把手工同步写成自动实时联动。

《红太阳》内置示例由原先单一段落结构扩展为五条章节级作者判断主线和六幕时空编排，涵盖权力与联盟、解释权、组织与教育技术、审干与抢救、制度化收束。示例明确标示“内置衍生示例 / 不含原书”；作者判断、平台编排、材料关系和证据缺口分层，不强行制造正反观点，也不生成伪页码或伪引文。

同时沉淀 `book-to-exploration` workflow 与 Draft 2020-12 Schema：覆盖 Prompt / 书籍双入口、允许来源集合、章节 / 来源包、作者判断、事实候选、Scene、证据关系、反证 / 缺口、人工复核、隐私和公开衍生检查。私有验证 artifact 只保留结构计数与待核对象，不含可重构原书的连续摘要。

### 关键决策与被否决的备选

- 默认必须是真空入口；否决强行打开示例书，或再增加一层只有“返回”的书籍首页。
- Prompt 首步只建立范围合同；否决在没有模型和来源时用前端假回复冒充已经“编织历史”。
- EPUB 走独立安全解析合同和按章窗口；否决把二进制当 UTF-8 文本，也否决把全书数千段同时挂入 DOM。
- 微信读书采用“按需嵌入尝试 + 手动桥接”；否决宣称跨域 iframe 能自动读取进度，或通过未授权脚本抓取登录态和正文。
- 《红太阳》示例只提交衍生分析；否决把私人 EPUB、路径、原文或长引文纳入 Git。五条作者判断来自章节级分析，把它们编排为六幕 Scene 是平台提议，不伪装成作者明示模型。
- 复用能力先以仓库内 workflow + Schema 交付；否决手写一份无法验证导入合同的全局 Skill。第二个项目出现时再从已验证合同提炼独立 Skill。
- 真实 LLM、私人持久化、模型费用和账户身份会改变隐私与成本边界，继续留在下一轮产品/技术决策；本轮不暗中选型。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore
```

最终验证：

- 后端全量：`214 passed + 1 skipped in 11.36s`；真实本机 EPUB opt-in：`1 passed`。
- 数据全量：7,396 实体 / 10,277 关系，`errors=0`、`warnings=19201`；没有删除、隐藏或降级既有 warning。
- 前端 full E2E：静止代码后 `110 passed + 1 skipped`，4.6m。此前边改前端边跑的一次全量被 HMR 打断 M12-3；独立复验 6/6，最终静止代码全量通过。
- 探索专项：`7/7`，14.3s，覆盖真空入口、Prompt hydration / 失败草案、EPUB adapter / 章节窗口、微信读书手动桥接、深度示例、私人导入和移动端。
- safe 根构建：validate + 213 modules / 2.15s；`edgeone-dist-safe` 86 files / 5.35 MB，atlas 0。safe runtime 专项 `1/1`，7.4s，不请求 `/tiles/atlas/`。
- final full 前端 build：213 modules / 1.46s；`ExplorationView` 36.85 kB / gzip 14.33 kB。现有 `seed` 与 MapLibre 大 chunk 警告仍在，未因本轮扩大。
- workflow：Schema 自检、私有 artifact 验证与隐私扫描通过；90 个对象引用在 Agent 前向测试中无重复、无悬空，正例 5/5、负例 10/10。
- 浏览器实拍：改造前、1440 真空入口、Prompt confirmed、1440 深度示例和 390 移动端；confirmed 后各区域无冲突状态，最终新交互日志 error 0、warning 0。证据见 `docs/design-qa.md` 与 `docs/design-qa/exploration-v5/`。
- 两次专项首跑暴露的是旧验收假设，不是降标修测试：深度示例更换作者主线后更新精确可访问名称；safe 路由新增真空入口后先显式打开示例再核地图资源。修正后目标行为和受限资源断言均保持。

性能边界：本机真实 EPUB 进程内 snapshot 约 2.79 MB；单份来源正文上限 8 MB，最多 64 个会话、6 小时 TTL。章节窗口避免 DOM 随全书段落线性增长，段落检索走缓存 Map。更大的书仍应在持久化阶段改为按章按需读取，不把当前内存模型直接放大。

### 未尽事项与已知问题

- 真实 LLM 尚未接入；Prompt、composer 与深度分析请求只建立合同、记录问题或排队为 `needs_model`，不会自动生成答案。
- 后端会话仍是单进程内存，不跨重启、worker、设备或账户恢复；没有加密私人存储、探索包导出或删除后的审计凭据。
- EPUB 已有章节和段落 locator，但尚无标准 CFI、用户版本/页码绑定、按章服务端懒取和多书对读；PDF/OCR 未做。
- 微信读书能否显示取决于原站登录和 frame 策略；自动 DOM / 选区 / 进度联动在当前跨域架构下不可用。若未来要自动化，必须走官方能力、扩展或用户明确授权的本地桥接。
- 《红太阳》示例是章节级衍生分析，不是证据审计完成版；段落锚点、页码、独立来源与反证检索仍待用户持有版本逐项绑定。
- 本轮未改 CI / 部署配置，未 push、未发布；现网仍是 v1.3.0 / 52b2f002。用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 前端入口与状态：`frontend/src/App.vue`、`frontend/src/api/client.js`、`frontend/src/stores/useExplorationStore.js`、`frontend/src/views/ExplorationView.vue`、`frontend/src/components/exploration/ExplorationEntry.vue`。
- 前端阅读与证据：`frontend/src/components/exploration/ExplorationReader.vue`、`frontend/src/components/exploration/ExplorationEvidence.vue`。
- 后端合同与服务：`backend/app/main.py`、`backend/app/api/explorations.py`、`backend/app/schemas/exploration.py`、`backend/app/services/exploration_service.py`。
- 自动验证：`backend/tests/test_api_explorations.py`、`frontend/e2e/exploration.spec.js`、`frontend/e2e/exploration-v5.spec.js`、`frontend/e2e/safe-distribution.spec.js`。
- 产品、workflow 与 QA：`docs/product-spec-exploration-v4.md`、`docs/workflows/book-to-exploration.md`、`docs/workflows/book-to-exploration.schema.json`、`docs/workflows/book-to-exploration.private-validation.json`、`docs/design-qa.md`、`docs/design-qa/exploration-v5/`、`prototypes/exploration-v4/.scratch/`。
- 项目入口与交接：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-27 · 探索 v6 单一入口与动态工作区

### 做了什么（结果）

把探索空状态从两张割裂的等权大卡收敛为一个主问题输入区。“上传本地书籍”仍然常驻首屏，但降为与“开始框定范围”并列的次级动作；点击后打开专用上传弹层，支持 EPUB / TXT / Markdown，Esc、遮罩、取消和关闭按钮都能退出。返回入口时不再显示上一份示例的状态；示例工作台顶部也删除了没有操作价值的“不含原书”短句。

工作台中央不再把研究 Brief、论证链和地图锁死为固定比例。两条横向分隔器现在分别控制 Brief / 其余区域与论证 / 地图，继承已有 SplitPane 的鼠标拖动、方向键、Home / End、双击复位和本地比例记忆。默认 1280×720 实测约为 92 / 154 / 354px；论证区展开到最大时地图仍保留 240px。地图 Scene 浮窗标题从 17px 收到 12px，回到与其他工作台标题一致的层级。

### 关键决策与被否决的备选

- 上传是主对话入口里的显式分支；否决继续保留第二张等权工具卡，也否决藏进 `+` 菜单。它的文件选择与隐私边界放在专用弹层，不长期占用首屏。
- 中央采用嵌套的通用纵向 SplitPane；否决仅增加“展开论证”二态按钮，因为复杂论证、地图细读和 Brief 校对需要连续比例，不是两个预设档位。
- 保留示例的“内置衍生示例”和版本待绑定信息；只删除无助于操作的“不含原书”短句，不把必要的来源与证据边界一并清空。
- 第一轮地图最小高度测试真实暴露了 SplitPane 的非对称边界缺陷：`hi === lo` 被误判为容器过窄，地图只剩 190px。修正为只在 `hi < lo` 时居中回退；没有降低 240px 断言或放宽验收。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore
```

最终验证：

- 探索专项：`7 passed in 16.2s`，覆盖 Prompt hydration / 失败草案、上传弹层、EPUB adapter / 章节窗口、微信读书手动桥接、示例论证回跳、地图播放、移动三视图、两条横向分隔器与地图最小高度。
- 共享 SplitPane / 人物区回归：`4 passed in 13.5s`，既有横向拖拽和人物区重算未回退。
- 前端构建：213 modules / 1.46s；`ExplorationView` 38.17 kB / gzip 14.77 kB。较 v5 增加约 1.32 kB / gzip 0.44 kB；没有新增依赖，新增运行开销仅为探索桌面的两个 ResizeObserver，MapLibre 仍按需加载。
- `handoff.json` JSON 解析、`git diff --check` 通过。
- 应用内浏览器在 1280×720 完成入口、上传弹层、默认工作台和论证展开态实拍；前后比较与几何数据见 `docs/design-qa.md` 和 `docs/design-qa/exploration-v6/`，`final result: passed`。

### 未尽事项与已知问题

- 真实 LLM、账户级持久化、EPUB CFI / 页码绑定、PDF / OCR 和微信读书自动同步边界没有因本轮布局改造而改变。
- 本轮未跑全站 110+1 的完整 E2E；共享组件影响面用探索 7/7 与现有 SplitPane 专项 4/4 覆盖，完整 E2E 基线仍为 v5 的 110 passed + 1 skipped。
- 本轮未改后端、数据、CI 或部署配置，未 push、未发布；现网仍是 v1.3.0 / 52b2f002。用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 前端入口与工作台：`frontend/src/App.vue`、`frontend/src/components/exploration/ExplorationEntry.vue`、`frontend/src/views/ExplorationView.vue`、`frontend/src/components/exploration/ExploreMapPanel.vue`、`frontend/src/components/shared/SplitPane.vue`。
- 自动验证：`frontend/e2e/exploration-v5.spec.js`、`frontend/e2e/exploration.spec.js`。
- 产品与视觉验收：`docs/product-spec-exploration-v4.md`、`docs/design-qa.md`、`docs/design-qa/exploration-v6/`。
- 项目入口与交接：`README.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-27 · 探索 v7 微信读书网页栏收敛

### 做了什么（结果）

把网页阅读栏从“先解释限制、再给阅读器、再常驻桥接表单”的三段式结构收为阅读优先。来源标题、两套跨域状态说明和 iframe 底部说明全部删除；必要的“在原站打开”移入阅读窗口右下，不再占一整行。手动进度桥接改为一行“同步阅读位置”，默认收起，需要时展开位置、可选摘录和同步按钮。

折叠入口使用 `aria-expanded` 和 `aria-controls`；收起时表单不挂 DOM，展开后保留原有真实 revision mutation，成功同步不会擅自收起用户正在操作的工具。

### 关键决策与被否决的备选

- 删除的是解释性头部，不是必要的逃生出口；否决把“在原站打开”一并删掉，改为阅读窗口内的紧凑次级动作。
- 手动桥接默认折叠但仍显式可见；否决藏进全局 `+` 菜单，也否决继续用大卡常驻。
- 不用新提示文案替换旧提示；跨域能力边界继续由真实行为、README 和产品文档承担，操作页只保留可执行动作。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore
```

最终验证：

- `npm run build`：212 modules / 1.62s；`ExplorationView` 37.75 kB / gzip 14.58 kB。移除两个不再使用的图标深导入，较 v6 少 1 个模块，未新增依赖。
- `npm run test:e2e -- exploration-v5.spec.js`：4 passed / 8.6s；覆盖旧文案缺席、默认折叠、ARIA 展开、真实手动 bridge mutation 和同步后保持展开。
- 应用内浏览器在 1195 × 719 复验默认 / 展开两态；旧头、旧状态与旧跨域说明均为 0，console error 0。视觉证据见 `design-qa.md`、`docs/design-qa.md` 和 `docs/design-qa/exploration-v7/`。

### 未尽事项与已知问题

- 微信读书是否可嵌入仍由原站登录和 frame 策略决定；跨域自动读取 DOM、选区或进度仍不在当前能力边界内。
- 本轮没有改后端、数据、CI 或部署配置，未 push、未发布；现网仍是 v1.3.0 / 52b2f002。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 前端与回归：`frontend/src/components/exploration/ExplorationReader.vue`、`frontend/e2e/exploration-v5.spec.js`。
- 产品与视觉验收：`README.md`、`design-qa.md`、`docs/design-qa.md`、`docs/design-qa/exploration-v7/`、`docs/product-spec-exploration-v4.md`。
- 交接与工作日志：`handoff.json`、`WORKLOG.md`。

## 2026-07-27 · 探索 v8 顶部控件与网页阅读高度

### 做了什么（结果）

把顶部两个难辨的圆形符号重绘为居中的键盘与资料库 Lucide 图标，并统一成 28px 软方钮。原先并列的澄 / 夜色块合为一个主题按钮：图标和单字显示当前主题，完整切换语义进入 title 与 `aria-label`，原有系统主题监听和本地时钟回退保持不变。

微信读书网页窗口不再固定 260px，而是默认占满左栏除“同步阅读位置”外的全部剩余高度。主动展开同步工具后才出现水平分隔，可拖动、可用 ArrowUp / ArrowDown、Home / End 调节、可双击复位，并记忆比例；再次折叠会恢复满高，同时保留同一 iframe DOM，避免第三方页面被无谓重载。

### 关键决策与被否决的备选

- 顶部图标保留两个独立动作，因为“快捷键帮助”和“资料来源 / 致谢”打开的是不同内容；否决只换皮但继续使用语义弱的问号 / 感叹号。
- 合并的是两个主题色块，不是帮助和来源；单一按钮显示当前状态与下一步切换语义，避免再用纯色块让用户猜。
- 高度调节只在同步工具展开时出现；否决默认常驻第二条粗控制柄，也否决通过销毁 / 重建 iframe 来重排高度。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore
```

最终验证：

- `npm run build`：214 modules / 1.43s；`ExplorationView` 40.83 kB / gzip 15.65 kB。仅新增按需深导入的 Lucide 图标和一个探索网页态 ResizeObserver，没有新增依赖。
- `npm run test:e2e -- ui-controls.spec.js exploration-v5.spec.js`：9 passed / 13.4s；覆盖主题往返、SVG 居中、满高阅读、水平分隔、键盘调节、折叠恢复和 iframe 不重挂载。
- 应用内浏览器在 1195 × 719 完成满高默认态与同步展开态实拍；初验暴露的 `Globe` 未注册 warning 已修复，后续没有新的 console warning / error。证据见 `design-qa.md`、`docs/design-qa.md` 和 `docs/design-qa/exploration-v8/`。

### 未尽事项与已知问题

- 微信读书是否可嵌入仍由原站登录和 frame 策略决定；跨域自动读取 DOM、选区或进度仍不在当前能力边界内。
- 本轮没有改后端、数据、CI 或部署配置，未 push、未发布；现网仍是 v1.3.0 / 52b2f002。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 前端：`frontend/src/App.vue`、`frontend/src/components/exploration/ExplorationReader.vue`。
- 自动验证：`frontend/e2e/ui-controls.spec.js`、`frontend/e2e/exploration-v5.spec.js`。
- 产品与视觉验收：`README.md`、`design-qa.md`、`docs/product-spec-exploration-v4.md`、`docs/design-qa.md`、`docs/design-qa/exploration-v8/`。
- 交接与工作日志：`handoff.json`、`WORKLOG.md`。

## 2026-07-27 · 探索 v9《安史之乱》公开受限 Demo

### 做了什么（结果）

把探索模块的公开示例从《红太阳是怎样升起的》切换为《安史之乱：历史、宣传与神话》。本机 EPUB 只做只读结构分析：识别 29 章、69 个 spine 文档、2,086 个段落锚点，并把内容收敛为河北 / 范阳、洛阳、潼关 / 灵宝、马嵬、太原、两京、睢阳、邺城、河阳 / 邙山九幕。原文件、正文、包内 locator、href、哈希和本机路径都没有进入仓库。

公开工作台保留完整的论证、阅读定位、Scene、年份、地图、证据与播放闭环。论证节点可展开并回到稳定公开锚点；当前 0 / 10 页通过权利审查，因此所有锚点只显示原创衍生摘要、章节级定位和“原文未公开”。Scene、锚点、年份和播放计时统一收回 Pinia store，不再由页面与阅读器分别维护。

EPUB 上传压缩体上限由 12 MiB 调整为 16 MiB，并同步修改请求 schema、服务端预检和边界测试。本机《安史之乱》样本可以通过正常导入合同；ZIP 展开体、条目数和单项安全限制没有放宽。

### 关键决策与被否决的备选

- 选择“全链路、有限原文”：公开 Demo 展示九幕完整产品能力，但原文逐页独立审查。否决只做前十页而让后续论证链接失效，也否决把完整正文发到浏览器后再用 CSS 打码。
- “最多 10 页”是产品窗口，不是法律安全线；当前没有已审查页面，所以明确为 0 页。以后只需把单个公开锚点晋升为 `excerpt_visible`，不用改信息架构。
- 地图只使用仓库已有且可核的地点坐标。潼关—灵宝、河阳—邙山保持 `location=null`；否决为画出连续路线而猜坐标或继承上一幕高亮。
- 不把“材料互证 / 不同解释”机械填成正反观点；直接冲突、观察层级不同和证据缺口继续分开表达。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore
```

最终验证：

- 后端 `pytest`：217 passed，1 skipped / 10.70s；真实私有 EPUB opt-in 另行通过。
- 数据校验：7396 entities / 10277 relations / `errors=0`；既有 warning 未隐藏或降级。
- 前端 `npm run build`：215 modules / 1.50s；`ExplorationView` 43.40 kB / gzip 16.30 kB。收回重复状态后较初版减少 2.37 kB / gzip 0.67 kB。
- 探索专项：7 passed / 13.8s；全量 E2E：110 passed，1 skipped / 4.8m。
- `VITE_RESTRICTED_MAPS=0` safe 专项：1 passed / 10.8s。
- 应用内浏览器在 1280 × 720 完成旧 / 新同视口比较，复验论证回跳、受限锚点、无坐标 Scene、零原文泄露和刷新后 console；未发现 P0 / P1 / P2。

### 未尽事项与已知问题

- 当前没有公开任何原文页；如要开放 1—10 页，需要逐页权利审查与可记录的发布检查，不能把“十页”当作自动免责线。
- 九幕是人工复核的静态公开投影；通用 LLM 拆书、引用审计、持久化、EPUB CFI / 版本页码绑定、PDF / OCR 和通用公开投影流水线仍未实现。
- 本轮没有改 CI / 部署配置，没有 push 或发布；现网仍是 v1.3.0 / 52b2f002。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 后端与合同：`backend/app/schemas/exploration.py`、`backend/app/services/exploration_service.py`、`backend/tests/test_api_explorations.py`。
- 前端公开数据与状态：`frontend/src/data/anshiPublicDemo.js`、`frontend/src/stores/useExplorationStore.js`。
- 前端界面：`frontend/src/components/exploration/ExplorationEntry.vue`、`ExplorationReader.vue`、`ExplorationEvidence.vue`、`frontend/src/views/ExplorationView.vue`。
- 自动验证：`frontend/e2e/exploration.spec.js`、`exploration-v5.spec.js`、`safe-distribution.spec.js`。
- 产品、工作流与视觉验收：`README.md`、`design-qa.md`、`docs/product-spec-exploration-v4.md`、`docs/workflows/book-to-exploration.md`、`docs/design-qa.md`、`docs/design-qa/exploration-v9/`。
- 交接与工作日志：`handoff.json`、`WORKLOG.md`。

## 2026-07-28 · 微信读书跨站登录恢复

### 做了什么（结果）

复现了“微信端提示登录成功，但嵌入页一直停在登录中”的状态。微信读书首页在 iframe 内可以加载，但父页面只能看到 iframe 的 `load`，不能跨域读取登录结果；扫码成功也不保证第三方 iframe 取得原站相同的 Cookie / 存储上下文。

网页来源改为把“在微信读书打开”作为可靠主入口，“在本站尝试嵌入”作为明确的实验性动作。嵌入后常备“登录卡住 / 重新载入 / 在原站打开 / 退出嵌入”四个恢复动作；“登录卡住”按需展开原因，并可直接退出 iframe、展开原有的手动位置同步。Pinia 不再把 iframe 文档加载误记为已嵌入可用，而是记录为 `iframe_unverified_manual_only`。

### 关键决策与被否决的备选

- 保留 iframe 作为渐进增强，但不再把它包装成稳定登录能力；否决继续让用户在无法观测的“登录中”页面里等待。
- 不代理微信读书登录、不读取或转存 Cookie，也不移除 iframe 沙箱；这类方案会扩大凭据与第三方内容风险，且仍不能形成可靠官方进度接口。
- 跨域原因不做常驻说明，只有用户点击“登录卡住”时才出现；恢复控件常驻，避免再次进入没有出口的状态。
- 重新载入会显式重建 iframe；普通的同步面板展开 / 折叠仍保留同一 iframe，避免无关重载。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# 浏览器打开：
http://127.0.0.1:5173/#route=explore
```

最终验证：

- `npm run build`：217 modules / 1.67s；`ExplorationView` 45.53 kB / gzip 16.90 kB，较 v9 增加 2.13 kB / gzip 0.60 kB；没有新增依赖。
- `npm run test:e2e -- exploration-v5.spec.js`：4 passed / 15.5s；覆盖原站主入口、未验证能力状态、iframe 重载、满高 / 分隔调节、手动同步和登录恢复降级。
- 应用内浏览器在 1280 × 720 夜间主题下复验真实微信读书首页、四个恢复动作与恢复弹层，页面布局正常。浏览器日志缓冲仍保留首次误用不存在的 `circle-help` 深导入所产生的旧 HMR 错误；已按本地 `@lucide/vue 1.25.0` 改为实际存在的 `circle-question-mark`，随后生产构建与 fresh navigation 均通过。

### 未尽事项与已知问题

- 微信读书没有提供给本站使用的跨域登录 / 阅读进度接口；实验性 iframe 未来仍可能被第三方 CSP、Cookie 策略或页面改版阻断。
- 自动实时联动仍只适用于用户上传的本地书籍；微信读书路径只能由用户主动同步位置和可选摘录。
- 本轮没有改后端、数据、CI 或部署配置，没有 push 或发布。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 前端：`frontend/src/components/exploration/ExplorationReader.vue`、`frontend/src/stores/useExplorationStore.js`。
- 自动验证：`frontend/e2e/exploration-v5.spec.js`。
- 产品与工作流：`README.md`、`docs/product-spec-exploration-v4.md`、`docs/workflows/book-to-exploration.md`。
- 工作日志：`WORKLOG.md`。

## 2026-07-28 · 微信读书真实 Chrome 登录诊断

### 做了什么（结果）

在同一个真实 Chrome 配置中完成了顶层页与本站 iframe 的对照复现：顶层 `weread.qq.com` 已显示“继续阅读”和“我的书架”，确认 Chrome 账号本身登录正常；本站 `127.0.0.1` 内的跨站 iframe 仍显示未登录首页。扫码成功后，`open.weixin.qq.com` 的嵌套登录帧明确抛出 `SecurityError`，无法把 OAuth 回调导航到微信读书目标帧。顶层登录后重新载入 iframe，登录态仍未进入嵌入上下文。

### 关键决策与被否决的备选

- 当前失败由两层独立限制共同构成：现有 iframe sandbox 阻断嵌套 OAuth 导航；跨站 iframe 也没有继承微信读书顶层页的 Cookie / Storage 会话。不能再把它笼统归因于 Codex 沙箱。
- 否决添加 `allow-top-navigation` 或移除 sandbox 作为修复：它会允许第三方内容导航整个本站页面，仍不能解决顶层会话不进入第三方嵌入上下文的问题，也无法形成可自动验证的登录保证。
- 否决同源反向代理微信读书：它需要承接并改写第三方登录、Cookie 与页面内容，扩大为凭据代理，超出当前公开产品的安全边界。
- 普通公网网页的可行 P0 仍是微信读书第一方窗口 + 用户主动同步；若必须同时满足 Chrome 登录与实时联动，需要单独评估用户安装并授权的 Chrome companion extension，让微信读书保持顶层页面、本站分析进入 side panel。

### 当前状态：现在能跑什么、怎么跑

现有代码没有为了制造“已修复”而放宽安全限制；本次诊断没有改前端、后端、数据、CI 或部署配置。真实 Chrome 顶层微信读书可正常使用，普通网页 iframe 不能被本站保证为可登录状态。

### 未尽事项与已知问题

- 需要产品与权限边界决策：继续公共网页的独立窗口路径，或立项仅授权 `https://weread.qq.com/*` 的 Chrome companion extension。
- 扩展方案即使获批，也应默认只同步用户主动选择的 locator / 选区，不后台批量抓取书籍正文；商店发布与外部授权不在本次诊断范围。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 工作日志：`WORKLOG.md`。

## 2026-07-28 · 微信读书 Chrome Companion 本地 beta

### 做了什么（结果）

按 Rick 选择的 A 方案，把微信读书从不可靠的跨站 iframe 改为“顶层阅读 + Chrome Side Panel 分析”。新增 `extensions/weread-companion/` Manifest V3 扩展：微信读书继续在顶层页面正常登录，Side Panel 内打开 history-kb companion 模式；窄栏默认显示论证，并可切换时空与出处。

扩展只在用户点击“读取当前选区”时读取当前微信读书 HTTPS URL、页面标题、可读 locator 与最多 2,000 个 Unicode 字符，再经过“加入当前探索”二次确认才发送。主站接收器校验 companion query、父窗口 source、扩展 origin、版本、ID、URL 与长度；同 ID 并发或重放只产生一次 mutation，ACK 不带正文。公开示例只做本地临时联动，私人工作区写真实 revision；刷新只持久化 exploration ID，后端 GET 成功才恢复，404 清除失效 ID。

主站原有“在本站尝试嵌入 / 登录卡住 / 重新载入”入口已删除。微信读书 tab 只保留顶层打开与默认收起的手动位置同步兜底，避免继续把用户送进已证实无法保证登录的死路。

### 关键决策与被否决的备选

- 当前扩展是本地 beta，只连接 `127.0.0.1:5173`；没有保留一个注定等不到 ACK 的“线上”按钮。正式版必须先固定扩展 ID，再同时配置生产 allowlist 与 `frame-ancestors`。
- Manifest 权限只保留 `sidePanel` 和 `https://weread.qq.com/*`。否决 Cookie、webRequest、全站、剪贴板和后台全文权限；单域常驻内容脚本是减少重复点击的体验取舍，未来不得扩域。
- Side Panel iframe 有明确 sandbox，不能导航顶层；扩展 CSP 默认只允许自身代码和本地工作台 frame。
- 用户读取后切换状态或收到任何终态 ACK，立即清空选区 DOM、内存与 pending packet。扩展 storage 权限也因本地单入口不再需要而移除。
- 为避免两边各自绿灯却协议断裂，新增扩展生产者与网页消费者共用的 `contracts/weread-companion/v1-example.json` fixture。

### 当前状态：现在能跑什么、怎么跑

```bash
scripts/dev.sh
# Chrome 打开 chrome://extensions，开启开发者模式，
# “加载已解压的扩展程序”选择：
/Users/rick/ZCodeProject/history-kb/extensions/weread-companion
```

最终验证：

- `cd extensions/weread-companion && npm test`：12 passed；覆盖权限、CSP、sender、URL、Unicode 长度、终态清理与 ACK 白名单。
- `cd frontend && npm run test:e2e -- e2e/weread-companion.spec.js e2e/exploration-v5.spec.js`：9 passed / 35.4s；旧 iframe 入口缺席，手动桥仍写真实 revision。
- `cd frontend && npm run build`：218 modules / 4.66s；`ExplorationView` 48.23 kB / gzip 17.99 kB，无新增依赖；已有 `seed` / `maplibre-gl` 大 chunk warning 未变化。
- 真实 Chrome 以 420 × 800 窄栏复验 companion 页面，论证 / 时空 / 出处与地图均可见。浏览器自动化受安全策略限制，不能代替用户操作 `chrome://extensions`，因此 unpacked 安装仍需手动完成。

### 未尽事项与已知问题

- 当前没有发布扩展，也没有改 CI / 部署配置、push 或发布站点；现网仍是 v1.3.0 / 52b2f002。
- 公开发布前还需固定扩展 ID、生产 `VITE_WEREAD_COMPANION_ORIGIN`、精确 `frame-ancestors`、Chrome 实机安装复验、Web Store 隐私 / Limited Use 披露。
- 线上私人 Exploration 仍是无账户、单进程内存和随机 ID capability，只适合本地或受控 beta；正式多用户前需要账户与会话隔离。
- 用户维护的未跟踪根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 扩展：`extensions/weread-companion/`。
- 共享合同：`contracts/weread-companion/v1-example.json`。
- 前端桥与状态：`frontend/src/composables/useWereadCompanionBridge.js`、`frontend/src/stores/useExplorationStore.js`、`frontend/src/App.vue`。
- 前端界面：`frontend/src/views/ExplorationView.vue`、`frontend/src/components/exploration/ExplorationReader.vue`。
- 自动验证：`frontend/e2e/weread-companion.spec.js`、`frontend/e2e/exploration-v5.spec.js`。
- 产品与交接：`README.md`、`docs/product-spec-exploration-v4.md`、`docs/workflows/book-to-exploration.md`、`docs/design-qa.md`、`handoff.json`、`WORKLOG.md`。

## 2026-07-31 · 朋友分享入口与公网 Demo-only 安全门

### 做了什么（结果）

新增稳定可复制的安史之乱公开入口 `#route=explore&demo=anshi`，可继续携带 `scene` 直接恢复指定一幕。生产前端默认跳过 Prompt / 上传空态，直接打开公开 Demo；用户点击工作台“返回”也不会进入私人入口。EdgeOne 云函数同步不注册任何 `/explorations/*` 路由，手工构造 Prompt、TXT / Markdown / EPUB 导入、读取、编织、修改或删除请求都会落到 404。

### 关键决策与被否决的备选

- 采用前后端双门禁，而不是只把按钮藏起来：前端构建 marker 必须声明 `private_explorations_enabled=false`，打包器拒绝误开的产物；云函数入口强制关闭整组私人路由。
- 本地 `scripts/dev.sh` 与常规 E2E 显式开启私人能力，保留当前研究工作流；公开 Demo 不依赖私人 API，仍是纯静态原创衍生数据。
- URL 继续以 hash 参数承载，不引入新的前端路由依赖；`demo=anshi` 与既有 `scene`、`year`、主题参数兼容。

### 当前状态：现在能跑什么、怎么跑

```text
http://127.0.0.1:5173/#route=explore&demo=anshi
```

验证结果：后端 EdgeOne / build gate 定向测试 9 passed；常规探索 E2E 5 passed；demo-only 专项 E2E 1 passed；生产 `npm run build` 通过，产物 marker 为 `{"distribution_profile":"full","private_explorations_enabled":false}`，打包前校验通过。

### 未尽事项与已知问题

- 本轮没有提交、推送或发布，也没有修改 CI / EdgeOne 部署配置。
- 公网 Demo 仍只公开原创衍生摘要和受限锚点；原书正文、私人 locator 与本机文件不在分享链路中。
- 用户与其他 worker 已有的并行工作区改动保持原样，未纳入本支判断。

### 文件级变更清单

- 分享路由与前端门禁：`frontend/src/App.vue`、`frontend/src/config/distribution.js`、`frontend/src/stores/useUIStore.js`、`frontend/src/stores/useExplorationStore.js`。
- 后端门禁与发布校验：`backend/app/core/config.py`、`backend/app/main.py`、`cloud-functions/api/[[default]].py`、`frontend/vite.config.js`、`scripts/build_edgeone.py`。
- 本地与测试运行：`scripts/dev.sh`、`frontend/playwright.config.js`。
- 自动验证：`backend/tests/test_edgeone_build.py`、`backend/tests/test_edgeone_runtime.py`、`frontend/e2e/exploration.spec.js`、`frontend/e2e/public-demo-only.spec.js`。
- 工作日志：`WORKLOG.md`。

## 2026-07-31 · v1.4.0 朋友分享版最终收口与 GitHub 首发

### 未尽事项与已知问题

- EdgeOne 现网仍是 v1.3.0 / 52b2f002；本轮只交付公开 GitHub 源码，没有把未经再次授权的生产部署混入“分享”动作。因此朋友需要按 README 本地启动，不能把旧现网页面当作 v1.4.0。
- 公开层是《安史之乱》九幕原创衍生 Demo，不下发原书正文、私人 locator 或本机 EPUB。真实 LLM 编织仍只生成 `needs_model/not_called` 合同；无账户持久化、PDF/OCR 与正式 Chrome Companion 发布均未完成。
- 数据硬闸门保持 `errors=0`，但仍有 19,201 条公开可见的内容工程 warning：主要是 CBDB 自动关系说明薄弱、人物生平缺口、82 个孤儿实体与 1,613 条旧出处格式问题。没有为了收版删除、隐藏或降级这些 warning。
- 自托管 atlas / CHGIS 与上游 `external_data/` 不是同一分发层：公开仓库保留产品运行所需的现有产物与署名边界，可重建的上游原始包从 Git 跟踪中移除并在本机保留。公开源码不构成对第三方素材的重新许可。

### 做了什么（结果）

把当前工作台收成可直接给朋友使用的 v1.4.0：稳定入口为 `#route=explore&demo=anshi`；生产前端直接进入公开 Demo，生产后端完全不注册 Prompt、上传、私人 Exploration 读写接口。本地 `scripts/dev.sh` 仍开放私人研究流程，两条能力边界不再靠隐藏按钮区分。

移动端补齐阅读、论证、时空、证据四个工作面，问题工作区末栏仍使用范围；切换工作区会恢复合理默认页。公开论证节点回到来源后会展开章节级定位、原创衍生摘要、核心论点与“原文未公开”边界，复制只含公开章节定位。地图保持九幕全览、顺序与非行军路线语义，桌面和移动端均可继续聚焦与播放。

发布前同时清理了两个明显风险：旧依赖中的 PostCSS / Vite / esbuild advisory 通过升级到 Vite 6.4.3 等兼容版本清零；旧 Git 历史中的两个超过 GitHub 100 MB 的上游原始包不进入公开首发历史。公开仓库使用当前已验收树的单一干净根提交，避免把本机原始包和旧历史一起上传。

### 关键决策与被否决的备选

- 公开能力采用前后端双门禁，并把 `private_explorations_enabled=false` 写入构建 marker；否决只隐藏按钮，因为手工请求仍会暴露无账户隔离的私人 API。
- 采用稳定 hash URL 与已有数据合同；否决为单个 Demo 引入新路由依赖或第二套状态源。
- 公开锚点提供可访问的章节级说明但不提供打码正文；否决在浏览器中下发正文后再视觉遮挡，因为那并不构成内容边界。
- GitHub 采用当前树的干净根历史，保留本地 main 的完整开发历史；否决直接推送含 577 MB SQLite 与 137 MB zip 的旧历史，也没有删除本机原始资料。
- 没有把“GitHub 分享”擅自扩展为 EdgeOne 发布；生产部署仍需单独授权和线上复验。

### 当前状态：现在能跑什么、怎么跑

```bash
git clone https://github.com/Longwind1984/historian.git
cd historian
scripts/dev.sh
# 打开 http://127.0.0.1:5173/#route=explore&demo=anshi
```

生产构建默认是 demo-only；本地脚本会显式开放 Prompt 与书籍导入。公开仓库不包含 `external_data/` 上游原始包，仓库内构建与运行所需资产仍在当前树中。

### 最终验证

- 后端：`223 passed + 1 skipped / 11.50s`。
- 数据：`7,396 entities / 10,277 relations / errors=0 / warnings=19,201 / 8.37s`。
- 全站 E2E：`123 passed + 2 skipped / 12.5m`；生产 demo-only 专项 `1/1`；safe profile 专项 `1/1`。
- Chrome Companion：Node 合同 `12/12`。
- 依赖：`npm audit` 为 `0 vulnerabilities`。
- 生产构建：Vite 6.4.3，`220 modules / 1.72s`；full EdgeOne `5,129 files / 134.30 MB`；safe `88 files / 5.42 MB / atlas 0`。只有既有 seed 与 MapLibre 懒加载大块提示。
- 浏览器：一体化服务下桌面与 390×844 移动阅读、论证、证据三态无横向溢出；API 与地图瓦片均返回 200，console error/warning=0。纯静态 Vite preview 不模拟 EdgeOne 函数，故不把其缺后端的 500 作为产品运行结果。
- Git / 文档：JSON 解析、`git diff --check`、公开树超大文件与常见凭据特征扫描均通过；用户未跟踪的根 `AGENTS.md` 保持不动。

### 文件级变更清单

- 公开门禁与运行配置：`backend/app/core/config.py`、`backend/app/main.py`、`cloud-functions/api/[[default]].py`、`frontend/src/config/distribution.js`、`frontend/vite.config.js`、`scripts/build_edgeone.py`、`scripts/dev.sh`。
- 分享入口与探索体验：`frontend/src/App.vue`、`frontend/src/stores/useUIStore.js`、`frontend/src/stores/useExplorationStore.js`、`frontend/src/views/ExplorationView.vue`、`frontend/src/components/exploration/ExplorationReader.vue`。
- 自动验证：`backend/tests/test_edgeone_build.py`、`backend/tests/test_edgeone_runtime.py`、`frontend/playwright.config.js`、`frontend/e2e/exploration.spec.js`、`frontend/e2e/exploration-argument-graph.spec.js`、`frontend/e2e/public-demo-only.spec.js`。
- 版本与依赖：`package.json`、`frontend/package.json`、`frontend/package-lock.json`。
- 公开仓库边界：`.gitignore` 与已停止跟踪但仍保留本机的 `external_data/`。
- 常新文档：`README.md`、`handoff.json`、`WORKLOG.md`。
