# 浏览器批注轮 checkpoint

## 已实现

- 删除 mode-bar；书籍工作栏合并书名、研究范围、本地状态、保存状态和保存动作。
- 右栏改为一体式 composer；`+` 菜单支持添加摘录、外部材料与人物事件关联，并聚焦输入。
- 常驻播放 dock 已删除；地图内次级入口默认收起，展开后可播放、暂停、步进与变速。
- 所有逻辑节点可打开内嵌详情；详情区明确作者摘要 / 证据边界，并能返回左栏对应段落。
- 三栏使用两条 `role=separator` 边界，可拖拽、方向键调整、双击复位；默认 280 / 自适应 / 300。
- 左栏新增“时间 · 事件柱”；内置阅读器新增“正文 / 锚点”切换，均与共享 Scene / 段落状态联动。
- 地图保留 fan-out Canvas 与 flow / beads；可见标签收敛为“材料关联”，完整语义放入 title / aria。
- 网页来源 limited / login 状态、产品旁注与状态 Notebook 保留。

## 验证

- IAB 收口：无地点 Scene 不再激活继承地点；separator 在 pointerup 消费最终位移；正文段落恢复键盘 Tab 可达。
- `npm run build`：通过；Vite 4570 modules，1.26s；JS 326.29 kB / gzip 99.23 kB；CSS 44.47 kB / gzip 8.45 kB。
- `npm run test:sites`：4 / 4 通过。
- IAB 1117px 首屏证据：`qa-annotation-round-1117.png`；无横向溢出，三栏、地图与 composer 均完整可见。
- 待主线 IAB 继续验收：分栏拖拽 / 键盘 / 双击、逻辑回原文、地图内播放展开、composer 菜单。
