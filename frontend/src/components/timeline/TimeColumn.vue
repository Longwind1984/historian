<template>
  <div class="tc-wrap" ref="rootRef">
    <!-- 朝代脉络 gutter(左侧固定宽度,内容随滚动同步) -->
    <div class="tc-gutter">
      <div class="tc-gutter-inner" ref="gutterInnerRef" :style="{ height: innerHeight + 'px' }">
        <div v-for="g in gutterBlocks" :key="g.key"
             class="tc-gutter-block"
             :style="g.style"
             :title="g.tip"
             role="button"
             tabindex="0"
             :aria-label="g.tip"
             @click="g.onClick"
             @keydown.enter.prevent="g.onClick"
             @keydown.space.prevent="g.onClick">
          <span class="tc-gutter-label" :style="g.labelStyle">{{ g.label }}</span>
          <span class="tc-gutter-year" :style="g.yearStyle">{{ g.startYear }}</span>
        </div>
      </div>
    </div>

    <!-- 滚动主体 -->
    <div class="tc-scroll" ref="scrollRef" @scroll="onScroll" @dblclick="resetZoom">
      <div class="tc-inner" :class="{ 'tc-dim': personDimOn }" :style="{ height: innerHeight + 'px' }">
        <!-- 年份刻度(视口虚拟化:只生成视口 ± 缓冲区内的 tick,L2 逐年也不卡) -->
        <div v-for="t in ticks" :key="t.key">
          <div class="tc-tick-line" :style="t.lineStyle"></div>
          <span v-if="t.isLabel" class="tc-tick-label" :style="t.labelStyle">{{ t.label }}</span>
        </div>

        <!-- 帝王世系带:二级年代坐标(一级为左侧朝代带)。L1/L2 随缩放淡入,视口虚拟化。
             按道号并排 -> 并立政权(三国/十六国/南北朝/五代)各占一道,不再全宽叠压;整条可点可悬浮。 -->
        <div v-for="e in viewportEmperors" :key="'emp-'+e.key"
             class="tc-emperor-band"
             :class="{selected: e.id === selectionStore.selectedEntityId}"
             :style="e.bandStyle"
             :title="e.title"
             role="button"
             tabindex="0"
             :aria-label="e.title"
             :aria-pressed="e.id === selectionStore.selectedEntityId"
             @click="e.onClick"
             @keydown.enter.prevent="e.onClick"
             @keydown.space.prevent="e.onClick"
             @focus="setHoverGuarded(e.id)"
             @blur="selectionStore.setHover(null)"
             @mouseenter="setHoverGuarded(e.id)"
             @mouseleave="selectionStore.setHover(null)">
          <span class="tc-emperor-label" :style="e.labelStyle">{{ e.label }}</span>
        </div>

        <!-- 选中人物/政权 生命带 -->
        <template v-if="selected && selectedBand">
          <div class="tc-life-band" :style="selectedBand.style"></div>
          <div class="tc-life-cap" :style="selectedBand.capStyle">{{ selectedBand.cap }}</div>
        </template>

        <!-- 关系连线 SVG overlay(选中人物的关系网在时间维度可视化)-->
        <svg class="tc-relation-svg" v-if="relationLines.length" :style="{ height: innerHeight + 'px' }">
          <line v-for="(ln, i) in relationLines" :key="'rl-'+i"
                :x1="ln.x1" :y1="ln.y1" :x2="ln.x2" :y2="ln.y2"
                :stroke="ln.color" :stroke-width="ln.width"
                :stroke-dasharray="ln.dash" :opacity="ln.opacity" />
        </svg>

        <!-- 因果链轨道 -->
        <template v-for="(chain, ci) in visibleChains" :key="'chain-' + ci">
          <div class="tc-chain-rail" :style="chain.railStyle"></div>
          <div v-for="(stub, si) in chain.stubs" :key="ci + '-' + si" class="tc-chain-stub" :style="stub.style"></div>
        </template>

        <!-- 人物生命条 -->
        <div v-for="p in viewportPeople" :key="p.id"
             class="tc-person-wrap"
             :class="{hovered: p.id === selectionStore.hoveredEntityId, selected: p.id === selectionStore.selectedEntityId}"
             :style="p.wrapStyle"
             :title="p.title"
             role="button"
             tabindex="0"
             :aria-label="p.title"
             :aria-pressed="p.id === selectionStore.selectedEntityId"
             @click="p.onClick"
             @keydown.enter.prevent="p.onClick"
             @keydown.space.prevent="p.onClick"
             @focus="setHoverGuarded(p.id)"
             @blur="selectionStore.setHover(null)"
             @mouseenter="setHoverGuarded(p.id)"
             @mouseleave="selectionStore.setHover(null)">
          <!-- 模糊纪年者不画生卒点:那两个点意味着确凿的起讫,而其生卒本不可考 -->
          <div class="tc-person-bar" :style="p.barStyle">
            <template v-if="!p.fuzzy">
              <!-- 生年不可考者不画生年点;在世者不画卒年刻度 -->
              <div v-if="!p.deathOnly" class="tc-birth-dot" :style="p.birthDotStyle"></div>
              <div v-if="!p.living" class="tc-death-tick" :style="p.deathTickStyle"></div>
            </template>
          </div>
          <div v-if="p.showName || p.id === selectionStore.hoveredEntityId || p.id === selectionStore.selectedEntityId"
               class="tc-person-name" :style="p.nameStyle">{{ p.name }}</div>
        </div>

        <!-- 聚合溢出道(T7.2,方向甲):区宽放不下的人物并入最右一道,按生年落刻度示密度、
             标「+N」;hover 见名单,click 平滑放大 —— 窗内并发下降后人物自然回列。
             M8 起名单与事件桶统一为同一套可点选清单(AggPopList),条目走 selectEntity -->
        <template v-if="personAgg">
          <div v-for="t in viewportAggTicks" :key="'agg-'+t.id"
               class="tc-agg-tick"
               :style="{ left: personAgg.x + 'px', top: t.top + 'px' }"
               :title="t.title"
               aria-hidden="true"
               @click="onAggClick"></div>
          <div class="tc-agg-badge"
               :style="{ left: personAgg.x + 'px', top: aggBadgeTop + 'px' }"
               role="button"
               tabindex="0"
               :aria-label="`${personAgg.count} 人暂并入聚合道；激活可放大回列`"
               @mouseenter="openPop({ kind: 'person' })"
               @mouseleave="closePopSoon"
               @focus="openPop({ kind: 'person' })"
               @click="onAggClick"
               @keydown.enter.prevent="onAggClick"
               @keydown.space.prevent="onAggClick">+{{ personAgg.count }}</div>
          <AggPopList v-if="personPopOpen"
               :title="personAgg.count + ' 人暂并入此道 · 点击道标放大回列'"
               :items="personAgg.items"
               unit="人"
               :pop-style="personPopStyle"
               @select="onPopSelect"
               @enter="keepPop"
               @leave="closePopSoon" />
        </template>

        <!-- 溢出槽(T8.1 分桶):放不下的事件按 y 距并桶 —— 单事件桶照旧落刻度(悬停见名、
             点选定位);多事件桶渲染「+N」计数徽标(族色继承既有调色),不再同 x 叠放。
             hover 桶弹该桶事件迷你清单(条目可点选),click 桶平滑放大到该区间(T8.2),
             放大后 yPos 变疏,原溢出事件自然回列 -->
        <template v-for="b in viewportBuckets" :key="b.key">
          <div v-if="b.count === 1"
               class="tc-overflow-tick"
               :class="{hovered: b.items[0].id === selectionStore.hoveredEntityId}"
               :style="b.items[0].style" :title="b.items[0].title"
               role="button"
               tabindex="0"
               :aria-label="b.items[0].title"
               :aria-pressed="b.items[0].id === selectionStore.selectedEntityId"
               @click="b.items[0].onClick"
               @keydown.enter.prevent="b.items[0].onClick"
               @keydown.space.prevent="b.items[0].onClick"
               @focus="setHoverGuarded(b.items[0].id)"
               @blur="selectionStore.setHover(null)"
               @mouseenter="setHoverGuarded(b.items[0].id)"
               @mouseleave="selectionStore.setHover(null)"></div>
          <div v-else
               class="tc-overflow-badge"
               :data-bucket-key="b.key"
               :style="b.badgeStyle"
               :title="b.count + ' 件收起于此 · 悬停见清单,点击放大回列'"
               role="button"
               tabindex="0"
               :aria-label="`${b.count} 件事件收起于此；激活可放大回列`"
               @mouseenter="openPop({ kind: 'bucket', key: b.key })"
               @mouseleave="closePopSoon"
               @focus="openPop({ kind: 'bucket', key: b.key })"
               @click="onBucketClick(b, $event)"
               @keydown.enter.prevent="onBucketClick(b, $event)"
               @keydown.space.prevent="onBucketClick(b, $event)"
               @dblclick.stop>+{{ b.count }}</div>
        </template>
        <AggPopList v-if="hoveredBucket"
             :title="hoveredBucket.count + ' 件收起于此 · 点击徽标放大回列'"
             :items="hoveredBucket.popItems"
             :cap="16"
             :pop-style="bucketPopStyle"
             @select="onPopSelect"
             @enter="keepPop"
             @leave="closePopSoon" />

        <!-- 事件:一律卡片;有跨度的在列左间隙挂一条尾巴示其延续 -->
        <template v-for="ev in viewportEvents" :key="ev.id">
          <div v-if="ev.tailStyle" class="tc-event-tail" :style="ev.tailStyle"></div>
          <div class="tc-event-card"
               :class="{hovered: ev.id === selectionStore.hoveredEntityId, selected: ev.id === selectionStore.selectedEntityId}"
               :style="ev.cardStyle"
               :title="ev.name + ' ' + ev.fullLabel"
               role="button"
               tabindex="0"
               :aria-label="ev.name + ' ' + ev.fullLabel"
               :aria-pressed="ev.id === selectionStore.selectedEntityId"
               @click="ev.onClick"
               @keydown.enter.prevent="ev.onClick"
               @keydown.space.prevent="ev.onClick"
               @focus="setHoverGuarded(ev.id)"
               @blur="selectionStore.setHover(null)"
               @mouseenter="setHoverGuarded(ev.id)"
               @mouseleave="selectionStore.setHover(null)">
            <Seal :type="ev.type" :category="ev.category" :size="14" variant="solid" />
            <span class="tc-event-name">{{ ev.name }}</span>
            <span class="tc-event-year">{{ ev.yearLabel }}</span>
          </div>
        </template>

        <!-- 选中人物的年谱 pins -->
        <div v-for="m in momentPins" :key="m.key"
             class="tc-moment-pin"
             :style="m.wrapStyle"
             :data-pin-lane-x="m.laneX"
             :title="m.tip"
             role="button"
             tabindex="0"
             :aria-label="m.label"
             @click="m.onClick"
             @keydown.enter.prevent="m.onClick"
             @keydown.space.prevent="m.onClick">
          <span class="tc-moment-dot" :style="m.dotStyle"></span>
          <span class="tc-moment-label" :style="m.labelStyle">{{ m.label }}</span>
        </div>
      </div>
    </div>

    <!-- 柱缘密度指示条(T8.3):全轴事件密度热区薄条贴柱右缘,与缩放无关 ——
         任一 zoomLevel 一瞥「哪里有戏」;刻痕随当前年掠过响应,点击条面跳年 -->
    <div class="tc-density" ref="densityRef"
         role="slider" tabindex="0" aria-label="全史事件密度"
         aria-orientation="vertical"
         :aria-valuemin="-ORIGIN" :aria-valuemax="AXIS_END"
         :aria-valuenow="Math.round(store.year)" :aria-valuetext="fmtY(Math.round(store.year))"
         @click="onDensityClick" @keydown="onDensityKeydown" @wheel="onDensityWheel">
      <div v-for="b in densityBins" :key="b.i" class="tc-density-bin"
           :style="{ opacity: b.op }" :title="b.tip"></div>
      <div class="tc-density-now" :style="{ top: densityNowTop + '%' }"></div>
    </div>

    <!-- 当前年 lens(固定横线) -->
    <div class="tc-lens">
      <div class="tc-lens-line"></div>
      <div class="tc-lens-label" :class="{pulse: lensPulse}">{{ lensLabel }}<span v-if="store.playing" class="tc-lens-playing" title="播放中 · Space 暂停"> ⏸</span></div>
      <div class="tc-lens-hint">此刻 -- 右栏与此线同步</div>
    </div>

    <!-- 时间工具组：跳年与尺度合并；尺度选项默认折叠，避免长期遮住时间柱。 -->
    <div class="tc-controls">
      <div class="tc-toolbar">
        <button class="tc-tool-button" title="跳至年份 (g)" aria-label="跳至年份" @click="jumpOpen = true">
          <CalendarSearch :size="16" :stroke-width="1.8" aria-hidden="true" />
        </button>
        <button class="tc-tool-button tc-scale-trigger" type="button"
                :aria-expanded="scaleOpen" aria-controls="timeline-scale-options"
                @click="scaleOpen = !scaleOpen">
          <Clock3 :size="15" :stroke-width="1.8" aria-hidden="true" />
          <span>{{ lodLabel }}</span>
          <ChevronDown class="tc-scale-chevron" :class="{open: scaleOpen}" :size="14" aria-hidden="true" />
        </button>
      </div>
      <div v-if="scaleOpen" id="timeline-scale-options" class="tc-scale-popover">
        <div class="tc-segmented" role="group" aria-label="时间轴尺度">
          <button :class="{active: lod===0}" @click="setLod(0)">朝代</button>
          <button :class="{active: lod===1}" @click="setLod(1)">帝王</button>
          <button :class="{active: lod===2}" @click="setLod(2)">编年</button>
          <button :class="{active: lod===3}" @click="setLod(3)">月</button>
          <button :class="{active: lod===4}" @click="setLod(4)">日</button>
        </div>
        <button class="tc-reset" @click="resetZoom" title="复位为朝代全景" aria-label="复位为朝代全景">
          <RotateCcw :size="15" :stroke-width="1.8" aria-hidden="true" />
        </button>
      </div>
    </div>

    <!-- M12 历法口径注记:亚年档才出。农历月按 1/12 年线性摆放是近似而非换算,
         不说明就等于默认读者以为已换算 —— 「求真高于中性」要求把这层不确定摆明。 -->
    <div v-if="subYear" class="tc-calendar-note">{{ calendarNote }}</div>

    <!-- C3 跳年弹层(共享组件,g 键唤起的是 App 层同一枚) -->
    <YearJump v-if="jumpOpen" @confirm="onJumpConfirm" @close="jumpOpen = false" />
  </div>
</template>

<script setup>
import { ref, computed, watch, watchEffect, onMounted, onBeforeUnmount, nextTick } from 'vue'
import CalendarSearch from '@lucide/vue/dist/esm/icons/calendar-search.mjs'
import ChevronDown from '@lucide/vue/dist/esm/icons/chevron-down.mjs'
import Clock3 from '@lucide/vue/dist/esm/icons/clock-3.mjs'
import RotateCcw from '@lucide/vue/dist/esm/icons/rotate-ccw.mjs'
import { useDataStore, useTimeStore, useSelectionStore, useFilterStore } from '../../stores'
import { getEntities, getEntity, getNeighbors, getRelations } from '../../api/client'
import { ERAS, fmtY, fmtYM, fmtMD, ganzhi, isGregorian, catHue } from '../../styles/palettes'
import { useAlivePeople } from '../../composables/useAlivePeople'
import { toAxisYear } from '../../utils/timeNavigation'
import Seal from '../shared/Seal.vue'
import YearJump from '../shared/YearJump.vue'
import AggPopList from './AggPopList.vue'

const dataStore = useDataStore()
const store = useTimeStore()
const selectionStore = useSelectionStore()
const filter = useFilterStore()
// 在世名单(单源,与 MomentPanel chips 同一份):车道提升集用 —— chips 上的人在柱上必有条
const aliveChips = useAlivePeople()
const rootRef = ref(null)
const scrollRef = ref(null)
const gutterInnerRef = ref(null)
// 柱内 hover-in 守卫:程序化平滑滚动(搜索跳年/朝代块点击/年谱跳转)途中与刚结束的
// 400ms 尾窗内,内容从静止光标下滑过/落定,Chrome 会重算悬停触发一串 mouseenter。
// hover 已不再切换档案,但这串误触仍会让刚选中的条目旁边闪出无关视觉高亮；store 的
// 350ms 抑制窗盖不住约 650ms 的滚动全程,故动画期+尾窗柱内 hover-in 一律忽略；
// mouseleave(清空)始终放行。
let hoverSuppressUntil = 0
function setHoverGuarded(id) {
  if (id && (scrollAnim || extScrollGuard || performance.now() < hoverSuppressUntil)) return
  selectionStore.setHover(id)
}
const people = ref([])
const emperors = ref([])
const events = ref([])
const selected = ref(null)
// 虚拟化:视口上沿 scrollTop + 视口高度,只渲染 [viewTop-BUF, viewTop+viewH+BUF] 内的节点
const viewTop = ref(0)
const viewH = ref(0)
const viewW = ref(700)
// M12:锚线所指的小数年(含月/日分量)。只供 lens 读数与几何,不进 store ——
// store.year 保持整数,是 URL / 地图换幅 / 在世名单 / 干支年号的唯一口径。
const exactYear = ref(store.year)
// 帝王世系带(二级年代坐标):紧贴朝代带右侧,并立帝王分道并排,不再全宽叠压
const ERA_W = 96          // 朝代带(.tc-gutter 不透明,宽 96px);帝王带紧贴其右
const EMP_LANE_W = 16     // 每道宽
const EMP_MAX_LANES = 6   // 超出并道(五代十国等极端并立)
let scrollRaf = 0
let scrollAnim = 0
// T7.1:scrollRef 尺寸观测 —— 拖 SplitPane/窗口缩放时 viewW 实时重算(含车道/事件列),
// 不再等下一次滚动。旧版只在 scroll/zoom/mount 时 syncViewTop,拖完手柄布局纹丝不动。
let resizeObs = null
// 程序化滚动时间戳:onScroll 会把 store.year 设为"中间年份",watch 异步回调时
// scrollTop 已推进 -> diff 巨大 -> 反向 cancel 动画(L2 长动画下尤其严重)。
// 故程序化滚动后 120ms 内的 store.year 变化一律视为内部、跳过,只放行外部跳转(搜索等)。
let lastProgScroll = 0
// 外部年份跳变(URL 恢复/hashchange/年谱点击/地图定位)引发的回滚动画防环旗:
// 动画期间 onScroll 不再回写 store —— 否则中间年份会持续冲刷 store 与 URL
// (分享出去的是飞行途中的某一年),落定年份也未必精确等于目标。
// 与星图扫描环 draggingScan 同款防环 pattern(starmap/engine/columnMount.js:605-610)。
let extScrollGuard = false
let extScrollTarget = null
// M12:外部锚定落定后的短暂保护窗。锚定的意图值(事件 tYear 取 floor)比 scrollTop
// 反算更权威 —— 见 onScroll 处注释。只对 external 锚定生效:zoomAt 换档后 store.year
// 本就该由新镜头位置反算得出,连它一起挡会让「点桶放大」的镜头年份停在原处(实测
// m8 T8.2 因此偏了 503 年)。
let anchorPinUntil = 0
let handledNavigationSeq = 0

// === lens 胶囊脉冲(B1):外部跳年(搜索/hashchange/年谱)引发回滚时,朱红闪一次
// 告知「柱子为你跳了」。类名挂 900ms(动画本身 160ms),连跳时重挂以重启动画。
// 挂久不是调味是刚需:滚动动画全程 ~650ms 里主线程被逐帧重渲染占满(单帧都不到
// longtask 阈值,但 CDP 断言会被饿着),实测 350/500ms 窗口内 Playwright 的首次采样
// 可能整段错过脉冲(B1 钉子 3 跑 2 败);900ms = 动画全程 + 断言排队余量,观感不变。
const lensPulse = ref(false)
let lensPulseTimer = 0
function flashLens() {
  clearTimeout(lensPulseTimer)
  lensPulse.value = false
  requestAnimationFrame(() => { lensPulse.value = true })
  lensPulseTimer = setTimeout(() => { lensPulse.value = false }, 900)
}

// === 几何:year -> px 映射,线性 ===
const TOP = 240  // 顶部留白给 lens(lens 线固定在 top:240px)
// 五级 LOD 的 px/年: L0 朝代远景(0.42) -> L1 帝王 -> L2 编年(12) -> L3 月 -> L4 日
const K_MIN = 0.42
const K_YEAR = 12      // L2 编年档(M12 之前的 K_MAX)
// L4 日档:8px/日 × 365.25 —— 取 8px 是「一日可点选」的下限。
// 内高 = TOP + 4126×2922 + 760 ≈ 1206 万 px。Chrome 单元素高度上限实测
// 33,554,428px(2^25),且 scrollTop=12,000,000 精确生效 —— 留有 2.8 倍余量。
// 实测脚本见 WORKLOG M12 段;此前「日档不可行」的判断是未实测的推断。
const K_MAX = 2922
const LEVEL_MAX = 4
const MONTH = 1 / 12
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))
function kFromLevel(lv) {
  // 分段指数,不并成一条曲线:lv∈[0,2] 段原样保留(0.42→2.245→12),
  // 使既有三档的 px/年 一个数都不变 —— M7 车道容量、M8 回列反推与其 e2e 断言
  // 全部标定在那三个值上,动一点就要重标定一片。lv∈[2,4] 段续接到 2922。
  if (lv <= 2) return K_MIN * Math.pow(K_YEAR / K_MIN, lv / 2)
  return K_YEAR * Math.pow(K_MAX / K_YEAR, (lv - 2) / 2)
}
// kFromLevel 的精确逆。M8 的回列反推「所需 k → 该去哪一档」必须走这里,
// 分段之后再拿单段公式套会算出错档(k=200 会被算成 lv≈5.4 而钳到顶)。
function levelFromK(kk) {
  if (kk <= K_YEAR) return 2 * Math.log(kk / K_MIN) / Math.log(K_YEAR / K_MIN)
  return 2 + 2 * Math.log(kk / K_YEAR) / Math.log(K_MAX / K_YEAR)
}
// 连续缩放等级 0..4;0=朝代 1=帝王 2=编年 3=月 4=日。取代旧 store.zoom 两档离散模式。
const zoomLevel = ref(1)
const scaleOpen = ref(false)
function k() { return kFromLevel(zoomLevel.value) }

// 月/日 -> 小数年。月按等分(1/12)而非真实月长:1912 前史料所载为农历,
// 农历月长本就 29/30 交替且置闰,强求「精确」反而是假精确;1912 后公历用
// 30.44 天均月,单月误差 <2 天(日档下 <16px)。位置是近似,标签是原载 ——
// 两者的差别在界面上以历法口径注记说明,不冒充换算过。
// 小数年 -> 整数年。两条来路口径不同,不能共用一个函数,这点踩过:
//
//  · yearOfIntent —— 入参是调用方的意图值(事件的 tYear),没经过像素往返。
//    直接 floor:755.917 就是「755 年十二月」,属 755 年。
//
//  · yearOfScroll —— 入参由 scrollTop 反算,而浏览器把 scrollTop 量化到整像素。
//    实测 750 年在 L1(k=2.245)下期望 scrollTop=6398.234,实存 6398,反算得
//    749.896 —— 量化误差 0.104 年。floor 会把它判成 749,首屏载入即错一年
//    (11 条 e2e 当场变红,且不是浮点 eps 能救的,量级差了五个数量级)。
//    故年档一律 round:一个像素跨 2.4 年时,「最近的那一年」才是唯一说得通的口径。
//    亚年档 k>=187,一像素 <0.006 年,floor 既安全又正确(且必须 floor,否则
//    锚线停在十二月时右栏会比 lens 快一年)。
function yearOfIntent(exact) { return Math.floor(exact) }

// 落在刻度一像素以内就归给那一格,否则归给「所在的那一格」。
// 这条规则同时管年界和月界 —— 两处犯的是同一个错:边界值经像素量化后总是
// 差一点点到不了整数,裸 floor 就整格掉到前一格。
// tol 取 0.75 像素(量化误差上界),因为像素栅格本就分辨不出比这更细的位置。
function snapIdx(v, tol) {
  const near = Math.round(v)
  return Math.abs(v - near) <= tol ? near : Math.floor(v)
}
function yearOfScroll(exact) { return snapIdx(exact, 0.75 / k()) }

function toTYear(d) {
  return toAxisYear(d)
}
const ORIGIN = 2100  // 时间轴原点:年 -2100(先秦上界)映射到顶部;yPos=(y+ORIGIN)*k
const AXIS_END = 2026       // 时间轴下界;在世人物的条延至此
const SPAN = ORIGIN + AXIS_END  // -2100..2026 总跨度 4126 年
function yPos(y) { return TOP + (y + ORIGIN) * k() }
const innerHeight = computed(() => TOP + SPAN * k() + 760)

// LOD 档位(用于按钮高亮):按等级分桶
const lod = computed(() => {
  const lv = zoomLevel.value
  if (lv < 0.5) return 0
  if (lv < 1.5) return 1
  if (lv < 2.5) return 2
  if (lv < 3.5) return 3
  return 4
})
const LOD_LABELS = ['朝代', '帝王', '编年', '月', '日']
const lodLabel = computed(() => LOD_LABELS[lod.value])
const axisUnit = computed(() => lod.value === 4 ? 'day' : lod.value === 3 ? 'month' : 'year')
watch(axisUnit, (unit) => store.setAxisContext(store.axisExactYear, unit), { immediate: true })
// 亚年档:事件按月/日分离摆放,刻度出月线,读数带月份
const subYear = computed(() => zoomLevel.value >= 2.5)
// 口径注记随所在年代变:1912 前后不是同一套历法,含糊其辞不如分别说清
const calendarNote = computed(() => {
  const yr = yearOfScroll(exactYear.value)
  return isGregorian(yr)
    ? '月/日为公历'
    : '月为史料原载农历 · 按 1/12 年摆放,未换算公历'
})
// 远景过滤:L0 下只显重要人物/事件,与旧"朝代脉络"模式一致
const overview = computed(() => zoomLevel.value < 0.55)
// 帝王段淡入:跨 L0->L1 边界平滑出现(不硬跳)
const emperorOpacity = computed(() => clamp((k() - 0.7) / 0.5, 0, 1))

// tick 密度按 k 分档(标准 nice ticks:跨档会切密度,但 LOD 层靠 opacity 平滑)
// 返回 [minorStep(年), majorStep(年), unit]。unit='month' 时步长为 1/12,
// 循环改按「自轴原点起第 N 个月」的整数索引走 —— 小数取模有浮点毛刺。
// 不出逐日刻度:农历月长 29/30 不等且置闰,公历月长 28~31,一把等分尺画到日
// 就是在宣称一种它撑不起的精确;日的价值在事件几何分离,不在刻度。
function tickSteps(kk) {
  if (kk >= 400) return [MONTH, MONTH * 3, 'month']  // L4 日: 月线, 季标
  if (kk >= 60) return [MONTH, 1, 'month']           // L3 月: 月线, 年标
  if (kk >= 9) return [1, 10, 'year']                // L2: 逐年线, 十年标
  if (kk >= 4) return [2, 20, 'year']
  if (kk >= 1.5) return [10, 50, 'year']             // L1: 帝王级
  if (kk >= 0.8) return [20, 100, 'year']
  return [100, 500, 'year']                          // L0: 朝代级
}

// === 加载数据 ===
async function loadData() {
  // 种子人物(有 bio 且非 CBDB 扩展)+ 事件/战役 + 帝王(role=emperor)
  const [personRes, eventRes, battleRes, emperorRes] = await Promise.all([
    // prefer_seed:库里 5593 个 Person 中 4892 是 CBDB 批量导入,而接口 limit 上限就是
    // 2000 —— 不排序的话种子人物会被 CBDB 挤掉大半(实测只剩 301/583 上得了轴)。
    // fields 是白名单:filter 里要用的字段必须列出,否则该字段恒为 undefined 而条件
    // 静默失效(reign_start 漏列过一次,21 位上古君主照旧上不了轴)。
    getEntities({ type: 'Person', limit: 2000, prefer_seed: true, fields: 'id,name,born,died,floruit_start,floruit_end,reign_start,reign_end,bio,image,courtesy_name,importance,roles,ext' }),
    getEntities({ type: 'Event', limit: 500, fields: 'id,name,date,end_date,description,impact,location,category,importance,ext' }),
    getEntities({ type: 'Battle', limit: 500, fields: 'id,name,date,end_date,description,location,significance,category,importance' }),
    getEntities({ type: 'Person', role: 'emperor', limit: 500, fields: 'id,name,alias,born,died,reign_start,reign_end,importance,ext' }),
  ])
  // 在世:有生年无卒年,且生年近到还可能在世。生年过早而无卒年的属卒年失载(非在世),
  // 不该一路画到今天 —— 当下库里 born-only 者最早生于 1928,尚无此情形,阈值是护栏。
  const isLiving = (p) => p.born?.year != null && p.died?.year == null
                          && p.born.year >= AXIS_END - 110
  const hasFl = (p) => p.floruit_start?.year != null && p.floruit_end?.year != null
  // 卒年已知、生年不可考:白起/卫青/赵高等确无生年可考,编一个即造假,又不该整个消失。
  // 此前要 born+died 俱全 → 91 人上不了轴,含秦始皇、关羽、张良、萧何、卫青、白起、
  // 李斯、管仲、赵高 9 位 importance=1 —— 正是点1「甚至没包含秦始皇等关键人物」。
  const isDeathOnly = (p) => p.died?.year != null && p.born?.year == null && !hasFl(p)
  // 只有在位年可依:禹/启/汤/武丁/盘庚/齐桓公/秦穆公/楚庄王/勾践/商纣王等 21 人,
  // 上古与先秦君主多不记生卒。此前 filter 不认 reign → 他们只在帝王带上,人物轴上没有。
  // 在位≠在世,故按模糊态画,tag 作「在位」而非生卒。
  const reignOf = (p) => [p.reign_start?.year ?? p.reign_end?.year,
                          p.reign_end?.year ?? p.reign_start?.year]
  const isReignOnly = (p) => p.born?.year == null && p.died?.year == null && !hasFl(p)
                             && reignOf(p)[0] != null
  people.value = personRes.items.filter(p => {
    if (p.id.startsWith('p_cbdb_')) return false
    return (p.born?.year != null && p.died?.year != null)
        || isLiving(p) || isDeathOnly(p) || hasFl(p) || isReignOnly(p)
  }).map(p => {
    // 生卒不详者回退活跃年代(floruit)。周公旦/妇好/姜尚/伊尹等本无可考生卒,
    // 编一个即造假;只记其见于史载的活动区间 —— 即点1 说的「模糊化表达」。
    // 四种时间锚,按确定度递降。除生卒外皆为模糊态,视觉与 title 都要能分辨。
    const hasBorn = p.born?.year != null
    const living = isLiving(p)
    const deathOnly = isDeathOnly(p)
    const reignOnly = isReignOnly(p)
    let from, to
    if (hasBorn) {
      from = p.born.year
      to = p.died?.year ?? AXIS_END          // 在世者条延至轴末
    } else if (deathOnly) {
      from = to = p.died.year                // 段长为零 → 只落一个卒年标记,不虚构生年
    } else if (reignOnly) {
      [from, to] = reignOf(p)                // 在位年;上古君主多不记生卒
    } else {
      from = p.floruit_start.year; to = p.floruit_end.year
    }
    return {
      id: p.id, name: p.name, type: 'Person',
      born: from, died: to,
      isFloruit: !hasBorn && !deathOnly,     // floruit 与 reignOnly 同走模糊视觉
      reignOnly,
      living, deathOnly,
      approx: !!p.ext?.disputed,     // 生卒有异说/系推估
      bio: p.bio, image: p.image, courtesy_name: p.courtesy_name,
      significance: p.significance,
      roles: p.roles || [], importance: p.importance,
    }
  })
  // 帝王:T4.1b 起,段起讫优先用在位年(reign_start/reign_end),回退生卒。
  // bce 约定的秦汉帝王 born/died/reign 为正数(=BCE),与前端 signed 年份空间(负=BCE)
  // 不兼容,其段在远景会错位--这是既有数据约定问题,见 WORKLOG/遗留。
  // 渲染单位是「在位段」而非「人」:重祚者(唐睿宗 684-690/710-712、唐中宗 684/705-710、
  // 明英宗 正统1435-1449/天顺1457-1464)有两段在位,而 reign_start/end 只装得下一段。
  // 数据里 ext.reigns 早已完整记着两次(含 note),前端却只读单组 → 帝王带上出现实洞:
  // 1460(天顺)、711(睿宗复位) 处无任何帝王 —— 作为坐标系这是缺失。
  emperors.value = emperorRes.items
    // 收录帝王:有在位年(reign)或有生卒即可——上古帝王多只有在位年、无确切生卒
    .filter(p => p.reign_start?.year != null || p.reign_end?.year != null || (p.born?.year != null && p.died?.year != null))
    .flatMap(p => {
      const base = {
        id: p.id, name: p.name,
        alias: Array.isArray(p.alias) ? (p.alias[0] || '') : (p.alias || ''),
        // 称谓统一:ext.title=大众通称(帝号>年号>本名,以通称为准),ext.regime=政权(着色/割据)
        title: p.ext?.title || null,
        regime: p.ext?.regime || null,
        born: p.born?.year ?? null, died: p.died?.year ?? null,
        importance: p.importance,
      }
      const rs = p.ext?.reigns
      if (Array.isArray(rs) && rs.length) {
        return rs
          .filter(r => r?.from != null)
          .map((r, i) => ({ ...base, key: `${p.id}#${i}`, reignStart: r.from,
                            reignEnd: r.to ?? r.from, reignNote: r.note || '' }))
      }
      return [{ ...base, key: p.id,
                reignStart: p.reign_start?.year ?? null,
                reignEnd: p.reign_end?.year ?? null, reignNote: '' }]
    })
    .sort((a, b) => (a.reignStart ?? a.born ?? 0) - (b.reignStart ?? b.born ?? 0))
  const evs = [...eventRes.items, ...battleRes.items]
    .filter(e => e.date?.year != null)
    .map(e => ({
      id: e.id, name: e.name, type: e.type,
      // Battle 也有 category(军事族 4 类),与 Event 同枚举 → 同族同色同字形,
      // 使「Battle 实体 / 军事类事件」这套双重建模在轴上收口为一种视觉。
      // 回落:Battle 缺值当单次战役,Event 缺值进兜底。
      category: e.category || (e.type === 'Battle' ? 'battle' : 'other'),
      importance: e.importance ?? 3,   // 缺省视为一般,与 schema 约定一致
      // 线索(ext.threads):同属一个历史问题的事件,与因果正交——
      // 燕云的「割让↔收复」隔 432 年,是同一问题的两端,不是谁导致谁。
      threads: (e.ext?.threads || []).map(t => t.name),
      year: e.date.year, year_end: e.end_date?.year,
      // M12:year 仍是整数(URL / 地图 / 在世名单 / 干支年号 / __hkbTimeline 全靠它,
      // 且 m8 的回列 e2e 直接消费 eventYears)。几何另走 tYear 小数年 —— 一名两用
      // 必然在某处把小数喂进 ganzhi 那类整数取模函数里。
      month: e.date.month ?? null, day: e.date.day ?? null,
      tYear: toTYear(e.date), tYearEnd: toTYear(e.end_date),
      description: e.description, impact: e.impact,
      location: e.location, significance: e.significance,
    }))
  events.value = evs.sort((a, b) => a.tYear - b.tYear)
  console.log(`[TimeColumn] loaded ${people.value.length} persons, ${emperors.value.length} emperors, ${events.value.length} events`)
}

// === 滚动 -> year ===
function syncViewTop() {
  if (scrollRef.value) {
    viewTop.value = scrollRef.value.scrollTop
    viewH.value = scrollRef.value.clientHeight
    viewW.value = scrollRef.value.clientWidth || 700
  }
}

function onScroll(e) {
  const st = e.target.scrollTop
  // 同步 gutter 滚动(gutter 视觉固定宽度,但内容随 scroll 垂直移动)
  if (gutterInnerRef.value) {
    gutterInnerRef.value.style.transform = `translateY(${-st}px)`
  }
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = 0
    syncViewTop()
    // M12:小数年只落在组件本地 ref,不进 store —— 进了 store 就会经 App 的
    // watch(timeStore.year) 每帧写一次 URL(settledYear 的 180ms 消抖挡得住地图,
    // 挡不住 URL)。地图/在世名单/干支年号一律只认整数年,本就不需要小数。
    const exact = clamp(-ORIGIN + st / k(), -ORIGIN, AXIS_END)
    // 外部锚定刚落定后仍可能补发量化后的尾随 scroll；这 250ms 内意图值比
    // scrollTop 回读更精确，连 exactYear 也不可被 0.3px 误差冲掉。
    if (!extScrollGuard && performance.now() < anchorPinUntil) return
    exactYear.value = exact
    // 外部跳变引发的回滚动画期间不回写年份(防环旗见上),动画结束由 finish 钉死目标年。
    // exactYear 在旗上方更新:动画途中 lens 读数要跟着走,否则月档下滚动时读数是僵的
    if (extScrollGuard) return
    store.setAxisContext(exact, axisUnit.value)
    // 锚定刚落定的保护窗内不回写年份:锚定的意图值(事件 tYear 取 floor)比像素回读
    // 更权威。L1 下一像素跨 0.445 年,锚到「755 年十二月」后由 scrollTop 反算只得
    // 756 —— 那不是更精确,是栅格分辨不出来,finish() 钉的 755 才对。
    // (watch(store.year) 的守卫②是同一道理的另一半:那里防跳年被自己的动画吞掉,
    //  这里防落定后被自己的回读覆盖。)
    const y = yearOfScroll(exact)
    if (y !== store.year) store.setYear(y)
    // C1 播放中手动滚柱即停(程序化滚动已被上方防环旗拦截,到此处必为用户滚动)
    if (store.playing) store.stopPlay()
  })
}

function scrollToYear(y, smooth = true, external = false) {
  const el = scrollRef.value
  if (!el) return
  // M12:滚动位置用小数(点选「755 年十一月」的事件要停在十一月那一格,不是正月),
  // 但 store/URL/extScrollTarget 一律整数年。此前这里无条件 Math.round,月档下
  // 任何锚定都会掉回该年正月。
  const exact = clamp(y, -ORIGIN, AXIS_END)
  const target = yearOfIntent(exact)   // 意图值,无像素往返,直接 floor
  const top = (exact + ORIGIN) * k()
  lastProgScroll = performance.now()
  if (external) { extScrollGuard = true; extScrollTarget = target; flashLens() }
  // 落定:清防环旗,并把年份精确钉在目标值 —— 动画末帧 scrollTop 经取整换算可能差 1 年,
  // 不钉的话 URL 与读数会停在邻近年份上
  const finish = () => {
    // hover 尾窗:落定后 Chrome 还会为静止光标下的元素补发一轮 mouseenter,压住
    hoverSuppressUntil = performance.now() + 400
    if (!external) return
    // 落定后的尾随 scroll 事件会拿 scrollTop 反算覆盖掉这里钉的年份,压一个短窗
    anchorPinUntil = performance.now() + 250
    extScrollGuard = false
    extScrollTarget = null
    exactYear.value = exact
    store.setAxisContext(exact, axisUnit.value)
    if (store.year !== target) store.setYear(target)
  }
  if (!smooth) { el.scrollTop = top; syncViewTop(); finish(); return }
  if (scrollAnim) cancelAnimationFrame(scrollAnim)
  const from = el.scrollTop, dist = top - from
  if (Math.abs(dist) < 2) { el.scrollTop = top; finish(); return }
  const dur = Math.min(650, Math.max(300, Math.abs(dist) * 0.12))
  const t0 = performance.now()
  const step = (t) => {
    lastProgScroll = t  // 每帧刷新,覆盖整个动画期间的 onScroll->store.year
    const f = Math.min(1, (t - t0) / dur)
    const e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2
    el.scrollTop = from + dist * e
    if (f < 1) scrollAnim = requestAnimationFrame(step)
    else { scrollAnim = 0; finish() }
  }
  scrollAnim = requestAnimationFrame(step)
}

// === 点选即锚定(M11) ===
// 原先柱上点选只改选中态,锚定线纹丝不动 —— 右栏地图/在世名单仍停在原年,
// 于是「点了安史之乱,右边还是天宝九载的疆域」。方案二:轴整体滚动,把选中者
// 送到锚定线上(scrollToYear 令 scrollTop=(y+ORIGIN)*k,该年恰落在 lens 的 TOP 处)。
//
// 走 store.setYear 而非直接 scrollToYear,是为与 SearchBar 的 B1 搜索闭环同一通道:
// watch(store.year) 负责平滑滚动 + lens 脉冲 + 经 settledYear 带动地图换幅与在世名单。
// 直接调 scrollToYear(external=false)则无脉冲、无防环旗 —— 帝王条此前正是这么写的。
function anchorTo(y) {
  if (y == null) return
  // 守卫②(watch 里的 120ms 窗)会把紧随程序化滚动而来的跳年误判为 onScroll 回写而
  // 静默吞掉 —— 连点两张卡时第二张不动。显式清零使本次跳年必然生效。
  lastProgScroll = 0
  const exact = clamp(y, -ORIGIN, AXIS_END)
  // 已停在此处(小数级)就只给脉冲,不做一次 0 距离动画
  // “已在此处”按当前像素分辨率判断。旧阈值 0.005 年约 1.8 天，会把日档一次
  // 8px 的轴日步进误判为零距离；半像素以下才是真的无可见移动。
  if (Math.abs(exactYear.value - exact) * k() < 0.5) { flashLens(); return }
  // M12:直接走 external 通道而不经 store.setYear —— 后者触发的 watch 只带得动
  // 整数年,月/日分量会在那一跳里被抹掉(点「755 年十一月」落回正月)。
  // finish() 仍会把整数年写回 store,地图与在世名单照常同步。
  scrollToYear(exact, true, true)
}

function consumeNavigation(request) {
  if (!request || request.seq === handledNavigationSeq || !scrollRef.value) return
  handledNavigationSeq = request.seq
  const exact = request.exactYear ?? toTYear(request)
  // 月份跳转若还在年档，亚像素不足以承载精确位置；进入既有月档后再用 anchorTo。
  if (request.month != null && zoomLevel.value < 3) {
    extScrollGuard = true
    extScrollTarget = yearOfIntent(exact)
    zoomLevel.value = 3
    nextTick(() => anchorTo(exact))
    return
  }
  anchorTo(exact)
}
// 选中 + 锚定的统一入口。year 为空(如无可定年实体)时只选中不动轴。
function selectAndAnchor(id, type, year) {
  selectionStore.selectEntity(id, type, 'timeline')
  anchorTo(year)
}

// === 缩放 ===
// 交互:Ctrl/⌘+滚轮缩放(普通滚轮留给列表滚动,避免冲突);触摸双指捏合;双击空白复位。
// 锚定光标指向的年份:缩放前后该年份停在原屏幕位置,不漂移。
function zoomAt(cursorY, newLevel) {
  const el = scrollRef.value
  if (!el) return
  newLevel = clamp(newLevel, 0, LEVEL_MAX)
  if (newLevel === zoomLevel.value) return
  const oldK = kFromLevel(zoomLevel.value)
  // 光标处的"内容坐标"-> 年份
  const cursorContentY = el.scrollTop + cursorY
  const yearAtCursor = (cursorContentY - TOP) / oldK - ORIGIN
  zoomLevel.value = newLevel
  const newK = kFromLevel(newLevel)
  // 反推新 scrollTop,使该年份仍停在 cursorY
  const target = (yearAtCursor + ORIGIN) * newK - cursorY + TOP
  el.scrollTop = target
  // 跳变大时 target 会超出旧 DOM 内高被浏览器钳住(innerHeight 是 computed,
  // 要等 Vue flush 才到位)——实测 L0 直跳 L2 目标 35881 被钳成 1833,镜头飞到
  // 年 -1939。rAF 时内高已更新,复核补设;小步缩放(滚轮)下此为 no-op
  requestAnimationFrame(() => {
    if (Math.abs(el.scrollTop - target) > 2) el.scrollTop = target
  })
  lastProgScroll = performance.now()
  // 缩放瞬间布局在光标下重排,同样压住 hover 补发(与 scrollToYear 尾窗同理)
  hoverSuppressUntil = performance.now() + 400
  syncViewTop()
}

function onWheel(e) {
  // Ctrl/⌘+滚轮 = 缩放;否则放行给列表滚动
  if (!e.ctrlKey && !e.metaKey) return
  e.preventDefault()
  const rect = scrollRef.value.getBoundingClientRect()
  const cursorY = e.clientY - rect.top
  zoomAt(cursorY, zoomLevel.value + (-e.deltaY) * 0.005)
}

// 触摸捏合:双指距离比 -> 缩放等级,锚定双指中点
let pinchDist0 = 0, pinchLevel0 = 0, pinchMidY = 0
function onTouchStart(e) {
  if (e.touches.length === 2) {
    const [a, b] = e.touches
    pinchDist0 = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY) || 1
    pinchLevel0 = zoomLevel.value
    const rect = scrollRef.value.getBoundingClientRect()
    pinchMidY = ((a.clientY + b.clientY) / 2) - rect.top
  }
}
function onTouchMove(e) {
  if (e.touches.length !== 2 || !pinchDist0) return
  e.preventDefault()
  const [a, b] = e.touches
  const dist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)
  const newLevel = pinchLevel0 + Math.log2(dist / pinchDist0) * 0.8
  zoomAt(pinchMidY, newLevel)
}

function setLod(level) {
  scaleOpen.value = false
  if (level === lod.value && Math.abs(zoomLevel.value - level) < 0.02) return
  // 换档保留锚线的精确月/轴日位置；用整数 store.year 会把七月重新送回正月。
  const y = exactYear.value
  // 内高从数万 px 瞬增到千万 px 时，浏览器会先用旧 scrollTop 发一帧 scroll；提前
  // 立防环旗，随后在 Vue 刷新高度后直接钉回原精确位置，避免镜头短暂飞到先秦。
  extScrollGuard = true
  extScrollTarget = yearOfIntent(y)
  zoomLevel.value = level
  nextTick(() => { scrollToYear(y, false, true); syncViewTop() })
}

function resetZoom() {
  scaleOpen.value = false
  const y = store.year
  zoomLevel.value = 0
  nextTick(() => { scrollToYear(y, true); syncViewTop() })
}

// === year -> 滚动(外部 year 变化时,如 URL 恢复/hashchange/年谱点击) ===
// 三重守卫:① 外部回滚动画途中又来了新的外部目标 -> 改目标重滚,不被自己的动画吞掉;
// ② 120ms 内刚发生过程序化滚动 -> 视为 onScroll 内部回写,跳过;
// ③ 否则若 scrollTop 已在该年份附近(取整误差)也跳过。仅真外部跳转才重滚。
watch(() => store.year, (y) => {
  const el = scrollRef.value
  if (!el) return
  if (extScrollGuard) {
    if (y !== extScrollTarget) scrollToYear(y, true, true)
    return
  }
  if (performance.now() - lastProgScroll < 120) return
  const expectedTop = (y + ORIGIN) * k()
  if (Math.abs(el.scrollTop - expectedTop) > Math.max(8, k())) {
    scrollToYear(y, true, true)
  }
})
watch(() => store.navigationRequest, consumeNavigation)

// === 选中实体 ===
watch(() => selectionStore.selectedEntityId, async (id) => {
  if (!id) { selected.value = null; return }
  try {
    selected.value = await getEntity(id)
  } catch { selected.value = null }
}, { immediate: true })

onMounted(async () => {
  await loadData()
  loadCausal()   // 不阻塞首屏:线索只在选中事件后才用得上
  await nextTick()
  if (scrollRef.value) {
    viewH.value = scrollRef.value.clientHeight
    // wheel/touch 需 preventDefault,手动绑定为 non-passive
    scrollRef.value.addEventListener('wheel', onWheel, { passive: false })
    scrollRef.value.addEventListener('touchstart', onTouchStart, { passive: false })
    scrollRef.value.addEventListener('touchmove', onTouchMove, { passive: false })
    // T7.1 尺寸观测:分栏拖拽/窗口缩放即重算布局
    resizeObs = new ResizeObserver(() => syncViewTop())
    resizeObs.observe(scrollRef.value)
  }
  // 挂载定位:滚到 store 当前年份。URL 带了 year 时,App 在 setup 阶段已 loadFromUrl 恢复,
  // 此处的 store.year 就是 URL 年份 —— 不存在「先滚默认 750 再被 URL 覆盖」的时序窗。
  scrollToYear(store.year, false)
  consumeNavigation(store.navigationRequest)
  syncViewTop()
  // 默认选中李白(仅当 URL 没指定实体 —— loadFromUrl 已在挂载前恢复选中态)。
  // 这是「演示锚点」而非随机默认:首屏需要一份有代表性的档案(关系/年谱/疆域俱全),
  // 进站即见完整交互样例;URL 带了 entity 时此锚点不生效。
  if (!selectionStore.selectedEntityId) {
    const libai = people.value.find(p => p.name === '李白')
    if (libai) selectionStore.selectEntity(libai.id, 'Person', 'timeline')
  }
})

onBeforeUnmount(() => {
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
  if (scrollAnim) cancelAnimationFrame(scrollAnim)
  clearTimeout(lensPulseTimer)
  if (resizeObs) resizeObs.disconnect()
  if (scrollRef.value) {
    scrollRef.value.removeEventListener('wheel', onWheel)
    scrollRef.value.removeEventListener('touchstart', onTouchStart)
    scrollRef.value.removeEventListener('touchmove', onTouchMove)
  }
})

// === gutter 朝代块 ===
// C3 跳年弹层：时间工具组内的日历搜索按钮唤起；确认后由柱平滑滚动并脉冲提示。
const jumpOpen = ref(false)
function onJumpConfirm(navigation) {
  jumpOpen.value = false
  store.stopPlay()
  store.requestNavigation(navigation)
}

const gutterBlocks = computed(() => {
  const _k = k()
  return ERAS.map((e, i) => {
    const top = yPos(e[1])
    const h = (e[2] - e[1]) * _k
    const chars = e[0].length
    const label = h >= chars * 17 + 14 ? e[0] : (h >= 30 ? e[0].charAt(0) : '')
    return {
      // key 取朝代本身,不取 label/startYear:后二者按可用高度派生,远景下双双成空串,
      // 多个窄朝代的 key 就都是 "" → Vue 无法正确 diff(实测远景复位时报重复 key)
      key: e[0] + ':' + e[1],
      label, startYear: h >= 22 ? fmtY(e[1]) : '',
      // C3 hover 提示:朝代 起–讫 · 点击前往(朝代名保持繁体,数据层不转写)
      tip: `${e[0]} ${fmtY(e[1])}–${fmtY(e[2])} · 点击前往`,
      onClick: () => scrollToYear(Math.round((e[1] + e[2]) / 2)),
      style: {
        top: top + 'px', height: h + 'px',
        background: i % 2 ? 'var(--hover)' : 'transparent',
      },
      labelStyle: {
        fontSize: (h > 200 ? 20 : 15) + 'px',
        letterSpacing: (h > 200 ? 8 : 3) + 'px',
      },
      yearStyle: {},
    }
  })
})

// === 年份刻度(视口虚拟化 + nice ticks) ===
const VIEW_BUF = computed(() => Math.max(viewH.value, 600))
const ticks = computed(() => {
  const _k = k()
  const [minorStep, majorStep, unit] = tickSteps(_k)
  const buf = VIEW_BUF.value
  // 视口内容 Y 范围 -> 年份范围(加缓冲)
  const yLo = Math.max(-ORIGIN, (viewTop.value - buf - TOP) / _k - ORIGIN)
  const yHi = Math.min(AXIS_END, (viewTop.value + viewH.value + buf - TOP) / _k - ORIGIN)
  const result = []
  const firstIdx = Math.ceil(yLo / minorStep)
  const lastIdx = Math.floor(yHi / minorStep)
  // 大刻度判定改按索引取模而非 ty % majorStep:亚年档 ty 是小数,浮点取模
  // 永远取不到 0(1/12*12 !== 1 的那类毛刺),整条轴会一个大刻度都不出。
  const ratio = Math.max(1, Math.round(majorStep / minorStep))
  const isMonth = unit === 'month'
  for (let i = firstIdx; i <= lastIdx; i++) {
    const ty = i * minorStep
    const top = yPos(ty)
    const isMajor = ((i % ratio) + ratio) % ratio === 0
    // 月档下索引 i 即「自轴原点起第 N 个月」,反解出年与月(负年取 floor 才对:
    // i=-1 是「年 -1 的十二月」而非「年 0 的负一月」)
    const ty_year = isMonth ? Math.floor(i / 12) : ty
    const ty_month = isMonth ? (((i % 12) + 12) % 12) + 1 : null
    result.push({
      key: 't' + i, year: ty_year, isLabel: isMajor,
      lineStyle: { top: top + 'px', opacity: isMajor ? 1 : 0.45 },
      // 月档大刻度落在正月时只写年(「750年正月」冗余),其余写年+月
      label: !isMajor ? ''
        : isMonth && ty_month !== 1 ? fmtYM(ty_year, ty_month) : fmtY(ty_year),
      labelStyle: { top: (top - 13) + 'px' },
    })
  }
  return result
})

// 帝王段起讫:在位优先、生卒回退(上古帝王多只有在位年);单端点者退化为标记
function empSpan(p) {
  const s = p.reignStart ?? p.born ?? p.reignEnd ?? p.died
  const en = p.reignEnd ?? p.died ?? p.reignStart ?? p.born
  return [s, en]
}
// === 帝王分道:对全量帝王做区间调度(道号稳定,不随视口跳动) ===
// 同一政权历代帝王在位首尾相接、互不重叠 -> 自然回落同一道;
// 唯并立政权(三国/十六国/南北朝/五代十国)才分出多道 -> 割据即以"多道并排"呈现。
const emperorLanes = computed(() => {
  const list = emperors.value
    .map(p => ({ p, s: empSpan(p)[0], e: empSpan(p)[1] }))
    .filter(x => x.s != null)
    .sort((a, b) => a.s - b.s || a.e - b.e)
  const lanes = []          // 每道已占用的讫年
  const laneOf = {}
  for (const x of list) {
    let li = lanes.findIndex(last => last <= x.s)
    if (li < 0) {
      if (lanes.length >= EMP_MAX_LANES) li = 0   // 极端并立:并入首道(宁可少数重叠,不撑爆横向)
      else { lanes.push(x.e); li = lanes.length - 1 }
    }
    if (lanes[li] == null || x.e > lanes[li]) lanes[li] = x.e
    laneOf[x.p.key] = li      // 按在位段取键:重祚者两段各自分道,按人取键会互相覆盖
  }
  return { laneOf, laneCount: Math.max(lanes.length, 1) }
})
const empGutterEnd = computed(() => ERA_W + emperorLanes.value.laneCount * EMP_LANE_W)

// 政权配色:取 --cat-* 既有色相,按首次出现顺序分配;wash 极淡以呼应朝代带的纸墨调
// 并立时各道色相相异 -> 割据状态不必额外标注即自证
// 注:palettes.js 以 `--cat-${type.toLowerCase()}` 注入,变量名全小写
const REGIME_HUES = ['var(--cat-polity)', 'var(--cat-place)', 'var(--cat-battle)',
                     'var(--cat-faction)', 'var(--cat-title)', 'var(--cat-person)']
const regimeHue = computed(() => {
  const order = []
  for (const p of [...emperors.value].sort((a, b) => (a.reignStart ?? a.born ?? 0) - (b.reignStart ?? b.born ?? 0))) {
    const r = p.regime || '—'
    if (!order.includes(r)) order.push(r)
  }
  const m = {}
  order.forEach((r, i) => { m[r] = REGIME_HUES[i % REGIME_HUES.length] })
  return m
})

// === 帝王在位段(L1/L2 显现;视口虚拟化) ===
const viewportEmperors = computed(() => {
  const op = emperorOpacity.value
  if (op <= 0.01) return []
  const _k = k()
  const lo = viewTop.value - VIEW_BUF.value
  const hi = viewTop.value + viewH.value + VIEW_BUF.value
  const selId = selectionStore.selectedEntityId
  const { laneOf } = emperorLanes.value
  return emperors.value.filter(p => {
    const [s, en] = empSpan(p)
    if (s == null) return false
    const top = yPos(s)
    const h = Math.max((en - s) * _k, 3)
    return top + h >= lo && top <= hi
  }).map(p => {
    // 有在位年用 reign,无则回退生卒;hover title 区分"在位/生卒"二者可辨
    const hasReign = p.reignStart != null || p.reignEnd != null
    const [s, en] = empSpan(p)
    const top = yPos(s)
    const h = Math.max((en - s) * _k, 3)
    const isSel = p.id === selId
    const isHov = p.id === selectionStore.hoveredEntityId
    const lane = laneOf[p.key] ?? 0
    // 称谓:ext.title(大众通称) > alias[0] > 本名
    const labelTxt = p.title || p.alias || p.name
    const showLabel = h >= labelTxt.length * 11 + 6
    const rangeTag = hasReign ? '在位' : '生卒'
    const hue = regimeHue.value[p.regime || '—'] || 'var(--ink)'
    // 淡 wash + 分隔线 + ink 竖排字,与朝代带同语言(原实心墨条过重)
    const bg = isSel ? `color-mix(in srgb, var(--accent) 30%, transparent)`
      : isHov ? `color-mix(in srgb, ${hue} 34%, transparent)`
              : `color-mix(in srgb, ${hue} 14%, transparent)`
    const regimeTag = p.regime ? p.regime + ' · ' : ''
    // 重祚者两段各自成条。年份本身已足以分辨是哪一次(正统1435-1449 / 天顺1457-1464),
    // 不再缀 reignNote —— 那句注解只在右栏档案里有位置,挂在 tooltip 上过满。
    return {
      id: p.id, key: p.key,
      label: showLabel ? labelTxt : '',
      yearLabel: '',
      title: `${regimeTag}${labelTxt}${p.name && p.name !== labelTxt ? ' · ' + p.name : ''} · ${rangeTag} ${fmtY(s)}–${fmtY(en)}`,
      // 帝王条锚在在位起点。此前是裸 scrollToYear(s)(无脉冲、不写 year),M11 统一走通道
      onClick: () => selectAndAnchor(p.id, 'Person', s),
      bandStyle: {
        left: (ERA_W + lane * EMP_LANE_W) + 'px',
        width: (EMP_LANE_W - 2) + 'px',
        top: top + 'px', height: h + 'px', opacity: op,
        background: bg,
        borderLeft: '2px solid ' + (isSel ? 'var(--accent)' : `color-mix(in srgb, ${hue} 55%, transparent)`),
        borderBottom: '1px solid var(--line)',
        zIndex: isSel || isHov ? 6 : 2,
      },
      labelStyle: {
        color: isSel ? 'var(--accent)' : 'var(--ink-mid)',
        fontWeight: isSel ? 700 : 500,
      },
      yearStyle: {},
    }
  })
})

// === 选中实体的生命带 ===
const selectedBand = computed(() => {
  const sel = selected.value
  if (!sel) return null
  let range = null
  if (sel.born?.year != null && sel.died?.year != null) range = [sel.born.year, sel.died.year]
  else if (sel.founded?.year != null && sel.ended?.year != null) range = [sel.founded.year, sel.ended.year]
  else if (sel.date?.year != null) range = [sel.date.year, sel.end_date?.year || sel.date.year]
  if (!range) return null
  const top = yPos(range[0])
  const h = Math.max((range[1] - range[0]) * k(), 6)
  return {
    style: { top: top + 'px', height: h + 'px' },
    cap: sel.name + ' · ' + fmtY(range[0]) + '–' + fmtY(range[1]),
    capStyle: { top: (top + 4) + 'px' },
  }
})

// === 选中实体的关联高亮 ===
// 原 relatedIds stub 已删:它恒返回空 Set,且自始至终无任何消费者(模板与脚本均未引用)。
// 关系连线的实际数据源在下方「关系连线」节:watch 选中实体时经 getNeighbors(id, 1) 惰性
// 载入 relationsForSelected,relationLines 据此把选中人物与柱上可见的关联人物连成虚线;
// 事件的「非关联淡出」则走另一条链:chainIds(因果 BFS ∪ 同线索成员)-> eventLayout 的 dim。

// === 人物 lane 分配(M7 双自适应,T7.2+T7.4) ===
// 旧算法两处致命:laneCount 是「全史最大并发」的全局常数(与宽度/年代无关,L0 实测 97),
// 区宽又被 44px 地板钳死 → 道距 0.45px,物理上必然压盖;750 年在世 8 人也背着全史
// 峰值挤在一坨。现改为:
//   ①车道索引按可见年代窗分配(T7.4):车道只分给窗内人,稀疏年代自然摊开;
//   ②容量封顶(T7.2):maxLanes = floor(区宽/最小道距 10px),超容人物并入最右一条
//     聚合溢出道(方向甲,Rick 已拍板)——该道按生年落刻度示密度、标「+N」,
//     hover 见名单、click 平滑放大,放大后窗内并发下降,人物自然回列;
//   ③提升集:选中/悬停/在世 chips 必占车道不入聚合 —— chips⇄柱条双向 hover(B3)
//     的前提是 chip 上的人在柱上有条;名单经 useAlivePeople 与 MomentPanel 单源共享。
const MIN_LANE_PITCH = 10   // 条 4px + 生年点 8/卒年刻度 10 的余量
const personLayout = computed(() => {
  const ov = overview.value
  const _k = k()
  const year = store.year
  const selId = selectionStore.selectedEntityId
  // 远景(LOD0)只显示重要人物(有 bio 且 bio 较长)；再并入 T4.6 身份/重要性筛选
  let list = ov ? people.value.filter(p => (p.bio || '').length > 30) : people.value
  list = list.filter(p => filter.passes(p))
  // 可见年代窗(含缓冲):车道只给窗内人分,索引不再背全史峰值。
  // 窗界按 100 年桶量化:滚动途中桶界不变 → 分道结果跨帧稳定(Vue 不重排 DOM);
  // 否则每帧全量重分道,滚动的 650ms 里主线程被重渲染占满(实测 B1 lens 脉冲因此丢帧)
  const BUCKET = 100
  const winLo = Math.floor(((viewTop.value - VIEW_BUF.value - TOP) / _k - ORIGIN) / BUCKET) * BUCKET
  const winHi = Math.ceil(((viewTop.value + viewH.value + VIEW_BUF.value - TOP) / _k - ORIGIN) / BUCKET) * BUCKET
  const sorted = list.filter(p => p.died >= winLo && p.born <= winHi)
    .sort((a, b) => a.born - b.born)
  const { pxA, pxB } = personZone.value
  const maxLanes = Math.max(1, Math.floor((pxB - pxA) / MIN_LANE_PITCH))
  // 车道避让间距。单位是「年」,但意图是「屏幕上别贴太近」—— M12 之前 k 只到 12,
  // 3 年 ≈ 36px 尚合理;到日档 k=2922 时 3 年 = 8766px,车道会被撑得空无一人。
  // 故近景改成按像素折算年,远景(k<1)仍用固定 40 年(那时 40 年才 17px)。
  const gap = ov ? 40 : Math.max(0.02, 36 / _k)
  // 提升集靠前分道:选中 > 在世 chips(序即 chips 序)。
  // 悬停者不入提升集:chips 已覆盖双向 hover 的互高亮对象,再为 hover 触发全量重分道
  // 不划算(hover 是高频动作,每次 hover 重排 400 条车道纯属自找抖动)
  const prio = []
  const pushPrio = (id) => { if (id && !prio.includes(id)) prio.push(id) }
  pushPrio(selId)
  for (const a of aliveChips.value) pushPrio(a.id)
  const prioSet = new Set(prio)
  const ordered = [
    ...prio.map(id => sorted.find(p => p.id === id)).filter(Boolean),
    ...sorted.filter(p => !prioSet.has(p.id)),
  ]
  const lanes = []
  const laneOf = {}
  const agg = []
  for (const p of ordered) {
    const li = lanes.findIndex(last => last + gap <= p.born)
    if (li >= 0) { lanes[li] = p.died; laneOf[p.id] = li; continue }
    // 提升集必占道 —— 可超出容量上限,道距随之收紧(chips 上限 16,超幅有限)
    if (prioSet.has(p.id) || lanes.length < maxLanes) {
      lanes.push(p.died); laneOf[p.id] = lanes.length - 1; continue
    }
    laneOf[p.id] = -1   // 聚合溢出道
    agg.push(p)
  }
  // 聚合道占最右一道;laneCount 把它算进除数,常规道距不被聚合道吃掉
  const laneCount = Math.max(lanes.length + (agg.length ? 1 : 0), 1)
  const aggLane = agg.length ? lanes.length : -1
  const laneX = (i) => pxA + (i * (pxB - pxA) / laneCount)

  // 名字按重要性贪心放置,放不下就不显名 —— 与事件卡片同一套纪律。
  // 名宽 18px 而道距常只 10px 上下,每个名字横压其后一两道;只能择要而显,余者靠悬停。
  const nameBoxes = []
  const showName = {}
  const byImp = [...sorted].sort((a, b) => (a.importance ?? 9) - (b.importance ?? 9))
  for (const p of byImp) {
    const li = laneOf[p.id]
    if (li == null || li < 0) continue   // 聚合道成员不落名(hover 聚合道见名单)
    const x = laneX(li)
    const top = yPos(p.born)
    const nh = (p.name || '').length * NAME_CH + 4
    const barH = Math.max((p.died - p.born) * _k, 8)
    if (barH < nh * 0.6) continue          // 条比名还短,写上去会溢出到别人的年代里
    const bx = [x + NAME_DX, x + NAME_DX + NAME_W, top, top + nh]
    const free = nameBoxes.every(b =>
      bx[1] <= b[0] || bx[0] >= b[1] || bx[3] <= b[2] || bx[2] >= b[3])
    if (free) { nameBoxes.push(bx); showName[p.id] = true }
  }

  // 选中聚光(T7.3):选中人物在轴上时其余条淡出至 0.25(复用事件 dim 链路模式)。
  // 淡出挂在 .tc-inner 的 tc-dim 类上走 CSS(见 personDimOn),不给每条内联 opacity ——
  // 否则每次选中切换 400 个节点内联样式全量 diff,选中瞬间主线程被重渲染占满
  const bars = sorted.filter(p => (laneOf[p.id] ?? -1) >= 0).map(p => {
    const x = laneX(laneOf[p.id])
    const top = yPos(p.born)
    const h = Math.max((p.died - p.born) * _k, 8)
    const isSel = p.id === selId
    const alive = p.born <= year && p.died >= year
    let solid
    if (isSel) solid = 'var(--accent)'
    else if (alive) solid = 'var(--cat-person)'
    else solid = 'color-mix(in srgb, var(--cat-person) 32%, transparent)'
    const glow = isSel ? '0 0 10px var(--accent-glow)'
               : alive ? '0 0 8px color-mix(in srgb, var(--cat-person) 50%, transparent)' : ''
    // 模糊纪年(活跃年代 / 生卒系推估)的两端渐隐:推估的年代不该看起来跟确凿的一样,
    // 端点虚化即「此处起讫不确」。生卒点/卒年刻度对这类人也不成立,一并不画。
    const fuzzy = p.isFloruit || p.approx
    // 在位≠活跃≠生卒,三者不可混称
    const rangeTag = p.reignOnly ? '在位' : p.isFloruit ? '活跃' : (p.approx ? '约' : '')
    // 在世者卒年开放,不写终点也不画卒年刻度(那意味着已故);
    // 卒年已知而生年不可考者写「?–卒年」,不虚构起点
    const rangeTxt = p.deathOnly ? `?–${fmtY(p.died)}`
                   : p.living ? `${fmtY(p.born)}–`
                   : `${fmtY(p.born)}–${fmtY(p.died)}`
    return {
      id: p.id, name: p.name,
      title: `${p.name} ${rangeTag}${rangeTxt}`,
      // p.born 是四态时间锚解析后的段起点(born→floruit→died→reign),与 utils/repYear
      // 的优先级同源 —— 同一个人无论从搜索进还是从柱上点进,都落在同一年
      onClick: () => selectAndAnchor(p.id, 'Person', p.born),
      _top: top, _h: h,
      fuzzy, living: p.living, deathOnly: p.deathOnly,
      wrapStyle: { left: x + 'px', top: top + 'px', height: h + 'px' },
      barStyle: {
        background: fuzzy
          ? `linear-gradient(to bottom, transparent, ${solid} 26%, ${solid} 74%, transparent)`
          : solid,
        boxShadow: glow,
      },
      birthDotStyle: { background: isSel ? 'var(--accent)' : (alive ? 'var(--cat-person)' : 'color-mix(in srgb, var(--cat-person) 50%, transparent)') },
      deathTickStyle: { background: isSel ? 'var(--accent)' : 'color-mix(in srgb, var(--cat-person) 55%, transparent)' },
      // 未获名位者不常显,但选中/悬停时必须显 —— 否则密集区无从查看是谁
      showName: !!showName[p.id],
      nameStyle: { color: isSel ? 'var(--accent)' : (alive ? 'var(--ink)' : 'var(--ink-soft)'),
                   fontWeight: (isSel || alive) ? 700 : 400,
                   fontStyle: fuzzy ? 'italic' : 'normal' },
    }
  })
  return { bars, laneOf, laneCount, laneX, agg, aggLane }
})
const visiblePeople = computed(() => personLayout.value.bars)

// === 聚合溢出道(方向甲)渲染数据 ===
// 刻度按各人生年落位示密度;「+N」徽标钉在视口上部(lens 线 240 之下),随滚动跟随。
// 徽标 top 拆成独立 computed:viewTop 每帧变,而刻度/名单只需跟 personLayout 重算。
// M8:names 只读列表升级为 items(带 id),与事件桶共用 AggPopList 可点选清单
const personAgg = computed(() => {
  const L = personLayout.value
  if (!L.agg.length) return null
  return {
    x: L.laneX(L.aggLane),
    count: L.agg.length,
    items: L.agg.map(p => ({
      id: p.id, name: p.name, type: 'Person',
      label: fmtY(p.born), hue: 'var(--cat-person)',
      year: p.born,          // M11:清单条目也要能锚定,与柱上直接点选同年
    })),
    ticks: L.agg.map(p => ({
      id: p.id, top: yPos(p.born),
      title: `${p.name} ${fmtY(p.born)}–${fmtY(p.died)} · 点击放大回列`,
    })),
  }
})
const aggBadgeTop = computed(() => viewTop.value + 252)
// 人物聚合道浮层定位(徽标左侧);开关在下方 T8.2 统一浮层管理
const personPopStyle = computed(() => {
  const a = personAgg.value
  if (!a) return {}
  return { left: Math.max(98, a.x - 166) + 'px', top: (aggBadgeTop.value + 24) + 'px' }
})
// 聚合刻度也走视口虚拟化:L0 下可达数百枚,一次性挂载会在选中/跳年瞬间堵主线程
const viewportAggTicks = computed(() => {
  const L = personAgg.value
  if (!L) return []
  const lo = viewTop.value - VIEW_BUF.value
  const hi = viewTop.value + viewH.value + VIEW_BUF.value
  return L.ticks.filter(t => t.top >= lo && t.top <= hi)
})
// 选中聚光(T7.3):选中人物在轴上(提升集保证其有条)时,人物区其余条整体淡出 ——
// 开关挂 .tc-inner 的 tc-dim 类走 CSS,一次类切换替代 400 条内联样式 diff
const personDimOn = computed(() => {
  const selId = selectionStore.selectedEntityId
  return selId != null && (personLayout.value.laneOf[selId] ?? -1) >= 0
})
// click 聚合道 → 以点击处年份为锚平滑放大:窗内并发随 k 上升而下降,人物自然回列
function onAggClick(e) {
  const rect = scrollRef.value.getBoundingClientRect()
  const clientY = e.type === 'keydown'
    ? e.currentTarget.getBoundingClientRect().top + e.currentTarget.getBoundingClientRect().height / 2
    : e.clientY
  zoomAt(clientY - rect.top, zoomLevel.value + 0.6)
}

// 事件列位按卡片实宽算,不用百分比:卡宽原先 CSS 写死 168px、列位却按 38/54/70% 走,
// 800px 面板下列距仅 127px —— 相邻列天生横叠 41px,"三列"从来没分开过。
// CARD_W 是唯一真源(卡片宽度由 cardStyle 内联给出,CSS 不再写 width),免得两处再漂。
// 人物名占位(竖排):12px 字 + 2px 字距 → 每字约 14px 高,整体约 18px 宽。
// NAME_DX:名字并非落在道位上,而在其右 8px 处(条宽 4 + flex gap 4)。碰撞盒必须按
// 实际占位算 —— 漏掉这 8px 会让判定整体偏移,重叠照旧发生。
const NAME_W = 18
const NAME_CH = 14
const NAME_DX = 8

const CARD_W = 160
// 卡高 32 → 22:32px 里印章占 18、上下 padding 占 12,过于敦实;高度直接决定同缩放下
// 能容多少张,32→22 让可见事件多出约四成。印章 18→14、字 12.5→11.5、padding 6→3。
const CARD_H = 22
const COL_GAP_X = 8
const ROW_GAP_Y = 3
const SEAL_SZ = 14

// 横向分区(自左至右):朝代带 | 帝王带 | 人物条 | 链轨道 | 溢出槽 | 事件列
// 链轨道/溢出槽/事件列统一由人物区右缘推导,各区不互压。
// M7 重定区宽(T7.2):旧策略 max(pxA+44, 30%视口) 双重钳制 —— 默认 720px 下区宽仅
// 44px、道距 0.45px,物理上必然压盖;新增宽度 70% 还全让给事件区。现:期望 47%
// 视口(实测 720px 下事件区仍保 2 列),地板 pxA+88,上限给事件区留至少一列。
const PERSON_RIGHT = 0.47       // 人物条右缘占面板比(期望值)
const MIN_ZONE_W = 88           // 人物区最小宽(旧 44px 地板钉死过窄)
const RAIL_DX = 6               // 链轨道
const OVERFLOW_DX = 13          // 溢出槽(隐藏事件的刻度)
const EVENT_DX = 26             // 事件列起点
const personZone = computed(() => {
  const pxA = empGutterEnd.value + 10
  const desired = Math.round(viewW.value * PERSON_RIGHT)
  const cap = Math.max(pxA + 44, viewW.value - (EVENT_DX + CARD_W + 8))
  const pxB = clamp(desired, Math.min(pxA + MIN_ZONE_W, cap), cap)
  return { pxA, pxB }
})
const personRightPx = computed(() => personZone.value.pxB)
const railX = computed(() => personRightPx.value + RAIL_DX)
const overflowX = computed(() => personRightPx.value + OVERFLOW_DX)

const eventCols = computed(() => {
  const left = personRightPx.value + EVENT_DX
  const avail = Math.max(CARD_W, viewW.value - left - 8)
  const n = Math.max(1, Math.floor((avail + COL_GAP_X) / (CARD_W + COL_GAP_X)))
  return Array.from({ length: n }, (_, i) => left + i * (CARD_W + COL_GAP_X))
})

// 事件卡上的时间读数。仅亚年档且该事件确有月份时才写到月/日 —— 年档下也写月份
// 会让一列卡片读数长短不齐反而难扫读,且大半事件本就无月份可写(210 个事件里
// 101 个有 month,10 个有 day)。历法字形由 fmtYM 按 1912 界分。
function evLabel(ev) {
  const hasSpan = ev.year_end != null && ev.year_end > ev.year
  if (subYear.value && ev.month != null) {
    // 卡上只写月/日:年由轴刻度给。写全「1937年7月7日–1945」会把 CARD_W 吃光,
    // 名字被截成「七…」—— 实测截图里正是如此。完整日期仍在 title(见模板)。
    const head = fmtMD(ev.year, ev.month, ev.day)
    return hasSpan ? head + '–' + fmtY(ev.year_end) : head
  }
  return hasSpan ? fmtY(ev.year) + '–' + fmtY(ev.year_end) : fmtY(ev.year)
}
// 悬停提示用的完整时间(含年),与卡上的短标签互补
function evFullLabel(ev) {
  const hasSpan = ev.year_end != null && ev.year_end > ev.year
  const head = fmtYM(ev.year, ev.month, ev.day)
  return hasSpan ? head + '–' + fmtY(ev.year_end) : head
}

// === 事件:统一为「卡片 + 时长尾巴」,贪心分列避让 ===
// 点3 的两半在这里一起解决:
//  1) 设计语言统一——单点与跨年不再是两套东西(卡片 vs 竖条),一律是卡片;有跨度的
//     在列左侧的间隙里挂一条细尾巴示其延续,尾巴走间隙故不压卡片。
//  2) 去倾轧——按实际 y 区间贪心分列(同帝王带分道那套),放不下的本层级不渲染。
//     这本身就是 LOD:k 越大 yPos 越疏,自然容得下越多,无需另设远景过滤。
const eventLayout = computed(() => {
  const selId = selectionStore.selectedEntityId
  const chain = chainIds.value
  const hasChain = chain.size > 1
  const cols = eventCols.value
  const { fwd, bwd } = causalAdj.value

  // 排序即放置优先级。线索成员置顶,否则缩小时链会被丢出现断链。
  // 无 importance 字段可用,以因果度数 + 线索归属 + 描述长度作代理。
  // importance 主导(1 核心/2 重要/3 一般,缺省视为 3),因果度数与线索归属只作同档内的次序。
  // 此前无此字段,只能拿「因果度数 + 描述长度」当代理 —— 等于让 bio 写得长的事件挤掉
  // 写得短的。线索成员仍置顶,否则缩小时链会断。
  const deg = (id) => (fwd.get(id)?.length || 0) + (bwd.get(id)?.length || 0)
  const score = (e) => (chain.has(e.id) ? 1e7 : 0)
    + (4 - (e.importance ?? 3)) * 1e4          // 核心 3万 / 重要 2万 / 一般 1万
    + deg(e.id) * 100 + (e.threads?.length ? 50 : 0)
  const ranked = [...events.value].sort((a, b) => score(b) - score(a))

  const lanes = cols.map(() => [])
  const out = []
  const overflow = []      // 放不下的:落进溢出槽,不静默丢弃
  for (const ev of ranked) {
    // M12:几何走小数年。同年不同月的事件由此第一次拉开距离 —— 此前它们 yc 相同,
    // 必然互相挤进溢出槽,且 onBucketClick 反推年距为 0 而永远回不了列。
    const yc = yPos(ev.tYear)
    const t = yc - CARD_H / 2, b = yc + CARD_H / 2
    let ci = -1
    for (let c = 0; c < cols.length; c++) {
      if (lanes[c].every(([lt, lb]) => b + ROW_GAP_Y <= lt || t >= lb + ROW_GAP_Y)) { ci = c; break }
    }
    if (ci < 0) {
      // 本层级放不下。此前直接 continue —— 用户无从知道少了什么;现落一枚刻度到
      // 溢出槽,悬停可见其名,放大后 yPos 变疏,自然回到列里。
      // M8 起带齐 category/importance/year/type:分桶、族色、清单与回列反推都要用
      const yearLabel = evLabel(ev)
      const fullLabel = evFullLabel(ev)
      overflow.push({
        id: ev.id, name: ev.name, type: ev.type, _top: yc,
        category: ev.category, importance: ev.importance,
        year: ev.year, year_end: ev.year_end, tYear: ev.tYear, yearLabel, fullLabel,
        title: `${ev.name} ${fullLabel}`,
        onClick: () => selectAndAnchor(ev.id, ev.type, ev.tYear),
        style: { left: overflowX.value + 'px', top: yc + 'px',
                 background: catHue(ev.category) },
      })
      continue
    }
    lanes[ci].push([t, b])

    const col = cols[ci]
    const isSel = ev.id === selId
    const onChain = chain.has(ev.id)
    const dim = hasChain && !onChain
    const hue = catHue(ev.category)          // 族色:粗读;类字形由 Seal 按 category 出
    const hasSpan = ev.year_end != null && ev.year_end > ev.year
    const tailH = hasSpan ? Math.max(yPos(ev.tYearEnd ?? ev.year_end) - yc, 3) : 0

    out.push({
      id: ev.id, name: ev.name, type: ev.type, category: ev.category,
      yearLabel: evLabel(ev), fullLabel: evFullLabel(ev),
      _top: t, _h: CARD_H + tailH, _col: col,
      onClick: () => selectAndAnchor(ev.id, ev.type, ev.tYear),
      cardStyle: {
        // 宽高都由 CARD_W/CARD_H 内联给出:碰撞算的是这两个数,若 CSS 另算一套,
        // 实际占位与碰撞判定就会错开(实测 CSS 算出 25 而 JS 用 22,靠 ROW_GAP 恰好
        // 垫平才没重叠 —— 那是巧合,字体一改即破)。
        left: col + 'px', top: yc + 'px', width: CARD_W + 'px', height: CARD_H + 'px',
        background: 'var(--paper-el)',
        border: '1px solid ' + (isSel || onChain ? 'var(--accent)'
                                : `color-mix(in srgb, ${hue} 28%, var(--line))`),
        boxShadow: isSel ? '0 3px 14px var(--accent-glow)'
                 : onChain ? '0 0 0 1px color-mix(in srgb, var(--accent) 30%, transparent)' : 'none',
        opacity: dim ? 0.22 : 1,
      },
      tailStyle: hasSpan ? {
        left: (col - 6) + 'px', top: yc + 'px', height: tailH + 'px',
        background: isSel || onChain ? 'var(--accent)'
                  : `color-mix(in srgb, ${hue} 55%, transparent)`,
        opacity: dim ? 0.22 : 1,
      } : null,
    })
  }
  return { items: out.sort((a, b) => a._top - b._top), overflow }
})
const visibleEvents = computed(() => eventLayout.value.items)

// === T8.1 溢出分桶:同 x 叠放的刻度按 y 距并桶 —— 同一段年代收起多件事时,
// 不再逐枚叠 7x2px 刻度(L0 实测 184 枚,远看像一根虚线尺),改渲染「+N」计数徽标;
// 单事件桶保持旧刻度行为(悬停见名、点选定位)
const BUCKET_GAP_PX = 16   // 刻度 y 距小于此值即并桶(≈徽标高;相邻桶质心距 ≥16,徽标不互叠)
const overflowBuckets = computed(() => {
  const ov = eventLayout.value.overflow
  if (!ov.length) return []
  const sorted = [...ov].sort((a, b) => a._top - b._top)
  const raw = []
  for (const o of sorted) {
    const last = raw[raw.length - 1]
    if (last && o._top - last.lastTop < BUCKET_GAP_PX) {
      last.items.push(o); last.lastTop = o._top
    } else {
      raw.push({ items: [o], lastTop: o._top })
    }
  }
  return raw.map((r, idx) => {
    const items = r.items
    const top = items.reduce((s, i) => s + i._top, 0) / items.length
    // 族色继承既有调色:取桶内最要者(importance 最小)的族色为徽标描边
    const lead = items.reduce((a, b) => ((a.importance ?? 3) <= (b.importance ?? 3) ? a : b))
    const hue = catHue(lead.category)
    const yearLo = Math.min(...items.map((i) => i.year))
    const yearHi = Math.max(...items.map((i) => i.year_end ?? i.year))
    return {
      key: `ovb-${idx}-${yearLo}`,
      count: items.length,
      items, top, yearLo, yearHi,
      badgeStyle: {
        left: overflowX.value + 'px', top: top + 'px',
        borderColor: `color-mix(in srgb, ${hue} 62%, transparent)`,
      },
      popItems: items.map((i) => ({
        // 浮层脱离轴刻度,写完整时间(含年)才读得懂
        id: i.id, name: i.name, type: i.type, label: i.fullLabel, hue: catHue(i.category),
        year: i.tYear ?? i.year,   // M11 锚定用;M12 起带小数(锚到月而非落回正月)
      })),
    }
  })
})
// 分桶也走视口虚拟化
const viewportBuckets = computed(() => {
  const lo = viewTop.value - VIEW_BUF.value
  const hi = viewTop.value + viewH.value + VIEW_BUF.value
  return overflowBuckets.value.filter((b) => b.top >= lo && b.top <= hi)
})

// === T8.2 聚合浮层统一:人物聚合道与事件桶共用 AggPopList 可点选清单。
// 徽标 hover 开、移出 140ms 宽限关(徽标→浮层短距离移动不闪关)。
// 浮层不套 hover 守卫:它不写 selection store,不会像 hover 预览那样劫持选中态;
// 滚动途中内容滑过静止光标而误开,也会随徽标滑走触发 mouseleave 自关
const activePop = ref(null)   // { kind:'person' } | { kind:'bucket', key }
let popTimer = 0
function openPop(p) {
  clearTimeout(popTimer)
  activePop.value = p
}
function keepPop() { clearTimeout(popTimer) }
function closePopSoon() {
  clearTimeout(popTimer)
  popTimer = setTimeout(() => { activePop.value = null }, 140)
}
function onPopSelect(it) {
  selectAndAnchor(it.id, it.type, it.year)
}
const personPopOpen = computed(() => activePop.value?.kind === 'person' && !!personAgg.value)
const hoveredBucket = computed(() => {
  const p = activePop.value
  if (!p || p.kind !== 'bucket') return null
  const b = overflowBuckets.value.find((x) => x.key === p.key)
  return b && b.count >= 2 ? b : null
})
// 事件桶浮层钉在徽标左侧;纵向夹在视口内,低位桶的清单不沉到屏外
const bucketPopStyle = computed(() => {
  const b = hoveredBucket.value
  if (!b) return {}
  const estH = 36 + Math.min(b.count, 16) * 22
  const top = clamp(b.top + 12, viewTop.value + 48, viewTop.value + viewH.value - estH - 8)
  const popOuterW = 196 // AggPopList:178 content + 16 padding + 2 border
  const gap = 8
  const leftCandidate = overflowX.value - popOuterW - gap
  const left = leftCandidate >= ERA_W + 4
    ? leftCandidate
    : clamp(overflowX.value + 32, ERA_W + 4, viewW.value - popOuterW - 8)
  return { left: left + 'px', top: top + 'px' }
})
// click 桶 → 平滑放大到该区间。所需 k 按「邻域事件全列回列」精确反推:
// 卡片等高等距 → 全列回列 ⇔ 任何 cols+1 件的年距 ≥ 卡高行距(区间图定理),
// 故取与桶区间相交的所有 cols+1 件窗口,所需最大 k 即所求;贪心按分数序放置
// 略劣于最优,留 15% 余量;封顶 K_MAX —— 超过最大缩放容量的紧密簇(如连续三年
// 各一件、列宽仅 2)本就回列不尽,余者留作更小的桶,不静默。锚定点击处,只放大不缩小
function onBucketClick(b, e) {
  const rect = scrollRef.value.getBoundingClientRect()
  const cols = Math.max(eventCols.value.length, 1)
  // M12:改用 tYear 反推。此前同年多件的年距恒为 0,兜底 0.01 使 wantK 爆表被
  // K_MAX 钳死 —— 同年多件事在旧体系下「永远回不了列」。有月份者年距变成 1/12,
  // 在新的 K_MAX 下回列真能兑现;仍无月份的同年事件依旧回不尽,那是数据缺位。
  const years = events.value.map((ev) => ev.tYear).sort((x, y) => x - y)
  let wantK = k()
  for (let i = 0; i + cols < years.length; i++) {
    if (years[i] > b.yearHi || years[i + cols] < b.yearLo) continue
    wantK = Math.max(wantK, (CARD_H + ROW_GAP_Y + 0.1) / Math.max(years[i + cols] - years[i], 0.01))
  }
  wantK = clamp(wantK * 1.15, k(), K_MAX)
  const newLevel = clamp(levelFromK(wantK), 0, LEVEL_MAX)
  const targetRect = e.currentTarget.getBoundingClientRect()
  const clientY = e.type === 'keydown' ? targetRect.top + targetRect.height / 2 : e.clientY
  zoomAt(clientY - rect.top, Math.max(newLevel, zoomLevel.value + 0.25))
}

// === 虚拟化:只渲染视口 ± 一屏缓冲区内的节点 ===
const viewportPeople = computed(() => {
  const lo = viewTop.value - VIEW_BUF.value
  const hi = viewTop.value + viewH.value + VIEW_BUF.value
  return visiblePeople.value.filter(p => p._top + p._h >= lo && p._top <= hi)
})
const viewportEvents = computed(() => {
  const lo = viewTop.value - VIEW_BUF.value
  const hi = viewTop.value + viewH.value + VIEW_BUF.value
  // 带子有 _h,按整条带子范围过滤;单年卡片 _h 缺省 0 退回原逻辑
  return visibleEvents.value.filter(e => e._top + (e._h || 0) >= lo && e._top <= hi)
})

// === 因果链 ===
// 全库因果边只有 ~74 条,一次拉完在前端 BFS,比按需 getNeighbors(depth=N) 省往返。
// 归一为 cause→effect:led_to 即因→果;caused_by 是其逆语义(from 起因于 to)。
const causalEdges = ref([])
async function loadCausal() {
  try {
    const [ledTo, causedBy] = await Promise.all([
      getRelations({ type: 'led_to', limit: 2000 }),
      getRelations({ type: 'caused_by', limit: 2000 }),
    ])
    causalEdges.value = [
      ...ledTo.items.map(r => ({ from: r.from, to: r.to, note: r.note })),
      ...causedBy.items.map(r => ({ from: r.to, to: r.from, note: r.note })),
    ]
  } catch (e) {
    console.warn('[TimeColumn] 因果边加载失败,线索功能降级为空', e)
    causalEdges.value = []
  }
}

const causalAdj = computed(() => {
  const fwd = new Map(), bwd = new Map()
  for (const e of causalEdges.value) {
    if (!fwd.has(e.from)) fwd.set(e.from, [])
    if (!bwd.has(e.to)) bwd.set(e.to, [])
    fwd.get(e.from).push(e.to)
    bwd.get(e.to).push(e.from)
  }
  return { fwd, bwd }
})

// 选中事件所在的线索 = 因果可达 ∪ 同线索(ext.threads)成员。
// 二者正交:因果答「谁引发了谁」,线索答「哪些事同属一个历史问题」。燕云的割让(936)
// 与收复(1368)隔 432 年、无因果路径,只有 thread 连得起来;而 澶渊→海上之盟 是因果。
const chainIds = computed(() => {
  const id = selectionStore.selectedEntityId
  if (!id) return new Set()
  const ev = events.value.find(e => e.id === id)
  if (!ev) return new Set()   // 只对事件/战役起作用,人物不走线索
  const out = new Set([id])
  // 因果:前后各展开(去环)
  const { fwd, bwd } = causalAdj.value
  for (const adj of [fwd, bwd]) {
    const q = [[id, 0]]
    while (q.length) {
      const [n, d] = q.shift()
      if (d >= 12) continue
      for (const nxt of adj.get(n) || []) {
        if (out.has(nxt)) continue
        out.add(nxt); q.push([nxt, d + 1])
      }
    }
  }
  // 线索:同名 thread 的全部成员
  if (ev.threads?.length) {
    for (const e of events.value) {
      if (e.threads?.some(t => ev.threads.includes(t))) out.add(e.id)
    }
  }
  return out.size > 1 ? out : new Set()   // 孤立事件不画线索
})

// 轨道:纵贯线索首尾的虚线 + 横向 stub 接到每个成员。
// stub 宽度须按成员所在列算——三列(38/54/70%)分布,固定宽度只够得着最左列,
// 中右列的成员会与轨道断开,轨道就退化成装饰。
const visibleChains = computed(() => {
  const ids = chainIds.value
  if (ids.size < 2) return []
  const members = visibleEvents.value.filter(e => ids.has(e.id))
  if (members.length < 2) return []
  const ys = members.map(e => e._top + CARD_H / 2)
  const top = Math.min(...ys), bot = Math.max(...ys)
  const rx = railX.value
  return [{
    railStyle: { left: rx + 'px', top: top + 'px', height: (bot - top) + 'px' },
    stubs: members.map(e => ({
      style: {
        left: rx + 'px', top: (e._top + CARD_H / 2) + 'px',
        width: (e._col - rx) + 'px',
      },
    })),
  }]
})

// === 关系连线(选中人物 -> 其在时间柱可见的关联人物)===
const relationLines = computed(() => {
  const sel = selected.value
  if (!sel || !relationsForSelected.value.length) return []
  const L = personLayout.value
  const selLane = L.laneOf[sel.id]
  if (selLane == null || selLane < 0) return []
  const lines = []
  // T7.3:x 与车道同款 px 几何(laneX)—— 旧公式 60+lane*24/count+'%' 是更早百分比
  // 布局的残留,连线错落到事件卡区;对端在聚合道时落在聚合道位上
  const selX = L.laneX(selLane) + 2   // bar 中心
  const selY = yPos(sel.born?.year ?? sel.founded?.year ?? sel.date?.year ?? 0) + 4
  for (const r of relationsForSelected.value) {
    const lane = L.laneOf[r.otherId]
    if (lane == null) continue
    const p = people.value.find(pp => pp.id === r.otherId)
    if (!p) continue
    const x = (lane >= 0 ? L.laneX(lane) : L.laneX(L.aggLane)) + 2
    const y = yPos(p.born) + 4
    lines.push({
      x1: selX, y1: selY, x2: x, y2: y,
      color: 'var(--accent)',
      width: 1.5,
      dash: '4 3',
      opacity: 0.5,
    })
  }
  return lines
})

// 选中人物的关系(惰性加载)
const relationsForSelected = ref([])
watch(() => selectionStore.selectedEntityId, async (id) => {
  relationsForSelected.value = []
  if (!id) return
  try {
    const r = await getNeighbors(id, 1)
    relationsForSelected.value = (r.edges || []).map(e => ({
      otherId: e.from === id ? e.to : e.from,
    }))
  } catch {}
}, { immediate: true })

// === 选中人物的年谱 pins(D3):有 life_events 沿生命带画大事记钉,无则仅生卒两钉 ===
const momentPins = computed(() => {
  const sel = selected.value
  if (!sel || sel.type !== 'Person' || zoomLevel.value < 1) return []
  const result = []
  const layout = personLayout.value
  const lane = layout.laneOf[sel.id]
  // 选中人物属于提升集，通常必有 lane；极端视窗外状态回落到人物区右缘，仍只用
  // 同一套人物几何。+5.5 = 4px 条中心(2) + 7px 钉半径(3.5)，配合 CSS 右对齐。
  const laneX = (lane != null && lane >= 0 ? layout.laneX(lane) : personRightPx.value) + 5.5
  const pinStyle = (year) => ({
    left: laneX + 'px', top: yPos(year) + 'px',
    maxWidth: Math.max(72, laneX - ERA_W - 12) + 'px',
  })
  const evts = Array.isArray(sel.life_events)
    ? sel.life_events.filter(e => e && e.year != null && e.event)
    : []
  if (evts.length) {
    // 超 5 条只画标 importance:1 的;全未标时取前 5 条(不虚构重要性,也不糊柱)
    let shown = evts
    if (evts.length > 5) {
      const imp = evts.filter(e => e.importance === 1)
      shown = imp.length ? imp : evts.slice(0, 5)
    }
    for (const e of [...shown].sort((a, b) => a.year - b.year)) {
      result.push({
        key: 'le-' + e.year + '-' + e.event.slice(0, 8),
        label: fmtY(e.year) + ' · ' + e.event,
        tip: e.event,   // hover tooltip 给完整事件文本(label 可能被 CSS 截断)
        // M11:年谱钉同样走统一通道 —— 点「安史之乱起」该把右栏也带到 755
        onClick: () => anchorTo(e.year),
        laneX, wrapStyle: pinStyle(e.year),
      })
    }
    return result
  }
  if (sel.born?.year != null) {
    result.push({
      key: 'born', label: fmtY(sel.born.year) + ' · 生', tip: '生',
      onClick: () => anchorTo(sel.born.year),
      laneX, wrapStyle: pinStyle(sel.born.year),
    })
  }
  if (sel.died?.year != null) {
    result.push({
      key: 'died', label: fmtY(sel.died.year) + ' · 卒', tip: '卒',
      onClick: () => anchorTo(sel.died.year),
      laneX, wrapStyle: pinStyle(sel.died.year),
    })
  }
  return result
})

// === T8.3 柱缘密度指示条:全轴(-2100..2026)事件密度热区薄条贴柱右缘。
// 与缩放无关(映射整段轴而非视口),任一 zoomLevel「哪里有戏」一瞥可得;
// 当前年刻痕随刷年掠过响应,点击条面跳年
const DENSITY_BINS = 90
const densityRef = ref(null)
const densityBins = computed(() => {
  const bins = new Array(DENSITY_BINS).fill(0)
  for (const e of events.value) {
    const i = clamp(Math.floor(((e.year + ORIGIN) / SPAN) * DENSITY_BINS), 0, DENSITY_BINS - 1)
    bins[i]++
  }
  const max = Math.max(...bins, 1)
  const step = SPAN / DENSITY_BINS
  return bins.map((c, i) => ({
    i,
    // 空段留 5% 底影(条仍读作尺),有事件按最热段归一拉开对比
    op: c === 0 ? 0.05 : 0.15 + 0.7 * (c / max),
    tip: `${fmtY(Math.round(-ORIGIN + i * step))}–${fmtY(Math.round(-ORIGIN + (i + 1) * step))} · ${c} 事`,
  }))
})
const densityNowTop = computed(() => clamp(((store.year + ORIGIN) / SPAN) * 100, 0, 100))
function onDensityClick(e) {
  const rect = densityRef.value.getBoundingClientRect()
  const ratio = clamp((e.clientY - rect.top) / rect.height, 0, 1)
  // 密度条是一次显式跳年，必须接管外部锚定 guard。若上一笔人物/事件锚定动画
  // 尚未 finish 就被这里取消，走 non-external 会把 extScrollGuard 永久留在 true。
  scrollToYear(Math.round(-ORIGIN + ratio * SPAN), true, true)
}
function onDensityKeydown(e) {
  const step = Math.max(1, Math.round(SPAN / DENSITY_BINS))
  let target = store.year
  if (e.key === 'ArrowUp') target -= step
  else if (e.key === 'ArrowDown') target += step
  else if (e.key === 'PageUp') target -= step * 5
  else if (e.key === 'PageDown') target += step * 5
  else if (e.key === 'Home') target = -ORIGIN
  else if (e.key === 'End') target = AXIS_END
  else return
  e.preventDefault()
  scrollToYear(clamp(Math.round(target), -ORIGIN, AXIS_END), true, true)
}
function onDensityWheel(e) {
  const el = scrollRef.value
  if (!el) return
  e.preventDefault()
  e.stopPropagation()
  if (e.ctrlKey || e.metaKey) { onWheel(e); return }
  const scale = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? el.clientHeight : 1
  el.scrollTop += e.deltaY * scale
}

// 测试钩子(M8):e2e 复算分桶/回列/密度用(与 __hkbMap 同款 DEV 先例)
watchEffect(() => {
  if (!import.meta.env.DEV) return
  window.__hkbTimeline = {
    eventsTotal: events.value.length,
    placed: eventLayout.value.items.length,
    overflowTotal: eventLayout.value.overflow.length,
    overflowIds: eventLayout.value.overflow.map((o) => o.id),
    zoom: zoomLevel.value,
    year: store.year,
    cols: eventCols.value.length,
    // eventYears 只增不改:m8 的回列 e2e 按 ROW=25 直接反推这组整数年,
    // 改成小数会让它的候选过滤筛空。小数年另开 eventTYears。
    eventYears: events.value.map((e) => e.year),
    eventTYears: events.value.map((e) => e.tYear),
    exactYear: exactYear.value,
    k: k(),
    lod: lod.value,
    subYear: subYear.value,
    axisUnit: axisUnit.value,
    navigationSeq: store.navigationRequest?.seq ?? 0,
    momentPins: momentPins.value.map((m) => ({ laneX: m.laneX, top: parseFloat(m.wrapStyle.top) })),
    buckets: overflowBuckets.value.map((b) => ({
      key: b.key, count: b.count, yearLo: b.yearLo, yearHi: b.yearHi,
      ids: b.items.map((i) => i.id), names: b.items.map((i) => i.name),
    })),
  }
})

// === lens 标签 ===
const lensLabel = computed(() => {
  // 亚年档下读数带月份。用 floor 而非 store.year(=round)取年:锚线停在
  // 「755 年十一月」时 round 会给出 756,读数与所指位置差一年
  if (subYear.value) {
    const ex = exactYear.value
    const yr = yearOfScroll(ex)
    // 月序同样过一遍像素容差:锚定「755 年十二月」的事件后,ex 经量化是 755.9148,
    // (ex-yr)*12 = 10.978,裸 floor 得十一月 —— 差的正是不到一像素
    const mo = clamp(snapIdx((ex - yr) * 12, (0.75 / k()) * 12) + 1, 1, 12)
    const gz = ganzhi(yr)
    return (gz ? gz + ' · ' : '') + fmtYM(yr, mo)
  }
  const y = store.year
  const gz = ganzhi(y)
  return (gz ? gz + ' · ' : '') + fmtY(y)
})
</script>

<style scoped>
.tc-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  background: radial-gradient(130% 100% at 60% 0%, var(--hero1) 0%, var(--hero2) 100%);
  overflow: hidden;
  transition: var(--transition-theme);
}

/* 左侧 gutter */
.tc-gutter {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 96px;
  z-index: 2;
  border-right: 1px solid var(--line);
  background: var(--paper);
  overflow: hidden;
}
.tc-gutter-inner {
  position: relative;
  width: 100%;
  /* height 由 :style 注入 = innerHeight */
  /* transform: translateY 由 onScroll 同步 */
  will-change: transform;
}
.tc-gutter-block {
  position: absolute;
  left: 0; width: 96px;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  transition: background 0.12s;
}
.tc-gutter-block:hover { background: var(--hover) !important; }
.tc-gutter-block:focus-visible,
.tc-emperor-band:focus-visible,
.tc-person-wrap:focus-visible,
.tc-agg-badge:focus-visible,
.tc-overflow-tick:focus-visible,
.tc-overflow-badge:focus-visible,
.tc-event-card:focus-visible,
.tc-moment-pin:focus-visible,
.tc-density:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.tc-gutter-label {
  writing-mode: vertical-rl;
  font-family: var(--serif);
  font-weight: 700;
  color: var(--ink-mid);
}
.tc-gutter-year {
  position: absolute;
  top: 4px; left: 6px;
  font-family: ui-monospace, monospace;
  font-size: 9px;
  color: var(--ink-faint);
}

/* 滚动区 */
.tc-scroll {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
.tc-inner { position: relative; }

/* 年份刻度 */
.tc-tick-line {
  position: absolute;
  left: 96px; right: 0;
  height: 1px;
  background: color-mix(in srgb, var(--ink) 6%, transparent);
  z-index: 1;
}
.tc-tick-label {
  position: absolute;
  left: 102px;
  font-family: ui-monospace, monospace;
  font-size: 9px;
  color: var(--ink-faint);
  z-index: 1;
}

/* 帝王在位段 */
/* 帝王世系带(二级年代坐标):left/width/z-index 由 bandStyle 按道号给出。
   不再全宽 -> 并立政权(三国/十六国/南北朝/五代)各占一道并排,不相叠压。 */
.tc-emperor-band {
  position: absolute;
  pointer-events: auto;
  cursor: pointer;
  transition: background 0.12s;
}
/* 竖排庙号:居于条的中心对称轴;字体/字号呼应朝代带标签(serif + ink-mid),仅更小 */
.tc-emperor-label {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 4px;
  writing-mode: vertical-rl;
  text-orientation: upright;
  font-family: var(--serif);
  font-size: 11px;
  line-height: 1;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  max-height: calc(100% - 8px);
  pointer-events: none;
  transition: color 0.12s;
}
.tc-emperor-label:hover { color: var(--accent) !important; }
/* 生命带 */
.tc-life-band {
  position: absolute;
  left: 96px; right: 0;
  z-index: 2;
  background: color-mix(in srgb, var(--accent) 6%, transparent);
  border-top: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
  pointer-events: none;
}
.tc-life-cap {
  position: absolute;
  right: 10px;
  z-index: 2;
  font-size: 10px;
  color: color-mix(in srgb, var(--accent) 85%, transparent);
  font-family: var(--serif);
  pointer-events: none;
}

/* 人物生命条 */
.tc-person-wrap {
  position: absolute;
  z-index: 4;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  cursor: pointer;
  contain: layout style;
  transition: opacity 0.15s;
}
/* T7.3 选中聚光:选中人物时其余条淡出至 0.25(复用事件 dim 模式);
   hovered 不淡出 —— 淡出态下密集区仍要能逐个查看是谁 */
.tc-dim .tc-person-wrap:not(.selected):not(.hovered) { opacity: 0.25; }
/* 道距常态 ≥10px,但提升集超容时可收紧到 ~5px,条本身仍细难点中;
   向两侧各外扩 3px 作命中区(不占位、不可见) */
.tc-person-bar::after {
  content: '';
  position: absolute;
  left: -3px; right: -3px; top: 0; bottom: 0;
}
.tc-person-bar {
  position: relative;
  width: 4px;
  border-radius: 2px;
  height: 100%;
}
.tc-birth-dot {
  position: absolute;
  top: -3px; left: -2px;
  width: 8px; height: 8px;
  border-radius: 50%;
}
.tc-death-tick {
  position: absolute;
  bottom: 0; left: -3px;
  width: 10px; height: 2px;
}
.tc-person-name {
  writing-mode: vertical-rl;
  font-family: var(--serif);
  font-size: 12px;
  letter-spacing: 2px;
  text-shadow: 0 1px 2px var(--hero1);
  white-space: nowrap;
  pointer-events: none;
}
/* 道距紧时悬停/选中的条须浮到相邻条之上,否则临时显出的名字会被压住 */
.tc-person-wrap.hovered, .tc-person-wrap.selected { z-index: 9; }
.tc-person-wrap.hovered .tc-person-name,
.tc-person-wrap.selected .tc-person-name {
  background: var(--paper-el);
  box-shadow: 0 0 0 2px var(--paper-el);
  border-radius: 2px;
}

/* 聚合溢出道(T7.2,方向甲):最右一道,刻度示密度,+N 徽标随滚动跟随视口 */
.tc-agg-tick {
  position: absolute;
  width: 6px;
  height: 3px;
  border-radius: 1.5px;
  transform: translateY(-50%);
  background: var(--cat-person);
  opacity: 0.75;
  cursor: pointer;
  z-index: 4;
}
.tc-agg-tick:hover { opacity: 1; box-shadow: 0 0 6px var(--accent-glow); }
.tc-agg-badge {
  position: absolute;
  z-index: 8;
  font-family: ui-monospace, monospace;
  font-size: 10px;
  line-height: 1.4;
  padding: 1px 5px;
  border-radius: 8px;
  background: var(--paper-el);
  border: 1px solid color-mix(in srgb, var(--cat-person) 55%, transparent);
  color: var(--ink-mid);
  cursor: pointer;
  transform: translateX(-3px);
  white-space: nowrap;
}
.tc-agg-badge:hover { border-color: var(--accent); color: var(--accent); }
/* hover 名单浮层(M8 起):样式与结构迁入 timeline/AggPopList.vue —— 人物聚合道与
   事件溢出桶共用同一组件,浮层可交互、条目可点选;类名不变,e2e 钉子不漂 */

/* 事件卡片 */
.tc-event-card {
  position: absolute;
  transform: translateY(-50%);
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 6px;
  /* width 由 cardStyle 内联(CARD_W 单一真源):列位要按卡宽算,两处各写一份必然漂移。
     高度须与 JS 的 CARD_H(22) 吻合:14(印章)+3*2(padding)+1*2(border)=22 */
  box-sizing: border-box;
  padding: 3px 8px;
  border-radius: 5px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, box-shadow 0.12s;
}
.tc-event-card:hover { background: var(--hover) !important; }
.tc-event-name {
  font-family: var(--serif);
  font-size: 11.5px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tc-event-year {
  margin-left: auto;
  font-family: ui-monospace, monospace;
  font-size: 10px;
  color: var(--ink-faint);
  flex-shrink: 0;
}

/* 跨年事件的时长尾巴:自卡片起向下延伸至终年,走列左侧间隙,故不压卡片。
   与单点事件共用一套语言——都是卡片,只是多一条尾。 */
.tc-event-tail {
  position: absolute;
  width: 3px;
  border-radius: 2px;
  z-index: 4;
  pointer-events: none;
}

/* 溢出槽:本缩放下放不下的事件各留一枚刻度。放不下就悄悄丢掉,用户无从知道少了什么;
   刻度既示其存在与年代,又以疏密透出该段的事件密度。放大后自然回到列里。 */
.tc-overflow-tick {
  position: absolute;
  width: 7px;
  height: 2px;
  border-radius: 1px;
  transform: translateY(-50%);
  opacity: 0.5;
  cursor: pointer;
  z-index: 3;
  transition: opacity 0.12s, width 0.12s;
}
.tc-overflow-tick:hover, .tc-overflow-tick.hovered {
  opacity: 1;
  width: 11px;
  box-shadow: 0 0 6px var(--accent-glow);
}

/* 溢出桶徽标(T8.1):同段年代收起多件事时不再逐枚叠刻度,渲染 +N;
   族色描边由 badgeStyle 内联给出(继承既有调色) */
.tc-overflow-badge {
  position: absolute;
  transform: translateY(-50%);
  z-index: 7;
  font-family: ui-monospace, monospace;
  font-size: 9.5px;
  line-height: 1.5;
  padding: 0 4px;
  border-radius: 7px;
  background: var(--paper-el);
  border: 1px solid var(--line);
  color: var(--ink-mid);
  cursor: pointer;
  white-space: nowrap;
}
.tc-overflow-badge:hover { border-color: var(--accent) !important; color: var(--accent); }

/* 柱缘密度指示条(T8.3):全轴事件密度热区薄条贴柱右缘;朱红热度 ∝ 各年代段事件数,
   与缩放无关。当前年刻痕随刷年掠过;整条可点跳年 */
.tc-density {
  position: absolute;
  right: 0; top: 0; bottom: 0;
  width: 7px;
  z-index: 24;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}
.tc-density-bin {
  flex: 1;
  min-height: 1px;
  background: var(--accent);
}
.tc-density-now {
  position: absolute;
  left: -4px;
  width: 11px;
  height: 2px;
  border-radius: 1px;
  background: var(--ink);
  pointer-events: none;
}

/* 年谱 pin */
.tc-moment-pin {
  position: absolute;
  transform: translate(-100%, -50%);
  z-index: 6;
  display: flex;
  flex-direction: row-reverse;
  align-items: center;
  gap: 6px;
  max-width: 34%;
  cursor: pointer;
}
.tc-moment-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent);
}
.tc-moment-label {
  font-size: 11px;
  color: var(--ink);
  background: var(--caption);
  border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent);
  border-radius: 6px;
  padding: 2px 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  backdrop-filter: blur(2px);
}

/* 关系连线 SVG overlay */
.tc-relation-svg {
  position: absolute;
  left: 0; top: 0;
  width: 100%;
  z-index: 3;
  pointer-events: none;
}

/* hover / selected 高亮 */
.tc-person-wrap.hovered { z-index: 10; }
.tc-person-wrap.hovered .tc-person-bar { box-shadow: 0 0 12px var(--accent-glow) !important; }
.tc-person-wrap.hovered .tc-person-name { color: var(--accent) !important; font-weight: 700 !important; }
.tc-event-card.hovered { z-index: 10; }
.tc-event-card.hovered { border-color: var(--accent) !important; box-shadow: 0 3px 14px var(--accent-glow) !important; }
.tc-event-card.selected { border-color: var(--accent); box-shadow: 0 3px 14px var(--accent-glow); }

/* 因果链:纵贯首尾的轨道 + 到每个成员的 stub。left 由 visibleChains 内联给出
   (贴事件列左侧);原先写死 106px 是旧布局的残留,那时还没有帝王带。 */
.tc-chain-rail {
  position: absolute;
  width: 0;
  border-left: 2px dashed color-mix(in srgb, var(--accent) 55%, transparent);
  z-index: 3;
  pointer-events: none;
}
.tc-chain-stub {
  position: absolute;
  height: 0;
  border-top: 2px dashed color-mix(in srgb, var(--accent) 55%, transparent);
  z-index: 3;
  pointer-events: none;
}

/* 当前年 lens */
.tc-lens {
  position: absolute;
  left: 0; right: 0;
  top: 240px;
  z-index: 25;
  pointer-events: none;
}
.tc-lens-line {
  height: 2px;
  background: var(--accent);
  box-shadow: 0 1px 6px var(--accent-glow);
}
.tc-lens-label {
  position: absolute;
  left: 10px;
  top: -13px;
  background: var(--accent);
  color: var(--accent-text);
  font-family: var(--serif);
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 13px;
  white-space: nowrap;
}
/* B1 跳年脉冲:朱红光晕一闪(160ms),告知「柱子为你跳了」 */
.tc-lens-label.pulse { animation: tc-lens-pulse 160ms ease-out; }
@keyframes tc-lens-pulse {
  0% { box-shadow: 0 0 0 0 var(--accent-glow); transform: scale(1.12); }
  100% { box-shadow: 0 0 0 12px transparent; transform: scale(1); }
}
.tc-lens-hint {
  position: absolute;
  right: 12px;
  top: -10px;
  font-size: 10px;
  color: var(--ink-soft);
  background: var(--caption);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 2px 9px;
}

/* 控制条 */
.tc-controls {
  position: absolute;
  top: 12px;
  left: 106px;
  z-index: 28;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.tc-toolbar {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--caption);
  backdrop-filter: blur(3px);
}
.tc-tool-button {
  min-height: 30px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--ink-mid);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}
.tc-tool-button + .tc-tool-button { border-left: 1px solid var(--line); border-radius: 0 6px 6px 0; }
.tc-tool-button:hover { color: var(--accent); background: var(--hover); }
.tc-scale-chevron { transition: transform 0.15s ease; }
.tc-scale-chevron.open { transform: rotate(180deg); }
.tc-scale-popover {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--caption);
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  backdrop-filter: blur(6px);
}
.tc-segmented {
  display: flex;
  background: var(--field);
  border-radius: 7px;
  padding: 2px;
  gap: 2px;
  backdrop-filter: blur(3px);
}
.tc-segmented button {
  padding: 5px 13px;
  border: none;
  border-radius: 6px;
  font-size: 12.5px;
  background: transparent;
  color: var(--ink-mid);
  cursor: pointer;
}
.tc-segmented button.active {
  background: var(--accent);
  color: var(--accent-text);
}
.tc-reset {
  width: 30px;
  height: 30px;
  padding: 0;
  border: none;
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--ink-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.tc-reset:hover { background: var(--hover); color: var(--accent); }
/* M12 历法口径注记:贴在缩放控件下方,不抢视线但一眼可见 */
.tc-calendar-note {
  position: absolute;
  top: 46px;
  left: 106px;
  z-index: 27;
  padding: 3px 9px;
  border-radius: 6px;
  background: var(--caption);
  border: 1px solid var(--line);
  color: var(--ink-soft, var(--ink-mid));
  font-size: 11px;
  letter-spacing: 0.02em;
  backdrop-filter: blur(3px);
  pointer-events: none;
}
/* C1 播放指示:lens 胶囊内的 ⏸(随胶囊一起脉冲) */
.tc-lens-playing { font-size: 11px; }

@media (max-width: 720px) {
  .tc-controls {
    top: 8px;
    left: 102px;
    right: 8px;
    gap: 6px;
    flex-wrap: nowrap;
  }
  .tc-segmented button { padding: 5px 9px; font-size: 11.5px; }
  .tc-reset { padding: 5px 9px; }
  .tc-calendar-note { top: 43px; left: 102px; font-size: 10px; }
  .tc-lens-hint { display: none; }
}
</style>
