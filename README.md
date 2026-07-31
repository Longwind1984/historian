# 互动中国历史知识库 · history-kb

> 把断代的中国历史数据变成**可切片、可追溯**的探索工具：**地图 × 时间轴 × 关系图**三视图联动，
> 覆盖前 2100（大禹）→ 2026，共 7,396 实体 / 10,277 关系；实体逐条带来源，批量关系可追溯到导入数据集。

> ⚠️ 本作品为个人研究 / 学习用途，内容仅供历史探索，不代表权威史料定论。实体数据均附史料出处，
> 以正史（二十四史、资治通鉴、续资治通鉴长编）为基础，辅以现代学术研究及结构化数据库（CBDB / CHGIS）；
> 具体日期、人物关系可能存在史源差异，标注「约」或留空处请以正史为准。

---

## 给朋友试玩

当前可分享版本以《安史之乱：历史、宣传与神话》的**原创衍生分析**为公开 Demo：九幕时间脉络、论证图、地图全览 / 聚焦、历史参照轴和关系化证据可以完整联动，但不下发原书正文、私人定位或本机文件。稳定入口为：

```text
http://127.0.0.1:5173/#route=explore&demo=anshi
```

```bash
git clone https://github.com/Longwind1984/historian.git
cd historian/frontend && npm ci
cd .. && scripts/dev.sh
```

首次运行需要 Node 18+、Python 3.11+ 与 [`uv`](https://docs.astral.sh/uv/)；`scripts/dev.sh` 会用 `uv` 按仓库锁定的 requirements 启动隔离后端，不会借用父目录环境。

公开构建默认直接进入 Demo，并关闭 Prompt、私人书籍上传与进程内探索会话；本地 `scripts/dev.sh` 保留这些私人研究能力。Chrome Companion 仍是本地 beta，需要手动加载 `extensions/weread-companion/`，不应当作朋友首次试玩的前置步骤。

`history.ricksi.com` 目前仍是较早的 v1.3.0 正式站，不包含本轮探索模块；在另行确认 EdgeOne 发布前，请分享 GitHub 与本地入口，不要把旧线上站当成本版本验收地址。

> 仓库公开不等于授予一揽子再许可。代码、结构化数据、图片、地图与第三方数据分别沿用各自来源及权利条件；`external_data/` 中可重建的 CBDB / CHGIS 上游原始包不进入公开仓库，运行所需的是 `data/` 下已经处理并带来源的信息。若需要再分发、商业使用或二次托管地图资源，请逐项核对来源条款。

---

## 产品判断

**要解决的问题**：史料断代、散落在正史与学术数据库里，普通人很难「给定一个年份，看当时谁在世、谁和谁有什么关系、版图长什么样」。本项目把人物 / 政权 / 事件 / 战役 / 地点等结构化成一张**带时间维度**的关系网，用三视图联动切片探索；实体逐条记录来源，CBDB 等批量关系按数据集追溯。

**关键 tradeoff · YAML + 内存索引 vs 图数据库**：选前者。7k 实体规模下，后端启动时构建 id / type / 年份 / 邻接索引，常用实体与年份查询为 O(1) / O(log N)，够用；而 `data/**/*.yaml` 既是数据本源又是可读真相源，`git diff` 即审稿，无需运维一个数据库。代价是数据量再上一个数量级时需要重新评估存储方案。

**被否决的方案 · Neo4j**：项目早期含一条 Neo4j 图数据库路径，但**从未被实测**，查询长期走内存索引 fallback，属死重。已移除其全部代码、依赖与导入脚本，决策与恢复路径见 `docs/decisions.md`（ADR-001）。

**交互取舍 · 显式选择优先**：悬停只做时间柱、在世人物与图谱之间的视觉互高亮，右侧档案必须点击或键盘激活后才切换，避免高密度图面里掠过即误换。低频的时间尺度、人物类型和地图图层默认折叠；重点人物、当前尺度与地图展开仍留在外层。配色只保留「澄 / 夜」，默认跟随系统深浅色，缺少系统能力时按本地 06:00 / 18:00 近似日夜切换。

**地图叙事取舍 · 可定位才播放**：地图放大为主体后可按年代播放事件与关键人物生平节点，镜头、左时间轴和档案共用同一状态。事件必须已有 `location` 或完整 `march`；人物生平节点只有在“人物与可定位事件有结构化关系、同年、且生平文本明确写出完整事件名”三项同时成立时才借该事件定位。没有地点的生平不拿出生地、籍贯或文本猜坐标。

**历史探索取舍 · 先保真，再编织**：本地开发的 `探索` 路由从真实空状态开始。用户可以直接提出一段历史问题，确认时间、空间与叙事主线；也可以上传私人 TXT / Markdown / EPUB，建立章节、段落锚点与连续阅读进度。阅读、论证链、Scene、地图与关系化证据共享同一工作台。私人正文只保存在有界后端进程内，重启即清除；Prompt 和分析请求目前只建立范围或排队，不调用模型。公开构建则默认进入受限 Demo，不开放这套无账户隔离的私人会话。没有可靠时间、地点或关系时，界面保持“尚未结构化”，不会沿用公开 Demo 的时空、论点或作者判断。正式 YAML / GeoJSON 仍是只读底座，探索层不会自动写回。

**外部阅读取舍 · 第一方阅读，主动桥接**：微信读书不再嵌入 history-kb。它保持为 Chrome 顶层、正常登录的第一方页面；本地 Companion Extension 在 Side Panel 打开探索工作台。扩展只有在用户点击“读取当前选区”时才读取当前标题、URL、定位与最多 2,000 字选区，再经“加入当前探索”二次确认写入当前 revision。它不读取 Cookie、书架或后台全文。当前交付是仅连接 `127.0.0.1:5173` 的 unpacked 本地 beta；线上版必须先固定扩展 ID、配置精确 origin 白名单与 `frame-ancestors`，并完成隐私披露。

**实体唯一性 · 高置信合并**：同一历史人物或事件只保留一个实体。证据足以闭合身份时，优先保留已有关系引用的稳定 ID，把另一份的独有字段、来源和外部标识合入并迁移引用；名字相似但证据不足，或字段存在史实冲突时不自动合并。

---

## 架构

```
浏览器
  Vue 3 + Vite
  ├── MapLibre GL    · 疆域 / 地点地图
  ├── d3-force + Canvas · 2D 关系图
  ├── 时间轴          · 年份切片（在世人物 + 疆域）
  ├── 历史探索        · Prompt / EPUB / 阅读 / 论证 / Scene / 证据
  └── Pinia           · 状态 / 跨视图联动
        │  REST + JSON（vite 代理 /api → 127.0.0.1:8000）
        ▼
FastAPI 后端 (:8000)
  ├── api/            · 薄路由（参数校验 + 调 service）
  ├── services/       · entity / graph / territory / timeline / exploration
  ├── exploration     · Prompt 范围与私人文本的有界进程内会话（非持久化）
  └── core/data.py    · 启动时构建内存索引（EntityIndex + RelationIndex）
        │  查询 O(1) / O(log N)，无外部数据库
        ▼
唯一真相源
  data/**/*.yaml      · 实体 + 关系（关系带 since / until）
  data/geo/*.geojson  · 各朝代疆域多边形
  schema/*.yaml       · 类型注册表（通用元数据数据驱动；专属交互仍需代码）
```

前端 API 客户端统一使用浏览器原生 `fetch`，不再携带 Axios 运行依赖。

---

## Quick start

线上正式地址：<https://history.ricksi.com/>。当前正式版本为 **v1.3.0 / 52b2f002**，EdgeOne Production 部署 `dpmr9bplyfcq` 于 2026-07-23 完成。生产环境采用 EdgeOne Pages 混合部署：Vue 静态前端与地图瓦片由边缘节点分发，`/api/*` 由 EdgeOne 云函数运行 FastAPI 兼容入口；数据编译为只读 JSON 随部署发布，不依赖常驻服务器或外部数据库。默认完整构建入口为仓库根目录的 `npm run build`，EdgeOne 配置见 `edgeone.json`，产物写入 `edgeone-dist/`。

公开再分发许可尚未书面确认时，可运行 `npm run build:safe` 生成独立的 `edgeone-dist-safe/`：该 profile 不打包 `chgis_*.geojson` 或 5,023 张谭图镜像瓦片，界面不提供“古”底图，也不会请求 `/tiles/atlas/*`；实体中已有的历史来源标识与固定署名仍保留。前端构建会写入 profile 标记，Python 打包器双向拒绝 full/safe 错配。根 `edgeone.json` 仍是完整构建配置；安全版只按“预构建成品直接上传”使用，平台是否支持从源码选择多 profile 尚需单独核验。本仓库只生成成品，不自动发布。

Rick 于 2026-07-23 明确选择继续以完整版本作为非商业个人研究与作品展示，并要求发布到 Production；v1.3.0 full 已上线。仓库仍未核实到 CHGIS 与谭图瓦片的单独书面公网再分发授权，因此这是站点所有者接受现状后的发布决定，不是“已经取得授权”的证明。来源弹层、固定署名、数据变换说明与 safe profile 均继续保留；若使用范围、运营主体或商业属性变化，应重新核验许可并可随时切换为 safe 产物。

当前站点版本由根 `package.json` 统一管理；构建时把版本、Git revision 与 UTC 时间写入 `/release.json`，右上角 `!` 的来源弹层显示同一版本号。Rick 的本机已安装 `release-history-kb` Skill，可用一条命令完成版本递增、Python 3.12 数据校验、Vite 构建、完整 EdgeOne 成品打包与结构检查：

```bash
python3 ~/.codex/skills/release-history-kb/scripts/release.py prepare --bump patch --profile full
python3 ~/.codex/skills/release-history-kb/scripts/release.py deploy --env preview --profile full
# 当前任务已明确确认正式发布后：
python3 ~/.codex/skills/release-history-kb/scripts/release.py deploy --env production --profile full --confirm-production
python3 ~/.codex/skills/release-history-kb/scripts/release.py verify --base-url https://history.ricksi.com/ --profile full
```

这条管线直接上传已经构建好的 `edgeone-dist/`，不会在云端重复编译 134 MB 产物；静态 hash 资源继续长期缓存，`release.json` 明确禁用长期缓存，便于部署后确认 CDN 已切换版本。中高风险改动先发 preview；Skill 默认拒绝未经明确确认的生产发布，并在构建失败时恢复版本文件。

> 命令均在**仓库根目录**执行。后端需 Python 3.11+（Docker / 推荐环境为 3.12），前端需 Node 18+。

### 一键启动（推荐）

```bash
scripts/dev.sh                 # 同时拉起后端 :8000 + 前端 :5173，Ctrl-C 一次全停
```

`dev.sh` 默认检查 8000 / 5173 端口，被占则报错退出。后端依次使用 `backend/.venv`、仓库根 `.venv`，都不存在时由 `uv` 严格按 `backend/requirements.txt` 启动隔离环境；绝不借父项目 venv。路径仍可用 `VENV_PATH` 显式覆盖，数据 / schema 可用 `DATA_DIR` / `SCHEMA_DIR` 覆盖。也支持 `--backend-only` / `--frontend-only`。

历史探索入口：<http://127.0.0.1:5173/#route=explore>。默认页以一个历史问题输入区为主；“上传本地书籍”是同一区域内始终可见的次级动作，打开专用弹层后支持 EPUB / TXT / Markdown，不再与对话路径割裂成两张等权卡片。进入工作台后，桌面端可确认 Prompt 范围、连续阅读、联动段落锚点，并分别拖动 Brief / 论证 / 地图的纵向边界；移动端仍以阅读、Scene 与出处为主，不提供复杂导入和编排。

微信读书本地伴读扩展位于 `extensions/weread-companion/`。先启动 `scripts/dev.sh`，再在 Chrome 的 `chrome://extensions` 开启开发者模式并“加载已解压的扩展程序”，选择该目录；打开微信读书任意阅读页后，点击扩展图标即可在 Side Panel 使用。完整安装、权限和协议边界见 [`extensions/weread-companion/README.md`](extensions/weread-companion/README.md)。

### 后端（手动）

```bash
scripts/run-backend.sh --host 127.0.0.1 --port 8000 --reload
```

脚本会设置本地数据路径并选择仓库虚拟环境；没有可用虚拟环境时，回退到 `uv` + `backend/requirements.txt`。若绕过脚本直接执行 Uvicorn，必须显式设置 `DATA_DIR` / `SCHEMA_DIR`，否则容器默认路径 `/app/data` 会让本地 API 静默为空。API 文档：<http://127.0.0.1:8000/docs>。

### 前端（手动）

```bash
cd frontend
npm ci
npm run dev      # → http://localhost:5173，vite 自动代理 /api → 127.0.0.1:8000
                 # 未检测到后端时按上述仓库内环境顺序自动拉起，关停随动不残留
```

### 验证后端起来了

```bash
curl http://127.0.0.1:8000/api/meta/stats
# {"entity_count":7396,"relation_count":10277,"entities_by_type":{"Battle":41,"Dynasty":19,"Event":210,"Faction":26,"Person":5627,"Place":1389,"Polity":84}}
```

<details>
<summary>容器化（可选）</summary>

容器部署已定稿并建立本地提交 `9b5b38f`（未 push / 未发布）：运行 `scripts/up.sh` 会选择 `docker compose` 或 legacy `docker-compose`，构建生产镜像并启动 backend(:8000) + frontend(:8080)。前端用 Node 22 严格按 lockfile 执行 `npm ci`，由 Nginx 同源代理 `/api` 与 `/tiles`；后端镜像不挂源码、不启用 reload，只读挂载 `data/` / `schema/`，健康检查通过后才启动前端。脚本用有界、失败即退出的真实 HTTP smoke 核对 stats / schema / entities / API 代理 / PNG 瓦片。

当前机器 Docker CLI 29.6.1 / server 29.5.2 可用，但没有 Compose plugin、legacy `docker-compose` 或 buildx；`scripts/up.sh` 会对此清晰报错。定稿时已用等价的隔离 network + 独立 backend/frontend 容器拓扑完成真实 build/run：后端返回 7,396 实体 / 10,266 关系，schema/entities、Nginx 配置、同源 API 与瓦片 PNG 均通过，临时容器、镜像和网络已清理。日常开发仍可使用上面的本地方式。
</details>

---

## 质量工具

| 工具 | 命令 | 说明 |
|---|---|---|
| 后端单测 | `uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q` | 223 项通过、1 项按预期跳过；测试依赖精确锁定，`conftest.py` 自动设数据路径 |
| 数据校验 | `uv run --with-requirements backend/requirements.txt python scripts/validate_data.py` | 全量实体 / 关系一致性 + 年份硬伤检查（errors=0 基线）；`--json out.json` 可导出结构化报告 |
| 前端 E2E | `cd frontend && npm run test:e2e` | v1.4.0 full profile 123 项通过、2 项按条件跳过；公开 demo-only 与 safe profile 另各 1/1 通过；Playwright 以 :8002 / :5174 冷启动隔离前后端，不复用陈旧进程；结束自动回收 |
| 安全分发 | `npm run build:safe`；`cd frontend && VITE_RESTRICTED_MAPS=0 npm run test:e2e -- safe-distribution.spec.js` | 生成 `edgeone-dist-safe/`；safe profile 专项 1/1 通过，同时验证时间柱与书籍探索均无受限地图入口、CHGIS 几何或谭图请求 |

---

## 谱系星图

- **图谱**：2D 力导向网（Obsidian Graph 范式），支持单击进局部、双击换中心、最短路查询。
- **星云**：3D 星空，星=实体、色=朝代、径=双链度，深空 bloom 与纸墨两态共用一套朝代色板。
- **时空柱**：3D 光丝柱，Z=时间、XY=方位，扫描环联动年份。详见 `docs/starmap-redesign.md`。

性能边界：默认 2D 图谱只加载不依赖 Three 的纯数据色板；Three 与其颜色适配仅在首次进入星云或时空柱时按需加载。若装配尚未完成就切走，晚到的 WebGL 控制器、Worker、动画帧、观察器与监听器会立即完整回收，不在已卸载页面继续运行。

## 时间柱

左栏是主坐标系：纵轴即时间；工具组默认显示「帝王」尺度，展开后可在 **朝代 / 帝王 / 编年 / 月 / 日** 五档间切换（0.42 → 2922 px/年）。
一条固定的锚定横线定义「此刻」，右栏的疆域图与在世人物名单永远与它同步。

移动端（≤720px）采用已经定稿的「时间柱主屏 + 底部地图抽屉」：时间柱继续占首屏主位，
抽屉保留此刻读数、真实 MapLibre 年代地图与在世人物，可点击把手、上下拖拽，也可用
ArrowUp/ArrowDown、Home/End 展开或收起。移动地图默认保持当年中国概览，不会被默认选中的
人物带离时间语境；收起首屏只加载读数摘要，约 891.5 kB 的 MapLibre 地图产物到首次主动展开时
才请求，之后收起再展开复用同一实例。桌面仍使用原双栏与可拖分栏，并立即显示地图。

- **点选即锚定**：点任一事件卡或人物条，轴整体滑动把它送到锚线上，右栏随之切年。
- **地图历史播放**：把地图放大为主体后出现播放 / 暂停 / 上一条 / 下一条；每条会聚焦已有地点或行军路线，左轴同步到同年，浮窗展示事件简介与来源。手动拖图或收起地图会暂停，当前卡仍保留。
- **月/日档**：同年不同月的事件按月分离摆放；1912 前的月份是史料原载农历，未换算成公历，
  界面上以中文月名与常驻注记标明——位置是近似，标签是原载，两者的差别不藏着。
- **不出逐日刻度**：农历月长 29/30 不等且置闰，一把等分尺画到日就是在宣称它撑不起的精确。

## 数据模型

**节点类型**——通用字段、搜索元数据与注册表由 `schema/` 驱动；新增类型会被后端识别，但若需要专属时间锚、地图定位、颜色或 3D 呈现，仍须补对应代码：

| 类型 | 含义 |
|---|---|
| Person 人物 | 帝王、将相、文士…（含 CBDB 4,892 人）|
| Polity 政权 | 五代十国及历代政权 |
| Faction 派系 | 沙陀集团、河朔三镇、南唐党争等非国家集体行动者 |
| Event 事件 | 政治 / 制度 / 文化事件 |
| Battle 战役 | 军事冲突 |
| Place 地点 | 都城、战场、籍贯（含 CBDB 1,005 地址）|
| Dynasty 朝代 | 夏→清大朝代（19）|

> 另有 `Title 官职 / 封号` 已在 schema 声明，数据尚未填充。

**时间感知关系**：关系可携带 `since` / `until` 时间区间，支持「947 年时谁是谁的什么」这类切片查询；没有可靠年代时不虚构区间。关系 `type` 为自由字符串，建议在 `schema/relations.yaml` 注册以便文档化与 UI 样式。

**扩展机制**：每个节点类型默认 `ext: allow`，可挂任意键值实验字段，成熟后再提升为正式 schema 字段。类型注册表与字段类型说明见 `schema/_registry.md`。

---

## 数据来源与规模

| 数据源 | 用途 | 规模 |
|---|---|---|
| 二十四史 + 资治通鉴 + 续资治通鉴长编等 | 非 CBDB curated 数据 | 1,499 实体 / 1,223 关系 |
| CBDB China Biographical Database (Harvard) | 人物 / 亲属 / 社交 / 官职 / 籍贯 | +5,897 实体（4,892 人 + 1,005 地）/ +9,031 关系 |
| CHGIS China Historical GIS (Harvard + 复旦) | 历代府级行政建置记录 | 18 文件 / 3,062 条按年中性展示的记录；另有 16 个手工 peak 文件用于政权疆域 |
| 谭其骧《中国历史地图集》（OSGeo 中国站配准瓦片） | 「古」底图按年换幅 | 年代表 28 幅 / 自托管 z2–z6（29 目录、5,023 PNG） |

合计 **7,396 实体 / 10,277 关系**，跨度**前 2100（大禹）→ 2026**。非 CBDB 人物 735 人全部可上时间轴，
帝王 261 人分属 47 政权（十大一统朝代在位链连续）；事件 + 战役 251 条，分 5 族 18 类。
完整构建日志与可重现数据管线见 `PROGRESS.md`。

**时间锚按确定度递降**——不确定的年代不伪装成确定的：

| 形态 | 示例 | 含义 |
|---|---|---|
| `前551–前479` | 孔丘 | 生卒确凿 |
| `约前536–前448` | 范蠡 | 有通说但存异说（`ext.disputed`）|
| `活跃前1250–前1192` | 妇好 | 生卒不可考，只记见于史载的活动区间（`floruit_*`）|
| `在位前685–前643` | 齐桓公 | 上古君主多不记生卒，只有在位年 |
| `?–前257` | 白起 | 卒年已知、生年确不可考 —— 不虚构起点 |
| `1930–` | 屠呦呦 | 在世 |

模糊纪年在轴上两端渐隐、名字斜体、不画生卒点 —— 推估的年代不该看起来跟确凿的一样。

---

## Roadmap

v3.0「看得清」（时间柱可读性 + 古地图补全，M7–M10）已落地：见 `docs/roadmap-v3.md`。

v3.1「看得细」（M11–M13）已落地，见 `WORKLOG.md` 2026-07-20 段：

- **M11 点选即锚定**——点柱上任一事件/人物，时间轴整体滑动把它送到锚定横线上，
  右侧疆域图与在世名单同步到那一年（锚线不动、轴动）。
- **M12 粒度下探到月/日**——缩放档由三级扩到五级（朝代/帝王/编年/月/日）。同年不同月的
  事件第一次能分开摆放。历法口径按 1912 分野：此前为史料原载农历（不换算，中文月名「十二月」），
  此后为公历（阿拉伯数字「7月7日」），亚年档常驻一行口径注记。
- **M13 真实图像与延伸阅读**——736 位种子人物中保留 439 位已有、许可与作者链完整的
  Wikidata/Commons 历史画像；当前 711 位写入 Wikidata QID，705 位写入中文维基条目。
  9 例官方实体级人工消歧已全部收口（0 AMBIG / 25 NONE）。本轮只补 QID 与中文条目；
  新发现的 P18 因缺 Commons 许可与作者链，未新增图片。
  流水线见 `scripts/align_wikidata.py`，对账物在 `data/_align/`。

v5「探索」已补齐正常产品入口：默认不假定已有书籍；Prompt 会真实建立可继续编辑的范围合同，TXT / Markdown / EPUB 会进入独立导入合同并生成可定位段落。桌面工作台包含可调三栏、连续正文 / 锚点 / 时间·事件柱 / 微信读书来源、可展开并回跳来源的论证节点、MapLibre Scene 地图、地图内次级播放，以及 `+ / 输入 / 发送` composer；移动端只承担阅读、Scene 与出处。阅读点击和滚动会以串行 revision 同步进度，避免并发覆盖；EPUB 阅读器只挂载当前章节，避免全书 DOM 线性增长。微信读书跨站 iframe 已被否决：同一 Chrome 的顶层页面能登录，不代表第三方 iframe 能共享 Cookie / Storage，OAuth 回调还可能被 sandbox 拦截。当前可靠路径是 Chrome Companion Extension：微信读书保持顶层页面，history-kb 在 Side Panel 以“论证 / 时空 / 出处”三视图运行；扩展经两次主动操作读取并提交不超过 2,000 字的当前选区。主站仍保留默认收起的手动位置同步作为无扩展兜底。

公开示例现为《安史之乱：历史、宣传与神话》：九幕原创衍生分析联动论证、阅读定位、时间、地图、证据与播放；地图默认以“全览”同时显示 7 个有可靠坐标的 Scene、9 幕顺序和连续柔性叙事曲线，另外 2 幕明确标为未定位，点选节点后才进入聚焦。曲线只表示叙事先后，不声称行军路线。左栏时间 tab 是 755—763 的纵向双轨：主轨为书中 Scene，参照轨只引入仓库已有明确年份字段的事件、人物与帝王，点击参照项会同步现有时间和实体选择。每幕论证不再压成四张概括卡，而是“问题 / 材料观察 / 推理机制 / 行动或转折 / 后果 / 限制”六类可寻址节点和显式关系；后端已建立来源 locator、认识论层级、禁止强造反方与禁止猜地点/因果的模型 Prompt 合同，但仍不实际调用模型。公开代码不包含本机 EPUB、正文、私有路径或可逆推出原文的定位。界面把“最多 10 页”作为待权利审查的产品窗口，而不是法律安全线；当前通过审查的公开正文为 0 页，所有回跳均落在稳定的受限锚点。当前仍不做账户级持久化、不解析 PDF / OCR，也不公开导出私人原书；完整边界与复用合同见 `docs/product-spec-exploration-v4.md` 和 `docs/workflows/book-to-exploration.md`。

### 文档索引

| 文档 | 讲什么 |
|---|---|
| `docs/roadmap-v3.md` | v3.0 方案与验收（M7 人物区 / M8 事件溢出 / M9 图集 / M10 收版，已落地） |
| `docs/roadmap-v2.md` | v2 迭代方向（历史文档） |
| `docs/decisions.md` | 架构决策记录（ADR），含被否决的方案与理由 |
| `docs/content-spec.md` | 内容规范：note / life_events / impact / sources 怎么写 |
| `docs/data-dictionary.md` | 数据字典：实体与字段的含义 |
| `docs/starmap-redesign.md` | 谱系星图/时空柱的设计 |
| `docs/product-spec-exploration-v4.md` | v4「探索」Product Spec、交互状态、书籍接入、地图生产方案与开发标注 |
| `docs/workflows/book-to-exploration.md` | v5 Prompt / 私人书籍到可复核时空探索的执行流程、隐私边界与验收矩阵 |
| `docs/workflows/book-to-exploration.schema.json` | 可暂停、可复核、可做公开投影的 Exploration Artifact 合同 |
| `extensions/weread-companion/README.md` | Chrome Side Panel 本地伴读扩展的安装、权限、消息协议与发布闸门 |
| `docs/design-qa.md` | 高密度界面 8 项优化的同视口视觉验收与证据 |
| `docs/march-routes.md` | **进军箭头专项**：军事族 111 条事件里哪些该画箭头、哪些不该，怎么写；当前总计 16 个实体 / 20 段，其中 15 个属于军事候选池 |
| `WORKLOG.md` | 会话日志（append-only），每轮做了什么、否决了什么、还欠什么 |

## License

本项目仅用于个人研究、学习与作品展示，不用于商业用途，也不构成权威史料。实体逐条附出处，批量关系按数据集追溯；具体日期与人物关系可能存在史源差异。

感谢并署名以下资源：CBDB China Biographical Database、CHGIS China Historical GIS、OSGeo 中国站配准的谭其骧《中国历史地图集》瓦片，以及 Vue、Vite、FastAPI、MapLibre、Wikimedia Commons 等开源软件与公共内容。CBDB 派生数据遵循其非商业、署名与相同方式共享要求；CHGIS 使用固定署名 “CHGIS Version 5. © Fairbank Center for Chinese Studies and the Institute for Chinese Historical Geography at Fudan University, Jan 2012.”，完整构建只按年份展示经筛选并去除误导性政权字段的记录。各地图、图片与软件仍分别受其原始许可约束，署名不替代再分发授权；当前 full Production 是站点所有者明确作出的非商业个人展示决定，safe profile 仍作为可逆替代方案保留。应用右上角 `!` 可随时查看完整来源与致谢。
