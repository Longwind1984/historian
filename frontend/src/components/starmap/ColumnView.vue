<template>
  <div class="cv-wrap">
    <div class="cv-toolbar">
      <span class="cv-mode">时空柱 · 3D</span>
      <div class="cv-presets">
        <button class="cv-btn" :class="{ on: preset === 'overview' }" @click="setPreset('overview')">俯瞰</button>
        <button class="cv-btn" :class="{ on: preset === 'cruise' }" @click="setPreset('cruise')">巡航</button>
        <button class="cv-btn" :class="{ on: preset === 'follow' }" @click="setPreset('follow')">跟随一生</button>
        <span class="cv-msg" :class="msgClass">{{ msg }}</span>
      </div>
      <span class="cv-spacer"></span>
      <button class="cv-btn" :class="{ on: ambientOn }" @click="toggleAmbient" title="全库双链最高的人物对常显淡弧">关联脉络</button>
      <span class="cv-count">
        {{ threadCount }} 光丝 · {{ yearLabel }}
        <span v-if="yearInColumn === false" class="cv-outside">· 柱轴范围外（前221–1912）</span>
      </span>
    </div>

    <div class="cv-stage" ref="stageRef">
      <!-- D5 空态统一:装配中/装配失败共用 EmptyState,文案与装配重试逻辑不变 -->
      <EmptyState v-if="loading" class="cv-loading" :text="loadError || '时空柱装配中…'" />
      <div v-else class="cv-legend">
        <span class="cv-leg-row"><span class="cv-sym bar">│</span>光丝=人物一生</span>
        <span class="cv-leg-row"><span class="cv-sym">○</span>环=事件</span>
        <span class="cv-leg-row"><span class="cv-sym">●</span>点=战役</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useTimeStore, useSelectionStore, useUIStore } from '../../stores'
import EmptyState from '../shared/EmptyState.vue'

const timeStore = useTimeStore()
const selectionStore = useSelectionStore()
const ui = useUIStore()

const stageRef = ref(null)
const loading = ref(true)
const loadError = ref('')
const threadCount = ref(0)
const preset = ref('')
const msg = ref('')
const msgClass = ref('')
const ambientOn = ref(true) // 「关联脉络」toggle，默认开

let controller = null
let drawCallTimer = 0
let stopSelectionWatch = null
let unmounted = false

// 显示直接读 store，不再复制一份可能在 three 异步装配期间过期的 yearLabel。
const yearLabel = computed(() => timeStore.year)
const yearInColumn = ref(null)

function syncYearToColumn(year) {
  if (!controller) return
  yearInColumn.value = controller.onYearChange(year)
}

// watch 在 onMounted 的动态 import / API 请求之前注册。装配期间若 URL 改年，computed
// 立即更新；控制器到位后再以下方显式 sync 补发最新值，竞态窗口不再丢事件。
watch(() => timeStore.year, syncYearToColumn)

// ============ 相机预设 ============
function setPreset(name) {
  if (!controller) return
  if (name === 'follow' && !selectionStore.selectedEntityId) {
    msg.value = '先选中一位人物'; msgClass.value = 'no'; return
  }
  const ok = controller.presetView(name)
  if (ok) {
    preset.value = name
    msg.value = name === 'follow' ? '陪他走完一生…' : ''
    msgClass.value = ''
  }
}

// ============ 关联脉络 toggle ============
function toggleAmbient() {
  if (!controller) return
  ambientOn.value = !ambientOn.value
  controller.setAmbientArcs(ambientOn.value)
}

// ============ 生命周期 ============
onMounted(async () => {
  const stage = stageRef.value
  try {
    if (unmounted || !stage) return
    // dynamic import 也可能跨过卸载边界；返回后先检查，再启动真实数据/WebGL 装配。
    const { mountColumn } = await import('../../starmap/engine/columnMount.js')
    if (unmounted || !stage.isConnected) return

    const mountedController = await mountColumn(stage, {
      onSelect: (id, type) => selectionStore.selectEntity(id, type, 'column'),
      onYearDrag: (year) => { timeStore.setYear(year) },
      getCurrentYear: () => timeStore.year,
      getSelectedEntityId: () => selectionStore.selectedEntityId,
      getPaletteMeta: () => ({ key: ui.palette, dark: !!ui.paletteMeta?.dark }),
    })
    // API 返回时组件可能已卸载；控制器晚到就立即释放，不写 Vue 或调试状态。
    if (unmounted || !stage.isConnected) {
      mountedController.dispose()
      if (import.meta.env.DEV) {
        window.dispatchEvent(new CustomEvent('starmap:late-dispose', { detail: { view: 'column' } }))
      }
      return
    }
    controller = mountedController
    threadCount.value = controller.threadCount
    syncYearToColumn(timeStore.year)
    loading.value = false
    // 调试桩（E2E B6 用）
    if (import.meta.env.DEV) {
      window.__starmapDebug = window.__starmapDebug || {}
      window.__starmapDebug.columnReady = false
      window.__starmapDebug.columnThreads = controller.threadCount
      window.__starmapDebug.columnArcs = 0
      window.__starmapDebug.columnDynastyColors = controller.getDynastyColors()
      window.__starmapDebug.columnScan = controller.getScanState()
    }
    mountedController.ready.then(() => {
      if (unmounted || controller !== mountedController) return
      if (import.meta.env.DEV && window.__starmapDebug) {
        window.__starmapDebug.columnReady = true
        // draw call / 弧数自述采样（报告用，0.5s 一次）
        drawCallTimer = window.setInterval(() => {
          if (!unmounted && controller === mountedController) {
            window.__starmapDebug.columnDrawCalls = mountedController.getDrawCalls()
            window.__starmapDebug.columnArcs = mountedController.getArcCount()
            window.__starmapDebug.columnScan = mountedController.getScanState()
          }
        }, 500)
      }
      // 选中联动：画 Person↔Person 关系弧 + 高亮丝（含 URL 初始选中）
      if (selectionStore.selectedEntityId) mountedController.focusEntity(selectionStore.selectedEntityId)
    })
    // 外部选中变化（档案卡/URL）-> 重画关系弧 + 高亮丝
    stopSelectionWatch = watch(() => selectionStore.selectedEntityId, (id) => {
      if (unmounted || controller !== mountedController) return
      mountedController.focusEntity(id)
      // B2:外部选中(非柱内点击)且是场景内人物 -> 「跟随一生」自动起飞,与工具条
      // 按钮同一代码路径(presetView);非人物/不在场景的实体只留高亮丝。
      // watch 非 immediate:初挂载不触发,URL 初始选中不会与入场相机打架,挂载期
      // 行为保持原样(ready 后仅 focusEntity 高亮)。
      if (id && selectionStore.origin !== 'column' && mountedController.canFollow(id)) {
        if (mountedController.presetView('follow')) {
          preset.value = 'follow'
          msg.value = '陪他走完一生…'; msgClass.value = ''
        }
      }
    })
  } catch (e) {
    if (unmounted) return
    console.error('[ColumnView] mount failed', e)
    loadError.value = '时空柱装配失败'
    loading.value = false
  }
})

onBeforeUnmount(() => {
  unmounted = true
  if (drawCallTimer) { clearInterval(drawCallTimer); drawCallTimer = 0 }
  if (stopSelectionWatch) { stopSelectionWatch(); stopSelectionWatch = null }
  if (controller) { controller.dispose(); controller = null }
  if (import.meta.env.DEV && window.__starmapDebug) {
    window.__starmapDebug.columnReady = false
  }
})

// 主题热切换
watch(() => ui.palette, () => {
  controller?.applyTheme({ key: ui.palette, dark: !!ui.paletteMeta?.dark })
})
</script>

<style scoped>
.cv-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--paper);
}
.cv-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-el);
  flex-wrap: wrap;
}
.cv-mode {
  font-family: var(--serif);
  font-size: 12px;
  color: var(--ink-soft);
  padding: 2px 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.cv-presets {
  display: flex;
  align-items: center;
  gap: 6px;
}
.cv-btn {
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--paper);
  color: var(--ink-mid);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.cv-btn:hover { background: var(--hover); color: var(--ink); }
.cv-btn.on { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
.cv-msg { font-size: 12px; color: var(--ink-soft); margin-left: 4px; }
.cv-msg.no { color: var(--ink-faint); }
.cv-spacer { flex: 1; }
.cv-count {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: var(--ink-soft);
}
.cv-outside { color: var(--accent); }
.cv-stage {
  flex: 1;
  min-height: 0;
  position: relative;
  background: var(--paper);
  overflow: hidden;
}
.cv-stage :deep(canvas.column-canvas) {
  position: absolute;
  inset: 0;
  display: block;
  cursor: grab;
}
/* 定位即可:排版/配色由 EmptyState 自带 */
.cv-loading {
  position: absolute;
  inset: 0;
}
.cv-legend {
  position: absolute;
  left: 12px;
  bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  pointer-events: none;
  font-family: var(--serif);
  font-size: 11px;
  color: var(--ink-soft);
  background: color-mix(in srgb, var(--paper-el) 72%, transparent);
  padding: 5px 9px;
  border-radius: 4px;
  border: 1px solid color-mix(in srgb, var(--line) 60%, transparent);
  letter-spacing: 0.03em;
}
.cv-leg-row { white-space: nowrap; }
.cv-sym {
  display: inline-block;
  width: 14px;
  color: var(--accent);
  font-weight: 600;
}
.cv-sym.bar { color: var(--ink-mid); }
</style>
