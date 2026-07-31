import { ref, watch } from 'vue'
import { useTimeStore, useSelectionStore } from '../stores'
import { getEntities } from '../api/client'

// 在世名单单源(M7):MomentPanel 的「此刻在世」chips 与 TimeColumn 的车道提升集共用
// 同一份 —— M7 车道按区宽容量封顶、超容入聚合道,若 chips 名单与柱上分道各算各的,
// 会出现「chip 有、柱上无条」,B3 双向 hover 互高亮落空。
// 取数跟「稳定年份」而非 year:year 每 rAF 一变,直接跟就是滑一下发几十个请求、
// 列表疯狂跳动;滑停 180ms(settledYear)后才取。
const aliveChips = ref([])
let started = false

export function useAlivePeople() {
  const store = useTimeStore()
  const selectionStore = useSelectionStore()
  if (!started) {
    started = true
    watch(() => store.settledYear, async (y) => {
      try {
        const r = await getEntities({ type: 'Person', year: y, limit: 30, prefer_seed: true, fields: 'id,name,born' })
        aliveChips.value = (r.items || []).filter(p => !p.id.startsWith('p_cbdb_')).slice(0, 16).map(p => ({
          id: p.id,
          label: p.name + ' · ' + (y - (p.born?.year || y)) + '岁',
          onClick: () => selectionStore.selectEntity(p.id),
        }))
      } catch { aliveChips.value = [] }
    }, { immediate: true })
  }
  return aliveChips
}
