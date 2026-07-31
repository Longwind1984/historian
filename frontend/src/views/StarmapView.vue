<template>
  <div class="sm-wrap">
    <div class="sm-header">
      <button class="sm-back" @click="ui.setRoute('timeline')">← 返回时间柱</button>
      <div class="sm-title">
        <span class="sm-seal">譜</span>
        <span>谱系星图</span>
        <span class="sm-sub" v-if="selectedName">· {{ selectedName }}</span>
      </div>
      <div class="sm-tabs">
        <button v-for="t in TABS" :key="t.key" class="sm-tab"
                :class="{ active: ui.view === t.key }" :data-tab="t.key"
                @click="ui.setView(t.key)">{{ t.label }}</button>
      </div>
      <span style="flex:1"></span>
      <span class="sm-year">此刻 {{ timeStore.year }} 年</span>
    </div>

    <div class="sm-body">
      <!-- 图谱 2D -->
      <div v-if="ui.view === 'web'" class="sm-graph-row">
        <WebGraph class="sm-graph-main" />
        <aside class="sm-detail" v-if="selectionStore.selectedEntityId">
          <EntityDetail :entity-id="selectionStore.selectedEntityId" />
        </aside>
      </div>

      <!-- 星云 3D（T3.2 Galaxy 引擎移植）-->
      <div v-else-if="ui.view === 'nebula'" class="sm-graph-row">
        <NebulaView class="sm-graph-main" />
        <aside class="sm-detail" v-if="selectionStore.selectedEntityId">
          <EntityDetail :entity-id="selectionStore.selectedEntityId" />
        </aside>
      </div>

      <!-- 时空柱 3D（T3.3）-->
      <div v-else-if="ui.view === 'column'" class="sm-graph-row">
        <ColumnView class="sm-graph-main" />
        <aside class="sm-detail" v-if="selectionStore.selectedEntityId">
          <EntityDetail :entity-id="selectionStore.selectedEntityId" />
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, defineAsyncComponent } from 'vue'
import { useTimeStore, useSelectionStore, useUIStore } from '../stores'
import { getEntity } from '../api/client'
import EntityDetail from '../components/graph/EntityDetail.vue'

// WebGraph 带 d3-force，按需加载不阻塞首屏（与 TimeColumn 同级懒加载）
const WebGraph = defineAsyncComponent(() => import('../components/starmap/WebGraph.vue'))
// NebulaView 带 three，独立 chunk：仅星云 tab 首次激活时加载（内部再动态 import 引擎）
const NebulaView = defineAsyncComponent(() => import('../components/starmap/NebulaView.vue'))
// ColumnView 带 three，独立 chunk：仅时空柱 tab 首次激活时加载
const ColumnView = defineAsyncComponent(() => import('../components/starmap/ColumnView.vue'))

const TABS = [
  { key: 'web', label: '图谱' },
  { key: 'nebula', label: '星云' },
  { key: 'column', label: '时空柱' },
]

const timeStore = useTimeStore()
const selectionStore = useSelectionStore()
const ui = useUIStore()
const selectedName = ref('')

watch(() => selectionStore.selectedEntityId, async (id) => {
  if (!id) { selectedName.value = ''; return }
  try {
    const e = await getEntity(id)
    selectedName.value = e.name || ''
  } catch { selectedName.value = '' }
}, { immediate: true })

// tab 状态写回 URL（view 字段）。App.vue 的 watch 不含 view，这里自行触发同步。
onMounted(() => {
  watch(() => ui.view, () => ui.syncToUrl(timeStore, selectionStore))
})
</script>

<style scoped>
.sm-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--paper);
  transition: var(--transition-theme);
}
.sm-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  height: 52px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-el);
  flex-shrink: 0;
}
.sm-back {
  padding: 5px 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: transparent;
  color: var(--ink-mid);
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
}
.sm-back:hover { background: var(--hover); }
.sm-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--serif);
  font-weight: 700;
  font-size: 17px;
  color: var(--ink);
}
.sm-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 5px;
  background: var(--accent);
  color: var(--accent-text);
  font-size: 15px;
  font-weight: 700;
}
.sm-sub { color: var(--ink-soft); font-weight: 400; font-size: 14px; }
.sm-tabs {
  display: flex;
  gap: 2px;
  background: var(--field);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 3px;
}
.sm-tab {
  padding: 5px 14px;
  border: none;
  border-radius: 5px;
  font-family: var(--serif);
  font-size: 13px;
  background: transparent;
  color: var(--ink-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.sm-tab:hover { color: var(--ink); }
.sm-tab.active { background: var(--accent); color: var(--accent-text); }
.sm-year {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: var(--ink-soft);
}
.sm-body { flex: 1; min-height: 0; position: relative; }
.sm-graph-row { display: flex; height: 100%; }
.sm-graph-main { flex: 1; min-width: 0; }
.sm-detail {
  width: 360px;
  flex-shrink: 0;
  border-left: 1px solid var(--line);
  background: var(--paper-el);
  overflow-y: auto;
  padding: 0.6rem 0.8rem;
}
</style>
