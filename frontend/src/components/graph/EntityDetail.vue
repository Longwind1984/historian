<template>
  <!-- D2 合并后本组件只剩壳:档案本体是共享 EntityProfile(详情/关系/链接/年谱/同代/史料
       与时间柱逐一对齐),此处只补星图侧栏的操作按钮,默认落「详情」tab。 -->
  <div class="graph-detail">
    <EntityProfile :entity-id="entityId" default-tab="detail">
      <template #actions="{ entity: ent, anchor }">
        <button class="primary" :disabled="!anchor" :title="anchor ? '' : '无地理数据'"
                @click="focusInMap(ent)">📍 在地图中定位</button>
        <button v-if="ent.type === 'Person' || ent.type === 'Faction'"
                @click="openInGraph">🕸 在关系图中展开</button>
        <button @click="selectionStore.clearSelection()">关闭</button>
      </template>
    </EntityProfile>
  </div>
</template>

<script setup>
import { useSelectionStore, useUIStore } from '../../stores'
import EntityProfile from '../shared/EntityProfile.vue'

defineProps({ entityId: { type: String, required: true } })
const selectionStore = useSelectionStore()
const ui = useUIStore()

function focusInMap(ent) {
  if (!ent) return
  // 地图在时间柱路由:先切回去,再发显式定位请求。请求存在 store 里,
  // MapPanel 挂载时会把滞留请求补发掉,时序上不用等。
  ui.setRoute('timeline')
  selectionStore.requestLocate(ent.id, ent.type)
}
function openInGraph() {
  // WebGraph 监听 selectedEntityId 自动以选中实体为中心重载局部图,
  // 只需切到星图的「图谱」tab,无需另传旗标。
  ui.setRoute('graph')
  ui.setView('web')
}
</script>

<style scoped>
.graph-detail { min-height: 0; overflow-y: auto; }
.graph-detail button:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
