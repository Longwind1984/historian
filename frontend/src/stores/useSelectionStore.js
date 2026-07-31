import { defineStore } from 'pinia'

// 显式选中后的 hover 抑制窗口（ms）。搜索下拉/弹层关闭时，鼠标下方卡片可能立刻
// mouseover；短暂忽略这次 hover-in，避免视觉高亮误导。档案本身始终只跟随 selected。
const HOVER_SUPPRESS_MS = 350
let _selectAt = 0

/** 选区 store：selected / hovered / origin / locateRequest */
export const useSelectionStore = defineStore('selection', {
  state: () => ({
    selectedEntityId: null,
    selectedEntityType: null,
    hoveredEntityId: null,
    // 选中来源('search'|'nebula'|'column'|'timeline'|'map'|'url'|null)。B2 防环用:
    // 星云/时空柱 watch 外部选中联动相机,来源是自家场景时跳过 —— 否则场景内点击
    // 会触发自我循环飞行(同款防环:columnMount.js 扫描环的 draggingScan)。
    // 未标注来源的调用点(档案内导航等)为 null,一律视为外部、正常联动。
    origin: null,
    // 「📍 地图定位」的显式请求通道。选中态不变时 selectedEntityId 的 watch 不触发,
    // 重复点同一实体就飞不了第二次;nonce 单调递增,每次点击都是一次新事件。
    // MapPanel 处理后把 id 置空(一次性消费),避免路由往返重挂载时拿滞留请求再飞。
    locateRequest: { id: null, type: null, nonce: 0 },
  }),
  actions: {
    selectEntity(id, type, origin = null) {
      this.selectedEntityId = id
      this.selectedEntityType = type
      this.hoveredEntityId = null
      this.origin = origin
      _selectAt = Date.now()
    },
    clearSelection() {
      this.selectedEntityId = null
      this.selectedEntityType = null
      this.origin = null
    },
    setHover(id) {
      // 抑制窗口内忽略 hover-in（id 非空），但始终允许清空（id 为空）。
      if (id && Date.now() - _selectAt < HOVER_SUPPRESS_MS) return
      this.hoveredEntityId = id
    },
    requestLocate(id, type) {
      this.locateRequest.id = id
      this.locateRequest.type = type
      this.locateRequest.nonce++
    },
  },
})
