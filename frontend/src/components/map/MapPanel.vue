<template>
  <div class="map-panel">
    <div id="map-container" ref="mapRef"></div>

    <!-- 地图工具：底图默认收起；与 MapLibre 缩放控件分居上下，避免遮挡。 -->
    <div class="map-tools">
      <div class="map-tool-row">
        <button class="bm-btn bm-layer-toggle" :class="{active: basemapOpen}"
                title="切换地图图层" aria-label="切换地图图层"
                :aria-expanded="basemapOpen" aria-controls="map-basemap-options"
                @click="basemapOpen = !basemapOpen">
          <Layers :size="17" :stroke-width="1.8" aria-hidden="true" />
        </button>
        <button class="bm-btn" :class="{active: expanded}"
                :title="expanded ? '收起地图' : '放大地图为主体'"
                :aria-label="expanded ? '收起地图' : '放大地图为主体'"
                :aria-pressed="expanded"
                @click="emit('expand')">
          <Minimize2 v-if="expanded" :size="17" :stroke-width="1.8" aria-hidden="true" />
          <Maximize2 v-else :size="17" :stroke-width="1.8" aria-hidden="true" />
        </button>
      </div>
      <div v-if="basemapOpen" id="map-basemap-options" class="map-basemap-switcher" role="group" aria-label="地图图层">
        <button v-for="b in BASEMAP_LIST" :key="b.id"
                :class="['bm-btn', {active: ui.basemap === b.id, disabled: disabledIds.includes(b.id)}]"
                :title="disabledIds.includes(b.id) ? '瓦片不可达 · 点击重试' : b.label"
                :aria-label="disabledIds.includes(b.id) ? `${b.label}底图瓦片不可达，激活重试` : `${b.label}底图`"
                :aria-pressed="ui.basemap === b.id"
                @click="switchBasemap(b.id)">
          <span class="bm-glyph">{{ b.glyph }}</span>
        </button>
      </div>
    </div>

    <!-- 历史播放只在地图成为主体后出现；收起地图即暂停，不在小窗里抢空间。 -->
    <MapStoryPlayer v-if="expanded" />

    <!-- 图例 -->
    <div class="map-overlay">
      <div class="map-year"><strong>{{ store.settledYear }} 年</strong> 地图记录<span
        v-if="ui.basemap === '古'" class="map-note-sub"> · 图集「{{ activeSheet ? activeSheet.label : fallbackSheetLabel + ' · 该年代图幅待补' }}」</span></div>
      <div v-if="legendEntries.length || administrativeCount" class="map-legend">
        <div v-if="administrativeCount" class="map-legend-item map-legend-admin">
          <span class="map-legend-dot" :style="{background: FALLBACK_COLOR}"></span>
          <span>CHGIS府级行政建置记录</span>
          <span class="map-legend-count">{{ administrativeCount }}</span>
        </div>
        <div v-for="(p, i) in legendEntries" :key="p.id != null ? p.id : 'item-' + i"
             class="map-legend-item map-legend-polity"
             :role="p.id != null ? 'button' : undefined"
             :tabindex="p.id != null ? 0 : undefined"
             :aria-label="p.id != null ? `查看${p.name}政权档案` : undefined"
             :aria-pressed="p.id != null ? p.id === selectionStore.selectedEntityId : undefined"
             @click="selectLegendPolity(p)"
             @keydown.enter.prevent="selectLegendPolity(p)"
             @keydown.space.prevent="selectLegendPolity(p)">
          <span class="map-legend-dot" :style="{background: p.color}"></span>
          <span>{{ p.name }} · 政权疆域</span>
          <span class="map-legend-count">{{ p.count }}</span>
        </div>
      </div>
      <!-- D5 空态统一:有疆域块但缺政权信息 / 整年无疆域,都用 EmptyState 紧凑态(可嵌浮层) -->
      <EmptyState v-else-if="territoryCount > 0" compact glyph="域"
                  :text="`疆域 ${territoryCount} 块`" sub="政权信息待补" />
      <!-- 无矢量疆域,但谭图有此年图幅(先秦/楚汉:郡县制前 CHGIS 无源,谭图有印刷图)。
           古底图上本图即疆域,不说「无数据」;非古底图给一键切古的入口。 -->
      <template v-else-if="yearSheet">
        <div v-if="ui.basemap === '古'" class="map-atlas-note">
          本图即谭其骧图集「{{ yearSheet.label }}」·矢量疆域无源
        </div>
        <button v-else class="map-atlas-switch" @click="switchBasemap('古')">
          此期疆域见「古」谭其骧图集「{{ yearSheet.label }}」
        </button>
      </template>
      <EmptyState v-else compact text="无疆域数据" />
    </div>

    <!-- 疆域 hover tooltip：DOM 元素，跟随光标 -->
    <div v-if="tooltipVisible" class="territory-tooltip"
         :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }">
      <div class="tt-primary">{{ tooltipPrimary }}</div>
      <div v-if="tooltipSecondary" class="tt-secondary">{{ tooltipSecondary }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import Layers from '@lucide/vue/dist/esm/icons/layers.mjs'
import Maximize2 from '@lucide/vue/dist/esm/icons/maximize-2.mjs'
import Minimize2 from '@lucide/vue/dist/esm/icons/minimize-2.mjs'
import maplibregl from 'maplibre-gl'
// 本项目此前从未引入 maplibre 的样式表 —— 其 .maplibregl-marker{position:absolute}
// 因此不存在,Marker 落回文档流,标注恒定偏出地图约一个容器高(实测 496px)。
// 控件(缩放/归属)的样式亦源于此。放在 MapPanel 内引入:仅用到地图的页面才付这份体积。
import 'maplibre-gl/dist/maplibre-gl.css'
import { useTimeStore, useSelectionStore, useUIStore, useMapStoryStore } from '../../stores'
import { getTerritories, getEntity } from '../../api/client'
import { catMeta, catHue } from '../../styles/palettes'
import { RESTRICTED_MAPS_ENABLED } from '../../config/distribution'
import EmptyState from '../shared/EmptyState.vue'
import MapStoryPlayer from './MapStoryPlayer.vue'

const { autoLocate, expanded } = defineProps({
  expanded: { type: Boolean, default: false },
  autoLocate: { type: Boolean, default: true },
})
const emit = defineEmits(['expand'])

const store = useTimeStore()
const selectionStore = useSelectionStore()
const storyStore = useMapStoryStore()
const currentStory = computed(() => storyStore.current)
if (import.meta.env.DEV) window.__hkbMapStory = storyStore
// 底图状态单源在 ui store(localStorage/URL 持久化都在那边),本组件只读与落地
const ui = useUIStore()
if (!RESTRICTED_MAPS_ENABLED && ui.basemap === '古') ui.setBasemap('素')
const mapRef = ref(null)
const basemapOpen = ref(false)
const legendEntries = ref([])   // 有政权信息时的图例条目；为空走降级文案
const territoryCount = ref(0)   // 当前年份疆域块数（含无政权信息情况）
const administrativeCount = ref(0) // CHGIS 行政记录数；不冒充任何政权疆域
let map = null
let mapRO = null
let storySyncUntil = 0

function pauseStoryForManualMap() {
  if (storyStore.playing) storyStore.pause()
}

watch(() => expanded, (on) => {
  if (on) storyStore.ensureLoaded()
  else storyStore.pause()
}, { immediate: true })

function selectLegendPolity(p) {
  if (p.id != null) selectionStore.selectEntity(p.id, 'Polity', 'map')
}

// 读取 palette 注入到 :root 的地图专用纸色 / 网格线色（palettes.js 每套各配 mapPaper/mapGrid,
// applyPalette 注入 --map-paper/--map-grid;缺省回落 --paper/--line）。
// D5:watch(ui.palette) 时会重取并 setPaintProperty,切「夜」底色同步变深。
function readPaper() {
  const cs = getComputedStyle(document.documentElement)
  return cs.getPropertyValue('--map-paper').trim()
      || cs.getPropertyValue('--paper').trim() || '#f2ebdd'
}
function readLine() {
  const cs = getComputedStyle(document.documentElement)
  return cs.getPropertyValue('--map-grid').trim()
      || cs.getPropertyValue('--line').trim() || '#e2d9c6'
}
// catHue() 返回的是 "var(--fam-military)" 这类引用,而 maplibre 的 paint 只吃真实色值 ——
// 直传会静默失灰。故先解析成 hex(同 readPaper/readLine 的路子)。
function resolveVar(cssColor, fallback = '#8a7c62') {
  const m = /^var\((--[\w-]+)\)$/.exec((cssColor || '').trim())
  if (!m) return cssColor || fallback
  const root = document.querySelector('#app > *') || document.documentElement
  return getComputedStyle(root).getPropertyValue(m[1]).trim()
      || getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim()
      || fallback
}

// 经纬网格 GeoJSON：每 10° 一条 LineString，纯代码生成（经线 37 + 纬线 17 ≈ 54 条，不落静态文件）。
// maplibre 原生无 graticule，用本地 geojson line source 近似。
function buildGraticule() {
  const features = []
  for (let lng = -180; lng <= 180; lng += 10) {
    features.push({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [[lng, -90], [lng, 90]] } })
  }
  for (let lat = -80; lat <= 80; lat += 10) {
    features.push({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [[-180, lat], [180, lat]] } })
  }
  return { type: 'FeatureCollection', features }
}
const GRATICULE_FC = buildGraticule()

// 瓦片失败退避状态：errCount 按 id 计（非响应式）；disabledIds 驱动 UI 灰显
const errCount = Object.create(null)
const disabledIds = ref([])

// === 谭其骧《中国历史地图集》分年代图幅 ===
// 这是「绘制好的非互动底图」——不是矢量疆域自动着色，是地图集本身的印刷图幅，
// 已由 OSGeo 中国站的 MapProxy 配准成 webmercator 瓦片。此前只挂了 mp0302 一张（原始社会
// 遗址分布图），与年份无关，等于摆设。
//
// 图层 id 无年代元数据可查：WMTS 能力文档里 10714 个图层的 Title 就是 id 本身、Abstract 空、
// bbox 全是全球默认；demo 目录页只列 id 不列名（mp0302 在目录页出现 10 次、mp03 段 177 个 id
// 与 GetCapabilities 完全一致——v3 M9 实测更正：旧注释「mp0302 根本不在 demo 目录」不成立，
// 但目录页同样不给年代）。故下表的年代归属是**逐幅取瓦片看图认出来的**（依据写在每条注释里），
// 不是查表得来。未覆盖的年代落兜底幅 mp0302（纯地理底图）+ 图例注明「该年代图幅待补」，不说假话。
const ATLAS_SHEETS = [
  { from: -9999, to: -2071, id: 'mp0302', label: '原始社会遗址' },   // 红黑点遗址分布 + 现代地名
  { from: -2070, to: -1601, id: 'mp0305', label: '夏' },            // 有仍/有虞/安邑/晋阳/平阳
  { from: -1600, to: -1047, id: 'mp0306', label: '商' },            // 亳/奄/鬼方/土方/林方/羌方
  { from: -1046, to: -772,  id: 'mp0308', label: '西周' },          // 宗周/成周/曲沃/严允(犬戎)
  { from: -771,  to: -477,  id: 'mp030b', label: '春秋' },          // 林胡/义渠/绵诸/翟/中山
  { from: -476,  to: -222,  id: 'mp0311', label: '战国' },          // 楼烦/林胡 + 郡制
  { from: -221,  to: -207,  id: 'mp031f', label: '秦' },            // 内史/陇西郡/北地郡/上郡/咸阳
  // 西汉全图（v3 M9 注册，探针拼图亲读）：图例都城=长安；西域都护府/匈奴/乌孙。新莽 9-24 无图落兜底。
  { from: -206,  to: 8,     id: 'mp0324', label: '西汉' },          // 长安 + 西域都护府/匈奴/乌孙
  // 东汉全图：图例都城=雒阳（东汉写法）；西域长史府/鲜卑/夫余。
  { from: 25,    to: 220,   id: 'mp0334', label: '东汉' },          // 雒阳 + 西域长史府/鲜卑
  // 三国全图：图例纪年「魏景元三年、蜀汉景耀五年、吴永安五年（262年）」；魏/蜀/吴。
  { from: 220,   to: 280,   id: 'mp0346', label: '三国' },          // 262年快照：洛阳 + 魏/蜀/吴
  // 西晋全图（v3 M9 新发现。勘察代理曾标「西汉全图·与 mp0324 重复」，亲读图例更正）：
  // 图例纪年「太康二年（281年）」、都城=洛阳；西域长史府/鲜卑/高昌戊己校尉。非西汉重复幅。
  { from: 281,   to: 316,   id: 'mp035a', label: '西晋' },          // 太康二年281：洛阳 + 西域长史府
  // 东晋十六国全图：图题纪年「…光初十年、…建兴十五年（327年）」；晋/赵/成/凉/代。
  { from: 317,   to: 350,   id: 'mp0375', label: '东晋 · 十六国' },  // 327年快照：晋/赵/成/凉/代
  { from: 351,   to: 393,   id: 'mp0373', label: '前秦 · 区域政权图' },   // 「前」+ 凉州/秦州/长安/梁州。区域政权图：单政权视角，未绘东晋等同期政权（v3 T9.4b 拍板注明）
  { from: 394,   to: 534,   id: 'mp0391', label: '北魏 · 区域政权图' },   // 沃野/武川/怀朔/薄骨律 六镇。区域政权图：单政权视角，未绘南朝同期政权（同上）
  // mp0393 区间由 535-580 收窄为 535-557（v3 M9）：557 西魏亡/北周立，558 起换 mp0394 全图。
  { from: 535,   to: 557,   id: 'mp0393', label: '西魏 · 区域政权图' },   // 「西魏」+ 灵州/夏州/长安。区域政权图：单政权视角（同上）
  // 北周北齐陈全图：图例纪年「陈太建四年、齐武平三年、周建德元年（572年）」；齐/周/陈/突厥/吐谷浑。
  { from: 558,   to: 580,   id: 'mp0394', label: '北周 · 北齐 · 陈' },   // 572年快照：齐/周/陈/突厥
  { from: 581,   to: 617,   id: 'mp03c9', label: '隋' },            // 「隋」+ 灵武郡/京兆郡 郡制
  // 唐三幅分期（v3 M9，图例纪年亲读，取代原 dc 独扛 618-906）：
  //   db=总章二年（669）初唐极盛：单于都护府/安西四镇（焉耆镇/龟兹镇）/吐蕃/大非川 → 618-704。
  //     勘察代理曾标「开元二十九年 741」，亲读图例更正为 669（北庭都护府 702 年才置，不在图上）。
  //   dc=开元二十九年（741）盛唐：都城=西京、道级驻所=河南府、碎叶；突厥牙帐 + 回纥/同罗/契苾/
  //     仆骨（后突厥期铁勒诸部）→ 705-755。复核结论：与 dd 不同期（dd 已无突厥、回鹘牙帐主导），
  //     故不从年代表移除，改挂 741 该在的区间（本地 z6 拼图未含图例纪年行，741 由「突厥牙帐+
  //     回纥诸部并存 + 道级驻所（非节度使）」与 dd 元和十五年（820）对照互斥推定）。
  //   dd=元和十五年（820）中晚唐：都城=上都、节度使/观察使/经略使；回鹘牙帐/契丹/奚/西受降城 → 756-906。
  { from: 618,   to: 704,   id: 'mp03db', label: '唐 · 前期' },     // 总章二年669：单于都护府/安西四镇
  { from: 705,   to: 755,   id: 'mp03dc', label: '唐 · 中期' },     // 开元二十九年741：突厥牙帐/回纥/西京
  { from: 756,   to: 906,   id: 'mp03dd', label: '唐 · 后期' },     // 元和十五年820：回鹘牙帐/各方镇
  // 定谳(v3 T9.4c,探针拼图亲读):图幅图例纪年「(后)晋天福八年(943)」—— 五代后晋,非宋初。
  // 佐证:河套有「定难(军)」「党项」+ 夏州/绥州/延州,行政区全是府州名(京兆府/凤翔府/
  // 太原府),无任何宋代路名(永兴军路等);北为辽(上京临潢府/辽阳府),江南为南唐。
  { from: 907,   to: 959,   id: 'mp0500', label: '五代十国' },       // 后晋天福八年(943)快照
  // 北宋辽时期全图（v3 M9 注册）：东京开封府/北京大名府/契丹(辽)/西夏/定难军/太原府。
  { from: 960,   to: 1126,  id: 'mp0503', label: '北宋 · 辽' },      // 东京开封府/北京大名府/定难军
  // 金南宋时期全图两幅分期（勘察代理曾标「同期重复版取一」，亲读图例纪年更正为两期）：
  //   053d=金皇统二年、南宋绍兴十二年（1142）：金/西夏兴庆府/开封府/归德府 → 1127-1175
  //   053e=金泰和八年、南宋嘉定元年（1208）：金/西夏/南京路 → 1176-1279
  { from: 1127,  to: 1175,  id: 'mp053d', label: '金 · 南宋' },      // 皇统二年1142：金/西夏兴庆府
  { from: 1176,  to: 1279,  id: 'mp053e', label: '金 · 南宋' },      // 泰和八年1208：金/南京路
  // 元全图不存在于 mp05xx（v3 M9 S1+S2 勘察穷尽：只有分省/宣政院/西域区域图）→ 1280-1367
  // 显式落兜底 + 图例「该年代图幅待补」。
  // mp051b（西夏区域图，1038-1227）移出年代表（v3 M9）：960-1279 已被 mp0503/053d/053e 三幅
  // 全图覆盖，不再用区域图占位；脚本 SHEETS 保留其条目备查。
  // 明两幅：0589=宣德八年（1433）：鞑靼/瓦剌/奴儿干都司/亦力把里；058a=万历十年（1582）：鞑靼土默特部。
  { from: 1368,  to: 1499,  id: 'mp0589', label: '明 · 前期' },      // 宣德八年1433：奴儿干都司/瓦剌
  { from: 1500,  to: 1643,  id: 'mp058a', label: '明 · 后期' },      // 万历十年1582：鞑靼土默特部
  // 清两幅定年（z6 台湾/外东北探针因服务器 SSL 断连取回暗片失败，改读图例纪年行，证据更硬）：
  //   05c1=嘉庆二十五年（1820）→ 1644-1857；05d1=光绪三十四年（1908）→ 1858-1911（外东北已失）。
  { from: 1644,  to: 1857,  id: 'mp05c1', label: '清 · 前期' },      // 嘉庆二十五年1820
  { from: 1858,  to: 1911,  id: 'mp05d1', label: '清 · 晚期' },      // 光绪三十四年1908
]
// 兜底：年份落在所有区间之外（新莽 9-24、元 1280-1367 —— 图幅未认/不存在）时用它。
// 取原始社会遗址图是因为它是纯地理底图、无政权界，用在任何年代都不会说假话。
// 兜底生效时图例显式注明「该年代图幅待补」（见模板 fallbackSheetLabel，v3 T9.4b）。
const ATLAS_FALLBACK = 'mp0302'
const fallbackSheetLabel = ATLAS_SHEETS.find(s => s.id === ATLAS_FALLBACK).label
// 自托管，不直连 OSGeo 中国瓦片站。那台 nginx 对 curl（GET 与 OPTIONS 都试过）稳定返回
// Access-control-allow-origin: *，但 Chromium 里 maplibre 取瓦片必报
// "blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present" ——
// 同一浏览器同一 URL，裸 <img> 加载 30~121ms 成功（img 不校验 CORS），maplibre 的 fetch 全灭。
// 差异不在可达性而在 CORS，且那台服务器我们控制不了。底图是产品功能，不挂在这种单点上。
// 瓦片由后端 /tiles/atlas 静态服出（见 backend/app/main.py），同源，没有 CORS 这回事。
// 抓取脚本：scripts/fetch_atlas_tiles.py
const atlasTileUrl = (id) => `/tiles/atlas/${id}/{z}/{x}/{y}.png`

function atlasSheetFor(year) {
  if (year == null) return null
  return ATLAS_SHEETS.find(s => year >= s.from && year <= s.to) || null
}

// === 5 套底图（素=本地古风零网络；其余 4 套在线瓦片）===
// 键即字形,与 useUIStore.basemap 的合法值一一对应(底图状态单源在 store)。
const BASEMAPS = {
  素: {
    id: '素', label: '素底 · 本地古风', glyph: '素',
    type: 'raster',
    tiles: [],  // 空=不请求瓦片，与退避停请求复用同一路径
    attribution: '',
    maxzoom: 10,
  },
  古: {
    id: '古', label: '谭其骧历史地图 · 随年换幅', glyph: '古',
    type: 'raster',
    tiles: [atlasTileUrl(ATLAS_FALLBACK)],   // 实际 URL 由 watch(settledYear) 换，见 applyAtlasSheet
    attribution: '© OSGeo 中国历史地图集(谭其骧)',
    // 自托管瓦片只抓到 z6（z7 要 +5712 个/+112MB，Rick 拍板不补 —— docs/roadmap-v3.md §5-2/T9.6）。
    // source 收到 6 后（sourceMaxzoom），zoom 7-10 是 z6 的栅格过采样：糊，但放大扫描图反而
    // 能读小字；改前 source maxzoom=10 会去请求不存在的 z7+ 瓦片 → 连续 404 → 退避灰显
    // 「瓦片不可达」（说假话）。地图本体仍放到 10（v3 T9.0）。
    maxzoom: 10,
    sourceMaxzoom: 6,
  },
  今: {
    id: '今', label: 'OpenStreetMap', glyph: '今',
    type: 'raster',
    tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
    attribution: '© OpenStreetMap contributors',
    maxzoom: 19,
  },
  浅: {
    id: '浅', label: 'CARTO 浅色', glyph: '浅',
    type: 'raster',
    tiles: ['https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
            'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
            'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'],
    attribution: '© CARTO © OpenStreetMap',
    maxzoom: 19,
  },
  卫: {
    id: '卫', label: 'Esri 卫星', glyph: '卫',
    type: 'raster',
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
    attribution: '© Esri',
    maxzoom: 18,
  },
}
const BASEMAP_LIST = Object.values(BASEMAPS)
  .filter((basemap) => RESTRICTED_MAPS_ENABLED || basemap.id !== '古')

// 统一 style 骨架：所有底图共用 basemap(raster) + graticule(geojson) 两个 source，
// 素底只是「瓦片 tiles 置空 + 网格层可见」。不 setStyle（会清掉疆域层），靠 setTiles 切换。
function buildStyle(bmId) {
  const bm = BASEMAPS[bmId] || BASEMAPS.素
  return {
    version: 8,
    // D4:symbol 层(text-field)强制要求 style 带 glyphs。标注全是汉字,实际由
    // localIdeographFontFamily 本地渲染(见 Map 构造),此 URL 仅为过校验,不会被请求
    // —— 除非标注里混入 CJK 区外字符(name_ch/name_ft/name 均无,拉丁/标点才会去取)。
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      basemap: {
        type: bm.type,
        // 素底给一个占位 URL 而非空数组:空数组会让 maplibre 在取 URL 时炸
        // (见 switchBasemap 注释)。该层在素底下 visibility:none,占位 URL 永不被请求。
        tiles: bm.tiles.length ? bm.tiles : BASEMAPS.今.tiles,
        tileSize: 256,
        attribution: bm.attribution,
        // source 级 maxzoom：古=6（瓦片只到 z6，见 BASEMAPS.古注释），其余沿用地图级上限。
        // 切底图时还要同步改（见 switchBasemap）——本函数只在挂载时跑一次。
        maxzoom: bm.sourceMaxzoom ?? bm.maxzoom,
      },
      graticule: { type: 'geojson', data: GRATICULE_FC },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': readPaper() } },
      { id: 'basemap-tiles', type: 'raster', source: 'basemap',
        layout: { visibility: bmId === '素' ? 'none' : 'visible' } },
      {
        id: 'graticule', type: 'line', source: 'graticule',
        layout: { visibility: bmId === '素' ? 'visible' : 'none' },
        paint: { 'line-color': readLine(), 'line-width': 1, 'line-opacity': 0.55 },
      },
    ],
  }
}

onMounted(() => {
  // 建图前按「即时 year」取图幅：URL 恢复在 App setup 已完成（year=1050），但
  // settledYear 有 180ms 消抖仍是默认 750 —— 若按 settledYear 取会先铺几秒
  // 「唐图配北宋图例」再自愈（M10 实测竞态）。消抖是为刷年节流，一次性初取不受其限。
  applyAtlasSheet(store.year ?? store.settledYear)
  map = new maplibregl.Map({
    container: mapRef.value,
    style: buildStyle(ui.basemap),
    // 移动抽屉是「此刻全局概览」：横宽不足桌面一半，略退一级才能把中国全境
    // 放进同一画面；桌面仍保留原来的近景。autoLocate=false 也保证默认选中人物
    // 不会在抽屉刚展开时把视野带离中国。
    center: autoLocate ? [109, 33] : [104, 34],
    zoom: autoLocate ? 3.5 : 3,
    minZoom: 2,
    maxZoom: 10,
    attributionControl: true,
    // D4:CJK 字形本地渲染 —— 疆域标注(纯汉字)不依赖外部 glyphs 服务,零网络。
    // 与全局 --serif 同栈,标注与纸墨语言同字形。
    localIdeographFontFamily: "'Noto Serif SC','Source Han Serif SC','STSong',serif",
    // 不给瓦片加任何自定义请求头。曾加过 Cache-Control: no-cache(注释称「绕过系统代理」),
    // 但 Cache-Control 不在 CORS 安全列表内 —— 一加就把简单请求变成预检请求,而瓦片 CDN
    // 的 OPTIONS 会被重定向,浏览器判「Redirect is not allowed for a preflight request」,
    // 四套在线底图(谭其骧/OSM/CARTO/Esri)因此全部加载失败,地图只剩轮廓。
    // 它们对简单 GET 本就返回 Access-Control-Allow-Origin: *,无需任何头即可直连。
  })
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-left')

  // 瓦片失败退避 + console 静音：maplibre 全 bundle 仅 Evented 在「error 事件无监听」时
  // 兜底 console.error(t.error) -- 挂上本监听即不再刷 console。本应用唯一网络错误源是
  // 瓦片（territories/graticule 均本地 geojson），故非素底期间任何 error 事件≈瓦片错误，
  // 无需解析 sourceId。连续 5 次 -> setTiles([]) 停请求 + UI 灰显。
  map.on('error', () => {
    if (ui.basemap === '素') return  // 素底无瓦片，不计
    const id = ui.basemap
    errCount[id] = (errCount[id] || 0) + 1
    if (errCount[id] >= 5) {
      // 隐藏图层即停请求。原先 setTiles([]) 也能停,但空数组本身会让 maplibre 取 URL 时炸,
      // 等于用一种刷屏换另一种。
      map.setLayoutProperty('basemap-tiles', 'visibility', 'none')
      if (!disabledIds.value.includes(id)) {
        disabledIds.value = [...disabledIds.value, id]
      }
    }
  })

  // D4:标注密度随缩放 —— zoom<4 只标大块疆域(阈值见 applyTerritoryLabelFilter)
  map.on('zoom', applyTerritoryLabelFilter)
  // 手动拖拽/点击/滚轮意味着用户接管镜头；只暂停，保留当前卡供继续观看。
  map.on('dragstart', pauseStoryForManualMap)
  map.on('click', pauseStoryForManualMap)
  map.getCanvas().addEventListener('wheel', pauseStoryForManualMap, { passive: true })

  // 首绘触发：不赌 style.load 事件时序。本图传内联 style JSON，Style._load
  // 在 requestAnimationFrame 回调里同步发 style.load/styledata；onMounted 里
  // once 挂上时事件往往已发过 -> 永久错过(实测 /api/territories 一次都没发)。
  // 改确定性三路：style 已就绪直绘 / styledata 事件 / 800ms 超时双保险。
  // painted 保证只绘一次；addSource 若因仍未就绪抛错，走 paintTerritories
  // 内部 try/catch 重试兜底。
  let painted = false
  const tryFirstPaint = () => {
    if (painted) return
    painted = true
    map.off('styledata', tryFirstPaint)
    paintTerritories(store.settledYear)
  }
  if (map.isStyleLoaded()) {
    tryFirstPaint()                       // style 已就绪(内联 style 解析完)
  } else {
    map.on('styledata', tryFirstPaint)    // 就绪事件路径
    setTimeout(tryFirstPaint, 800)        // 双保险：事件被吞时强制尝试
  }

  // 容器尺寸现由用户拖分栏决定,必须让 maplibre 重算画布 —— 否则画布停在旧尺寸,
  // 图像被拉伸变形。ResizeObserver 直连容器,比监听 window.resize 准(拖手柄不改窗口)。
  mapRO = new ResizeObserver(() => { if (map) map.resize() })
  mapRO.observe(mapRef.value)

  // E2E 断言用：DEV 下暴露 map 实例，供 T1.3 检查疆域图层存在
  if (import.meta.env.DEV) window.__hkbMap = map

  // 异步 MapPanel 挂载前可能已经发生两种定位意图：显式「📍」请求优先；否则补消费
  // 当前选中实体。旧代码只补前者，时间柱卡先被点中时 selected watch 尚未注册，
  // 选中态虽已落地，事件标注/行军路线却永久缺席。
  if (selectionStore.locateRequest.id) takeLocateRequest()
  else if (autoLocate && selectionStore.selectedEntityId) {
    locateEntity(selectionStore.selectedEntityId, selectionStore.selectedEntityType)
  }
  if (expanded && currentStory.value) focusStoryEntry(currentStory.value)
})

onBeforeUnmount(() => {
  storyStore.pause()
  if (import.meta.env.DEV && window.__hkbMapStory === storyStore) delete window.__hkbMapStory
  if (mapRO) { mapRO.disconnect(); mapRO = null }
  if (map) map.getCanvas().removeEventListener('wheel', pauseStoryForManualMap)
  if (map) map.remove()
})

// style 结构未初始化时 setLayoutProperty / addSource 会抛 "Style is not done loading"。
// 不能用 isStyleLoaded()/idle 作闸门：MapLibre 的 Style.loaded() 还会等待所有 source，
// 慢瓦片或持续更新的 GeoJSON 可让它长期为 false，实际此时 addSource 已经安全。基础 bg
// 图层来自内联 style；它存在即说明 style 结构已初始化。styledata 负责正常唤醒，800ms
// 重检负责事件时序错过时收口；两条路径都不留下无限等待的监听。
function whenStyleReady(fn) {
  if (!map) return
  const ready = () => Boolean(map?.getLayer('bg'))
  if (ready()) { fn(); return }

  let done = false
  let timer = null
  const cleanup = () => {
    if (map) map.off('styledata', tryRun)
    if (timer) clearTimeout(timer)
  }
  const tryRun = () => {
    if (done || !ready()) return
    done = true
    cleanup()
    fn()
  }
  map.on('styledata', tryRun)
  timer = setTimeout(() => {
    tryRun()
    if (!done) cleanup()
  }, 800)
}

function switchBasemap(id) {
  basemapOpen.value = false
  if (!map) return
  if (!RESTRICTED_MAPS_ENABLED && id === '古') return
  // 同 id 且未禁用 -> 无操作；同 id 但已禁用 -> 当重试处理（恢复 tiles，不经过 store）
  if (id === ui.basemap) {
    if (disabledIds.value.includes(id)) whenStyleReady(() => applyBasemapNow(id))
    return
  }
  // 单源:只写 store,落地交给下面的 watch —— localStorage/URL 持久化随 store 一并生效
  ui.setBasemap(id)
}

// store 是底图唯一真相,任何来源(按钮/URL 恢复/hashchange)的变更都经此落地到地图
watch(() => ui.basemap, (id) => {
  if (!RESTRICTED_MAPS_ENABLED && id === '古') {
    ui.setBasemap('素')
    return
  }
  whenStyleReady(() => applyBasemapNow(id))
})

// D5:配色热切换 —— 素底背景/经纬网/标注光晕/行军外廓跟 palette 重取
// (此前只在建图时读一次,切「夜」后地图仍是纸色)
watch(() => ui.palette, () => {
  whenStyleReady(() => {
    map.setPaintProperty('bg', 'background-color', readPaper())
    map.setPaintProperty('graticule', 'line-color', readLine())
    if (map.getLayer('territory-label')) map.setPaintProperty('territory-label', 'text-halo-color', readPaper())
    if (map.getLayer('march-casing')) map.setPaintProperty('march-casing', 'line-color', readPaper())
  })
})

function applyBasemapNow(id) {
  if (!map) return
  let bm = BASEMAPS[id]
  if (!bm) return
  // 切换/重试=重置该 id 计数 + 清灰显（给一次重试机会）
  errCount[id] = 0
  if (disabledIds.value.includes(id)) {
    disabledIds.value = disabledIds.value.filter(x => x !== id)
  }
  // 素底改为「隐藏瓦片层」而非「tiles 置空」:置空后 maplibre 仍会为每块可见瓦片算 URL,
  // 在空数组上取下标即 undefined.replace(...) → 放大地图触发 resize 时一次刷出上百条
  // 「Cannot read properties of undefined (reading 'replace')」。隐藏图层则根本不进取瓦片流程。
  // 切到「古」时立刻按当前年份取图幅 —— 否则要等下一次滑动才换，用户会看到上一次的年代
  if (id === '古') {
    appliedSheetId = null
    applyAtlasSheet(store.settledYear)
    bm = BASEMAPS.古
  }
  if (id !== '素' && map.getSource('basemap')) {
    const src = map.getSource('basemap')
    src.setTiles(bm.tiles)
    // source maxzoom 随底图走（古=6，其余 18/19）。buildStyle 只在挂载时设一次，
    // 不在这里同步则「古」继承挂载时那家底图的 maxzoom，z7+ 照样请求不存在的瓦片
    // → 404 退避灰显。maxzoom 是 RasterTileSource 的公开属性（maplibre-gl.d.ts），
    // SourceCache 每次取覆盖瓦片时实时读它，改完下一帧即生效。
    src.maxzoom = bm.sourceMaxzoom ?? bm.maxzoom
  }
  map.setLayoutProperty('basemap-tiles', 'visibility', id === '素' ? 'none' : 'visible')
  // 网格层仅素底可见
  map.setLayoutProperty('graticule', 'visibility', id === '素' ? 'visible' : 'none')
  // D4:「古」图集自带地名,疆域标注压半透明避免打架;其余底图恢复 0.7
  if (map.getLayer('territory-label')) {
    map.setPaintProperty('territory-label', 'text-opacity', id === '古' ? 0.45 : 0.7)
  }
  // 调整 maxZoom
  map.setMaxZoom(bm.maxzoom)
}

// properties 缺失时的降级配色（CHGIS 导出 GeoJSON 暂无政权信息）
const FALLBACK_COLOR = '#9a8c7a'

// === D4 疆域政权标注层 ===
// 主行政名取 feature 属性:name_ch(CHGIS 简体全量) -> name_ft(繁体) -> name(peak 图单名);
// 三者皆缺时 coalesce 得 null,maplibre 不渲染该 feature —— 不写「未知」(原则 6)。
// _area 为外环 shoelace 面积(度²,仅作大小排序用):zoom<4 只标面积 ≥ 60 分位的大块,
// 小政权在全局视图不糊成一片(rank/min-zoom 启发式 —— 数据无 min-area 属性)。
function ringAreaDeg2(ring) {
  let a = 0
  for (let i = 0, n = ring.length; i < n; i++) {
    const [x1, y1] = ring[i], [x2, y2] = ring[(i + 1) % n]
    a += x1 * y2 - x2 * y1
  }
  return Math.abs(a / 2)
}
function featureAreaDeg2(f) {
  const g = f.geometry || {}
  const polys = g.type === 'Polygon' ? [g.coordinates]
              : g.type === 'MultiPolygon' ? g.coordinates : []
  let a = 0
  for (const poly of polys) if (poly && poly[0]) a += ringAreaDeg2(poly[0])
  return a
}
let labelMinArea = 0   // 当前年份面积 60 分位阈值,每次 paintTerritories 重算

function applyTerritoryLabelFilter() {
  if (!map || !map.getLayer('territory-label')) return
  map.setFilter('territory-label', ['>=', ['get', '_area'], map.getZoom() < 4 ? labelMinArea : 0])
}

// 请求时序守卫:并发的 paintTerritories 会乱序落地 —— 直开 #year=-300 时 immediate watch
// 先发 year=750(唐 871 块,payload 大、返回慢),紧接着发 -300(0 块,返回快),750 的响应
// 后到就把 -300 的清空覆盖掉,残留「唐 871」(实测直开时闪现)。用单调递增 nonce 而非年份
// 比对:年份比对挡不住同年重入与 style.load 重试。await 后 nonce 已被超越即作废本次。
let territoryReqSeq = 0
async function paintTerritories(year, seq = null) {
  if (!map) return
  if (seq === null) seq = ++territoryReqSeq   // 顶层调用领号;重试沿用原号

  let fc
  try {
    fc = await getTerritories(year)
  } catch (e) {
    console.warn('territories fetch failed', e)
    return
  }
  // 落地时若已有更新的请求领了更大的号,丢弃本次(否则慢的旧年覆盖快的新年)
  if (seq !== territoryReqSeq) return

  const features = fc.features || []
  // feature-state 高亮要求每个 feature 有稳定唯一 id；CHGIS 导出无顶层 id，按序号注入
  // （从 1 起，避开 MapLibre 对 id:0 的历史边界处理）
  features.forEach((f, i) => {
    f.id = i + 1
    // D4:标注层面积阈值用 —— 外环 shoelace 面积(度²)注入 _area
    f.properties = f.properties || {}
    f.properties._area = featureAreaDeg2(f)
  })
  // 面积 60 分位:zoom<4 时只标 ≥ 该值的大块疆域
  const sortedAreas = features.map(f => f.properties._area).sort((a, b) => a - b)
  labelMinArea = sortedAreas.length ? sortedAreas[Math.floor(sortedAreas.length * 0.6)] : 0

  // 图例分两类：CHGIS 是中性行政建置记录；仅独立 peak/手绘边界按政权聚合。
  const polities = new Map()
  let adminCount = 0
  for (const f of features) {
    const p = f.properties || {}
    if (p.record_kind === 'chgis_prefecture') {
      adminCount++
      continue
    }
    if (p.polity_id == null) continue
    if (!polities.has(p.polity_id)) {
      polities.set(p.polity_id, {
        id: p.polity_id,
        name: p.polity_name,
        color: p.polity_color,
        count: 0,
      })
    }
    polities.get(p.polity_id).count++
  }
  territoryCount.value = features.length
  administrativeCount.value = adminCount
  legendEntries.value = [...polities.values()]
    .map(p => ({
      id: p.id,
      name: p.name || '（未命名政权）',
      color: p.color || FALLBACK_COLOR,
      count: p.count,
    }))
    .sort((a, b) => b.count - a.count)

  // 旧图层清理 + 新图层添加。style 未就绪时 addSource/addLayer 会抛
  // "Style is not done loading." —— 兜底：等 style.load 后重试一次，不静默放弃
  try {
    ;['territory-fill', 'territory-border', 'territory-label'].forEach(layer => {
      if (map.getLayer(layer)) map.removeLayer(layer)
    })
    if (map.getSource('territories')) map.removeSource('territories')

    // 旧 source 已移除，其 feature-state 一并失效；重置 hover 游标与 tooltip
    hoveredTerritoryId = null
    tooltipVisible.value = false

    if (!features.length) return

    map.addSource('territories', { type: 'geojson', data: fc })

    map.addLayer({
      id: 'territory-fill',
      type: 'fill',
      source: 'territories',
      paint: {
        'fill-color': ['coalesce', ['get', 'polity_color'], FALLBACK_COLOR],
        'fill-opacity': ['case',
          ['boolean', ['feature-state', 'hover'], false], 0.62,
          ['==', ['get', 'is_primary'], true], 0.42,
          0.25],
      },
    })  // 无 beforeId=追加到顶层：fill 在瓦片之上（border 本就无 beforeId，更在 fill 之上）

    map.addLayer({
      id: 'territory-border',
      type: 'line',
      source: 'territories',
      paint: {
        'line-color': ['coalesce', ['get', 'polity_color'], FALLBACK_COLOR],
        'line-width': ['case',
          ['boolean', ['feature-state', 'hover'], false], 3,
          ['==', ['get', 'is_primary'], true], 2, 1],
        'line-opacity': 0.85,
      },
    })

    // D4 疆域政权标注层(此前清理列表引用了它,层从未真正添加 —— 疆域只能靠 hover 探名)。
    // 字号随 zoom 缩放;文字色=政权色 ~70% 透明 + 纸色 halo;「古」图集自带地名,压 0.45。
    // CJK 由 localIdeographFontFamily 本地渲染,不请求外部 glyphs。
    map.addLayer({
      id: 'territory-label',
      type: 'symbol',
      source: 'territories',
      layout: {
        'text-field': ['coalesce', ['get', 'name_ch'], ['get', 'name_ft'], ['get', 'name']],
        'text-font': ['Noto Sans SC'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 3, 10, 6, 14, 9, 18],
        'text-max-width': 8,
        'text-allow-overlap': false,
      },
      paint: {
        'text-color': ['coalesce', ['get', 'polity_color'], FALLBACK_COLOR],
        'text-opacity': ui.basemap === '古' ? 0.45 : 0.7,
        'text-halo-color': readPaper(),
        'text-halo-width': 1.4,
      },
    })
    applyTerritoryLabelFilter()

    map.off('click', 'territory-fill', onTerritoryClick)
    map.on('click', 'territory-fill', onTerritoryClick)
    map.off('mousemove', 'territory-fill', onTerritoryHover)
    map.on('mousemove', 'territory-fill', onTerritoryHover)
    map.off('mouseleave', 'territory-fill', onTerritoryLeave)
    map.on('mouseleave', 'territory-fill', onTerritoryLeave)
  } catch (e) {
    if (seq === territoryReqSeq && map) {
      // style 尚未就绪：style.load 一旦发出即重试（沿用本号，仍是最新才重试，防循环）
      map.once('style.load', () => paintTerritories(year, seq))
    } else {
      console.warn('territory paint failed', e)
    }
  }
}

// 疆域 hover：跟随光标的 DOM tooltip + feature-state 高亮（不整层重绘）
let hoveredTerritoryId = null
const tooltipVisible = ref(false)
const tooltipPrimary = ref('')
const tooltipSecondary = ref('')
const tooltipX = ref(0)
const tooltipY = ref(0)

function onTerritoryClick(e) {
  const p = e.features[0].properties
  if (p?.polity_id) selectionStore.selectEntity(p.polity_id, 'Polity', 'map')
}
function onTerritoryHover(e) {
  if (!e.features.length) return
  const f = e.features[0]
  const p = f.properties || {}
  const nameCh = p.name_ch || ''
  const polityName = p.polity_name || ''
  const typeCh = p.type_ch || ''
  // 只有真实政权疆域可点开实体；CHGIS 行政记录保持普通 hover 光标。
  map.getCanvas().style.cursor = p.polity_id ? 'pointer' : ''
  // 两者皆缺 -> 不显示 tooltip
  if (!nameCh && !polityName) {
    hideTerritoryTooltip()
    return
  }
  // feature-state 高亮：切到新 feature 时先清旧
  if (hoveredTerritoryId !== null && hoveredTerritoryId !== f.id) {
    map.setFeatureState({ source: 'territories', id: hoveredTerritoryId }, { hover: false })
  }
  if (hoveredTerritoryId !== f.id) {
    if (f.id != null) map.setFeatureState({ source: 'territories', id: f.id }, { hover: true })
    hoveredTerritoryId = f.id
  }
  // 文案明确区分行政建置记录与政权疆域，避免把文件名时期误读为归属。
  tooltipPrimary.value = nameCh || polityName
  if (p.record_kind === 'chgis_prefecture') {
    const years = p.beg_yr != null && p.end_yr != null ? `${p.beg_yr}–${p.end_yr}` : ''
    tooltipSecondary.value = [typeCh, 'CHGIS府级行政建置记录', years]
      .filter(Boolean).join('·')
  } else {
    tooltipSecondary.value = nameCh
      ? [polityName, typeCh, '政权疆域'].filter(Boolean).join('·')
      : [typeCh, '政权疆域'].filter(Boolean).join('·')
  }
  tooltipX.value = e.originalEvent.clientX
  tooltipY.value = e.originalEvent.clientY
  tooltipVisible.value = true
}
function onTerritoryLeave() {
  hideTerritoryTooltip()
  if (map) map.getCanvas().style.cursor = ''
}
function hideTerritoryTooltip() {
  if (hoveredTerritoryId !== null && map && map.getSource('territories')) {
    map.setFeatureState({ source: 'territories', id: hoveredTerritoryId }, { hover: false })
  }
  hoveredTerritoryId = null
  tooltipVisible.value = false
}

// 疆域重绘跟「稳定年份」而非 year:year 每 rAF 一变,滑一下就要重绘几十次,
// 地图疯狂跳动。滑停 180ms 后才落定 —— 见 useTimeStore.settledYear。
// immediate：activeSheet 是图例要读的，若等第一次滑动才算，切到「古」时图例会误落
// 兜底文案而实际早该匹配上（实测 750 年停在商幅，因为 settledYear 从未变过）。
// activeSheet/appliedSheetId 必须先于 watch 声明：immediate 回调同步执行，
// 声明在 watch 之后会撞 TDZ（「Cannot access 'activeSheet' before initialization」），
// 默认年 750 进 #year=750 时 settledYear 不再变化，图例永落兜底（M10 集成实测逮到）。
const activeSheet = ref(null)
// 与当前底图无关地问「这一年谭其骧图集有没有图幅」。用于空态:矢量疆域为空时,
// 先秦/楚汉这类 CHGIS 无源的年份其实在「古」底图上有权威印刷图 —— 别再一句「无疆域数据」
// 把用户挡在门外。返回 null = 连图幅都没有(如新莽 9-24、元 1280-1367 的显式兜底),那才是真无。
const yearSheet = computed(() => RESTRICTED_MAPS_ENABLED
  ? atlasSheetFor(store.settledYear)
  : null)
let appliedSheetId = null
watch(() => store.settledYear, async (y) => {
  applyAtlasSheet(y)
  await paintTerritories(y)
}, { immediate: true })

// 「古」底图随年换幅。跟 settledYear 而非 year：滑动中每 rAF 换一次瓦片源 = 每帧重取一屏瓦片。
// 且只在图幅 id 真的变了时才 setTiles —— 同一朝代内滑动不该产生任何网络请求。
function applyAtlasSheet(year) {
  if (!RESTRICTED_MAPS_ENABLED) {
    activeSheet.value = null
    return
  }
  const sheet = atlasSheetFor(year)
  activeSheet.value = sheet
  const id = sheet?.id || ATLAS_FALLBACK
  if (id === appliedSheetId) return
  appliedSheetId = id
  BASEMAPS.古.tiles = [atlasTileUrl(id)]
  if (map && ui.basemap === '古') {
    whenStyleReady(() => {
      const src = map.getSource('basemap')
      if (src) src.setTiles(BASEMAPS.古.tiles)
    })
  }
}

// 实体选中 → 飞行定位(三联动之一)
// === 选中事件 → 地图上落一个标注点 ===
// 此前 watch 只认 Place/Polity/Person,Event/Battle 一个都没接 —— 选中淝水之战地图
// 纹丝不动。全库 251 条事件里 162 条(64%)的 location 指向有经纬度的 Place,可直接落点。
// 视觉与时间柱同源:族色作底、印章字形作芯,一眼知其为何类。
// 用 DOM Marker 而非 symbol 图层:maplibre 的 text-field 要求 style 带 glyphs 字形服务器
// (实测报「use of "text-field" requires a style "glyphs" property」),而挂 glyphs 意味着
// 新增外部依赖、且中文字形包极大。DOM Marker 直接复用本应用的字体与印章样式,零网络依赖,
// 与时间柱上的印章同形同色。
let eventMarker = null
let marchMarkers = []
let locateSeq = 0
// 两个清理分开:paintEventMark 内部要先清自己的旧标注,若它连 march 一并清,
// 就会把先画的箭头擦掉(踩过:印章在、箭头恒为 0)。clearEventMark 只管印章。
function clearEventMark() {
  if (eventMarker) { eventMarker.remove(); eventMarker = null }
}
function clearMarch() {
  marchMarkers.forEach(m => m.remove()); marchMarkers = []
  ;['march-line', 'march-casing'].forEach(l => { if (map?.getLayer(l)) map.removeLayer(l) })
  if (map?.getSource('march')) map.removeSource('march')
}
function clearEventOverlay() { clearEventMark(); clearMarch() }

// 全线外接框:把整条行军路线(及落点)纳入视野。只 flyTo 落点的话,起点与箭头多在视野外。
function fitToLegs(legs, extra) {
  if (!map || !legs.length) return
  const pts = legs.flatMap(l => [[l.fromLng, l.fromLat], [l.toLng, l.toLat]])
  if (extra) pts.push(extra)
  const lngs = pts.map(p => p[0]), lats = pts.map(p => p[1])
  map.fitBounds([[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
                { padding: 64, maxZoom: 7, duration: 1200 })
}

// 进军箭头:逐段 from→to 画线,终点落一个箭头。数据只在史载起讫明确者才有(见
// schema/battle.yaml 的 march),无则不画 —— 没有数据而画方向即是编造。
function paintMarch(legs, hue, seq) {
  if (!map || !legs.length) return
  // 地图首屏与实体 API 并发加载；实体先返回时 style 可能尚不可写。旧实现直接 addSource，
  // 异常被空 catch 吞掉后只会“下次选中再画”，导致同一条 E2E 偶发有线、偶发无线路。
  // 复用底图切换的 style-ready 闸门；等待期间若用户已改选实体，不补画过期路线。
  whenStyleReady(() => {
    if (!map || seq !== locateSeq) return
    clearMarch()
    try {
      map.addSource('march', { type: 'geojson', data: {
        type: 'FeatureCollection',
        features: legs.map(l => ({ type: 'Feature', properties: { note: l.note || '' },
          geometry: { type: 'LineString', coordinates: [[l.fromLng, l.fromLat], [l.toLng, l.toLat]] } })),
      }})
      // 双层:浅色外廓压住底图杂色,深色芯线走向清楚
      map.addLayer({ id: 'march-casing', type: 'line', source: 'march',
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': readPaper(), 'line-width': 5, 'line-opacity': 0.9 } })
      map.addLayer({ id: 'march-line', type: 'line', source: 'march',
        layout: { 'line-cap': 'round' },
        paint: { 'line-color': hue, 'line-width': 2, 'line-dasharray': [3, 1.6] } })
      // 箭头:DOM Marker 旋转到该段方位角(同样绕开 glyphs 依赖)
      for (const l of legs) {
        const el = document.createElement('div')
        el.className = 'march-arrow'
        el.title = l.note || ''
        const brg = Math.atan2(l.toLng - l.fromLng, l.toLat - l.fromLat) * 180 / Math.PI
        el.innerHTML = `<span class="march-arrow-head" style="border-bottom-color:${hue};`
                     + `transform:rotate(${brg}deg)"></span>`
        marchMarkers.push(new maplibregl.Marker({ element: el, anchor: 'center' })
          .setLngLat([l.toLng, l.toLat]).addTo(map))
      }
    } catch (error) {
      console.warn('[MapPanel] 行军路线绘制失败', error)
    }
  })
}
function paintEventMark(lng, lat, glyph, hue, name) {
  if (!map) return
  clearEventMark()
  const el = document.createElement('div')
  el.className = 'evt-mark'
  el.title = name || ''
  el.innerHTML = `<span class="evt-mark-halo" style="background:${hue}"></span>`
                 + `<span class="evt-mark-seal" style="background:${hue}">${glyph}</span>`
  eventMarker = new maplibregl.Marker({ element: el, anchor: 'center' })
    .setLngLat([lng, lat]).addTo(map)
}

function focusStoryEntry(entry) {
  if (!entry || !map || !expanded) return
  const seq = ++locateSeq
  clearEventOverlay()

  const hue = entry.kind === 'life_event'
    ? resolveVar('var(--accent)')
    : resolveVar(catHue(entry.category))
  const legs = (entry.march || []).map((leg) => ({
    fromLng: leg.from.longitude,
    fromLat: leg.from.latitude,
    toLng: leg.to.longitude,
    toLat: leg.to.latitude,
    note: `${leg.from.name} → ${leg.to.name}${leg.note ? ' · ' + leg.note : ''}`,
  }))
  if (legs.length) paintMarch(legs, hue, seq)

  const point = entry.location
  if (point) {
    const glyph = entry.kind === 'life_event' ? '人' : catMeta(entry.category).glyph
    paintEventMark(point.longitude, point.latitude, glyph, hue,
                   `${entry.title} · ${point.name}`)
  }
  if (legs.length) {
    fitToLegs(legs, point ? [point.longitude, point.latitude] : null)
  } else if (point) {
    map.flyTo({ center: [point.longitude, point.latitude], zoom: 6, duration: 1200 })
  }

  // 地图与左轴共用 timeStore。TimeColumn 的平滑回滚会在 650ms 内回写若干中间年，
  // 留一段程序化同步窗，避免把自己的动画误判为用户手动定年。
  storySyncUntil = performance.now() + 1300
  store.setYear(entry.year)
  selectionStore.selectEntity(entry.entity_id, entry.entity_type, 'map-story')
}

watch(currentStory, (entry) => {
  if (entry && expanded) focusStoryEntry(entry)
})

watch(() => store.year, () => {
  // 用户从左轴改年后，旧卡与新年份已不再对应；结束故事而不留一张误导的旧简介。
  if (currentStory.value && performance.now() > storySyncUntil) storyStore.reset()
})

// 实体定位:选中联动(selectedEntityId)与「📍」显式请求(locateRequest)共用同一份飞行逻辑。
// 抽出来的原因:重复点同一实体的 📍 时选中态不变、watch 不触发,必须靠 nonce 通道再飞。
async function locateEntity(id, type) {
  const seq = ++locateSeq
  if (!id || !map) { clearEventOverlay(); return }
  try {
    const e = await getEntity(id)
    if (seq !== locateSeq) return
    if (e.type === 'Event' || e.type === 'Battle') {
      clearEventOverlay()
      const hue = resolveVar(catHue(e.category))
      // 进军路线(有则画):各段起讫并发取,免得逐段串行往返
      const legs = []
      if (Array.isArray(e.march) && e.march.length) {
        const ids = [...new Set(e.march.flatMap(m => [m.from, m.to]))]
        const got = await Promise.all(ids.map(i => getEntity(i).catch(() => null)))
        if (seq !== locateSeq) return
        const byId = Object.fromEntries(ids.map((i, k) => [i, got[k]]))
        for (const m of e.march) {
          const a = byId[m.from], b = byId[m.to]
          if (a?.latitude == null || b?.latitude == null) continue
          legs.push({ fromLng: a.longitude, fromLat: a.latitude,
                      toLng: b.longitude, toLat: b.latitude,
                      note: `${a.name} → ${b.name}${m.note ? ' · ' + m.note : ''}` })
        }
      }
      if (legs.length) paintMarch(legs, hue, seq)

      if (!e.location) {               // 89 条无 location(变法/外交等本无单一地点),不强安
        if (legs.length) fitToLegs(legs)
        return
      }
      const p = await getEntity(e.location).catch(() => null)
      if (seq !== locateSeq) return
      if (p?.latitude == null) return
      paintEventMark(p.longitude, p.latitude, catMeta(e.category).glyph, hue,
                     `${e.name} · ${p.name}`)
      // 有行军路线则取全线外接框,否则只对准落点 —— 只对准落点时箭头多半在视野外
      if (legs.length) fitToLegs(legs, [p.longitude, p.latitude])
      else map.flyTo({ center: [p.longitude, p.latitude], zoom: 6, duration: 1200 })
      return
    }
    clearEventOverlay()
    if (e.type === 'Place' && e.latitude != null) {
      map.flyTo({ center: [e.longitude, e.latitude], zoom: 7, duration: 1200 })
    } else if (e.type === 'Polity' && e.capital) {
      const cap = await getEntity(e.capital).catch(() => null)
      if (seq !== locateSeq) return
      if (cap?.latitude != null) map.flyTo({ center: [cap.longitude, cap.latitude], zoom: 6, duration: 1200 })
    } else if (e.type === 'Person' && e.birthplace) {
      const bp = await getEntity(e.birthplace).catch(() => null)
      if (seq !== locateSeq) return
      if (bp?.latitude != null) map.flyTo({ center: [bp.longitude, bp.latitude], zoom: 6, duration: 1200 })
    }
  } catch {}
}

watch(() => selectionStore.selectedEntityId, (id) => {
  if (selectionStore.origin !== 'map-story') {
    // 手动改选会让地图转向新实体；旧故事卡若继续悬着就与镜头相矛盾。
    if (currentStory.value) storyStore.reset()
    if (autoLocate) locateEntity(id, selectionStore.selectedEntityType)
  }
})

// 「📍 地图定位」显式请求:nonce 单调递增,同一实体连点也必然触发(选中态 watch 做不到)。
watch(() => selectionStore.locateRequest.nonce, () => {
  takeLocateRequest()
})

// 请求一次性消费:id 置空,否则路由往返重挂载时(onMounted 的补发)会拿滞留请求再飞一次。
function takeLocateRequest() {
  const { id, type } = selectionStore.locateRequest
  if (!id) return
  selectionStore.locateRequest.id = null
  locateEntity(id, type)
}
</script>

<style scoped>
/* 事件标注:印章落在地图上,与时间柱同形同色。Marker 的 DOM 由 maplibre 插进容器,
   scoped 样式够不着,故用 :deep()。晕圈让它在深浅底图上都立得住。 */
/* 不要给 .evt-mark 设 position:maplibre 给 Marker 元素设的是 absolute + transform,
   写 relative 会把它盖成「以文档流位置为基点做偏移」,标注遂飘到地图外(实测落在
   容器下方 240px 处)。absolute 元素本身就是其 absolute 子元素的包含块,晕圈照常定位。 */
:deep(.evt-mark) {
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
}
:deep(.evt-mark-halo) {
  position: absolute; inset: -9px;
  border-radius: 50%;
  opacity: 0.22;
  animation: evt-pulse 2.4s ease-out infinite;
}
:deep(.evt-mark-seal) {
  position: relative;
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 4px;
  font-family: var(--serif);
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  color: var(--on-cat);
  box-shadow: 0 0 0 1.5px var(--paper-el), 0 1px 4px rgba(0,0,0,0.25);
}
/* 进军箭头:CSS 三角,按该段方位角旋转。同样不设 position —— maplibre 的
   .maplibregl-marker 已给 absolute+transform,写死会把它顶出地图(见上)。 */
:deep(.march-arrow) {
  width: 0; height: 0;
  display: flex; align-items: center; justify-content: center;
}
:deep(.march-arrow-head) {
  display: block;
  width: 0; height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-bottom: 11px solid currentColor;
  filter: drop-shadow(0 0 1.5px var(--paper-el));
}

@keyframes evt-pulse {
  0%   { transform: scale(0.85); opacity: 0.30; }
  70%  { transform: scale(1.25); opacity: 0; }
  100% { transform: scale(1.25); opacity: 0; }
}

.map-panel {
  position: relative;
  width: 100%;
  height: 100%;
}
#map-container { position: absolute; inset: 0; }

.map-tools {
  position: absolute;
  top: 0.6rem;
  left: 0.6rem;
  z-index: 5;
}
.map-tool-row,
.map-basemap-switcher {
  display: flex;
  gap: 3px;
  background: var(--caption);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 3px;
  backdrop-filter: blur(4px);
}
.map-basemap-switcher { margin-top: 5px; }
.bm-btn {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--ink-mid);
  font-family: var(--serif);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s;
}
.bm-btn:hover { background: var(--hover); }
.bm-btn:focus-visible,
.map-legend-polity:focus-visible,
.map-atlas-switch:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.bm-btn.active {
  background: var(--accent);
  color: var(--accent-text);
}
.bm-btn.disabled { opacity: 0.4; cursor: not-allowed; }
.bm-btn.disabled:hover { background: transparent; }

.map-overlay {
  position: absolute;
  top: 0.6rem;
  right: 0.6rem;
  background: var(--caption);
  border: 1px solid var(--line);
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8em;
  color: var(--ink-soft);
  max-width: 220px;
  z-index: 5;
  backdrop-filter: blur(4px);
}
.map-year { font-family: var(--serif); color: var(--ink); }
.map-legend { margin-top: 0.35rem; display: flex; flex-direction: column; gap: 0.15rem; }
.map-legend-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 1px 2px;
  border-radius: 3px;
}
.map-legend-polity { cursor: pointer; }
.map-legend-polity:hover { background: var(--hover); }
.map-legend-admin { cursor: default; }
.map-legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}
.map-legend-count {
  margin-left: auto;
  font-size: 0.85em;
  color: var(--ink-faint);
}
.map-note-sub { color: var(--ink-faint); }
/* 空态·古图接入:古底图上的说明 + 非古底图上一键切古的入口 */
.map-atlas-note { margin-top: 0.35rem; font-size: 11px; color: var(--ink-faint); line-height: 1.5; }
.map-atlas-switch {
  margin-top: 0.35rem;
  padding: 4px 9px;
  font-size: 11px;
  line-height: 1.4;
  text-align: left;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
  border-radius: 6px;
  cursor: pointer;
}
.map-atlas-switch:hover { background: color-mix(in srgb, var(--accent) 16%, transparent); }

/* 疆域 hover tooltip：position:fixed 贴视口，靠 transform 让出光标；
   配色全走设计变量，四套 palette（含夜·深色）下均可读 */
.territory-tooltip {
  position: fixed;
  z-index: 20;
  pointer-events: none;
  background: var(--paper-el);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 0.3rem 0.55rem;
  font-size: 0.8em;
  line-height: 1.3;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  transform: translate(12px, 12px);
  white-space: nowrap;
  max-width: 240px;
}
.territory-tooltip .tt-primary {
  font-family: var(--serif);
  font-weight: 600;
  color: var(--ink);
}
.territory-tooltip .tt-secondary {
  margin-top: 0.1rem;
  font-size: 0.85em;
  color: var(--ink-soft);
}
</style>
