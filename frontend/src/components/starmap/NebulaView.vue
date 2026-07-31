<template>
  <div class="nv-wrap">
    <!-- 工具条：Connect-two 六度飞行 -->
    <div class="nv-toolbar">
      <span class="nv-mode">星云 · 3D</span>
      <div class="nv-connect">
        <div class="nv-field">
          <input v-model="fromText" class="nv-input" placeholder="起点"
                 @input="onSearchInput('from')" @focus="fromOpen = fromSugg.length > 0" @blur="delayedClose('from')" />
          <ul v-if="fromOpen && fromSugg.length" class="nv-sugg">
            <li v-for="h in fromSugg" :key="h.id" @mousedown.prevent="pickSugg('from', h)">
              <span class="nv-sugg-name">{{ h.name }}</span><span class="nv-sugg-type">{{ typeLabel(h.type) }}</span>
            </li>
          </ul>
        </div>
        <span class="nv-arrow">→</span>
        <div class="nv-field">
          <input v-model="toText" class="nv-input" placeholder="终点"
                 @input="onSearchInput('to')" @focus="toOpen = toSugg.length > 0" @blur="delayedClose('to')" />
          <ul v-if="toOpen && toSugg.length" class="nv-sugg">
            <li v-for="h in toSugg" :key="h.id" @mousedown.prevent="pickSugg('to', h)">
              <span class="nv-sugg-name">{{ h.name }}</span><span class="nv-sugg-type">{{ typeLabel(h.type) }}</span>
            </li>
          </ul>
        </div>
        <button class="nv-btn" @click="runConnect" :disabled="connectRunning">六度飞行</button>
        <button class="nv-btn nv-btn-ghost" v-if="connectRunning" @click="cancelConnect">停止</button>
        <span class="nv-msg" :class="msgClass">{{ connectMsg }}</span>
      </div>
      <span class="nv-spacer"></span>
      <span class="nv-count">{{ starCount }} 星</span>
    </div>

    <!-- 画布舞台（引擎挂载点）-->
    <div class="nv-stage" ref="stageRef">
      <!-- D5 空态统一:装配中/装配失败共用 EmptyState,文案与装配重试逻辑不变 -->
      <EmptyState v-if="loading" class="nv-loading" :text="loadError || '星云装配中…'" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useSelectionStore, useUIStore } from '../../stores'
import { fullTextSearch } from '../../api/client'
import { SEALS } from '../../styles/palettes'
import EmptyState from '../shared/EmptyState.vue'

const selectionStore = useSelectionStore()
const ui = useUIStore()

const stageRef = ref(null)
const loading = ref(true)
const loadError = ref('')
const starCount = ref(0)
const connectRunning = ref(false)
const connectMsg = ref('')
const msgClass = ref('')

// Connect-two 输入态
const fromText = ref('李白')
const fromId = ref('p_li_bai')
const fromSugg = ref([])
const fromOpen = ref(false)
const toText = ref('岳飞')
const toId = ref('p_yuefei')
const toSugg = ref([])
const toOpen = ref(false)
let searchTimer = null
const closeTimers = new Set()

let controller = null
let unmounted = false

const typeLabel = (t) => (SEALS[t] ? SEALS[t].label : t || '')

// ============ 联想搜索 ============
function onSearchInput(which) {
  if (unmounted) return
  const text = which === 'from' ? fromText.value : toText.value
  if (which === 'from') fromId.value = ''
  else toId.value = ''
  clearTimeout(searchTimer)
  if (!text.trim()) {
    if (which === 'from') fromSugg.value = []
    else toSugg.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    searchTimer = null
    try {
      const r = await fullTextSearch(text.trim(), 8)
      if (unmounted) return
      const list = r.hits || []
      if (which === 'from') { fromSugg.value = list; fromOpen.value = list.length > 0 }
      else { toSugg.value = list; toOpen.value = list.length > 0 }
    } catch { /* 忽略单次联想失败 */ }
  }, 180)
}
function pickSugg(which, hit) {
  if (which === 'from') { fromText.value = hit.name; fromId.value = hit.id; fromOpen.value = false }
  else { toText.value = hit.name; toId.value = hit.id; toOpen.value = false }
}
function delayedClose(which) {
  // mousedown 选词先于 blur，延迟关闭避免点不到
  const timer = setTimeout(() => {
    closeTimers.delete(timer)
    if (unmounted) return
    if (which === 'from') fromOpen.value = false
    else toOpen.value = false
  }, 120)
  closeTimers.add(timer)
}
/** 未从联想选词时，按当前文本兜底解析：精确名命中->id，否则原样当 id */
async function resolveId(text, fallbackId) {
  if (fallbackId) return fallbackId
  const t = (text || '').trim()
  if (!t) return ''
  try {
    const r = await fullTextSearch(t, 1)
    return r.hits?.[0]?.id || t
  } catch { return t }
}

// ============ Connect-two ============
async function runConnect() {
  const activeController = controller
  if (!activeController || unmounted) return
  const f = await resolveId(fromText.value, fromId.value)
  if (unmounted || controller !== activeController) return
  const t = await resolveId(toText.value, toId.value)
  if (unmounted || controller !== activeController) return
  if (!f || !t) { connectMsg.value = '请选择起终点'; msgClass.value = 'no'; return }
  connectRunning.value = true
  connectMsg.value = '巡航中…'; msgClass.value = ''
  try {
    const r = await activeController.connectTwo(f, t)
    if (unmounted || controller !== activeController) return
    if (r.ok) { connectMsg.value = `${r.depth} 跳飞行完成`; msgClass.value = 'ok' }
    else { connectMsg.value = '无路径（≤6 跳）'; msgClass.value = 'no' }
  } catch (e) {
    if (unmounted || controller !== activeController) return
    console.error('[NebulaView] connectTwo failed', e)
    connectMsg.value = '查询失败'; msgClass.value = 'no'
  } finally {
    if (!unmounted && controller === activeController) connectRunning.value = false
  }
}
function cancelConnect() { controller?.cancelConnect() }

// ============ 选中回调（点击星 / Connect-two 逐跳）============
// 点击星与 Connect-two 逐跳都经此 -> selectionStore.selectEntity -> 档案卡浮出。
// origin 记 'nebula':下方 watch 见自家来源即跳过,相机不被自己的点击再指挥一次(防环)。
function onSelect(entityId) {
  selectionStore.selectEntity(entityId, null, 'nebula')
}

// ============ 外部选中 -> 相机飞近(B2,收编 T3.4)============
// 搜索/URL/时间柱/地图选中时,若该实体在星图上,复用点击星的飞行路径
// (mount.js focusEntity:聚焦高亮+飞近+选中名牌),空闲巡航在飞行完成后才恢复
// (cameraDirector 既有行为)。origin === 'nebula' 时相机本就在飞,跳过防自我循环;
// 实体不在星图上 focusEntity 返回 false,静默不飞。Connect-two 巡航期间场景内
// 点击导航仍禁用(引擎 connectActive guard,不变)。
watch(() => selectionStore.selectedEntityId, (id) => {
  if (!controller || !id) return
  if (selectionStore.origin === 'nebula') return
  controller.focusEntity(id)
})

// ============ 生命周期 ============
onMounted(async () => {
  const stage = stageRef.value
  try {
    if (unmounted || !stage) return
    // 懒加载本身也可能跨过卸载边界；import 返回后先检查，避免无意义地启动数据装配。
    const { mountNebula } = await import('../../starmap/engine/mount.js')
    if (unmounted || !stage.isConnected) return

    const mountedController = await mountNebula(stage, {
      onSelect,
      onHover: () => {},
      getPaletteMeta: () => ({ key: ui.palette, dark: !!ui.paletteMeta?.dark }),
    })
    // 数据与 WebGL 装配完成时组件可能早已离开；晚到控制器必须当场完整释放。
    if (unmounted || !stage.isConnected) {
      mountedController.dispose()
      if (import.meta.env.DEV) {
        window.dispatchEvent(new CustomEvent('starmap:late-dispose', { detail: { view: 'nebula' } }))
      }
      return
    }
    controller = mountedController
    starCount.value = controller.starCount
    loading.value = false
    // 调试桩（E2E B5 用）
    if (import.meta.env.DEV) {
      window.__starmapDebug = window.__starmapDebug || {}
      window.__starmapDebug.nebulaReady = false
      window.__starmapDebug.nebulaStars = controller.starCount
    }
    mountedController.ready.then(() => {
      if (unmounted || controller !== mountedController) return
      if (import.meta.env.DEV && window.__starmapDebug) {
        window.__starmapDebug.nebulaReady = true
      }
      // 进入星云时若已有选中实体，飞抵它（一次性入场定位;后续变更由上方 watch 接管）
      const pre = selectionStore.selectedEntityId
      if (pre) mountedController.focusEntity(pre)
    })
  } catch (e) {
    if (unmounted) return
    console.error('[NebulaView] mount failed', e)
    loadError.value = '星云装配失败'
    loading.value = false
  }
})

onBeforeUnmount(() => {
  unmounted = true
  if (searchTimer) { clearTimeout(searchTimer); searchTimer = null }
  for (const timer of closeTimers) clearTimeout(timer)
  closeTimers.clear()
  if (controller) { controller.dispose(); controller = null }
  if (import.meta.env.DEV && window.__starmapDebug) {
    window.__starmapDebug.nebulaReady = false
  }
})

// 主题热切换
watch(() => ui.palette, () => {
  nextTick(() => controller?.applyTheme({ key: ui.palette, dark: !!ui.paletteMeta?.dark }))
})
</script>

<style scoped>
.nv-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--paper);
}
.nv-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-el);
  flex-wrap: wrap;
}
.nv-mode {
  font-family: var(--serif);
  font-size: 12px;
  color: var(--ink-soft);
  padding: 2px 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.nv-connect {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.nv-field { position: relative; }
.nv-input {
  width: 120px;
  padding: 4px 8px;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--paper);
  color: var(--ink);
  font-size: 12px;
  font-family: inherit;
}
.nv-input:focus { outline: none; border-color: var(--accent); }
.nv-sugg {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 20;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
  background: var(--paper-el);
  border: 1px solid var(--line);
  border-radius: 5px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  max-height: 240px;
  overflow-y: auto;
  min-width: 160px;
}
.nv-sugg li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
}
.nv-sugg li:hover { background: var(--hover); }
.nv-sugg-name { color: var(--ink); font-family: var(--serif); }
.nv-sugg-type { color: var(--ink-faint); font-size: 10px; }
.nv-arrow { color: var(--ink-soft); }
.nv-btn {
  padding: 4px 12px;
  border: 1px solid var(--accent);
  border-radius: 5px;
  background: var(--accent);
  color: var(--accent-text);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}
.nv-btn:disabled { opacity: 0.5; cursor: default; }
.nv-btn-ghost { background: transparent; color: var(--accent); }
.nv-msg { font-size: 12px; color: var(--ink-soft); }
.nv-msg.ok { color: var(--accent); font-weight: 600; }
.nv-msg.no { color: var(--ink-faint); }
.nv-spacer { flex: 1; }
.nv-count { font-family: ui-monospace, monospace; font-size: 11px; color: var(--ink-soft); }
.nv-stage {
  flex: 1;
  min-height: 0;
  position: relative;
  background: var(--paper);
  overflow: hidden;
}
.nv-stage :deep(canvas.nebula-canvas) {
  position: absolute;
  inset: 0;
  display: block;
  cursor: grab;
}
/* 定位即可:排版/配色由 EmptyState 自带 */
.nv-loading {
  position: absolute;
  inset: 0;
}
/* 引擎标签层（CSS2DRenderer DOM）定位兜底 */
.nv-stage :deep(.gx-label) {
  font-family: var(--serif), serif;
  font-size: 11px;
  color: var(--ink-mid);
  background: var(--caption, rgba(249,243,231,0.9));
  padding: 0 4px;
  border-radius: 3px;
  white-space: nowrap;
  pointer-events: none;
}
.nv-stage :deep(.gx-label.sel) {
  color: var(--accent);
  font-weight: 600;
}
</style>
