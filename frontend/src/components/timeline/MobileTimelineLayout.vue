<template>
  <div ref="rootRef" class="mtl-root" data-testid="mobile-timeline">
    <div class="mtl-column"><TimeColumn /></div>

    <section
      ref="drawerRef"
      class="mtl-drawer"
      :class="{ 'mtl-drawer-open': expanded, 'mtl-drawer-dragging': dragging }"
      :style="drawerStyle"
      aria-label="此刻详情"
      data-testid="mobile-moment-drawer"
    >
      <button
        ref="handleRef"
        class="mtl-handle"
        type="button"
        :aria-expanded="expanded"
        aria-controls="mobile-moment-content"
        :aria-label="expanded ? '收起此刻详情' : '展开此刻详情'"
        @click="toggle"
        @keydown="onHandleKeydown"
        @pointerdown="onPointerDown"
      >
        <span class="mtl-grip" aria-hidden="true"></span>
      </button>
      <div
        id="mobile-moment-content"
        class="mtl-content"
        :aria-hidden="!expanded"
        :inert="expanded ? undefined : true"
      >
        <MomentPanel mobile :map-enabled="everOpened" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, ref } from 'vue'

const TimeColumn = defineAsyncComponent(() => import('./TimeColumn.vue'))
const MomentPanel = defineAsyncComponent(() => import('./MomentPanel.vue'))

const rootRef = ref(null)
const drawerRef = ref(null)
const handleRef = ref(null)
const expanded = ref(false)
const everOpened = ref(false)
const dragging = ref(false)
const dragOffset = ref(0)

let pointerId = null
let pointerStartY = 0
let pointerStartOffset = 0
let didDrag = false
let suppressClick = false

const drawerStyle = computed(() => dragging.value
  ? { transform: `translateY(${dragOffset.value}px)` }
  : undefined)

function closedOffset() {
  const drawer = drawerRef.value
  if (!drawer) return 0
  const height = drawer.getBoundingClientRect().height
  const peek = Number.parseFloat(getComputedStyle(drawer).getPropertyValue('--drawer-peek')) || 112
  return Math.max(0, height - peek)
}

function setExpanded(value) {
  if (value) everOpened.value = true
  expanded.value = value
}

function toggle() {
  if (suppressClick) return
  setExpanded(!expanded.value)
}

function onHandleKeydown(event) {
  if (event.key === 'ArrowUp' || event.key === 'Home') {
    event.preventDefault()
    setExpanded(true)
  } else if (event.key === 'ArrowDown' || event.key === 'End') {
    event.preventDefault()
    setExpanded(false)
  }
}

function onPointerDown(event) {
  if (event.button != null && event.button !== 0) return
  pointerId = event.pointerId
  pointerStartY = event.clientY
  pointerStartOffset = expanded.value ? 0 : closedOffset()
  dragOffset.value = pointerStartOffset
  dragging.value = true
  didDrag = false
  event.currentTarget.setPointerCapture(event.pointerId)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
  event.preventDefault()
}

function onPointerMove(event) {
  if (!dragging.value || event.pointerId !== pointerId) return
  const delta = event.clientY - pointerStartY
  if (Math.abs(delta) > 4) didDrag = true
  dragOffset.value = Math.max(0, Math.min(closedOffset(), pointerStartOffset + delta))
}

function onPointerUp(event) {
  if (!dragging.value || event.pointerId !== pointerId) return
  const maxOffset = closedOffset()
  // pointer capture 理论上会持续派发 move；仍按 pointerup 的最终坐标再算一次，
  // 避免低频触控设备只给首尾事件时抽屉误判方向。
  const delta = event.clientY - pointerStartY
  const finalOffset = Math.max(0, Math.min(maxOffset, pointerStartOffset + delta))
  didDrag = didDrag || Math.abs(delta) > 4
  setExpanded(finalOffset < maxOffset * 0.55)
  dragging.value = false
  dragOffset.value = 0
  suppressClick = didDrag
  if (suppressClick) setTimeout(() => { suppressClick = false }, 0)
  try { handleRef.value?.releasePointerCapture(event.pointerId) } catch {}
  pointerId = null
  removePointerListeners()
}

function removePointerListeners() {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
}

onBeforeUnmount(removePointerListeners)
</script>

<style scoped>
.mtl-root {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--paper);
}

.mtl-column {
  position: absolute;
  inset: 0;
}

.mtl-drawer {
  /* 390×844 下展开净位移保持 >200px，同时折叠态仍露出完整把手与一行摘要。 */
  --drawer-peek: 104px;
  position: absolute;
  z-index: 40;
  left: 0;
  right: 0;
  bottom: 0;
  height: min(41%, 360px);
  display: grid;
  grid-template-rows: 38px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--line);
  border-bottom: 0;
  border-radius: 22px 22px 0 0;
  background: var(--paper-el);
  box-shadow: 0 -8px 28px rgba(44, 39, 33, 0.14);
  transform: translateY(calc(100% - var(--drawer-peek)));
  transition: transform 220ms cubic-bezier(0.22, 0.8, 0.24, 1);
  will-change: transform;
}

.mtl-drawer-open { transform: translateY(0); }
.mtl-drawer-dragging { transition: none; }

.mtl-handle {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 38px;
  padding: 0;
  border: 0;
  border-radius: 22px 22px 0 0;
  background: var(--paper-el);
  color: var(--ink-soft);
  touch-action: none;
  cursor: ns-resize;
}

.mtl-handle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -4px;
}

.mtl-grip {
  width: 36px;
  height: 4px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ink-soft) 48%, transparent);
}

.mtl-content {
  min-height: 0;
  overflow: hidden;
}

@media (prefers-reduced-motion: reduce) {
  .mtl-drawer { transition: none; }
}
</style>
