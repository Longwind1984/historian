<template>
  <!-- D2 单一档案卡:时间柱 MomentPanel 与星图侧栏共用,tab 取并集
       详情/关系/链接/年谱/同代/史料。壳只传 entityId 与操作按钮,
       字段一处维护、两路由逐一对齐。年谱/同代/链接惰性加载(既有行为);
       hover 预览为轻量态,只取实体本体,关系/同代等重数据锁定后才取。 -->
  <div class="ep-wrap">
    <div v-if="loading && !entity" class="ep-ph">加载中…</div>
    <EmptyState v-else-if="!entity" compact glyph="闕" text="未找到该实体。" />
    <template v-else>
      <!-- 头像 + 名 + 类型徽 + 元信息 -->
      <div class="ep-head">
        <div class="ep-avatar" :style="avatarStyle">
          <!-- imgBroken 而非 style.display='none':后者把 img 藏了,而占位 span 是
               v-else 永不出现 —— 图挂掉时头像位变成一个空的纯渐变块,连字都没有。
               全库 102 个 image 里实测约 78% 已失效(李白/杜甫皆 404),所以这不是
               边缘情形,是当前站上的常态观感。 -->
          <img v-if="entity.image && !imgBroken" :src="entity.image" :alt="entity.name"
               referrerpolicy="no-referrer" @error="imgBroken = true" />
          <span v-else class="ep-avatar-char">{{ displayInitial }}</span>
          <span class="ep-avatar-seal"><Seal :type="entity.type" :category="entity.type === 'Event' ? entity.category : null" :size="14" /></span>
        </div>
        <div class="ep-head-info">
          <div class="ep-name">
            {{ entity.name }}<span v-if="entity.name_en" class="ep-name-en">{{ entity.name_en }}</span>
          </div>
          <div class="ep-meta">
            <span class="ep-type-badge" :style="{ background: dataStore.typeMeta(entity.type).color }">{{ dataStore.typeMeta(entity.type).label }}</span>
            <span v-if="metaLine">{{ metaLine }}</span>
          </div>
          <div class="ep-tags" v-if="hasTags">
            <span v-if="entity.courtesy_name" class="ep-tag">字 {{ entity.courtesy_name }}</span>
            <span v-if="entity.art_name" class="ep-tag">号 {{ entity.art_name }}</span>
            <span v-for="tag in (entity.alias || [])" :key="tag" class="ep-tag">{{ tag }}</span>
          </div>
        </div>
        <div class="ep-preview-badge" v-if="preview">预览</div>
      </div>

      <!-- Bio / Description(wiki 链接;Bio 缺时以历史意义顶位,详情节相应去重)-->
      <div class="ep-bio" v-if="bioText">
        <WikiLinkText :text="bioText" :mentions="bioMentions" :self-id="entity.id" @navigate="navigate" />
      </div>

      <!-- 因果链(Event 专属,T4.5;预览不取关系故不显)-->
      <div v-if="showCausal" class="ep-causal">
        <div class="ep-cap">因果</div>
        <div v-if="causal.causes.length" class="ep-causal-row">
          <span class="ep-causal-arrow">← 前因</span>
          <span v-for="c in causal.causes" :key="'c'+c.id" class="ep-causal-item" @click="navigate(c.id)">
            <span class="ep-causal-name">{{ c.name }}</span>
            <span class="ep-causal-note" v-if="c.note">{{ c.note }}</span>
          </span>
        </div>
        <div v-if="causal.effects.length" class="ep-causal-row">
          <span class="ep-causal-arrow">-&gt; 后果</span>
          <span v-for="c in causal.effects" :key="'e'+c.id" class="ep-causal-item" @click="navigate(c.id)">
            <span class="ep-causal-name">{{ c.name }}</span>
            <span class="ep-causal-note" v-if="c.note">{{ c.note }}</span>
          </span>
        </div>
        <div v-if="causal.parts.length" class="ep-causal-row">
          <span class="ep-causal-arrow">从属</span>
          <span v-for="c in causal.parts" :key="'p'+c.id" class="ep-causal-item" @click="navigate(c.id)">{{ c.name }}</span>
        </div>
        <div v-if="causal.concurrent.length" class="ep-causal-row">
          <span class="ep-causal-arrow">同期</span>
          <span v-for="c in causal.concurrent" :key="'s'+c.id" class="ep-causal-item" @click="navigate(c.id)">{{ c.name }}</span>
        </div>
      </div>

      <!-- 标签页(并集):详情/关系/链接/年谱/同代/史料 -->
      <div class="ep-tabs">
        <button :class="{active: tab==='detail'}" @click="setTab('detail')">详情</button>
        <button :class="{active: tab==='relations'}" @click="setTab('relations')">
          关系 <span class="ep-tab-count" v-if="relationsReady && relations.length">{{ relations.length }}</span>
        </button>
        <button :class="{active: tab==='links'}" @click="setTab('links')">
          链接 <span class="ep-tab-count" v-if="countsReady">{{ linkCounts.outbound + linkCounts.inbound }}</span>
        </button>
        <button :class="{active: tab==='chronology'}" @click="setTab('chronology')" v-if="hasChronology">年谱</button>
        <button :class="{active: tab==='contemporary'}" @click="setTab('contemporary')">同代</button>
        <button :class="{active: tab==='sources'}" @click="setTab('sources')" v-if="hasSourcesTab">史料</button>
      </div>

      <!-- 详情:分类型字段节(全量保留旧 EntityDetail 各节;史料出处移入「史料」tab)-->
      <div v-show="tab==='detail'" class="ep-tab-body">
        <div class="ep-section" v-if="entity.significance && !bioIsSignificance">
          <h4>历史意义</h4>
          <WikiLinkText :text="entity.significance" :mentions="mentionsFor('significance')" :self-id="entity.id" @navigate="navigate" />
        </div>
        <div class="ep-section" v-if="entity.impact">
          <h4>影响</h4>
          <WikiLinkText :text="entity.impact" :mentions="mentionsFor('impact')" :self-id="entity.id" @navigate="navigate" />
        </div>

        <template v-if="entity.type === 'Person'">
          <div class="ep-section" v-if="entity.birthplace">
            <h4>籍贯</h4>
            <a class="ep-ref" @click="navigateRef(entity.birthplace)">{{ refName(entity.birthplace) }}</a>
          </div>
        </template>

        <template v-if="entity.type === 'Polity'">
          <div class="ep-section">
            <h4>存续</h4>
            <div>{{ yearOf(entity.founded) }}–{{ yearOf(entity.ended) }}</div>
          </div>
          <div class="ep-section" v-if="entity.founder">
            <h4>创建者</h4>
            <a class="ep-ref" @click="navigateRef(entity.founder)">{{ refName(entity.founder) }}</a>
          </div>
          <div class="ep-section" v-if="entity.ended_by">
            <h4>亡于</h4>
            <a class="ep-ref" @click="navigateRef(entity.ended_by)">{{ refName(entity.ended_by) }}</a>
          </div>
        </template>

        <template v-if="entity.type === 'Faction'">
          <div class="ep-section" v-if="entity.nature">
            <h4>性质</h4>
            <div>{{ natureLabel(entity.nature) }}</div>
          </div>
          <div class="ep-section" v-if="relationsLoading || coreMembers.length">
            <h4>核心成员</h4>
            <div v-if="relationsLoading && !relationsReady" class="ep-ph">读取中…</div>
            <div v-else>
              <!-- 领袖在前;leader_of 加粗(旧 is-leader 行为) -->
              <a class="ep-ref ep-tag" v-for="m in coreMembers" :key="m.otherId"
                 :class="{ 'is-leader': m.edgeType === 'leader_of' }"
                 :title="m.note" @click="navigate(m.otherId)">
                {{ m.otherName }}
              </a>
            </div>
          </div>
        </template>

        <template v-if="entity.type === 'Battle'">
          <div class="ep-section" v-if="entity.combatants?.length">
            <h4>参战方</h4>
            <div>
              <template v-for="(c, i) in entity.combatants" :key="i">
                <a class="ep-ref" @click="navigateRef(c)">{{ refName(c) }}</a>
                <span v-if="i < entity.combatants.length - 1"> vs </span>
              </template>
            </div>
          </div>
          <div class="ep-section" v-if="entity.victor">
            <h4>胜方</h4>
            <a class="ep-ref" @click="navigateRef(entity.victor)">{{ refName(entity.victor) }}</a>
          </div>
          <div class="ep-section" v-if="entity.commanders?.length">
            <h4>主帅</h4>
            <div>
              <a class="ep-ref ep-tag" v-for="c in entity.commanders" :key="c" @click="navigateRef(c)">{{ refName(c) }}</a>
            </div>
          </div>
          <div class="ep-section" v-if="entity.location">
            <h4>地点</h4>
            <a class="ep-ref" @click="navigateRef(entity.location)">{{ refName(entity.location) }}</a>
          </div>
        </template>

        <EmptyState v-if="!hasDetailSections" compact glyph="闕" text="暂无更多详情字段。" />
      </div>

      <!-- 关系:REL_LABELS 分组(静态表优先,schema 标签兜底),组内出向在前 -->
      <div v-show="tab==='relations'" class="ep-tab-body">
        <div v-if="relationsLoading" class="ep-ph">读取中…</div>
        <template v-else-if="relationsReady">
          <EmptyState v-if="relations.length === 0" compact glyph="系" text="无关系数据" />
          <div v-else class="ep-rel-group" v-for="group in groupedRelations" :key="group.label">
            <div class="ep-cap">{{ group.label }} · {{ group.items.length }}</div>
            <div v-for="item in group.items" :key="item.key" class="ep-relation"
                 @click="navigate(item.otherId)"
                 @mouseenter="selectionStore.setHover(item.otherId)"
                 @mouseleave="selectionStore.setHover(null)">
              <Seal :type="item.otherType" :size="18" />
              <span class="ep-relation-name">{{ item.otherName }}</span>
              <span class="ep-relation-years" v-if="relYears(item)">{{ relYears(item) }}</span>
              <span class="ep-relation-note" v-if="item.note">{{ item.note }}</span>
              <span class="ep-relation-interval" v-if="relInterval(item)">⏱ {{ relInterval(item) }}</span>
              <span class="ep-relation-dir">{{ item.direction }}</span>
            </div>
          </div>
        </template>
        <!-- 预览态不取关系(轻量 hover):宁可显式声明,不拿锁定实体的旧数据冒充 -->
        <EmptyState v-else compact glyph="系" text="悬停预览中 · 点击锁定查看关系" />
      </div>

      <!-- 链接:wiki 出入链与计数都在首次切入时惰性加载 -->
      <div v-show="tab==='links'" class="ep-tab-body">
        <div v-if="linksLoading" class="ep-ph">读取中…</div>
        <template v-else-if="linksReady">
          <div class="ep-link-group" v-if="outboundLinks.length">
            <div class="ep-cap">出链 · 正文提到</div>
            <div v-for="m in outboundLinks" :key="m.to_id" class="ep-backlink" @click="navigate(m.to_id)">
              <Seal :type="m.to_type" :size="16" />
              <span>{{ m.to_name }}</span>
              <span class="ep-link-field">{{ fieldLabel(m.field) }}</span>
            </div>
          </div>
          <div class="ep-link-group" v-if="backlinks.length">
            <div class="ep-cap">入链 · 被提到</div>
            <div v-for="b in backlinks" :key="b.from_id" class="ep-backlink" @click="navigate(b.from_id)">
              <Seal :type="b.from_type" :size="16" />
              <span>{{ b.from_name }}</span>
              <span class="ep-link-field">{{ fieldLabel(b.field) }}</span>
            </div>
          </div>
          <EmptyState v-if="!outboundLinks.length && !backlinks.length" compact glyph="鏈" text="无 wiki 链接" />
        </template>
        <EmptyState v-else compact glyph="鏈" text="悬停预览中 · 点击锁定查看链接" />
      </div>

      <!-- 年谱(D3):life_events 大事记优先,无则仅生卒 + 显式「待补」(原则 6,不编造)。
           惰性:籍贯解析等到首次切到本 tab 才发请求。 -->
      <div v-show="tab==='chronology'" class="ep-tab-body">
        <div v-for="m in chronology" :key="m.year + m.label" class="ep-chrono" @click="timeStore.setYear(m.year)">
          <span class="ep-chrono-year">{{ m.yearLabel }}</span>
          <span class="ep-chrono-label">{{ m.label }}</span>
        </div>
        <div v-if="!hasLifeEvents" class="ep-chrono-note">年谱待补 · 仅录生卒</div>
      </div>

      <!-- 同代:惰性加载(首次切 tab 才取);空态走 EmptyState(D5 收尾)-->
      <div v-show="tab==='contemporary'" class="ep-tab-body">
        <div v-if="contemporariesLoading" class="ep-ph">读取同代人物中…</div>
        <template v-else-if="contemporariesReady">
          <EmptyState v-if="contemporaries.length === 0" compact glyph="代"
                      text="无同时代人物" sub="可能生卒年缺失" />
          <template v-else>
            <div class="ep-contemp-intro">同一时代({{ midlifeYear }} 前后)的 {{ contemporaries.length }} 位人物</div>
            <div class="ep-contemp-grid">
              <div class="ep-contemp-card" v-for="c in contemporaries.slice(0, 60)" :key="c.id"
                   @click="navigate(c.id)">
                <Avatar :src="c.image" :name="c.name" type="Person" :size="36" />
                <div>
                  <div class="ep-relation-name">{{ c.name }}</div>
                  <div class="ep-relation-years">{{ c.born?.year ?? '?' }}–{{ c.died?.year ?? '?' }}</div>
                </div>
              </div>
            </div>
          </template>
        </template>
        <EmptyState v-else compact glyph="代" text="悬停预览中 · 点击锁定查看同代" />
      </div>

      <!-- 史料出处:统一进「史料」tab(旧 EntityDetail 塞详情节,已迁此)-->
      <div v-show="tab==='sources'" class="ep-tab-body">
        <!-- 典籍与延伸分节而不分 tab:两者都是「去哪儿读」,但一个是史料本身、
             一个是后人编的参考,混在一张无标题的列表里会让读者以为维基条目
             与《旧唐书》同级。分节标题足以立此界,不必为它再添第七个 tab。 -->
        <template v-if="entity.sources?.length">
          <div class="ep-sec-label">典籍出处</div>
          <ul class="ep-sources">
            <li v-for="(s, i) in (entity.sources || [])" :key="i">{{ s }}</li>
          </ul>
        </template>
        <template v-if="readingLinks.length">
          <div class="ep-sec-label">延伸阅读</div>
          <ul class="ep-reading">
            <li v-for="l in readingLinks" :key="l.href">
              <a :href="l.href" target="_blank" rel="noopener noreferrer">
                {{ l.label }}<span class="ep-reading-site">{{ l.site }}</span>
              </a>
            </li>
          </ul>
        </template>
        <!-- 图像署名位:CC BY / CC BY-SA 强制署名,PD 也该注明出处。
             放在史料 tab 而非头像下方 —— 头像 52×64,挂不下一行作者名。 -->
        <template v-if="entity.image_license">
          <div class="ep-sec-label">图像出处</div>
          <div class="ep-img-credit">
            <a v-if="entity.image_source_page" :href="entity.image_source_page"
               target="_blank" rel="noopener noreferrer">{{ entity.image_license }}</a>
            <span v-else>{{ entity.image_license }}</span>
            <span v-if="entity.image_credit"> · {{ entity.image_credit }}</span>
          </div>
        </template>
      </div>

      <!-- 操作区:壳按路由自供按钮(时间柱「展开谱系星图→/📍」,星图「📍/🕸/关闭」)-->
      <div class="ep-actions" v-if="$slots.actions">
        <slot name="actions" :entity="entity" :anchor="hasGeoAnchor" :preview="preview" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useDataStore, useTimeStore, useSelectionStore } from '../../stores'
import { getEntity } from '../../api/client'
import { useEntityDetail } from '../../composables/useEntityDetail'
import { fmtY } from '../../styles/palettes'
import Seal from './Seal.vue'
import Avatar from './Avatar.vue'
import WikiLinkText from './WikiLinkText.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  entityId: { type: String, required: true },
  // hover 预览(轻量):只取实体本体,关系/同代等重数据不取,tab 不重置
  preview: { type: Boolean, default: false },
  // 壳差异之一:时间柱选中后落在「关系」,星图侧栏落在「详情」
  defaultTab: { type: String, default: 'detail' },
})

const dataStore = useDataStore()
const timeStore = useTimeStore()
const selectionStore = useSelectionStore()

const {
  entity, loading,
  relations, relationsLoading, relationsLoadedFor, causal,
  outboundLinks, backlinks, linkCounts, linkCountsFor, linksLoading, linksLoadedFor,
  contemporaries, contemporariesLoading, contemporariesLoadedFor,
  loadEntity, ensureRelations, ensureLinks, ensureContemporaries,
} = useEntityDetail()

const tab = ref(props.defaultTab)

// === 加载编排:hover 预览只取本体(轻量);显式选中才重置 tab 并按需取数。
// 两种入口都算「新锁定」:换了一个非预览实体;或把正预览的实体点击锁定
// (此时 id 不变、preview 翻转,单看 entityId 会漏 —— 故两个 prop 一起 watch)。
// hover 结束回到已锁定实体不算新锁定:tab 保持,数据已缓存不重复取。 ===
let lastLockedId = null
watch([() => props.entityId, () => props.preview], async ([id, isPrev]) => {
  if (!id) return
  const isNewLock = !isPrev && id !== lastLockedId
  if (!isPrev) lastLockedId = id
  if (isNewLock) tab.value = props.defaultTab
  await loadEntity(id)
  if (isPrev) return
  // mention 图冷建是全库扫描；未打开链接页时不为角标抢占后端 CPU。
  // 首次切入链接页会一次取齐出链、入链和计数，随后仍显示同一角标。
  // Faction 的「核心成员」与 Event 的「因果链」都在详情区,概览就要关系,不能等关系 tab
  if (entity.value?.type === 'Faction' || entity.value?.type === 'Event') ensureRelations(id)
  ensureForTab(tab.value)
}, { immediate: true })

// tab 惰性:切到才取。预览态只放行轻量 tab(链接点击取数是旧 MomentPanel 既有行为;
// 年谱只需一次籍贯解析);关系/同代属重数据,锁定后再取。
function setTab(t) {
  tab.value = t
  if (props.preview && (t === 'relations' || t === 'contemporary')) return
  ensureForTab(t)
}
function ensureForTab(t) {
  const id = props.entityId
  if (!id) return
  if (t === 'relations') ensureRelations(id)
  else if (t === 'links') ensureLinks(id)
  else if (t === 'contemporary') ensureContemporaries(id, midlifeYear.value)
  else if (t === 'chronology') resolveBirthplace()
}

// === 数据就绪守卫:切实体后旧数据不得在新区名下露脸(旧 MomentPanel 预览期
//     关系 tab 显示锁定实体数据的串台问题,随合并一并修掉)===
const relationsReady = computed(() => !!entity.value && relationsLoadedFor.value === entity.value.id)
const linksReady = computed(() => !!entity.value && linksLoadedFor.value === entity.value.id)
const contemporariesReady = computed(() => !!entity.value && contemporariesLoadedFor.value === entity.value.id)
const countsReady = computed(() => !!entity.value && linkCountsFor.value === entity.value.id && !!linkCounts.value)

// === 导航:档案内一切跳转都是显式选中(350ms hover 抑制窗在 store,行为不变)===
function navigate(id) {
  if (!id) return
  selectionStore.selectEntity(id)
}
function navigateRef(idOrObj) {
  if (idOrObj == null) return
  navigate(typeof idOrObj === 'string' ? idOrObj : idOrObj.id)
}

// === 头部 ===
// 图加载失败旗。切换实体必须重置,否则上一个实体的失败会让下一个实体
// 即使有好图也直接落占位(Avatar.vue 的 watch(src) 同款)。
const imgBroken = ref(false)
watch(() => entity.value?.id, () => { imgBroken.value = false })
const displayInitial = computed(() => (entity.value?.name || '?').charAt(0))
const hasTags = computed(() => {
  const e = entity.value
  return !!(e && (e.courtesy_name || e.art_name || (e.alias || []).length))
})
const avatarStyle = computed(() => {
  const sel = entity.value
  if (!sel) return {}
  const catColor = `var(--cat-${(sel.type || 'Person').toLowerCase()})`
  return { background: `linear-gradient(160deg, ${catColor}, color-mix(in srgb, ${catColor} 55%, black))` }
})

// 元信息行:生卒(享年)/政权存续/事件年份 + 今名(今名来自旧 EntityDetail meta)
const metaLine = computed(() => {
  const sel = entity.value
  if (!sel) return ''
  let base = ''
  if (sel.born?.year != null || sel.died?.year != null) {
    const b = sel.born?.year, d = sel.died?.year
    const age = (b != null && d != null) ? d - b : null
    base = fmtY(b) + ' – ' + fmtY(d) + (age > 0 && age < 120 ? ' · 享年 ' + age : '')
  } else if (sel.founded?.year != null && sel.ended?.year != null) {
    base = '存续 ' + fmtY(sel.founded.year) + ' – ' + fmtY(sel.ended.year)
  } else if (sel.date?.year != null) {
    const y0 = sel.date.year, y1 = sel.end_date?.year
    base = (y1 != null && y1 > y0)
      ? fmtY(y0) + ' – ' + fmtY(y1) + ' · ' + (y1 - y0) + '年'
      : fmtY(y0) + ' 年'
  }
  if (sel.modern_name) base = base ? base + ' · 今 ' + sel.modern_name : '今 ' + sel.modern_name
  return base
})

// === Bio:本体 bio/description 优先;都没有时以历史意义顶位(旧 MomentPanel 行为),
//     详情 tab 的「历史意义」节相应去重,不两处同文 ===
const bioText = computed(() => {
  const e = entity.value
  if (!e) return ''
  return e.bio || e.description || e.significance || ''
})
const bioIsSignificance = computed(() => {
  const e = entity.value
  return !!e && !e.bio && !e.description && !!e.significance
})
// wiki mentions 只在出入链为本实体时才可用:offset 按本文切,串实体会切错文
const bioMentions = computed(() => {
  if (!entity.value || linksLoadedFor.value !== entity.value.id) return []
  const fields = bioIsSignificance.value ? ['significance'] : ['bio', 'description']
  return outboundLinks.value.filter(m => fields.includes(m.field))
})
function mentionsFor(field) {
  if (!entity.value || linksLoadedFor.value !== entity.value.id) return []
  return outboundLinks.value.filter(m => m.field === field)
}

// === 因果链(Event):预览不取关系故不显(旧 showCausal 行为)===
const showCausal = computed(() => {
  if (props.preview) return false
  if (entity.value?.type !== 'Event') return false
  if (!relationsReady.value) return false
  const c = causal.value
  return !!c && (c.causes.length || c.effects.length || c.parts.length || c.concurrent.length)
})

// === 详情 tab:分类型字段节(旧 EntityDetail 全量保留)===
function yearOf(ym) { return ym?.year ?? '' }

const NATURE_LABELS = {
  military_clan: '军事集团',
  political: '政治派系',
  scholarly: '学术/文人集团',
  regional: '地域集团',
  ethnic: '部族集团',
  religious: '宗教派别',
  eunuch: '宦官集团',
  merchant: '商人/商业集团',
}
function natureLabel(n) { return NATURE_LABELS[n] || n }

// id 引用(籍贯/创建者/参战方…)的显名:对象直取,字符串后台解析并缓存
const nameCache = new Map()
function refName(idOrObj) {
  if (idOrObj == null) return ''
  if (typeof idOrObj !== 'string') return idOrObj.name || idOrObj.id || JSON.stringify(idOrObj)
  if (nameCache.has(idOrObj)) return nameCache.get(idOrObj)
  getEntity(idOrObj).then(e => {
    nameCache.set(idOrObj, e.name || idOrObj)
  }).catch(() => nameCache.set(idOrObj, idOrObj))
  return idOrObj
}

// 核心成员:指向本集团的 leader_of / member_of,领袖在前
const coreMembers = computed(() => {
  if (!relationsReady.value) return []
  const ms = relations.value.filter(
    r => r.direction === '←' && (r.edgeType === 'leader_of' || r.edgeType === 'member_of'))
  return ms.sort((a, b) => (a.edgeType === 'leader_of' ? 0 : 1) - (b.edgeType === 'leader_of' ? 0 : 1))
})

const hasDetailSections = computed(() => {
  const e = entity.value
  if (!e) return false
  if ((e.significance && !bioIsSignificance.value) || e.impact) return true
  if (e.type === 'Person') return !!e.birthplace
  if (e.type === 'Polity') return true  // 存续节恒在
  if (e.type === 'Faction') return !!(e.nature || coreMembers.value.length || relationsLoading.value)
  if (e.type === 'Battle') return !!(e.combatants?.length || e.victor || e.commanders?.length || e.location)
  return false
})

// === 关系 tab:REL_LABELS 静态表全量保留(旧 EntityDetail 分组),schema 标签兜底 ===
const REL_LABELS = {
  father_of: '父',
  mother_of: '母',
  spouse_of: '配偶',
  sibling_of: '兄弟/姐妹',
  child_of: '子女',
  served_under: '效力于',
  mentored_by: '师从',
  participated_in: '参与',
  led: '指挥',
  member_of: '成员',
  leader_of: '领袖',
  held_title: '官职',
  usurped: '篡夺',
  founded: '创立',
  killed: '弑',
  allied_with: '盟友/交往',
  associated_with: '交往',
}
function relLabel(t) { return REL_LABELS[t] || dataStore.relationMeta(t).label || t }
const groupedRelations = computed(() => {
  const groups = {}
  for (const it of relations.value) {
    const label = relLabel(it.edgeType)
    if (!groups[label]) groups[label] = { label, items: [] }
    groups[label].items.push(it)
  }
  // 组按规模降序;组内保持 composable 的出向在前排序
  return Object.values(groups).sort((a, b) => b.items.length - a.items.length)
})
function relYears(item) {
  return item.otherBorn != null ? `${fmtY(item.otherBorn)}–${fmtY(item.otherDied)}` : ''
}
function relInterval(item) {
  const s = item.since, u = item.until
  if (s && u) return `${s}–${u}`
  if (s) return `${s}+`
  if (u) return `≤${u}`
  return ''
}

// === 链接 tab ===
const FIELD_LABELS = {
  bio: '生平',
  description: '简介',
  significance: '历史意义',
  impact: '影响',
  note: '备注',
  pres_loc: '现今位置',
}
function fieldLabel(f) { return FIELD_LABELS[f] || f }

// === 年谱(D3):life_events 优先;籍贯解析惰性到首次切 tab ===
const birthplaceName = ref('')
const birthplaceResolvedFor = ref(null)
async function resolveBirthplace() {
  const sel = entity.value
  const bp = sel?.birthplace
  if (!sel || !bp || birthplaceResolvedFor.value === sel.id) return
  birthplaceResolvedFor.value = sel.id
  birthplaceName.value = ''
  // 籍贯是 Place id(如李白 pl_suiye_libai),需解析成名;对象形态(嵌套 Place)直接用
  if (typeof bp === 'object' && bp.name) { birthplaceName.value = bp.name; return }
  try {
    const p = await getEntity(typeof bp === 'string' ? bp : bp.id)
    birthplaceName.value = p?.name || ''
  } catch { /* 解析不到就只显示生年行,不硬凑地名 */ }
}

const lifeEventsOf = (sel) => Array.isArray(sel?.life_events)
  ? sel.life_events.filter(e => e && e.year != null && e.event)
  : []
// 大事记超 5 条只取标 importance:1 的(数据规范 §2 预留该字段);
// 全未标注时取前 5 条 —— 不虚构重要性,也不把柱/卡淹没(与 TimeColumn pins 同规则)。
function pickLifeEvents(evts) {
  if (evts.length <= 5) return evts
  const imp = evts.filter(e => e.importance === 1)
  return imp.length ? imp : evts.slice(0, 5)
}

const chronology = computed(() => {
  const sel = entity.value
  if (!sel) return []
  const evts = lifeEventsOf(sel)
  if (evts.length) {
    return pickLifeEvents(evts)
      .map(e => ({ year: e.year, yearLabel: fmtY(e.year), label: e.event }))
      .sort((a, b) => a.year - b.year)
  }
  const result = []
  if (sel.born?.year != null) {
    // 籍贯名只在本实体已解析时取用(守卫同 links):切实体瞬间不拿旧地名
    const bpName = birthplaceResolvedFor.value === sel.id ? birthplaceName.value : ''
    result.push({ year: sel.born.year, yearLabel: fmtY(sel.born.year),
                  label: bpName ? '生于' + bpName : '生' })
  }
  if (sel.died?.year != null) result.push({ year: sel.died.year, yearLabel: fmtY(sel.died.year), label: '卒' })
  return result
})
const hasLifeEvents = computed(() => lifeEventsOf(entity.value).length > 0)
const hasChronology = computed(() => chronology.value.length > 0)

// === 延伸阅读(M13)===
// 只收有稳定 URL 规则的站点。存条目标题/ID 而非整条 URL,域名或路径变了只改这里。
// 百度百科不收:词条可由任何人改写且无版本溯源,与「求真高于中性」不相容。
// ctext / 维基文库(原典深链)价值更高但需要「书名→urn」映射表,等第二个真实用例
// 再说 —— 现在只有 sources 里的字符串,还不足以支撑一层解析抽象。
const readingLinks = computed(() => {
  const e = entity.value
  if (!e) return []
  const out = []
  if (e.wikipedia_zh) {
    out.push({ label: e.wikipedia_zh, site: '中文维基百科',
               href: 'https://zh.wikipedia.org/wiki/' + encodeURIComponent(e.wikipedia_zh) })
  }
  if (e.wikidata_id) {
    out.push({ label: e.wikidata_id, site: 'Wikidata',
               href: 'https://www.wikidata.org/wiki/' + encodeURIComponent(e.wikidata_id) })
  }
  return out
})
// 史料 tab 现在承载三节,任一节有内容就该出
const hasSourcesTab = computed(() => {
  const e = entity.value
  return !!(e && (e.sources?.length || readingLinks.value.length || e.image_license))
})

// === 同代 tab:中生年(生卒中点)为锚 ===
const midlifeYear = computed(() => {
  if (!entity.value) return null
  const b = entity.value.born?.year, d = entity.value.died?.year
  if (b && d) return Math.round((b + d) / 2)
  if (b) return b + 30
  if (d) return d - 30
  return null
})

// === 地理锚点:无锚点定位是纯空操作,壳据此禁用按钮(与 MapPanel 飞行分支同源)===
const hasGeoAnchor = computed(() => {
  const e = entity.value
  if (!e) return false
  if (e.type === 'Person') return !!e.birthplace
  if (e.type === 'Polity') return !!e.capital
  if (e.type === 'Event' || e.type === 'Battle') return !!(e.location || (Array.isArray(e.march) && e.march.length))
  if (e.type === 'Place') return e.latitude != null
  return false
})
</script>

<style scoped>
.ep-wrap { min-height: 0; }
.ep-ph { color: var(--ink-faint); font-size: 12px; padding: 4px 0; }
.ep-cap { font-size: 10px; letter-spacing: 0.16em; color: var(--ink-faint); text-transform: uppercase; margin-bottom: 7px; }

/* 头部 */
.ep-head { display: flex; gap: 12px; position: relative; }
.ep-avatar { width: 52px; height: 64px; border-radius: 5px; flex-shrink: 0; position: relative; overflow: hidden; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.14); }
.ep-avatar img { width: 100%; height: 100%; object-fit: cover; }
.ep-avatar-char { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-family: var(--serif); font-size: 26px; color: rgba(255,255,255,0.94); }
.ep-avatar-seal { position: absolute; bottom: 3px; right: 3px; }
.ep-head-info { flex: 1; min-width: 0; }
.ep-name { font-family: var(--serif); font-weight: 900; font-size: 21px; line-height: 1.15; color: var(--ink); }
.ep-name-en { font-size: 10px; color: var(--ink-faint); letter-spacing: 0.1em; margin-left: 6px; font-family: var(--sans); }
.ep-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 11px; color: var(--ink-soft); margin-top: 3px; }
.ep-type-badge { display: inline-block; padding: 1px 8px; border-radius: 9px; color: #fff; font-size: 10px; }
.ep-tags { display: flex; gap: 4px; margin-top: 5px; flex-wrap: wrap; }
.ep-tag { padding: 1px 7px; border-radius: 9px; background: var(--chip); border: 1px solid var(--line); font-size: 10px; color: var(--ink-soft); }
.ep-preview-badge { position: absolute; top: 0; right: 0; padding: 2px 8px; border-radius: 9px; background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); font-size: 10px; }

.ep-bio { font-family: var(--serif); font-size: 13px; line-height: 1.85; color: var(--ink); margin-top: 11px; }

/* 因果链(Event) */
.ep-causal { margin-top: 10px; padding: 8px 10px; background: var(--chip); border-radius: 6px; border-left: 3px solid var(--accent); }
.ep-causal-row { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; margin-top: 4px; font-size: 12px; }
.ep-causal-arrow { color: var(--accent); font-size: 10.5px; flex-shrink: 0; font-weight: 600; }
.ep-causal-item { cursor: pointer; }
.ep-causal-name { font-family: var(--serif); color: var(--link); }
.ep-causal-note { color: var(--ink-faint); font-size: 10.5px; margin-left: 4px; }

/* 标签页 */
.ep-tabs { display: flex; gap: 1px; border-bottom: 1px solid var(--line); margin-top: 12px; flex-wrap: wrap; }
.ep-tabs button { padding: 6px 10px; border: none; border-bottom: 2px solid transparent; border-radius: 0; background: transparent; color: var(--ink-soft); font-family: inherit; font-size: 12.5px; cursor: pointer; }
.ep-tabs button:hover { color: var(--ink); }
.ep-tabs button.active { color: var(--accent); border-bottom-color: var(--accent); }
.ep-tab-count { font-size: 10px; color: var(--ink-faint); margin-left: 2px; }
.ep-tab-body { padding-top: 8px; }

/* 详情节 */
.ep-section { margin-top: 9px; font-size: 12.5px; line-height: 1.6; color: var(--ink-mid); }
.ep-section h4 { color: var(--ink-faint); font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 3px; font-weight: 600; }
.ep-ref { color: var(--link); cursor: pointer; text-decoration: underline dotted; text-underline-offset: 2px; }
.ep-ref:hover { color: var(--accent); }
.ep-ref.ep-tag { text-decoration: none; display: inline-block; margin: 0 4px 4px 0; padding: 2px 9px; font-size: 11px; }
.ep-ref.ep-tag:hover { border-color: var(--accent); }
.ep-ref.ep-tag.is-leader { color: var(--ink); font-weight: 600; }

/* 关系分组 */
.ep-rel-group { margin-top: 8px; }
.ep-relation { display: flex; align-items: center; gap: 8px; padding: 4px 5px; border-radius: 5px; font-size: 12.5px; cursor: pointer; transition: background 0.1s; }
.ep-relation:hover { background: var(--hover); }
.ep-relation-name { font-family: var(--serif); color: var(--ink); }
.ep-relation-years { font-size: 10px; color: var(--ink-faint); }
.ep-relation-note { color: var(--ink-faint); font-size: 10px; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ep-relation-interval { font-size: 10px; color: var(--ink-faint); }
.ep-relation-dir { margin-left: auto; color: var(--accent); font-size: 11px; font-weight: 600; }

/* 链接 */
.ep-link-group { margin-top: 8px; }
.ep-backlink { display: flex; align-items: center; gap: 7px; padding: 3px 5px; border-radius: 5px; font-size: 12px; cursor: pointer; }
.ep-backlink:hover { background: var(--hover); }
.ep-backlink span:nth-child(2) { font-family: var(--serif); }
.ep-link-field { margin-left: auto; font-size: 10px; color: var(--ink-faint); background: var(--chip); padding: 1px 6px; border-radius: 8px; }

/* 年谱 */
.ep-chrono { display: flex; align-items: baseline; gap: 10px; padding: 3px 5px; border-radius: 5px; cursor: pointer; }
.ep-chrono:hover { background: var(--hover); }
.ep-chrono-year { font-family: ui-monospace, monospace; font-size: 11px; color: var(--accent); min-width: 40px; text-align: right; }
.ep-chrono-label { font-size: 12.5px; color: var(--ink-mid); }
/* D3 待补注记:无 life_events 时显式声明「仅录生卒」(原则 6) */
.ep-chrono-note { margin-top: 6px; font-size: 10.5px; color: var(--ink-faint); letter-spacing: 0.04em; }

/* 同代 */
.ep-contemp-intro { font-size: 11px; color: var(--ink-faint); margin-bottom: 6px; }
.ep-contemp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
.ep-contemp-card { display: flex; align-items: center; gap: 8px; padding: 4px 5px; border-radius: 5px; cursor: pointer; border: 1px solid transparent; }
.ep-contemp-card:hover { background: var(--hover); border-color: var(--line); }

/* 史料 */
.ep-sources { margin: 4px 0 0 1.2em; padding: 0; font-size: 12px; line-height: 1.6; color: var(--ink-soft); }
/* M13 延伸阅读 / 图像署名 */
.ep-sec-label {
  margin-top: 12px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--ink-mid);
}
.ep-sec-label:first-child { margin-top: 0; }
.ep-reading { margin: 4px 0 0 1.2em; padding: 0; font-size: 12px; line-height: 1.7; }
.ep-reading a { color: var(--accent); text-decoration: none; }
.ep-reading a:hover { text-decoration: underline; }
.ep-reading-site {
  margin-left: 6px;
  font-size: 11px;
  color: var(--ink-mid);
}
.ep-img-credit {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--ink-mid);
}
.ep-img-credit a { color: var(--ink-soft); }

/* 操作区(按钮本体样式归壳) */
.ep-actions { margin-top: 14px; display: flex; gap: 6px; flex-wrap: wrap; }
</style>
