# Exploration v4 production backend checkpoint

## 2026-07-27 · 阶段 1：现状审计与最小闭环边界

- FastAPI 入口是 `backend/app/main.py:create_app()`；现有 API 以薄 router + service/core 数据层组织，依赖已锁定 FastAPI 0.115 / Pydantic 2.9.2。
- 正式知识库由 YAML / GeoJSON 与编译 JSON 驱动，现有 `core/data.py` 是只读索引；探索数据不能进入这套 loader，也不能写回 `data/`。
- 测试通过共享 `TestClient` 运行；新增探索 API 应沿用 `backend/tests/`，不借用父目录虚拟环境。
- 本阶段只支持 UTF-8 私有 TXT / Markdown；不加入 multipart、EPUB、PDF、OCR 或 LLM 依赖。请求正文只保存在当前后端进程内，重启即清除；不落仓库、不写日志。
- 最小真实闭环：导入并解析章节/段落锚点 → 获取 Exploration snapshot → composer 记录问题/笔记或提出 Scene → 选择/复核 Scene。没有依据的结构化 Scene/Claim 固定为 `model_inference + pending_review`；段落只作为 `source_context`，不会被系统自动宣称为“支持事实”。
- TXT / Markdown 无可靠页码，API 的定位合同只返回章节与段落锚点，`page_label` 固定为空；不生成伪引文、伪页码或历史地点。
- 进程内 store 采用有界会话数、TTL、revision 乐观并发和显式删除；后续账户、跨设备持久化、IndexedDB、EPUB 分页与真实 LLM 是明确缺口。

## 2026-07-27 · 阶段 2：API 与服务合同落盘

- 新增 `/api/explorations/import`、`GET/DELETE /api/explorations/{id}`、`POST /compose` 与 `POST /mutations`。
- 导入 parser 只把 Markdown 标题或纯文本「第…章/节/卷…」识别为章节；正文按空行形成段落，锚点由章节序号、段落序号和文本摘要哈希稳定生成。
- 返回的 `PrivateDocument` 不包含 raw content 字段；段落正文只存在会话 snapshot 中，`retention=process_memory`、`ephemeral=true`，所有 TXT/Markdown `page_label=null`。
- composer 的 question/note 只记录为 `recorded_no_llm`；`propose_scene` 才创建结构，但 Claim 固定为 `model_inference + pending_review`。段落 Evidence 关系固定为 `source_context`，不自动宣称支持；Scene 不接受猜测地点，`map_state=no_location`、`map_focus=null`。
- mutation 使用 `base_revision` 防止旧 UI 覆盖新状态，首版只允许选择段落、选择 Scene、接受/驳回 Scene。接受复核不会把 `model_inference` 偷升格为事实。

## 2026-07-27 · 阶段 3：定向测试

- `backend/tests/test_api_explorations.py` 覆盖 Markdown/纯文本解析、稳定段落锚点、无页码/无书目推断、question 的 no-LLM 记录、带/不带锚点的 Scene 提议、证据定位、revision 冲突、未知锚点回滚、显式清除与有界内存淘汰。
- 首轮测试发现纯文本首个「第1章」被误作书名；已修正为只有 Markdown 首标题可在用户未填 title 时作为文档标题，纯文本章节标题只做章节结构。
- 定向结果：`9 passed`。测试同时确认接受 Scene 后仍保持 `model_inference`，不会因人工接受结构就自动晋升为事实。

## 2026-07-27 · 阶段 4：完整后端回归与交付状态

- 完整命令：`uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q`
- 结果：`205 passed in 11.97s`，探索 API 与现有实体、关系、时间轴、地图、EdgeOne 构建测试共同通过。
- 当前可运行闭环不需要外部网络或 LLM key：导入 TXT/Markdown → 返回章节/段落锚点 snapshot → 记录 composer 问题/笔记或提出待复核 Scene → 选择/复核 → 显式清除会话。
- 隐私边界：全文仅存在 FastAPI worker 的内存 snapshot；最多 64 个会话、默认 6 小时 TTL、最旧会话有界淘汰，服务重启或 DELETE 会清除。没有磁盘、数据库、正式 YAML/GeoJSON 或日志写入路径。
- 当前缺口：多 worker 之间不共享会话；没有账户/跨设备恢复；EPUB/PDF/OCR、真实页码体系、浏览器 IndexedDB、地点实体核验、知识库检索与 LLM 结构提取尚未实现。生产接入前需决定会话亲和或受控私有持久层，不能把当前内存 store 描述成耐久保存。
