# v5 前端 checkpoint

## 2026-07-27 · 探索入口、材料阅读与网页桥接

- Explore 默认进入真正空状态，不再默认加载书籍或延安整风 Scene。
- 两个主入口已落地：
  - 输入历史问题：调用 `/api/explorations/from-prompt` 建立进程内探索，并用响应中的 `scope_contract`、研究问题 Scene 和 revision hydration 当前工作区；失败时只保留明确标记为“未同步服务端”的本机草案。
  - 上传材料：TXT / Markdown 调用 `/api/explorations/import`；EPUB 读取 `ArrayBuffer`、分块转 base64 后调用真实 `/api/explorations/import-epub` 合同。
- Prompt 范围合同可继续细化：右侧提供时间、空间、叙事主线三个输入，调用 `update_scope_contract`；服务端响应同时刷新 Brief、剩余缺项与 revision。
- 《红太阳是怎样升起的》保留为次级示例入口；只使用既有作者论证摘要与结构，不加载本机 EPUB、不冒充原文。
- 有工作区后，左上角操作为“返回探索入口”；可继续当前探索或切换材料，不再返回时间柱。
- 私人文档阅读器按章节窗口渲染：
  - 章节下拉、上一章 / 下一章、正文 / 锚点视图和阅读进度共用同一组选中状态。
  - 点击或滚动段落同时更新 `selectedAnchorId`、`selectedSceneId=anchor-context:<id>` 与 `selectedEvidenceAnchorId`。
  - 滚动选中先本地即时更新，450ms 稳定后调用 `update_reading_progress`；后端用段落 locator 回填 section / paragraph / spine / href / progression，并同步 active anchor。
  - 所有阅读与范围 mutation 共用一条 revision 串行队列。`update_reading_progress` 已同时更新 active anchor，不再额外发送会争用同一 `base_revision` 的 `set_active_anchor`。
- 性能验收样本：E2E EPUB 响应为 2 章、40 段；任一时刻正文 DOM 只挂当前章 20 段。切到第二章后第一章正文为 0 个 DOM 节点；滚到底时阅读进度为 100%，Scene 与 evidence context 和 selected anchor 一致。
- 微信读书网页态：
  - 默认不请求第三方页面；用户主动点击后才尝试 iframe。
  - 始终明确“手动同步、不自动读取 DOM”；iframe 是否可见由原站登录与 frame 策略决定。
  - 用户可手动提交阅读位置与粘贴段落，调用真实 `sync_external_reading_progress`，再用服务端 `external_reading_bridge` 响应生成 `web-bridge` 上下文；不声称自动实时联动。
- 移动端继续使用阅读 / 时空 / 出处三页签；空状态采用单列入口，地图仍只在“时空”页签挂载。

## 合同与未尽事项

- Prompt、TXT / Markdown、EPUB、阅读进度、范围更新和微信读书手动桥接都已接入当前真实后端合同。当前服务仍只做规则脚手架与结构记录，不调用 LLM；界面不把 `needs_model` 冒充为答案。
- 微信读书跨域 DOM、选区和登录状态不可由本站可靠读取；本轮只交付 iframe 尝试与用户主动桥接。示例书没有服务端 snapshot，因此不会伪装成同步成功；真实同步需先建立 Prompt 或材料探索。
- EPUB base64 是传输适配，不落 localStorage；解析后的私人文档、Prompt 范围和外部阅读桥接都遵循后端进程内存、重启清除边界。
- 当前界面没有独立“深度分析”入口，因此没有为 `request_deep_analysis` 硬造新控件；待产品入口出现后再接现有 compose 合同。

## 验证

- `cd frontend && npm run build`：通过。ExplorationView 产物 35.66 kB（gzip 13.68 kB）；ExploreMapPanel 继续独立懒加载 11.81 kB（gzip 4.30 kB）。
- `cd frontend && npm run test:e2e -- exploration-v5.spec.js exploration.spec.js`：7 passed。
- 覆盖：空状态、真实 Prompt 请求与响应 hydration、Prompt 失败诚实态、真实范围更新及 revision、次级 Demo、EPUB base64 请求与服务端式 locator hydration、章节窗口、滚动阅读 mutation 串行化、真实微信读书手动桥接、既有地图/播放/分栏、TXT/Markdown 导入和移动端回归。
