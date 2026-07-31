# 生产前端实施 checkpoint

## 2026-07-27 · Phase 0：现状与边界

- 已确认生产端为 Vue 3.5 / Pinia 2.2 / Vite 5.4 / MapLibre 4.7，不新增依赖。
- 全局入口当前由 `useUIStore.route` 和 URL hash 管理，没有 Vue Router；探索模块将沿用这条契约。
- 现有 `SplitPane.vue` 支持拖拽、双击复位与持久化，但缺少键盘分隔条语义；生产接入时补齐后复用为嵌套三栏。
- 现有 `MapPanel.vue` 与时间柱/实体选中/历史播放深度耦合；探索态将复用 MapLibre、底图和时间 store 契约，另设书籍场景层，避免污染静态工作台。
- 用户现有 README、WORKLOG、handoff、产品规格与原型改动均保留；本轮只写 `frontend/` 和本 checkpoint。
- 真实性红线：不放入伪造原文、页码、真实 LLM 已完成等声明；示例内容明确标为“作者论证摘要 / 版本待核”。
- 无地点场景只保留当前视野，不继承上一场景的地点高亮。

## 2026-07-27 · Phase 1：可运行主链路

- 全局新增 Explore 路由并写入 URL；路由值白名单化，Scene id 可恢复。
- 生产端已形成单书工作区：两行顶部、桌面可调三栏、阅读/网页/时间来源、论证节点、关系化证据、地图内播放。
- ≤720px 降级为阅读 / 时空 / 出处三个查看页签；地图仅在“时空”页签挂载，移动端不开放导入和复杂编织。
- 新增真实 TXT/Markdown 私人导入：调用后端进程内 exploration API，展示真实段落锚点且页码保持未知。
- 导入任意文本后不再显示高华示例判断；证据栏只显示当前导入锚点、尚未生成关系和已记录问题。
- composer 已接后端 question 记录；界面明确显示“仅记录，未调用模型”。
- 书籍 Scene 使用独立 store / sceneIndex / 计时器，并统一同步 `timeStore`；无地点 Scene 清空当前地点图层但保留视野。
- 三套播放在路由切换时互斥暂停；探索 Scene 不写正式实体 selection，也不复用 march 层。
- 验证：`npm run build` 通过；`npm run test:e2e -- exploration.spec.js` 通过（1 passed，隔离前后端）。
