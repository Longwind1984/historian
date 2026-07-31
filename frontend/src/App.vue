<template>
  <div class="app" :class="{ 'companion-mode': companionMode }" ref="appRoot" v-if="!loading && !error">
    <header class="mast">
      <div class="mast-brand">
        <span class="mast-logo">紀</span>
        <div class="mast-brand-text">
          <div class="mast-title"><span>紀年圖譜</span><span class="mast-title-suffix"> · 時間柱</span></div>
          <!-- D1 文案分层:品牌层从繁(紀年圖譜/以時為軸),UI 层从简,英文残留清除 -->
          <div class="mast-subtitle">以時為軸</div>
        </div>
      </div>
      <div class="mast-search-wrap"><SearchBar ref="searchBarRef" /></div>
      <span class="mast-spacer"></span>
      <div class="mast-route">
        <button :class="{active: ui.route === 'timeline'}" @click="ui.setRoute('timeline')">时间柱</button>
        <button :class="{active: ui.route === 'graph'}" @click="ui.setRoute('graph')">谱系星图</button>
        <button :class="{active: ui.route === 'explore'}" @click="ui.setRoute('explore')">探索</button>
      </div>
      <button class="mast-help" title="快捷键帮助 (?)" aria-label="打开快捷键帮助" @click="helpOpen = !helpOpen">
        <Keyboard :size="16" :stroke-width="1.8" aria-hidden="true" />
      </button>
      <button
        class="mast-info"
        type="button"
        title="资料来源与致谢"
        aria-label="打开资料来源与致谢"
        aria-haspopup="dialog"
        aria-controls="attribution-dialog"
        :aria-expanded="creditsOpen"
        @click="creditsOpen = true"
      ><LibraryBig :size="16" :stroke-width="1.8" aria-hidden="true" /></button>
      <button
        class="mast-palette"
        type="button"
        :title="themeToggleLabel"
        :aria-label="themeToggleLabel"
        @click="togglePalette"
      >
        <Moon v-if="ui.palette === '夜'" :size="15" :stroke-width="1.8" aria-hidden="true" />
        <Sun v-else :size="15" :stroke-width="1.8" aria-hidden="true" />
        <span>{{ ui.palette }}</span>
      </button>
      <div class="mast-year" v-if="ui.route === 'timeline' || ui.route === 'explore'">
        <div class="mast-year-main">{{ yearTitle }}</div>
        <div v-if="yearSub" class="mast-year-sub">{{ yearSub }}</div>
      </div>
    </header>
    <!-- T4.6 人物身份/重要性筛选：作用于时间柱在世列表与图谱 2D 节点；
         星云/时空柱为概览模式不接筛选，故仅在 timeline 或 graph+web 时显示 -->
    <FilterBar v-if="ui.route === 'timeline' || (ui.route === 'graph' && ui.view === 'web')" />
    <main class="app-body" v-if="ui.route === 'timeline'">
      <MobileTimelineLayout v-if="isMobile" />
      <SplitPane v-else ref="mainSplit" storage-key="split-timeline">
        <template #left><TimeColumn /></template>
        <template #right><MomentPanel /></template>
      </SplitPane>
    </main>
    <main class="app-body app-body-graph" v-else-if="ui.route === 'graph'">
      <GraphView />
    </main>
    <main class="app-body app-body-explore" v-else-if="ui.route === 'explore'">
      <ExplorationView />
    </main>
  </div>
  <div class="splash" v-else-if="loading">
    <div class="splash-logo">紀</div>
    <div class="splash-title">紀年圖譜</div>
    <div class="splash-sub">加载中…</div>
  </div>
  <!-- D5 空态统一:后端断连升级为全屏 EmptyState + 重试(重跑 dataStore.init) -->
  <EmptyState v-else full glyph="斷" text="无法连接后端"
              :sub="error ? '请先启动服务 · ' + error : '请先启动服务'"
              action-text="重试" @action="boot" />
  <!-- C1 全局快捷键浮层:跳年框 / 帮助表(浮层挂载于根,不受路由切换影响) -->
  <YearJump v-if="jumpOpen" @confirm="onJumpConfirm" @close="jumpOpen = false" />
  <HotkeyHelp v-if="helpOpen" @close="helpOpen = false" />
  <AttributionDialog v-if="creditsOpen" @close="creditsOpen = false" />
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, defineAsyncComponent } from 'vue'
import { useDataStore } from './stores/useDataStore'
import { useTimeStore } from './stores/useTimeStore'
import { useSelectionStore } from './stores/useSelectionStore'
import { useUIStore } from './stores/useUIStore'
import { useExplorationStore } from './stores/useExplorationStore'
import { useMapStoryStore } from './stores/useMapStoryStore'
import Keyboard from '@lucide/vue/dist/esm/icons/keyboard.mjs'
import LibraryBig from '@lucide/vue/dist/esm/icons/library-big.mjs'
import Moon from '@lucide/vue/dist/esm/icons/moon.mjs'
import Sun from '@lucide/vue/dist/esm/icons/sun.mjs'
import { fmtY, ganzhi, nianhao } from './styles/palettes'
import SearchBar from './components/shared/SearchBar.vue'
import SplitPane from './components/shared/SplitPane.vue'
import FilterBar from './components/shared/FilterBar.vue'
import YearJump from './components/shared/YearJump.vue'
import HotkeyHelp from './components/shared/HotkeyHelp.vue'
import EmptyState from './components/shared/EmptyState.vue'
import AttributionDialog from './components/shared/AttributionDialog.vue'
import { useHotkeys } from './composables/useHotkeys'
import { PRIVATE_EXPLORATIONS_ENABLED } from './config/distribution'

// 懒加载：重依赖视图(MapLibre/星图 three)按需加载，不阻塞首屏
const TimeColumn = defineAsyncComponent(() => import('./components/timeline/TimeColumn.vue'))
const MomentPanel = defineAsyncComponent(() => import('./components/timeline/MomentPanel.vue'))
const MobileTimelineLayout = defineAsyncComponent(() => import('./components/timeline/MobileTimelineLayout.vue'))
const GraphView = defineAsyncComponent(() => import('./views/StarmapView.vue'))
const ExplorationView = defineAsyncComponent(() => import('./views/ExplorationView.vue'))

const dataStore = useDataStore()
const timeStore = useTimeStore()
const selectionStore = useSelectionStore()
const ui = useUIStore()
const explorationStore = useExplorationStore()
const mapStoryStore = useMapStoryStore()

const appRoot = ref(null)
const searchBarRef = ref(null)
const creditsOpen = ref(false)
const companionMode = new URLSearchParams(window.location.search).get('companion') === '1'
function mediaMatches(query) {
  try {
    return typeof window !== 'undefined'
      && typeof window.matchMedia === 'function'
      && window.matchMedia(query).matches
  } catch {
    return false
  }
}
const isMobile = ref(mediaMatches('(max-width: 720px)'))
let mobileMedia = null
let themeMedia = null
let themeFallbackTimer = 0

// C1 全局快捷键:/ 聚焦搜索、←→ 步进、Space 播放、g 跳年、1/2/3 星图 tab、
// t 回时间柱、Esc 分层关、? 帮助。键位表见 useHotkeys.js。
const { helpOpen, jumpOpen, onJumpConfirm } = useHotkeys({
  timeStore, ui, selectionStore,
  focusSearch: () => searchBarRef.value && searchBarRef.value.focus(),
})

// URL 恢复要赶在一切子组件挂载之前:TimeColumn/星图都是异步组件,若等 dataStore.init()
// 完成再恢复,它们的挂载默认值(滚到 750、默认选中李白)会先跑一遍。setup 阶段恢复后,
// 任何组件挂载时读到的都是 URL 指定的年份与选中实体。
explorationStore.hydrate()
ui.loadFromUrl(timeStore, selectionStore, explorationStore)
if (ui.route === 'explore') {
  if (!PRIVATE_EXPLORATIONS_ENABLED && !explorationStore.isSampleWorkspace) {
    explorationStore.openSample()
    ui.syncToUrl(timeStore, selectionStore, explorationStore)
  }
  explorationStore.syncTime()
}
// 已打开页面改 hash(粘贴分享链接)也要重载 —— 此前只在挂载时恢复一次,
// 同文档导航完全不生效,这是 handoff 记录的「#year 不生效」主因。
function onHashChange() { ui.loadFromUrl(timeStore, selectionStore, explorationStore) }

// 地图「放大为主体」的外层一半:时间柱让位。右栏内的纵向占比由 MomentPanel 管,
// 二者听同一个 ui.mapExpanded —— 只调右栏内部最多到全屏两成,称不上主体。
const mainSplit = ref(null)
const MAIN_MAP_RATIO = 0.22   // 时间柱压到两成,余下让给右栏(地图)
let mainRatioBefore = null
watch(() => ui.mapExpanded, (on) => {
  const sp = mainSplit.value
  if (!sp) return
  if (on) { mainRatioBefore = sp.ratio; sp.setRatio(MAIN_MAP_RATIO) }
  else { sp.setRatio(mainRatioBefore ?? 0.5) }
})
const loading = ref(true)
const error = ref(null)
const nextPalette = computed(() => ui.palette === '夜' ? '澄' : '夜')
const themeToggleLabel = computed(
  () => `当前${ui.palette}色主题，切换到${nextPalette.value}色主题`,
)
function togglePalette() { ui.setPalette(nextPalette.value) }

const yearTitle = computed(() => {
  if (ui.route === 'explore') {
    if (explorationStore.entryOpen || !explorationStore.hasWorkspace) return '探索'
    if (explorationStore.workspaceKind === 'question') {
      return explorationStore.snapshot?.brief?.time_range || '时间待确认'
    }
    if (explorationStore.workspaceKind === 'document') return '时间待确认'
    return explorationStore.currentScene?.date || explorationStore.range
  }
  const y = timeStore.year
  return nianhao(y) || fmtY(y)
})
const yearSub = computed(() => {
  if (ui.route === 'explore') {
    if (explorationStore.entryOpen || !explorationStore.hasWorkspace) return ''
    if (explorationStore.workspaceKind === 'question') {
      const confirmed = explorationStore.snapshot?.scope_contract?.fields_needing_confirmation?.length === 0
      return confirmed ? '用户问题 · 范围已确认' : '用户问题 · 范围待确认'
    }
    if (explorationStore.workspaceKind === 'document') return '私人文本 · 尚未建立 Scene'
    return `${explorationStore.range} · 当前 Scene`
  }
  const y = timeStore.year
  const gz = ganzhi(y)
  // D1:去掉「 CE」后缀 —— 负年已由 fmtY 显示「前」,正年直书「N 年」
  return (gz ? gz + ' · ' : '') + fmtY(y)
})

onMounted(() => {
  window.addEventListener('hashchange', onHashChange)
  try {
    mobileMedia = window.matchMedia('(max-width: 720px)')
    isMobile.value = mobileMedia.matches
    mobileMedia.addEventListener('change', onMobileChange)
  } catch {
    mobileMedia = null
  }
  try {
    themeMedia = window.matchMedia('(prefers-color-scheme: dark)')
    themeMedia.addEventListener('change', onThemeChange)
  } catch {
    // 缺少系统主题能力时，每分钟跨过 06:00/18:00 即自然切换。
    themeFallbackTimer = window.setInterval(() => ui.syncPaletteToEnvironment(), 60_000)
  }
  ui.syncPaletteToEnvironment()
  boot()
})

function onMobileChange(event) { isMobile.value = event.matches }
function onThemeChange() { ui.syncPaletteToEnvironment() }

// 初始化与「重试」共用同一条引导路径:断连页的 EmptyState action 即重跑此函数
async function boot() {
  loading.value = true
  error.value = null
  try {
    await dataStore.init()
    if (companionMode) await explorationStore.restorePrivateWorkspace()
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
    await nextTick()
    if (appRoot.value) ui.setRootEl(appRoot.value)
    else ui.setRootEl(document.documentElement)
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', onHashChange)
  if (mobileMedia) mobileMedia.removeEventListener('change', onMobileChange)
  if (themeMedia) themeMedia.removeEventListener('change', onThemeChange)
  if (themeFallbackTimer) window.clearInterval(themeFallbackTimer)
})

// 状态变化 → URL 同步
watch(() => [timeStore.year, selectionStore.selectedEntityId, ui.route, ui.palette, ui.basemap, explorationStore.sceneIndex], () => {
  ui.syncToUrl(timeStore, selectionStore, explorationStore)
})

// 三套播放互斥且离开路由即停，避免后台计时器继续改写共享时间。
watch(() => ui.route, (route) => {
  if (route !== 'timeline') timeStore.stopPlay()
  if (route !== 'explore') explorationStore.pause()
  if (route !== 'timeline') mapStoryStore.pause()
  if (route === 'explore') {
    if (!PRIVATE_EXPLORATIONS_ENABLED && !explorationStore.isSampleWorkspace) {
      explorationStore.openSample()
      ui.syncToUrl(timeStore, selectionStore, explorationStore)
    }
    explorationStore.syncTime()
  }
})

watch(appRoot, (el) => { if (el) ui.setRootEl(el) })
</script>

<style scoped>
.app {
  display: grid;
  grid-template-rows: 58px auto 1fr;
  grid-template-columns: 1fr;
  height: 100vh;
  width: 100vw;
  background: var(--paper);
  color: var(--ink);
  overflow: hidden;
  transition: var(--transition-theme);
}
.mast {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 20px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-el);
  z-index: 30;
  transition: var(--transition-theme);
}
.mast-brand { display: flex; align-items: center; gap: 11px; }
.mast-logo {
  display: inline-flex; align-items: center; justify-content: center;
  width: 33px; height: 33px; border-radius: 5px;
  background: var(--accent); color: var(--accent-text);
  font-family: var(--serif); font-weight: 700; font-size: 18px;
}
.mast-brand-text { line-height: 1.15; }
.mast-title { font-family: var(--serif); font-weight: 900; font-size: 17px; color: var(--ink); }
.mast-subtitle { font-size: 8.5px; letter-spacing: 0.2em; color: var(--ink-soft); }
.mast-search-wrap { flex: 0 1 420px; }
.mast-spacer { flex: 1; }
.mast-route {
  display: flex; gap: 2px; background: var(--field);
  border: 1px solid var(--line); border-radius: 8px; padding: 3px;
}
.mast-route button {
  padding: 5px 12px; border: none; border-radius: 5px;
  font-family: inherit; font-size: 12.5px;
  background: transparent; color: var(--ink-mid); cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.mast-route button.active { background: var(--accent); color: var(--accent-text); }
.mast-palette {
  min-width: 46px; height: 28px; padding: 0 7px; border-radius: 7px;
  border: 1px solid var(--line); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  gap: 5px; font-family: inherit; font-size: 11px; line-height: 1;
  color: var(--ink-soft); background: var(--field);
  transition: color 0.12s, border-color 0.12s, background 0.12s;
}
.mast-palette svg { display: block; flex: 0 0 auto; }
.mast-palette:hover { color: var(--accent); border-color: var(--accent); background: var(--hover); }
.mast-palette:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.mast-year { text-align: right; }
.mast-year-main { font-family: var(--serif); font-weight: 700; font-size: 15px; color: var(--ink); }
.mast-year-sub { font-size: 10px; color: var(--ink-soft); }
/* C1 顶部工具入口：语义图标、克制软底，与对应浮层/对话框同键。 */
.mast-help, .mast-info {
  width: 28px; height: 28px; border-radius: 7px;
  border: 1px solid var(--line); background: var(--field);
  color: var(--ink-soft); cursor: pointer; padding: 0;
  display: inline-flex; align-items: center; justify-content: center;
  transition: color 0.12s, border-color 0.12s, background 0.12s;
}
.mast-help svg, .mast-info svg { display: block; }
.mast-help:hover, .mast-info:hover {
  color: var(--accent); border-color: var(--accent); background: var(--hover);
}
.mast-help:focus-visible, .mast-info:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.app-body { grid-row: 3; min-height: 0; display: flex; overflow: hidden; }
.app-body-graph { display: block; }
.app-body-explore { display: block; }
.app.companion-mode { grid-template-rows: 48px auto 1fr; }
.companion-mode .mast { gap: 10px; padding: 0 12px; }
.companion-mode .mast-search-wrap,
.companion-mode .mast-route,
.companion-mode .mast-help,
.companion-mode .mast-info,
.companion-mode .mast-palette,
.companion-mode .mast-year { display: none; }
.companion-mode .mast-brand-text { display: block; }
.companion-mode .mast-title-suffix,
.companion-mode .mast-subtitle { display: none; }
.companion-mode .mast-spacer::after {
  content: '微信读书联动';
  color: var(--ink-soft);
  font-size: 10px;
}

@media (min-width: 721px) and (max-width: 1200px) {
  .mast { gap: 10px; padding: 0 12px; }
  .mast-brand { gap: 8px; }
  .mast-title { white-space: nowrap; font-size: 15px; }
  .mast-title-suffix, .mast-subtitle { display: none; }
  .mast-search-wrap { flex: 0 1 330px; min-width: 210px; }
  .mast-route button { padding: 5px 8px; white-space: nowrap; }
  .mast-year { min-width: 102px; }
  .mast-year-main, .mast-year-sub { white-space: nowrap; }
}

@media (max-width: 720px) {
  .app { grid-template-rows: 54px auto 1fr; }
  .mast {
    gap: 8px;
    padding: 0 10px;
    overflow: visible;
  }
  .mast-brand { flex: 0 0 auto; gap: 8px; }
  .mast-logo { width: 30px; height: 30px; font-size: 17px; }
  .mast-title { font-size: 15px; white-space: nowrap; }
  .mast-title-suffix, .mast-subtitle { display: none; }
  .mast-search-wrap { flex: 1 1 60px; min-width: 46px; max-width: 72px; }
  .mast-spacer { display: none; }
  .mast-route { flex: 0 0 auto; }
  .mast-route button { padding: 5px 5px; font-size: 10.5px; white-space: nowrap; }
  .mast-palette, .mast-year, .mast-help { display: none; }
  .mast-info { flex: 0 0 28px; padding: 0; }
  .app-body { position: relative; min-height: 0; }
}
</style>
