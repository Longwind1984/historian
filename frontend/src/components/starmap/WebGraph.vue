<template>
  <div class="wg-wrap">
    <!-- 工具条：模式 / 类型筛选 / 朝代着色 / 路径 / 物理预设 -->
    <div class="wg-toolbar">
      <span class="wg-mode" :data-mode="debugMode">{{ modeLabel }}</span>
      <div class="wg-chips">
        <button v-for="t in TYPES" :key="t.key" class="wg-chip"
                :class="{ active: typeFilter[t.key] }"
                :style="{ '--c': `var(--cat-${t.key.toLowerCase()})` }"
                @click="toggleType(t.key)">{{ t.label }}</button>
      </div>
      <button class="wg-chip" :class="{ active: dynastyColor }" @click="dynastyColor = !dynastyColor">朝代着色</button>
      <button class="wg-chip" :class="{ active: pathOpen }" @click="pathOpen = !pathOpen">路径</button>
      <span class="wg-spacer"></span>
      <span class="wg-count">{{ stats.nodeCount }} 节点 · {{ stats.edgeCount }} 边<span v-if="stats.capped" class="wg-capped"> · 仅显示前 {{ stats.nodeCount }} 项</span></span>
    </div>

    <!-- 控制条：深度 / 双链阈值 / 物理三参 -->
    <div class="wg-controls">
      <label class="wg-ctrl" v-if="mode === 'local'">
        深度 <b>{{ depth }}</b>
        <input type="range" min="1" max="3" step="1" v-model.number="depth"
               class="wg-range" data-testid="depth-slider" />
      </label>
      <label class="wg-ctrl" v-if="mode === 'global'">
        双链 ≥ <b>{{ minLinks }}</b>
        <input type="range" min="1" max="10" step="1" v-model.number="minLinks" class="wg-range" />
      </label>
      <label class="wg-ctrl">
        斥力
        <input type="range" min="-400" max="-20" step="10" v-model.number="phys.charge"
               class="wg-range" @input="physPreset = ''" />
      </label>
      <label class="wg-ctrl">
        链距
        <input type="range" min="10" max="200" step="5" v-model.number="phys.linkDistance"
               class="wg-range" @input="physPreset = ''" />
      </label>
      <label class="wg-ctrl">
        向心
        <input type="range" min="0" max="1" step="0.02" v-model.number="phys.center"
               class="wg-range" @input="physPreset = ''" />
      </label>
      <select class="wg-preset" v-model="physPreset" @change="onPresetChange">
        <option value="">自定义</option>
        <option value="sparse">疏朗</option>
        <option value="compact">紧凑</option>
        <option value="radial">放射</option>
      </select>
    </div>

    <!-- 路径面板(D1):原始 id 输入 -> 联想检索选实体(复用星云 connect-two 的
         /links/search 联想模式),选中成 chip(印章+名,可清除);未选词时按文本兜底解析 -->
    <div class="wg-path" v-if="pathOpen">
      <div class="wg-pick">
        <span v-if="pathFromEntity" class="wg-pick-chip">
          <Seal :type="pathFromEntity.type" :size="14" />
          <span class="wg-pick-name">{{ pathFromEntity.name }}</span>
          <button class="wg-pick-x" title="清除" @click="clearPathPick('from')">×</button>
        </span>
        <template v-else>
          <input v-model="pathFromText" placeholder="起点 · 输入检索" class="wg-input" data-testid="path-from-input"
                 @input="onPathSearchInput('from')" @focus="pathFromOpen = pathFromSugg.length > 0" @blur="delayedPathClose('from')" />
          <ul v-if="pathFromOpen && pathFromSugg.length" class="wg-sugg">
            <li v-for="h in pathFromSugg" :key="h.id" @mousedown.prevent="pickPathSugg('from', h)">
              <span class="wg-sugg-name">{{ h.name }}</span><span class="wg-sugg-type">{{ typeLabel(h.type) }}</span>
            </li>
          </ul>
        </template>
      </div>
      <span class="wg-arrow">→</span>
      <div class="wg-pick">
        <span v-if="pathToEntity" class="wg-pick-chip">
          <Seal :type="pathToEntity.type" :size="14" />
          <span class="wg-pick-name">{{ pathToEntity.name }}</span>
          <button class="wg-pick-x" title="清除" @click="clearPathPick('to')">×</button>
        </span>
        <template v-else>
          <input v-model="pathToText" placeholder="终点 · 输入检索" class="wg-input" data-testid="path-to-input"
                 @input="onPathSearchInput('to')" @focus="pathToOpen = pathToSugg.length > 0" @blur="delayedPathClose('to')" />
          <ul v-if="pathToOpen && pathToSugg.length" class="wg-sugg">
            <li v-for="h in pathToSugg" :key="h.id" @mousedown.prevent="pickPathSugg('to', h)">
              <span class="wg-sugg-name">{{ h.name }}</span><span class="wg-sugg-type">{{ typeLabel(h.type) }}</span>
            </li>
          </ul>
        </template>
      </div>
      <button class="wg-btn" @click="runPath">查路径</button>
      <button class="wg-btn wg-btn-ghost" v-if="pathActive" @click="clearPath">清除</button>
      <span class="wg-path-msg" :class="{ ok: pathFound, no: pathActive === false && pathMsg }">{{ pathMsg }}</span>
    </div>

    <!-- 画布舞台 -->
    <div class="wg-stage" ref="stageRef">
      <canvas ref="canvasRef" class="wg-canvas" data-testid="webgraph-canvas"
              @mousedown="onMouseDown" @mousemove="onMouseMove" @mouseup="onMouseUp"
              @mouseleave="onMouseLeave" @dblclick="onDblClick" @wheel.prevent="onWheel" />
      <!-- D5 空态统一:全局未选中提示(文案随 D1 改「双链前列」) -->
      <EmptyState v-if="mode === 'global' && !selectionStore.selectedEntityId"
                  class="wg-hint" glyph="指"
                  text="未选中实体 · 显示双链前列子图"
                  sub="单击节点进入局部图,双击换中心,拖拽钉住" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onBeforeUnmount, watchEffect } from 'vue'
import { forceSimulation, forceLink, forceManyBody, forceX, forceY, forceCollide } from 'd3-force'
import { useSelectionStore, useUIStore, useFilterStore } from '../../stores'
import { getGlobalGraph, getNeighbors, getShortestPath, getEntity, getEntities, getRelations, fullTextSearch } from '../../api/client'
import { SEALS, PALETTES } from '../../styles/palettes'
import { DYNASTY_COLORS, DYNASTY_RANGES, COEXISTING_DYNASTY_IDX, DYNASTY_NAME_TO_IDX } from '../../starmap/engine/inkPalette.js'
import Seal from '../shared/Seal.vue'
import EmptyState from '../shared/EmptyState.vue'

const selectionStore = useSelectionStore()
const ui = useUIStore()
const filter = useFilterStore()

// ---- 朝代色：统一来自 inkPalette（单一来源，与星云/时空柱同源；14 朝代 founded 升序）----
// 纸墨派生 DYN_INK（保色相、降饱和、统一中明度，对齐 Nebula nodeLightness 纸面观感）；
// 夜派生 DYN_STAR（2D 无 bloom，统一提亮到 L=60% 自身够亮成星，S 保留不荧光）。
function _shiftHex(hex, sMul, lTo) {
  const n = parseInt(hex.slice(1), 16)
  let r = (n >> 16 & 255) / 255, g = (n >> 8 & 255) / 255, b = (n & 255) / 255
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b)
  let h = 0, s = 0, l = (mx + mn) / 2
  if (mx !== mn) {
    const d = mx - mn
    s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn)
    if (mx === r) h = (g - b) / d + (g < b ? 6 : 0)
    else if (mx === g) h = (b - r) / d + 2
    else h = (r - g) / d + 4
    h /= 6
  }
  s *= sMul; l = lTo
  const hue = (p, q, t) => { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1/6) return p + (q - p) * 6 * t; if (t < 1/2) return q; if (t < 2/3) return p + (q - p) * (2/3 - t) * 6; return p }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s
  const p = 2 * l - q
  return '#' + [hue(p, q, h + 1/3), hue(p, q, h), hue(p, q, h - 1/3)]
    .map(x => Math.round(Math.max(0, Math.min(1, x)) * 255).toString(16).padStart(2, '0')).join('')
}
const DYN_INK = DYNASTY_COLORS.map((h) => _shiftHex(h, 0.92, 0.5))
const DYN_STAR = DYNASTY_COLORS.map((h) => _shiftHex(h, 1, 0.6))

const TYPES = Object.keys(SEALS).filter(k => k !== 'Dynasty').map(k => ({
  key: k, label: SEALS[k].label,
}))

// ---- 响应式状态（仅 UI 需要；节点/边为高频数据，用 plain let 避免 Vue 代理开销）----
const mode = ref('global')            // 'local' | 'global'（path 为叠加层）
const pathOpen = ref(false)
// D1 路径起终点:联想检索选中实体(chip),未选词时按文本兜底解析成 id
const pathFromText = ref('')
const pathFromEntity = ref(null)
const pathFromSugg = ref([])
const pathFromOpen = ref(false)
const pathToText = ref('')
const pathToEntity = ref(null)
const pathToSugg = ref([])
const pathToOpen = ref(false)
let pathSearchTimer = null
const pathMsg = ref('')
const pathActive = ref(false)
const pathFound = ref(false)
const depth = ref(1)
const minLinks = ref(2)
const dynastyColor = ref(false)
const physPreset = ref('')
const phys = reactive({ charge: -120, linkDistance: 45, center: 0.06 })
const typeFilter = reactive(
  TYPES.reduce((m, t) => { m[t.key] = true; return m }, {})
)
const stats = reactive({ nodeCount: 0, edgeCount: 0, capped: false })

// ---- 非响应式热数据 ----
let nodes = []
let edges = []
let nodeMap = new Map()
let adjacency = new Map()
let sim = null

// ---- T4.6 人物 roles/importance 缓存 ----
// /global 与 /neighbors 节点白名单不含 roles/importance，故懒加载全量 Person meta
// 供节点筛选（模块级缓存，组件卸载不重拉；limit 上限 2000，分 3 页并发）
const personMeta = new Map()  // id -> { roles, importance, dynastyRef }
// 政权 id -> 朝代下标。由 includes 关系(Dynasty → Polity)构建 —— 朝代归属查表用，
// 别在前端另抄一份映射，那是漂移的开始。
const polityDynastyIdx = new Map()
let personMetaPromise = null
function ensurePersonMeta() {
  if (personMetaPromise) return personMetaPromise
  personMetaPromise = (async () => {
    try {
      // fields 是白名单：filter/读取用到的字段必须列出，漏了就恒为 undefined 且不报错
      const F = 'id,roles,importance,dynasty_ref'
      const [p0, p1, p2, dyns, incs] = await Promise.all([
        getEntities({ type: 'Person', limit: 2000, offset: 0, fields: F }),
        getEntities({ type: 'Person', limit: 2000, offset: 2000, fields: F }),
        getEntities({ type: 'Person', limit: 2000, offset: 4000, fields: F }),
        getEntities({ type: 'Dynasty', limit: 100, fields: 'id,name' }),
        getRelations({ type: 'includes', limit: 500 }),
      ])
      for (const r of [p0, p1, p2]) for (const it of (r.items || [])) {
        personMeta.set(it.id, {
          roles: it.roles || [], importance: it.importance ?? null,
          dynastyRef: it.dynasty_ref ?? null,
        })
      }
      const dynName = new Map((dyns.items || []).map(d => [d.id, d.name]))
      for (const rel of (incs.items || incs || [])) {
        const idx = DYNASTY_NAME_TO_IDX[dynName.get(rel.from)]
        if (idx != null && rel.to) polityDynastyIdx.set(rel.to, idx)
      }
    } catch (e) {
      console.error('[WebGraph] ensurePersonMeta failed', e)
    }
  })()
  return personMetaPromise
}
// 非响应式热数据（续）
let view = { x: 0, y: 0, k: 1 }
let hoveredId = null
let hoverNeighbors = new Set()
let pathNodeIds = new Set()
let pathEdgeKeys = new Set()
let cssW = 0, cssH = 0, dpr = 1, ctx = null
let vars = {}
let rafPending = false
// 拖拽 / 平移
let dragNode = null, dragMoved = false, dragWasPinned = false, downX = 0, downY = 0, panStart = null

const stageRef = ref(null)
const canvasRef = ref(null)

const modeLabel = ref('全局 · 双链前列')   // D1:去英文 Top,UI 层从简
const debugMode = ref('global')

// ============ 朝代归属（与后端 DynastyIndex 同逻辑）============
// 一等依据：dynasty_ref（人物所属政权）→ includes 关系 → 朝代。年份判不了 1050 年的人
// 是辽是宋（那取决于他在哪），故年份只是缺 dynasty_ref 时的回落，且回落时并存朝代降级。
function dynastyIdxOf(e) {
  const ref = personMeta.get(e?.id)?.dynastyRef
  if (ref) {
    const idx = polityDynastyIdx.get(ref)
    if (idx != null) return idx
  }
  const b = e?.born, d = e?.died
  let y = (b && typeof b === 'object') ? b.year : null
  if (y == null && d && typeof d === 'object') y = d.year
  if (y == null) return -1
  // 两轮：先试非并存朝代，都不中再试并存的（辽/金）
  for (const coexisting of [false, true]) {
    for (let i = 0; i < DYNASTY_RANGES.length; i++) {
      if (COEXISTING_DYNASTY_IDX.has(i) !== coexisting) continue
      if (y >= DYNASTY_RANGES[i][1] && y <= DYNASTY_RANGES[i][2]) return i
    }
  }
  return -1
}

// ============ 几何 ============
function nodeRadius(n) {
  const r = 4 + 1.6 * Math.log(1 + (n.degree || 0))
  return Math.max(4, Math.min(14, r))
}
function edgeKey(a, b) { return a < b ? a + '|' + b : b + '|' + a }

// ============ 读 CSS 变量（纸墨色板）============
function readVars() {
  const stage = stageRef.value
  if (!stage) return
  const cs = getComputedStyle(stage)
  const v = (n) => cs.getPropertyValue(n).trim()
  vars = {
    ink: v('--ink') || '#2c2721',
    accent: v('--accent') || '#c24a32',
    edge: v('--edge') || v('--line') || '#cdc0a4',
    inkFaint: v('--ink-faint') || '#a9a08b',
    inkMid: v('--ink-mid') || '#4a4539',
    serif: v('--serif') || 'serif',
    cat: {
      Person: v('--cat-person'), Polity: v('--cat-polity'), Faction: v('--cat-faction'),
      Event: v('--cat-event'), Battle: v('--cat-battle'), Place: v('--cat-place'),
      Title: v('--cat-title'), Dynasty: v('--cat-dynasty'),
    },
  }
  scheduleRender()
}
function typeColorOf(n) { return vars.cat?.[n.type] || vars.inkMid }
function dynColorOf(n) {
  if (n.dynastyIdx < 0) return vars.inkFaint
  return (PALETTES[ui.palette]?.dark ? DYN_STAR : DYN_INK)[n.dynastyIdx]
}

// ============ 调度渲染 ============
function scheduleRender() {
  if (rafPending) return
  rafPending = true
  requestAnimationFrame(() => { rafPending = false; render() })
}

// ============ 数据装载 ============
function makeNode(e, centerId) {
  const isCenter = centerId && e.id === centerId
  const meta = personMeta.get(e.id)
  return {
    id: e.id, name: e.name || e.id, type: e.type || 'Person',
    degree: 0, born: e.born, died: e.died, dynastyIdx: dynastyIdxOf(e),
    roles: meta?.roles || [], importance: meta?.importance ?? null,
    x: isCenter ? 0 : (Math.random() - 0.5) * 80,
    y: isCenter ? 0 : (Math.random() - 0.5) * 80,
    vx: 0, vy: 0, fx: null, fy: null, pinned: false,
  }
}

function buildGraph(rawNodes, rawEdges, centerId) {
  // 聚合边（同 pair 多关系 -> count）
  const pairMap = new Map()
  const idSet = new Set(rawNodes.map(n => n.id))
  for (const e of rawEdges) {
    const a = e.from, b = e.to
    if (!a || !b || !idSet.has(a) || !idSet.has(b)) continue
    const k = edgeKey(a, b)
    const pe = pairMap.get(k) || { u: a < b ? a : b, v: a < b ? b : a, count: 0, types: new Set() }
    pe.count++
    if (e.type) pe.types.add(e.type)
    pairMap.set(k, pe)
  }
  const newEdges = [...pairMap.values()]

  // 节点度：global 用真实双链度(out+in)；local 用诱导子图入射数
  const deg = new Map()
  for (const n of rawNodes) {
    deg.set(n.id, (n.out != null && n.in != null) ? (n.out + n.in) : 0)
  }
  for (const e of newEdges) {
    deg.set(e.u, (deg.get(e.u) || 0) + e.count)
    deg.set(e.v, (deg.get(e.v) || 0) + e.count)
  }

  nodes = rawNodes.map(n => {
    const nd = makeNode(n, centerId)
    nd.degree = deg.get(n.id) || 0
    return nd
  })
  // 节点上限（depth 3 的超 hubs 保护；BFS 序即近邻序，取前 N。
  // manyBody 走 Barnes-Hut 四叉树 O(n log n)，架构可承 5k；边渲染 O(E)/帧是真实瓶颈，故限到 1k）
  const NODE_CAP = 1000
  const capped = rawNodes.length > NODE_CAP
  if (nodes.length > NODE_CAP) {
    const keep = new Set(nodes.slice(0, NODE_CAP).map(n => n.id))
    if (centerId) keep.add(centerId)
    nodes = nodes.filter(n => keep.has(n.id))
    newEdges.forEach(e => { e._drop = !keep.has(e.u) || !keep.has(e.v) })
  }
  edges = newEdges.filter(e => !e._drop)
  nodeMap = new Map(nodes.map(n => [n.id, n]))

  pathActive.value = false
  pathFound.value = false
  pathMsg.value = ''
  pathNodeIds = new Set()
  pathEdgeKeys = new Set()
  stats.nodeCount = nodes.length
  stats.edgeCount = edges.length
  stats.capped = capped

  rebuildSim()
  setTimeout(fitView, 500)
}

function buildAdjacency() {
  adjacency = new Map()
  for (const n of nodes) adjacency.set(n.id, new Set())
  for (const e of edges) {
    adjacency.get(e.u)?.add(e.v)
    adjacency.get(e.v)?.add(e.u)
  }
}

// （重）建仿真：保留已有节点坐标（forceSimulation 不覆盖已存在的 x/y）
function rebuildSim() {
  if (sim) sim.stop()
  const links = edges.map(e => ({ source: e.u, target: e.v }))
  sim = forceSimulation(nodes)
    .force('link', forceLink(links).id(d => d.id).distance(phys.linkDistance).strength(0.5))
    .force('charge', forceManyBody().strength(phys.charge))
    .force('x', forceX(0).strength(phys.center))
    .force('y', forceY(0).strength(phys.center))
    .force('collide', forceCollide().radius(d => nodeRadius(d) + 3))
    .alpha(1).alphaDecay(0.04)
    .on('tick', scheduleRender)
  buildAdjacency()
  scheduleRender()
}

// ============ 加载 ============
async function loadGlobal() {
  mode.value = 'global'
  modeLabel.value = '全局 · 双链前列'   // D1:去英文 Top,UI 层从简
  try {
    const r = await getGlobalGraph(200, minLinks.value)
    buildGraph(r.nodes || [], r.edges || [], null)
    stats.capped = !!r.truncated
  } catch (e) {
    console.error('[WebGraph] loadGlobal failed', e)
    buildGraph([], [], null)
  }
}

async function loadLocal(id) {
  mode.value = 'local'
  modeLabel.value = '局部 · 以选中为中心'
  try {
    const r = await getNeighbors(id, depth.value)
    buildGraph(r.nodes || [], r.edges || [], id)
  } catch (e) {
    console.error('[WebGraph] loadLocal failed', e)
    buildGraph([{ id, name: id, type: 'Unknown' }], [], id)
  }
}

// ============ 路径模式（叠加高亮：路径节点/边朱印红，其余淡出）============
// 联想搜索:与星云 connect-two 同一模式(180ms 防抖 + mousedown 先选词后 blur)
const typeLabel = (t) => (SEALS[t] ? SEALS[t].label : t || '')
function onPathSearchInput(which) {
  const text = which === 'from' ? pathFromText.value : pathToText.value
  clearTimeout(pathSearchTimer)
  if (!text.trim()) {
    if (which === 'from') pathFromSugg.value = []
    else pathToSugg.value = []
    return
  }
  pathSearchTimer = setTimeout(async () => {
    try {
      const r = await fullTextSearch(text.trim(), 8)
      const list = r.hits || []
      if (which === 'from') { pathFromSugg.value = list; pathFromOpen.value = list.length > 0 }
      else { pathToSugg.value = list; pathToOpen.value = list.length > 0 }
    } catch { /* 忽略单次联想失败 */ }
  }, 180)
}
function pickPathSugg(which, hit) {
  const picked = { id: hit.id, name: hit.name, type: hit.type || 'Person' }
  if (which === 'from') { pathFromEntity.value = picked; pathFromOpen.value = false }
  else { pathToEntity.value = picked; pathToOpen.value = false }
}
function clearPathPick(which) {
  if (which === 'from') { pathFromEntity.value = null; pathFromText.value = ''; pathFromSugg.value = [] }
  else { pathToEntity.value = null; pathToText.value = ''; pathToSugg.value = [] }
}
function delayedPathClose(which) {
  // mousedown 选词先于 blur,延迟关闭避免点不到
  setTimeout(() => { if (which === 'from') pathFromOpen.value = false; else pathToOpen.value = false }, 120)
}
/** 未从联想选词时按文本兜底:精确名首命中 -> id,否则原样当 id(兼容老用法) */
async function resolvePathId(entity, text) {
  if (entity) return entity.id
  const t = (text || '').trim()
  if (!t) return ''
  try {
    const r = await fullTextSearch(t, 1)
    return r.hits?.[0]?.id || t
  } catch { return t }
}

async function runPath() {
  const from = await resolvePathId(pathFromEntity.value, pathFromText.value)
  const to = await resolvePathId(pathToEntity.value, pathToText.value)
  if (!from || !to) { pathMsg.value = '请选择起终点'; return }
  pathMsg.value = '查询中…'
  try {
    const r = await getShortestPath(from, to, 4)
    if (r && r.path && r.path.length) {
      const ids = new Set([from, to])
      const pe = new Set()
      for (const hop of r.path) {
        ids.add(hop.from); ids.add(hop.to)
        pe.add(edgeKey(hop.from, hop.to))
      }
      // 补全路径上不在当前图中的节点
      for (const id of ids) {
        if (!nodeMap.has(id)) {
          try {
            const e = await getEntity(id)
            const nd = makeNode(e, null)
            nodes.push(nd); nodeMap.set(id, nd)
          } catch { /* 忽略单个缺失 */ }
        }
      }
      // 补全路径边（用于力布局拉出链 + 高亮渲染）
      const existKeys = new Set(edges.map(e => edgeKey(e.u, e.v)))
      for (const hop of r.path) {
        const k = edgeKey(hop.from, hop.to)
        if (!existKeys.has(k)) {
          edges.push({ u: hop.from < hop.to ? hop.from : hop.to, v: hop.from < hop.to ? hop.to : hop.from, count: 1, types: new Set([hop.type]) })
          existKeys.add(k)
        }
      }
      pathNodeIds = ids
      pathEdgeKeys = pe
      pathActive.value = true
      pathFound.value = true
      pathMsg.value = `${r.path.length} 跳路径`
      stats.nodeCount = nodes.length
      stats.edgeCount = edges.length
      rebuildSim()
      setTimeout(fitView, 400)
    } else {
      pathActive.value = false
      pathFound.value = false
      pathMsg.value = '无路径（≤4 跳）'
    }
  } catch (e) {
    console.error('[WebGraph] runPath failed', e)
    pathActive.value = false
    pathFound.value = false
    pathMsg.value = '查询失败'
  }
}

function clearPath() {
  pathActive.value = false
  pathFound.value = false
  pathMsg.value = ''
  // 重载底层图，丢弃路径补入的节点/边
  if (selectionStore.selectedEntityId) loadLocal(selectionStore.selectedEntityId)
  else loadGlobal()
}

// ============ 物理预设 ============
const PRESETS = {
  sparse: { charge: -260, linkDistance: 90, center: 0.04 },
  compact: { charge: -60, linkDistance: 25, center: 0.12 },
  radial: { charge: -120, linkDistance: 40, center: 0.3 },
}
function onPresetChange() {
  const p = PRESETS[physPreset.value]
  if (!p) return
  phys.charge = p.charge
  phys.linkDistance = p.linkDistance
  phys.center = p.center
}

// ============ 渲染 ============
function nodeAlpha(n) {
  if (n.id === selectionStore.selectedEntityId) return 1
  if (pathActive.value) return pathNodeIds.has(n.id) ? 1 : 0.12
  if (hoveredId) {
    if (n.id === hoveredId || hoverNeighbors.has(n.id)) return 1
    return 0.12
  }
  return 1
}

// T4.6 人物筛选：非 Person 放行；Person 受 focusMode/activeRoles 约束（与类型 chips 共存）
function personVisible(n) { return filter.passes(n) }

function render() {
  if (!ctx || !canvasRef.value) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, cssW, cssH)
  ctx.translate(view.x, view.y)
  ctx.scale(view.k, view.k)

  const selectedId = selectionStore.selectedEntityId
  // ---- 边 ----
  for (const e of edges) {
    const a = nodeMap.get(e.u), b = nodeMap.get(e.v)
    if (!a || !b) continue
    if (!typeFilter[a.type] || !typeFilter[b.type]) continue
    if (!personVisible(a) || !personVisible(b)) continue
    const key = edgeKey(e.u, e.v)
    const onPath = pathActive.value && pathEdgeKeys.has(key)
    let alpha
    if (pathActive.value) alpha = onPath ? 0.95 : 0.06
    else if (hoveredId) alpha = (a.id === hoveredId || b.id === hoveredId) ? 0.85 : 0.06
    else alpha = 0.42
    ctx.globalAlpha = alpha
    ctx.strokeStyle = onPath ? vars.accent : vars.edge
    ctx.lineWidth = (1 + 0.5 * (e.count - 1)) / view.k
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1
    const ox = -dy / len * 4, oy = dx / len * 4
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    ctx.quadraticCurveTo(mx + ox, my + oy, b.x, b.y)
    ctx.stroke()
  }
  ctx.globalAlpha = 1

  // ---- 节点 ----
  let visNodeCount = 0
  for (const n of nodes) {
    if (!typeFilter[n.type] || !personVisible(n)) continue
    visNodeCount++
    const r = nodeRadius(n) + (n.id === selectedId ? 2.5 : 0)
    const alpha = nodeAlpha(n)
    const isHi = n.id === selectedId || (pathActive.value && pathNodeIds.has(n.id))
    ctx.globalAlpha = alpha
    // 墨点
    ctx.fillStyle = isHi ? vars.accent : vars.ink
    ctx.beginPath()
    ctx.arc(n.x, n.y, r, 0, 6.2832)
    ctx.fill()
    // 类型/朝代 印章色细环
    ctx.strokeStyle = dynastyColor.value ? dynColorOf(n) : typeColorOf(n)
    ctx.lineWidth = 1.5 / view.k
    ctx.beginPath()
    ctx.arc(n.x, n.y, r + 2 / view.k, 0, 6.2832)
    ctx.stroke()
    // hover 朱印晕
    if (n.id === hoveredId) {
      ctx.strokeStyle = vars.accent
      ctx.globalAlpha = 0.5
      ctx.lineWidth = 2 / view.k
      ctx.beginPath()
      ctx.arc(n.x, n.y, r + 5 / view.k, 0, 6.2832)
      ctx.stroke()
      ctx.globalAlpha = alpha
    }
    // 标签 LOD：zoom>1.5 或 选中/hover/钉住/路径
    if (n.id === selectedId || n.id === hoveredId || n.pinned ||
        (pathActive.value && pathNodeIds.has(n.id)) || view.k > 1.5) {
      ctx.globalAlpha = alpha
      ctx.fillStyle = vars.ink
      ctx.font = `${11 / view.k}px ${vars.serif}`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(n.name, n.x, n.y + r + 3 / view.k)
    }
  }
  ctx.globalAlpha = 1
  if (import.meta.env.DEV && window.__starmapDebug) {
    window.__starmapDebug.visibleNodeCount = visNodeCount
  }
}

// ============ 视图：fit / hit / zoom / pan ============
function fitView() {
  if (!nodes.length) { view = { x: cssW / 2, y: cssH / 2, k: 1 }; scheduleRender(); return }
  let minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9
  for (const n of nodes) {
    if (n.x < minx) minx = n.x; if (n.x > maxx) maxx = n.x
    if (n.y < miny) miny = n.y; if (n.y > maxy) maxy = n.y
  }
  const bw = Math.max(1, maxx - minx), bh = Math.max(1, maxy - miny)
  const pad = 70
  const k = Math.min((cssW - pad * 2) / bw, (cssH - pad * 2) / bh, 2.5)
  view.k = Math.max(0.3, k)
  const cx = (minx + maxx) / 2, cy = (miny + maxy) / 2
  view.x = cssW / 2 - cx * view.k
  view.y = cssH / 2 - cy * view.k
  scheduleRender()
}

function nodeAt(sx, sy) {
  const wx = (sx - view.x) / view.k, wy = (sy - view.y) / view.k
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i]
    if (!typeFilter[n.type] || !personVisible(n)) continue
    const r = nodeRadius(n) + (n.id === selectionStore.selectedEntityId ? 2.5 : 0) + 4 / view.k
    if ((n.x - wx) ** 2 + (n.y - wy) ** 2 <= r * r) return n
  }
  return null
}

function updateHoverNeighbors() {
  hoverNeighbors = hoveredId ? (adjacency.get(hoveredId) || new Set()) : new Set()
}

// ============ 鼠标交互 ============
function onMouseDown(e) {
  downX = e.offsetX; downY = e.offsetY
  const n = nodeAt(e.offsetX, e.offsetY)
  if (n) {
    dragNode = n; dragMoved = false; dragWasPinned = n.pinned
    if (sim) sim.alphaTarget(0.3).restart()
  } else {
    panStart = { x: e.offsetX - view.x, y: e.offsetY - view.y }
  }
}
function onMouseMove(e) {
  if (dragNode) {
    if (!dragMoved && (e.offsetX - downX) ** 2 + (e.offsetY - downY) ** 2 > 9) dragMoved = true
    if (dragMoved) {
      const wx = (e.offsetX - view.x) / view.k, wy = (e.offsetY - view.y) / view.k
      dragNode.fx = wx; dragNode.fy = wy; dragNode.pinned = true
      scheduleRender()
    }
  } else if (panStart) {
    view.x = e.offsetX - panStart.x
    view.y = e.offsetY - panStart.y
    scheduleRender()
  } else {
    const n = nodeAt(e.offsetX, e.offsetY)
    const id = n ? n.id : null
    if (id !== hoveredId) {
      hoveredId = id
      updateHoverNeighbors()
      if (canvasRef.value) canvasRef.value.style.cursor = id ? 'pointer' : 'grab'
      scheduleRender()
    }
  }
}
function onMouseUp() {
  if (dragNode) {
    if (!dragMoved) {
      if (dragWasPinned) {
        // 再点解除钉住
        dragNode.fx = null; dragNode.fy = null; dragNode.pinned = false
        if (sim) sim.alphaTarget(0.3).restart()
      } else {
        // 单击 = 选中（局部图以此为新中心，档案卡浮出）
        selectionStore.selectEntity(dragNode.id)
      }
    }
    if (sim) sim.alphaTarget(0)
    dragNode = null
  }
  panStart = null
}
function onMouseLeave() {
  if (hoveredId) { hoveredId = null; updateHoverNeighbors(); scheduleRender() }
  if (canvasRef.value) canvasRef.value.style.cursor = 'default'
}
function onDblClick(e) {
  const n = nodeAt(e.offsetX, e.offsetY)
  if (n) selectionStore.selectEntity(n.id)  // 双击换中心
}
function onWheel(e) {
  const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
  const nk = Math.max(0.2, Math.min(4, view.k * factor))
  const wx = (e.offsetX - view.x) / view.k, wy = (e.offsetY - view.y) / view.k
  view.k = nk
  view.x = e.offsetX - wx * nk
  view.y = e.offsetY - wy * nk
  scheduleRender()
}
function onKey(e) {
  if (ui.view !== 'web') return
  const tag = document.activeElement?.tagName
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return
  // C1:Space 让位给全局年代播放,谱系图适配视野改 f
  if (e.key === 'f' && !e.ctrlKey && !e.metaKey && !e.altKey) { fitView() }
}

function toggleType(key) { typeFilter[key] = !typeFilter[key]; scheduleRender() }

// ============ 尺寸 ============
function resize() {
  const stage = stageRef.value
  if (!stage) return
  const w = stage.clientWidth, h = stage.clientHeight
  if (w === cssW && h === cssH) return
  cssW = w; cssH = h; dpr = window.devicePixelRatio || 1
  const c = canvasRef.value
  if (c) { c.width = Math.max(1, Math.floor(w * dpr)); c.height = Math.max(1, Math.floor(h * dpr)) }
  scheduleRender()
}
let ro = null

// ============ 生命周期 ============
onMounted(async () => {
  ctx = canvasRef.value.getContext('2d')
  readVars()
  resize()
  ro = new ResizeObserver(resize)
  ro.observe(stageRef.value)
  window.addEventListener('keydown', onKey)
  // 预拉人物 roles/importance 供 T4.6 筛选（失败不阻塞：personMeta 空=Person importance 全 null，focusMode 开时会被过滤）
  await ensurePersonMeta()
  // 首次装载：有选中 -> 局部，否则全局
  if (selectionStore.selectedEntityId) loadLocal(selectionStore.selectedEntityId)
  else loadGlobal()
})

onBeforeUnmount(() => {
  if (sim) sim.stop()
  if (ro) ro.disconnect()
  window.removeEventListener('keydown', onKey)
})

// ============ watchers ============
// 选中实体变化 -> 局部图重载（无选中 -> 全局）
watch(() => selectionStore.selectedEntityId, (id) => {
  if (id) loadLocal(id)
  else if (mode.value !== 'global') loadGlobal()
})
// 深度滑杆
watch(depth, () => {
  if (mode.value === 'local' && selectionStore.selectedEntityId) loadLocal(selectionStore.selectedEntityId)
})
// 双链阈值（防抖）
let minLinksTimer = null
watch(minLinks, () => {
  if (mode.value !== 'global') return
  clearTimeout(minLinksTimer)
  minLinksTimer = setTimeout(loadGlobal, 250)
})
// T4.6 筛选态变化 -> 重绘（节点/边可见性随 focusMode/roles 变化）
watch(() => [filter.focusMode, filter.activeRoles.join(',')], () => scheduleRender())
// 物理三参联动
watch(phys, () => {
  if (!sim) return
  sim.force('charge').strength(phys.charge)
  sim.force('link').distance(phys.linkDistance)
  sim.force('x').strength(phys.center)
  sim.force('y').strength(phys.center)
  sim.alpha(0.5).restart()
}, { deep: true })
// 配色切换 -> 重读变量
watch(() => ui.palette, readVars)
// 类型/朝代开关只需重绘
watch([typeFilter, dynastyColor], scheduleRender, { deep: true })

// DEV 调试桩（E2E 用）
watchEffect(() => {
  debugMode.value = pathActive.value ? 'path' : mode.value
  if (import.meta.env.DEV) {
    window.__starmapDebug = {
      mode: debugMode.value,
      nodeCount: stats.nodeCount,
      pathFound: pathActive.value && pathFound.value,
    }
  }
})
</script>

<style scoped>
.wg-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--paper);
}
.wg-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-el);
  flex-wrap: wrap;
}
.wg-mode {
  font-family: var(--serif);
  font-size: 12px;
  color: var(--ink-soft);
  padding: 2px 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.wg-chips { display: flex; gap: 3px; flex-wrap: wrap; }
.wg-chip {
  padding: 3px 9px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: transparent;
  color: var(--ink-mid);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  position: relative;
}
.wg-chip::before {
  content: '';
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--c, var(--ink-faint));
  margin-right: 5px;
  vertical-align: middle;
  opacity: 0.45;
}
.wg-chip.active { background: var(--field); color: var(--ink); border-color: var(--ink-faint); }
.wg-chip.active::before { opacity: 1; }
.wg-spacer { flex: 1; }
.wg-count {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: var(--ink-soft);
}
.wg-capped { color: var(--accent); }
.wg-controls {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 5px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-el);
  flex-wrap: wrap;
}
.wg-ctrl {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-mid);
}
.wg-ctrl b { color: var(--accent); font-family: ui-monospace, monospace; min-width: 14px; text-align: center; }
.wg-range { width: 90px; vertical-align: middle; }
.wg-preset {
  padding: 3px 6px;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--field);
  color: var(--ink-mid);
  font-size: 12px;
  font-family: inherit;
}
.wg-path {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--field);
}
.wg-pick { position: relative; }
/* D1 选中实体 chip:印章 + 名 + 清除 */
.wg-pick-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: var(--paper);
  font-size: 12px;
}
.wg-pick-name { font-family: var(--serif); color: var(--ink); }
.wg-pick-x {
  border: none;
  background: transparent;
  color: var(--ink-faint);
  cursor: pointer;
  font-size: 13px;
  padding: 0 2px;
  line-height: 1;
}
.wg-pick-x:hover { color: var(--accent); }
.wg-sugg {
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
.wg-sugg li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
}
.wg-sugg li:hover { background: var(--hover); }
.wg-sugg-name { color: var(--ink); font-family: var(--serif); }
.wg-sugg-type { color: var(--ink-faint); font-size: 10px; }
.wg-input {
  width: 130px;
  padding: 4px 8px;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--paper);
  color: var(--ink);
  font-family: inherit;
  font-size: 12px;
}
.wg-input:focus { outline: none; border-color: var(--accent); }
.wg-arrow { color: var(--ink-soft); }
.wg-btn {
  padding: 4px 12px;
  border: 1px solid var(--accent);
  border-radius: 5px;
  background: var(--accent);
  color: var(--accent-text);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}
.wg-btn-ghost { background: transparent; color: var(--accent); }
.wg-path-msg { font-size: 12px; color: var(--ink-soft); }
.wg-path-msg.ok { color: var(--accent); font-weight: 600; }
.wg-path-msg.no { color: var(--ink-faint); }
.wg-stage {
  flex: 1;
  min-height: 0;
  position: relative;
  background: var(--paper);
}
.wg-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
}
/* D5 空态统一:画布角落提示 —— EmptyState 行内缩小版(横排小印章,不遮画布) */
.wg-hint {
  position: absolute;
  left: 12px;
  bottom: 10px;
  pointer-events: none;
  max-width: 60%;
  padding: 0;
  flex-direction: row;
  align-items: center;
  gap: 7px;
  text-align: left;
}
.wg-hint :deep(.empty-glyph) { width: 20px; height: 20px; font-size: 11px; border-radius: 4px; }
.wg-hint :deep(.empty-body) { flex-direction: column; align-items: flex-start; gap: 1px; }
.wg-hint :deep(.empty-text) { font-size: 11px; color: var(--ink-faint); }
.wg-hint :deep(.empty-sub) { font-size: 10px; color: var(--ink-faint); }
</style>
