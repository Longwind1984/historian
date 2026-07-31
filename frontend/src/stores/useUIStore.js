import { defineStore } from 'pinia'
import { PALETTES, PALETTE_KEYS, SEALS, applyPalette } from '../styles/palettes'
import {
  PUBLIC_EXPLORATION_DEMO_SLUG,
  RESTRICTED_MAPS_ENABLED,
} from '../config/distribution'

function paletteFromLocalTime(date = new Date()) {
  const hour = date.getHours()
  return hour >= 6 && hour < 18 ? '澄' : '夜'
}

// prefers-color-scheme 是无需权限的浏览器能力；只有运行环境不提供/调用失败时，
// 才以当地 06:00/18:00 近似日出日落。真正天文日出需要位置权限，不为换主题打扰用户。
export function detectEnvironmentPalette() {
  try {
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? '夜' : '澄'
    }
  } catch {
    // 非浏览器 WebView 可能暴露 matchMedia 但调用失败，降级到本地时间。
  }
  return paletteFromLocalTime()
}

// 底图键与 MapPanel 的 BASEMAPS 一一对应(素=本地古风,古=谭其骧图集,今=OSM,浅=CARTO,卫=Esri)。
// store 是唯一真相:组件读它,切换走 setBasemap —— 持久化与 URL 同步才有单点可挂。
const BASEMAP_KEYS = ['素', ...(RESTRICTED_MAPS_ENABLED ? ['古'] : []), '今', '浅', '卫']
const BASEMAP_DEFAULT = RESTRICTED_MAPS_ENABLED ? '古' : '素'
function detectInitialBasemap() {
  const saved = localStorage.getItem('history-kb-basemap')
  if (!RESTRICTED_MAPS_ENABLED && saved === '古') {
    localStorage.setItem('history-kb-basemap', BASEMAP_DEFAULT)
  }
  return BASEMAP_KEYS.includes(saved) ? saved : BASEMAP_DEFAULT
}

/** UI 设置 store：palette / route / basemap + URL 持久化 */
export const useUIStore = defineStore('ui', {
  state: () => ({
    palette: detectEnvironmentPalette(),
    route: 'timeline',   // 'timeline' | 'graph' | 'explore'
    view: 'web',         // 星图内 tab：'web' | 'nebula' | 'column'（仅 route=graph 时有意义）
    basemap: detectInitialBasemap(),
    // 地图「放大为主体」:地图嵌在右栏内,只调右栏内的纵向占比最多到全屏两成 ——
    // 称不上主体。故此标志同时驱动外层横向分栏(时间柱让位)与右栏纵向分栏。
    // 放在 store 而非逐层 emit:两个分栏分处 App 与 MomentPanel,无共同父级可传。
    mapExpanded: false,
    rootEl: null,
  }),
  getters: {
    paletteMeta: (state) => PALETTES[state.palette],
    sealMeta: () => (type) => SEALS[type] || SEALS.Person,
  },
  actions: {
    setPalette(key) {
      if (!PALETTE_KEYS.includes(key)) return
      this.palette = key
      this.applyPaletteToRoot()
    },
    syncPaletteToEnvironment() { this.setPalette(detectEnvironmentPalette()) },
    setRootEl(el) {
      this.rootEl = el
      this.applyPaletteToRoot()
    },
    applyPaletteToRoot() {
      if (this.rootEl) applyPalette(this.rootEl, this.palette)
    },
    setRoute(r) {
      if (['timeline', 'graph', 'explore'].includes(r)) this.route = r
    },
    setView(v) { if (['web', 'nebula', 'column'].includes(v)) this.view = v },
    setBasemap(b) {
      if (!BASEMAP_KEYS.includes(b)) return
      this.basemap = b
      localStorage.setItem('history-kb-basemap', b)
    },
    toggleMapExpanded() { this.mapExpanded = !this.mapExpanded },
    syncToUrl(timeStore, selectionStore, explorationStore = null) {
      const p = new URLSearchParams()
      p.set('year', timeStore.year)
      // entity 写成 id:Type(如 p_li_bai:Person):旧链接只存 id,跨会话恢复后类型只能靠
      // 重新拉实体猜。类型已知就带上;loadFromUrl 两种形式都认。
      if (selectionStore.selectedEntityId) {
        const t = selectionStore.selectedEntityType
        p.set('entity', t ? `${selectionStore.selectedEntityId}:${t}` : selectionStore.selectedEntityId)
      }
      if (this.route !== 'timeline') p.set('route', this.route)
      if (this.route === 'explore' && explorationStore?.isSampleWorkspace) {
        p.set('demo', PUBLIC_EXPLORATION_DEMO_SLUG)
      }
      if (this.route === 'explore' && explorationStore?.currentScene?.id) {
        p.set('scene', explorationStore.currentScene.id)
      }
      if (this.route === 'graph' && this.view !== 'web') p.set('view', this.view)
      if (this.palette !== '澄') p.set('palette', this.palette)
      if (this.basemap !== BASEMAP_DEFAULT) p.set('basemap', this.basemap)
      const hash = '#' + p.toString()
      if (window.location.hash !== hash) {
        window.history.replaceState(null, '', hash)
      }
    },
    loadFromUrl(timeStore, selectionStore, explorationStore = null) {
      const h = window.location.hash.slice(1)
      if (!h) return
      const p = new URLSearchParams(h)
      // 必须走 setYear:直接赋 year 会绕过 settledYear 的联动 —— 从 URL 恢复到 950 年时
      // 右栏与地图仍停在默认的 750,读数与游标对不上。
      if (p.get('year')) {
        const yy = parseInt(p.get('year'), 10)
        if (!Number.isNaN(yy)) timeStore.setYear(yy)
      }
      const ent = p.get('entity')
      if (ent) {
        // 新形式 id:Type;旧形式裸 id(类型留空,各面板拉实体后自取)
        // 直接写字段而非走 selectEntity:setup 阶段恢复不该触发 hover 抑制窗。
        // origin 标 'url',星图/时空柱认其为外部选中、正常联动(初挂载不自动飞,见各视图)。
        const ci = ent.lastIndexOf(':')
        if (ci > 0) {
          selectionStore.selectedEntityId = ent.slice(0, ci)
          selectionStore.selectedEntityType = ent.slice(ci + 1)
        } else {
          selectionStore.selectedEntityId = ent
        }
        selectionStore.origin = 'url'
      }
      const route = p.get('route')
      if (route && ['timeline', 'graph', 'explore'].includes(route)) this.route = route
      const demo = p.get('demo')
      if (
        this.route === 'explore'
        && demo === PUBLIC_EXPLORATION_DEMO_SLUG
        && explorationStore
      ) {
        explorationStore.openSample?.()
      }
      const sceneId = p.get('scene')
      if (this.route === 'explore' && sceneId && explorationStore) {
        const index = explorationStore.$state
          ? (explorationStore.currentScene?.id === sceneId
            ? explorationStore.sceneIndex
            : null)
          : null
        if (index == null) {
          // Scene id 的稳定解析由 store action 完成；未知 id 保留当前 Scene。
          explorationStore.selectSceneById?.(sceneId)
        }
      }
      const v = p.get('view')
      if (v && ['web', 'nebula', 'column'].includes(v)) this.view = v
      if (p.get('palette') && PALETTE_KEYS.includes(p.get('palette'))) {
        this.palette = p.get('palette')
      }
      const bm = p.get('basemap')
      if (bm && BASEMAP_KEYS.includes(bm)) this.basemap = bm
      else if (!RESTRICTED_MAPS_ENABLED && bm === '古') {
        this.basemap = BASEMAP_DEFAULT
        localStorage.setItem('history-kb-basemap', BASEMAP_DEFAULT)
        p.delete('basemap')
        window.history.replaceState(null, '', `#${p.toString()}`)
      }
    },
  },
})
