<template>
  <div class="sp-root" :class="{ vertical }" ref="rootRef">
    <div class="sp-pane sp-pane-left" :style="{ flexBasis: leadPx + 'px' }">
      <slot name="left" />
    </div>
    <div class="sp-handle"
         :class="{ dragging }"
         role="separator"
         tabindex="0"
         :aria-label="label"
         :aria-orientation="vertical ? 'horizontal' : 'vertical'"
         aria-valuemin="0"
         aria-valuemax="100"
         :aria-valuenow="Math.round(ratio * 100)"
         @pointerdown="onDown"
         @pointermove="onMove"
         @pointerup="onUp"
         @pointercancel="onUp"
         @dblclick="reset"
         @keydown="onKeydown">
    </div>
    <div class="sp-pane sp-pane-right">
      <slot name="right" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

// 通用分栏：前 | 6px 手柄 | 后。比例持久化到 localStorage[storageKey]。
// vertical=true 时改为上 | 手柄 | 下，逻辑完全共用 —— 只是把「宽/clientX」换成
// 「高/clientY」。第二个用例是地图占比(右栏内上下分)，故泛化而非另写一个组件。
// 拖拽跟手：pointerdown 时捕获指针，pointermove 直接改 ratio -> computed leadPx
// -> 单属性 flexBasis 内联 patch，一帧一次 reflow，无 rAF 延迟。
const props = defineProps({
  storageKey: { type: String, required: true },
  min: { type: Number, default: 280 },
  minLead: { type: Number, default: null },
  minTrail: { type: Number, default: null },
  default: { type: Number, default: 0.5 },
  vertical: { type: Boolean, default: false },
  label: { type: String, default: '调整分栏尺寸' },
})

const HANDLE_W = 6
const rootRef = ref(null)
const containerSize = ref(0)      // 横向=宽,纵向=高
const ratio = ref(props.default)  // 前段占比 0..1，持久化对象
const dragging = ref(false)
let dragPointerId = null
const leadMin = computed(() => props.minLead ?? props.min)
const trailMin = computed(() => props.minTrail ?? props.min)

// 读取持久化比例（非法值回退 default）
function loadRatio() {
  try {
    const raw = localStorage.getItem(props.storageKey)
    if (raw == null) return props.default
    const v = Number(raw)
    if (!Number.isFinite(v) || v <= 0 || v >= 1) return props.default
    return v
  } catch {
    return props.default
  }
}
function persist() {
  try { localStorage.setItem(props.storageKey, String(ratio.value)) } catch {}
}

// 比例 -> 前段 px，按 lead/trail 最小值 clamp；未单独提供时双方沿用 min。
const leadPx = computed(() => {
  const cs = containerSize.value
  if (!cs) return 0
  const lo = leadMin.value
  const hi = cs - HANDLE_W - trailMin.value
  if (hi < lo) return Math.max(0, (cs - HANDLE_W) / 2) // 极窄：居中，不卡死
  return Math.max(lo, Math.min(hi, ratio.value * cs))
})

function onDown(e) {
  // 只响应主键；触摸/触控笔/鼠标统一走 pointer
  if (e.button != null && e.button !== 0) return
  dragging.value = true
  dragPointerId = e.pointerId
  e.currentTarget.setPointerCapture(e.pointerId)
  document.body.style.userSelect = 'none'
  e.preventDefault()
}

function onMove(e) {
  if (!dragging.value || e.pointerId !== dragPointerId) return
  const el = rootRef.value
  if (!el) return
  const cs = containerSize.value
  if (!cs) return
  const rect = el.getBoundingClientRect()
  // 指针定位到手柄中线 -> 前段末沿 = 指针 - 容器起沿 - 半手柄
  const pointer = props.vertical ? e.clientY - rect.top : e.clientX - rect.left
  let lp = pointer - HANDLE_W / 2
  const lo = leadMin.value
  const hi = cs - HANDLE_W - trailMin.value
  if (hi < lo) lp = (cs - HANDLE_W) / 2
  else lp = Math.max(lo, Math.min(hi, lp))
  ratio.value = lp / cs
}

function onUp(e) {
  if (!dragging.value) return
  dragging.value = false
  if (dragPointerId != null) {
    try { e.currentTarget.releasePointerCapture(dragPointerId) } catch {}
    dragPointerId = null
  }
  document.body.style.userSelect = ''
  persist()
}

// 双击复位
function reset() {
  ratio.value = props.default
  persist()
}

// 分隔条必须脱离鼠标也能调整。横向用 ←/→，纵向用 ↑/↓；
// Home/End 只到双方最小尺寸边界，不允许把任一面板压成不可恢复的 0。
function onKeydown(e) {
  const backward = props.vertical ? 'ArrowUp' : 'ArrowLeft'
  const forward = props.vertical ? 'ArrowDown' : 'ArrowRight'
  if (![backward, forward, 'Home', 'End'].includes(e.key)) return
  e.preventDefault()
  const cs = containerSize.value
  if (!cs) return
  const lo = leadMin.value
  const hi = Math.max(lo, cs - HANDLE_W - trailMin.value)
  let nextPx = leadPx.value
  if (e.key === 'Home') nextPx = lo
  else if (e.key === 'End') nextPx = hi
  else nextPx += e.key === forward ? 12 : -12
  nextPx = Math.max(lo, Math.min(hi, nextPx))
  ratio.value = nextPx / cs
  persist()
}

/** 供外部按预设比例展开/收起（如地图的「放大」）。clamp 由 leadPx 兜底。 */
function setRatio(v) {
  if (!Number.isFinite(v) || v <= 0 || v >= 1) return
  ratio.value = v
  persist()
}
defineExpose({ setRatio, ratio })

// 容器尺寸观测：resize 时按比例保持（leadPx 由 ratio×cs 重算）
let ro = null
onMounted(() => {
  ratio.value = loadRatio()
  if (rootRef.value) {
    const r = rootRef.value.getBoundingClientRect()
    containerSize.value = props.vertical ? r.height : r.width
    ro = new ResizeObserver((entries) => {
      for (const ent of entries) {
        containerSize.value = props.vertical ? ent.contentRect.height : ent.contentRect.width
      }
    })
    ro.observe(rootRef.value)
  }
})
onBeforeUnmount(() => {
  if (ro) ro.disconnect()
  document.body.style.userSelect = ''
})
</script>

<style scoped>
.sp-root {
  display: flex;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.sp-root.vertical { flex-direction: column; }

.sp-pane {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.sp-root:not(.vertical) > .sp-pane { height: 100%; }
.sp-root.vertical > .sp-pane { width: 100%; }

.sp-pane-left {
  flex: 0 0 auto; /* flex-basis 由内联 style 给定，shrink:0 锁死拖出来的尺寸 */
}
.sp-pane-right {
  flex: 1 1 0; /* 吃掉前段 + 手柄之外的余量 */
}

.sp-handle {
  flex: 0 0 6px;
  position: relative;
  touch-action: none; /* 触屏拖动不触发页面滚动 */
  z-index: 5;
}
.sp-root:not(.vertical) > .sp-handle { width: 6px; cursor: col-resize; }
.sp-root.vertical > .sp-handle { height: 6px; cursor: row-resize; }

.sp-handle::after {
  content: '';
  position: absolute;
  background: var(--line);
  transition: background 0.15s, width 0.15s, height 0.15s;
}
.sp-root:not(.vertical) > .sp-handle::after {
  left: 50%; top: 0; bottom: 0; width: 1px; transform: translateX(-50%);
}
.sp-root.vertical > .sp-handle::after {
  top: 50%; left: 0; right: 0; height: 1px; transform: translateY(-50%);
}
.sp-handle:hover::after,
.sp-handle.dragging::after {
  background: var(--accent);
}
.sp-handle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.sp-root:not(.vertical) > .sp-handle:hover::after,
.sp-root:not(.vertical) > .sp-handle.dragging::after { width: 2px; }
.sp-root.vertical > .sp-handle:hover::after,
.sp-root.vertical > .sp-handle.dragging::after { height: 2px; }
</style>
