# 2026-07-27｜v5 拆书到历史探索 workflow checkpoint

## 已完成

- 新增 `docs/workflows/book-to-exploration.md`：Prompt / 书籍双入口、研究范围、章节 / 来源锚点、作者论点、事实候选、时空实体、Scene、证据关系、反证 / 缺口、人工复核和公开投影的连续工作流。
- 新增 Draft 2020-12 JSON Schema，强制区分 `source_statement / author_judgment / platform_inference / external_evidence`。
- 用本机私有《红太阳》EPUB 做只读验证，记录 15 章、76 小节、30 内容单元、487,694 去空白可见字符、3,428 段落标签；未记录文件路径、UUID、正文、长引文或段落内容。
- 把私有验证推进到 `analysis_proposed`：
  - 5 个章节级 `author_judgment`；
  - 1 个明确不是作者明示模型的 `platform_inference`；
  - 5 个 pending fact candidates；
  - 9 个人物 / 地点候选、5 个时间引用、4 个地点引用；
  - 5 个 pending Scene；
  - 9 条 pending 证据关系；
  - 9 个开放缺口。
- 更新产品规格 v5 章节，明确当前生产能力、目标工作流、版权 / 隐私、公开衍生分析与微信读书状态。

## 关键判断

- 章节级 locator 足以做首个深度结构 Demo，但不足以进入 `evidence_audited`：段落 CFI、独立来源和反证检索仍是阻塞项。
- 接受 `author_judgment` 只表示忠实表达作者，不表示平台接受其历史结论。
- 五条主线来自章节级作者论证摘要；把它们编成连续 Scene 是平台提议，不能伪装成作者明示的五阶段模型。
- 没有反证材料时记录 `counterevidence_not_found`，不机械补正反观点。
- 私人 EPUB 不入库；公开投影默认不带引文、原文、私有 locator、路径、凭据或可重构原书的连续摘要。
- 微信读书 iframe 只可能是预览；跨域 DOM / 选区读取固定为 false，登录、禁嵌与手动进度桥接分别建状态。

## Skill / workflow 取舍

用户允许沉淀为 Skill 或 workflow。本轮选择把 workflow + Schema 直接版本化在仓库，因为它与当前 Exploration 数据合同、发布检查和人工复核状态紧密耦合，外部用户和后续 Agent 都能随项目演进共同读取。`skill-creator` 的标准脚手架在当前运行时没有提供可执行初始化脚本，因此没有手写一份无法自证导入合同的全局 Skill；若后续第二个仓库需要复用，再从这份已验证 workflow 提炼为独立 Skill。

## 验证

- `python3 -m json.tool`：Schema 与私有验证 JSON 均通过。
- 本机 `jsonschema 4.25.1`：
  - `Draft202012Validator.check_schema` 通过；
  - 私有 artifact 验证通过；
  - Prompt 最小前向 fixture 验证通过；
  - `publishable_derivative` 带非 pass release check 的负例被正确拒绝。
- 自定义结构自检通过：
  - 90 个对象 ID / 跨对象引用无重复、无悬空；
  - Claim 恰为 5 个 `author_judgment` + 1 个 `platform_inference`；
  - Claim / fact / Scene / relation 全部 `pending_review`；
  - 无 excerpt、`/Users/`、`file://`、HTML 正文、Cookie 或下载站文件名进入 artifact。

## 当前边界与下一步

- Prompt 与本地 EPUB resolver 已进入生产切片；真实 LLM、持久化和段落 CFI 仍未实现。
- 下一工程步应补段落 CFI 与按章按需服务，再按章节批次接入模型；不能先生成全书巨图。
- 进入外部核对前，需要独立来源检索、权利记录、超时 / checkpoint 和 Claim 级关系分类。
- 正式知识库晋升仍是另一条人工流程，不由本 workflow 直接改 YAML / GeoJSON。

## 前向测试缺口修复

二次最小上下文测试发现并修复五类合同缺口：

1. `research_scope.allowed_source_sets` 成为确认范围的必填项；
2. Prompt 路径增加 `source_packets` 分组对象，包含目的、来源、锚点和状态；
3. `input.mode=none / prompt / book` 使用 `oneOf` 互斥，Prompt 不得带 `book_ref`，book 不得带 Prompt；
4. 生命周期强制 scope 状态，并禁止 Prompt 出现 book chapters、禁止 book 出现 source packets；进入 `structure_indexed` 后分别要求至少一个来源包或章节；
5. release checks 改为 `pass / fail / unknown / not_applicable`，只有全部 pass 才允许公开衍生。

同时补充：

- `prompt_send_policy` 与 `model_send_policy` 分离：前者管理用户 Prompt，后者只管理书籍片段和外部来源材料；
- gap 新增 `target_type`；跨引用校验必须证明 `target_id` 存在于声明的合法对象集合。

复验结果：

- 正例通过：私人 `analysis_proposed`、empty、Prompt `scope_confirmed`、Prompt `structure_indexed + source_packets`、全部发布检查 pass 的公开衍生；
- Schema 负例通过：Prompt 携带 book、book 携带 Prompt、none 携带 Prompt、Prompt 伪 book structure、book 混入来源包、analysis 使用 draft scope、confirmed scope 缺允许来源、结构态 Prompt 无 packet、结构态 book 无 chapter、公开衍生含非 pass 检查；
- 自定义负例通过：gap 声明 `target_type=scene` 却指向 Claim 时被拒绝；
- 隐私扫描通过：artifact 不含本机路径、file URL、HTML 正文、Cookie 或下载站文件名。
