# Book-only exploration checkpoint

- 已移除页面级编织态与播放态入口和组件，只渲染书籍探索工作空间。
- 研究 Brief、论证链、地图 Scene 浮窗、播放控制与时间轨已内联到书籍页。
- 旧 `Route` 直虚线 JSX/CSS 已删除；地图使用 DPR + ResizeObserver 的 Canvas cubic Bézier。
- `?route=flow` 为双层柔性曲线；`?route=beads` 为沿同一曲线的稀疏珠点；两者均无箭头、无虚线。
- IAB 首轮指出的未满高问题已修：`.book-view` 现在占满工作区，地图吸收剩余高度，播放 dock 保持固定行。
- beads 方案已增强为不等距疏朗珠点：浅色 halo + 实心内核，无连续线。
- IAB 满高复核已通过；flow 主/次关联对比度已提升，仍低于地点与浮窗层级。
- IAB 发现旧 Canvas backing size 正常但无可见像素；已改为两阶段生命周期：父 contentRect → React state → 显式 backing attrs → 独立 layout effect 绘制，并暴露 `data-rendered` / `data-size` 诊断属性。
- 当前 `npm run build` 已通过：Vite 4570 modules，JS 300.59 kB / gzip 92.57 kB，CSS 37.73 kB / gzip 7.50 kB；Sites 4 / 4。
- IAB 最终实际截图已确认 Canvas 有可见像素，且拓扑改为从浮窗右下材料 hub 分别 fan-out 到延安 / 西安 / 重庆，不再串联城市。
- 最终证据：`qa-book-only-flow-fanout-1440-final.png`、`qa-book-only-beads-fanout-1440-final.png`；地图裁图为 `/private/tmp/book-only-flow-fanout-map.jpg`、`/private/tmp/book-only-beads-fanout-map.jpg`。
- `npm run test:sites` 已通过：4 / 4。
- 4173 现有本地服务 unsandboxed HTTP 200；实际视觉验收由主线在 IAB 完成。
