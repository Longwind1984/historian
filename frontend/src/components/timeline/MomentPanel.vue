<template>
  <div class="mp-wrap" :class="{ 'mp-mobile': mobile }">
    <!-- 年号读数 -->
    <div class="mp-moment">
      <div class="mp-moment-title">
        <span class="mp-title-main">{{ momentTitle }}</span>
        <span class="mp-title-sub">{{ momentSub }}</span>
      </div>
      <div class="mp-moment-meta">{{ momentMeta }}</div>
    </div>

    <!-- 舆图 ／ 档案:纵向分栏,地图占比由用户拖定(此前写死 240px、仅占全屏面积一成)。
         拖手柄调比例、双击复位;地图右上角「放」键一键放大为主体。 -->
    <SplitPane ref="mapSplit" vertical :storage-key="mobile ? 'split-map-mobile' : 'split-map'"
               :min="mobile ? 64 : 120" :default="mobile ? 0.58 : 0.34">
      <template #left><MapPanel v-if="mapEnabled" @expand="toggleMapExpand" :expanded="mapExpanded" :auto-locate="!mobile" /></template>
      <template #right>
        <div class="mp-below">

    <!-- 在世人物 chips(实时随 year 刷新)-->
    <div class="mp-alive">
      <div class="mp-cap">此刻在世 · 点选</div>
      <div class="mp-chips" v-if="aliveChips.length">
        <!-- hover 双向互高亮(B3):chip hover -> setHover -> 柱上生命条显名提亮;
             反向,柱上 hover 人物 -> hoveredEntityId -> 此处 hov 加框。两方向都认
             store 里的 hoveredEntityId,不限定来源。 -->
        <span v-for="a in aliveChips" :key="a.id"
              class="mp-chip"
              :class="{sel: a.id === selectionStore.selectedEntityId, hov: a.id === selectionStore.hoveredEntityId}"
              role="button"
              tabindex="0"
              :aria-label="`查看${a.label}档案`"
              :aria-pressed="a.id === selectionStore.selectedEntityId"
              @click="a.onClick"
              @keydown.enter.prevent="a.onClick"
              @keydown.space.prevent="a.onClick"
              @focus="selectionStore.setHover(a.id)"
              @blur="selectionStore.setHover(null)"
              @mouseenter="selectionStore.setHover(a.id)"
              @mouseleave="selectionStore.setHover(null)">{{ a.label }}</span>
      </div>
      <EmptyState v-else compact glyph="人" text="此年前后暂无收录人物在世。" />
    </div>

    <!-- 深度档案(D2 合并):显式点击/键盘激活后才切换；hover 只做双向视觉提示。 -->
    <div class="mp-dossier" v-if="!mobile && displayId">
      <EntityProfile :entity-id="displayId" default-tab="relations">
        <template #actions="{ entity: ent, anchor }">
          <button class="mp-btn mp-btn-primary" @click="openInGraph">展开谱系星图 →</button>
          <button class="mp-btn" v-if="ent.type === 'Person' || ent.type === 'Polity'"
                  :disabled="!anchor" :title="anchor ? '' : '无地理数据'"
                  @click="locateOnMap(ent)"><MapPin :size="14" aria-hidden="true" />地图定位</button>
        </template>
      </EntityProfile>
    </div>

    <div class="mp-dossier" v-else-if="!mobile">
      <EmptyState glyph="案" text="点击时间柱上的人物或事件，展开档案。" />
    </div>

        </div>
      </template>
    </SplitPane>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineAsyncComponent } from 'vue'
import MapPin from '@lucide/vue/dist/esm/icons/map-pin.mjs'
import { useTimeStore, useSelectionStore, useUIStore } from '../../stores'
import { useAlivePeople } from '../../composables/useAlivePeople'
import { repYear } from '../../utils/repYear'
import { ERAS, fmtY, ganzhi, nianhao } from '../../styles/palettes'
import SplitPane from '../shared/SplitPane.vue'
import EntityProfile from '../shared/EntityProfile.vue'
import EmptyState from '../shared/EmptyState.vue'
const MapPanel = defineAsyncComponent(() => import('../map/MapPanel.vue'))

const { mobile, mapEnabled } = defineProps({
  mobile: { type: Boolean, default: false },
  mapEnabled: { type: Boolean, default: true },
})

const store = useTimeStore()
const selectionStore = useSelectionStore()

// 地图占比:拖手柄自由调;「放」键切换「主体」态 —— 本组件管右栏内的纵向占比,
// 外层横向分栏(时间柱让位)由 App 监听同一标志处理,二者合起来才够得上「主体」。
// 记住展开前的比例,收起时还原 —— 用户拖出来的比例不该被一次放大抹掉。
const ui = useUIStore()
const mapSplit = ref(null)
const mapExpanded = computed(() => ui.mapExpanded)
const MAP_EXPANDED = 0.82
let ratioBeforeExpand = null
function toggleMapExpand() { ui.toggleMapExpanded() }
watch(() => ui.mapExpanded, (on) => {
  const sp = mapSplit.value
  if (!sp) return
  if (on) { ratioBeforeExpand = sp.ratio; sp.setRatio(MAP_EXPANDED) }
  else { sp.setRatio(ratioBeforeExpand ?? 0.34) }
})

// === 档案展示的实体：显式选中唯一权威；hover 只保留跨区域高亮。 ===
// 只传 id:实体/关系/链接/年谱/同代的取数全在 EntityProfile(经 useEntityDetail),
// 本壳不再自取 —— 两套档案卡合并后,字段一处维护。
const displayId = computed(() => selectionStore.selectedEntityId)

// === 在世人物 chips ===
// M7 起名单单源化(useAlivePeople):TimeColumn 的车道提升集也用同一份,
// 保证「chip 有、柱上必有条」,B3 双向 hover 互高亮不因聚合道而落空。
const aliveChips = useAlivePeople()

// === 年号读数 ===
// 读数跟稳定年份:与在世列表同源。若标题即时而列表滞后,二者打架比都滞后更糟。
// 即时读数在左侧时间柱的游标上(那是光标,本就该跟手)。
// (旧 activePolity stub 恒 return null 且无模板引用,随 D2 一并删除。)
const momentTitle = computed(() => {
  const y = store.settledYear
  const era = ERAS.find(e => y >= e[1] && y < e[2])
  return era ? era[0] : (y < 0 ? '先秦' : '近世')
})
const momentSub = computed(() => {
  const y = store.settledYear
  const nh = nianhao(y)
  const gz = ganzhi(y)
  // D1:去「 CE」后缀(负年已由 fmtY 显示「前」)
  return (nh ? nh + ' · ' : '') + (gz ? gz + ' · ' : '') + fmtY(y)
})
const momentMeta = computed(() => {
  return `此刻在世 ${aliveChips.value.length} 人`
})

function openInGraph() { ui.setRoute('graph') }

// 实体的代表年份抽成共享真源(utils/repYear.js,B1):搜索跳年与地图定位同一优先级,
// 只许改一处。此处 locateOnMap 仍需要它把时间柱带到实体的年代。
// 地理锚点判断在 EntityProfile(hasGeoAnchor 插槽 prop),与 MapPanel 飞行分支同源。
function locateOnMap(ent) {
  if (!ent) return
  // 走显式定位请求而非重复 selectEntity:选中同一实体时 watch 不触发,请求通道(nonce)
  // 才能保证连点两次都飞。顺带把时间柱带到代表年份、把地图放大为主体 —— 点了「定位」
  // 用户要看的就是地图,藏在两成高的小格里等于没定位。
  selectionStore.requestLocate(ent.id, ent.type)
  const y = repYear(ent)
  if (y != null) store.setYear(y)
  ui.mapExpanded = true
}
</script>

<style scoped>
.mp-wrap { height: 100%; overflow-y: auto; background: var(--paper-el); border-left: 1px solid var(--line); transition: var(--transition-theme); }

.mp-moment { padding: 16px 20px 12px; border-bottom: 1px solid var(--line); }
.mp-moment-title { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.mp-title-main { font-family: var(--serif); font-weight: 900; font-size: 28px; line-height: 1; color: var(--ink); }
.mp-title-sub { font-family: var(--serif); font-size: 13px; color: var(--accent); }
.mp-moment-meta { font-size: 11px; color: var(--ink-soft); margin-top: 5px; }

/* 地图高度由纵向分栏给定(此前写死 240px);其下为可滚的档案区 */
.mp-below { height: 100%; overflow-y: auto; overflow-x: hidden; }

.mp-alive { padding: 12px 20px 6px; }
.mp-cap { font-size: 10px; letter-spacing: 0.16em; color: var(--ink-faint); text-transform: uppercase; margin-bottom: 7px; }
.mp-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.mp-chip { display: inline-block; padding: 3px 10px; border-radius: 13px; font-size: 12px; border: 1px solid var(--line); background: var(--chip); color: var(--ink-mid); cursor: pointer; transition: background 0.1s; }
.mp-chip:hover { background: var(--hover); }
.mp-chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
/* B3 互高亮:柱上(或任何来源)hover 到的人,chip 加朱框对号;.sel 选中态优先保持原样 */
.mp-chip.hov { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent-glow); }
.mp-chip.sel { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }

.mp-dossier { border-top: 1px solid var(--line); padding: 14px 20px 22px; }

/* 壳自供的操作按钮(EntityProfile 只给操作区容器) */
.mp-btn { flex: 1; padding: 9px; border-radius: 7px; font-size: 12px; cursor: pointer; border: 1px solid var(--line); background: var(--paper-el); color: var(--ink-mid); font-family: inherit; transition: var(--transition-theme); display: inline-flex; align-items: center; justify-content: center; gap: 5px; }
.mp-btn-primary { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
.mp-btn-primary:hover { opacity: 0.88; }
.mp-btn:hover { background: var(--hover); }
.mp-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.mp-btn:disabled:hover { background: var(--paper-el); }

.mp-mobile {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border-left: 0;
}
.mp-mobile .mp-moment { padding: 12px 18px 10px; }
.mp-mobile .mp-title-main { font-size: 24px; }
.mp-mobile .mp-alive { padding: 8px 18px 14px; }
.mp-mobile .mp-chips { gap: 4px; }
.mp-mobile .mp-chip { padding: 3px 8px; font-size: 11px; }
</style>
