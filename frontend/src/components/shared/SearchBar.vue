<template>
  <div ref="rootRef" class="search-bar">
    <Search class="search-icon" :size="16" :stroke-width="1.8" aria-hidden="true" />
    <input
      ref="inputRef"
      v-model="query"
      @input="onInput"
      @focus="focused = true"
      @blur="onBlur"
      @keydown="onKeydown"
      placeholder="搜索人物 / 政权 / 派系 / 事件…"
      role="combobox"
      aria-label="搜索历史实体"
      aria-autocomplete="list"
      aria-haspopup="listbox"
      aria-controls="global-search-results"
      :aria-expanded="resultsOpen"
      :aria-activedescendant="activeOptionId"
      style="width: 100%;"
    />
    <div class="search-results" v-if="resultsOpen">
      <!-- C2 类型筛选 chips:结果里出现了哪些类型就给哪些印章,单选,默认全部 -->
      <div class="sb-chips" role="group" aria-label="搜索结果类型" v-if="typeChips.length > 1">
        <button class="sb-chip" :class="{ active: !typeFilter }"
                aria-label="显示全部类型" :aria-pressed="!typeFilter"
                @click="setTypeFilter('')">全部</button>
        <button v-for="t in typeChips" :key="t" class="sb-chip"
                :class="{ active: typeFilter === t }"
                :aria-label="`筛选${dataStore.typeMeta(t).label || t}`"
                :aria-pressed="typeFilter === t"
                @click="setTypeFilter(typeFilter === t ? '' : t)">{{ sealGlyph(t) }}</button>
      </div>
      <div id="global-search-results" role="listbox" aria-label="搜索建议">
        <div
          v-for="(r, i) in filtered"
          :key="r.id"
          :id="optionId(r)"
          class="item"
          :class="{ hl: i === hlIndex }"
          role="option"
          :aria-selected="i === hlIndex"
          @mousedown.prevent="select(r)"
          @mouseenter="hlIndex = i"
        >
          <span class="icon">{{ dataStore.typeMeta(r.type).label?.charAt(0) || '?' }}</span>
          <div>
            <div>
              {{ r.name }}
              <span v-if="modernBadge(r)" class="sb-modern">今名·{{ r.modern_name }}</span>
            </div>
            <div class="meta">
              {{ dataStore.typeMeta(r.type).label }}
              <span v-if="r.born || r.died">· {{ yearOf(r.born) }}–{{ yearOf(r.died) }}</span>
              <span v-if="r.founded || r.ended">· {{ yearOf(r.founded) }}–{{ yearOf(r.ended) }}</span>
            </div>
          </div>
        </div>
        <!-- C2 空态:无结果时给提示而非空弹层 -->
        <div class="sb-empty" role="status" v-if="!filtered.length">未寻得『{{ query }}』· 试试朝代名或帝王名</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Search from '@lucide/vue/dist/esm/icons/search.mjs'
import { useDataStore, useSelectionStore, useTimeStore, useUIStore } from '../../stores'
import { getEntities } from '../../api/client'
import { repYear } from '../../utils/repYear'
import { SEALS } from '../../styles/palettes'

const dataStore = useDataStore()
const selectionStore = useSelectionStore()
const timeStore = useTimeStore()
const ui = useUIStore()
const query = ref('')
const results = ref([])
const focused = ref(false)
const loading = ref(false)
const hlIndex = ref(0)        // 键盘高亮行(C2)
const typeFilter = ref('')    // 类型筛选(C2):空 = 全部,单选
const inputRef = ref(null)
const rootRef = ref(null)
let timer = null
const resultsOpen = computed(() => !!(focused.value && query.value && (results.value.length || !loading.value)))
const activeOptionId = computed(() => {
  if (!resultsOpen.value || !filtered.value.length) return undefined
  return optionId(filtered.value[hlIndex.value] || filtered.value[0])
})

// C1 快捷键「/」的落点:App 经 ref 调 focus
function focus() { inputRef.value && inputRef.value.focus() }
defineExpose({ focus })

// 结果中出现过的类型(保持 SEALS 顺序,印章稳定不跳)
const typeChips = computed(() => {
  const present = new Set(results.value.map(r => r.type))
  return Object.keys(SEALS).filter(t => present.has(t))
})
const filtered = computed(() =>
  typeFilter.value ? results.value.filter(r => r.type === typeFilter.value) : results.value
)
function sealGlyph(t) { return SEALS[t]?.glyph || '?' }
function optionId(r) { return `global-search-option-${r.id}` }
function setTypeFilter(type) {
  typeFilter.value = type
  hlIndex.value = 0
}

// C2 今名徽标:名/别名都未命中而 modern_name 命中 -> 标「今名·xx」
function modernBadge(r) {
  const q = query.value.trim()
  if (!q || !r.modern_name || !r.modern_name.includes(q)) return false
  if ((r.name || '').includes(q)) return false
  const aliases = [...(r.alias || []), ...(r.aliases || [])]
  if (aliases.some(a => (a || '').includes(q))) return false
  return true
}

function onInput() {
  clearTimeout(timer)
  typeFilter.value = ''
  if (!query.value || query.value.length < 1) {
    results.value = []
    loading.value = false
    return
  }
  loading.value = true
  timer = setTimeout(async () => {
    try {
      // fields 白名单须覆盖 repYear 的四态时间锚(born/floruit/died/reign)与
      // Event/Battle 的 date,否则代表年推导静默落空、搜索跳年失效。
      // C2 增补 modern_name(今名徽标)与 alias/aliases(徽标判定时排除别名命中)。
      const data = await getEntities({ q: query.value, limit: 12, fields: 'id,name,modern_name,alias,aliases,born,died,founded,ended,floruit_start,reign_start,date' })
      results.value = data.items
      hlIndex.value = 0
    } catch (e) {
      results.value = []
    } finally {
      loading.value = false
    }
  }, 200)
}

function onBlur() {
  setTimeout(() => {
    if (!rootRef.value?.contains(document.activeElement)) focused.value = false
  }, 150)
}

// C2 键盘导航:↑/↓ 移高亮(滚动进视野),Enter 选高亮,Esc 收弹层
function onKeydown(e) {
  const list = filtered.value
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    if (!list.length) return
    e.preventDefault()
    const d = e.key === 'ArrowDown' ? 1 : -1
    hlIndex.value = (hlIndex.value + d + list.length) % list.length
    const el = e.target.parentElement.querySelectorAll('.search-results .item')[hlIndex.value]
    if (el) el.scrollIntoView({ block: 'nearest' })
    return
  }
  if (e.key === 'Enter') {
    if (focused.value && list.length) { e.preventDefault(); select(list[hlIndex.value] || list[0]) }
    return
  }
  if (e.key === 'Escape' && focused.value) {
    results.value = []
    focused.value = false
  }
}

function select(r) {
  selectionStore.selectEntity(r.id, r.type, 'search')
  // B1 搜索闭环:点击选中(仅点击,hover 预览不触发)且实体可定年时,时间柱滚到它的
  // 年代 —— TimeColumn 的 watch store.year 负责平滑滚动与 lens 脉冲。Place 等无代表年
  // 的类型不滚柱(地图仍经 MapPanel 的 watch 飞过去)。仅在时间柱页跳年;星图页年份
  // 不动,相机联动由星云/时空柱自己的 watch 接管。
  if (ui.route === 'timeline') {
    const y = repYear(r)
    if (y != null) timeStore.setYear(y)
  }
  query.value = r.name
  results.value = []
  focused.value = false
}

function yearOf(ym) {
  return ym && ym.year != null ? ym.year : ''
}
</script>

<style scoped>
/* C2:类型筛选 chips / 今名徽标 / 空态(其余样式在 main.css 的 .search-results) */
.search-bar { margin-left: 1rem; flex: 0 1 360px; }
.search-icon {
  position: absolute;
  left: 0.72rem;
  top: 50%;
  z-index: 2;
  transform: translateY(-50%);
  color: var(--ink-soft);
  pointer-events: none;
}
.search-bar input { padding-left: 2.25rem; }
.sb-chips {
  display: flex; gap: 4px; padding: 0.35rem 0.7rem;
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; background: var(--bg-card); z-index: 1;
}
.sb-chip {
  min-width: 22px; padding: 1px 6px;
  border: 1px solid var(--border); border-radius: 5px;
  background: transparent; color: var(--text-dim);
  font-size: 12px; cursor: pointer; line-height: 1.5;
}
.sb-chip.active { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
.sb-modern {
  margin-left: 6px; padding: 0 5px;
  border: 1px solid var(--border); border-radius: 4px;
  font-size: 0.72em; color: var(--text-dim);
}
.item.hl { background: var(--bg-elevated); }
.sb-empty { padding: 0.5rem 0.7rem; color: var(--text-dim); font-size: 0.82em; }

@media (max-width: 720px) {
  .search-bar { margin-left: 0; width: 100%; min-width: 0; flex: none; }
  .search-bar input {
    height: 34px;
    min-width: 0;
    padding: 0.35rem 0.55rem 0.35rem 2rem;
    font-size: 12px;
  }
  .search-icon { left: 0.6rem; }
  .search-results {
    position: fixed;
    top: 54px;
    left: 10px;
    right: 10px;
    max-height: min(360px, calc(100vh - 70px));
  }
}
</style>
