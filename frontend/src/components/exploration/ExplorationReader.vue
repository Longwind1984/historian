<template>
  <aside class="xr">
    <div class="xr-tabs" role="tablist" aria-label="探索来源">
      <button role="tab" :aria-selected="store.sourceTab === 'reader'" :class="{ active: store.sourceTab === 'reader' }" @click="store.setSourceTab('reader')">
        <BookOpenText :size="14" />{{ store.workspaceKind === 'question' ? '问题' : store.isSampleWorkspace ? '阅读窗口' : '阅读' }}
      </button>
      <button role="tab" :aria-selected="store.sourceTab === 'web'" :class="{ active: store.sourceTab === 'web' }" @click="store.setSourceTab('web')"><Globe :size="14" />微信读书</button>
      <button role="tab" :aria-selected="store.sourceTab === 'timeline'" :class="{ active: store.sourceTab === 'timeline' }" @click="store.setSourceTab('timeline')"><ListTree :size="14" />时间</button>
    </div>

    <div v-if="store.sourceTab === 'reader' && store.workspaceKind === 'question'" class="xr-question">
      <MessagesSquare :size="25" />
      <small>{{ store.questionSyncState === 'synced' ? '当前进程中的研究问题' : '用户提出的历史问题' }}</small>
      <h2>{{ store.questionPrompt }}</h2>
      <p v-if="store.questionSyncState === 'synced'">服务端已建立范围合同与证据缺口脚手架。下一步确认时间、空间、对象与叙事主线；当前没有生成历史结论。</p>
      <p v-else>当前只保留本机草案，服务端尚未建立探索。你仍可补充材料，或返回入口重试。</p>
      <button @click="store.openEntry()"><BookUp :size="14" />添加书籍或材料</button>
    </div>

    <div v-else-if="store.sourceTab === 'reader'" class="xr-body">
      <div class="xr-book">
        <span class="xr-seal">书</span>
        <div>
          <strong>{{ store.snapshot?.document?.title || publicDemo.title }}</strong>
          <span>{{ store.snapshot ? store.snapshot.document.author || '作者未提供' : publicDemo.authorLabel }}</span>
          <small>{{ store.snapshot ? store.snapshot.document.version_label || '版本未提供 · 私人文本' : '公开演示 · 原文受限' }}</small>
        </div>
        <button v-if="store.isSampleWorkspace" class="xr-boundary-trigger" type="button"
                :aria-expanded="boundaryOpen" @click="boundaryOpen = !boundaryOpen">来源边界</button>
      </div>

      <div class="xr-meta">
        <span>{{ store.snapshot ? `${store.snapshot.document.paragraph_count} 个段落锚点 · 无伪页码` : publicWindowLabel }}</span>
        <div role="group" aria-label="阅读器视图">
          <button :class="{ active: store.readerView === 'text' }" @click="store.setReaderView('text')">{{ store.isSampleWorkspace ? '窗口' : '正文' }}</button>
          <button :class="{ active: store.readerView === 'anchors' }" @click="store.setReaderView('anchors')">锚点</button>
        </div>
      </div>

      <section v-if="store.isSampleWorkspace && boundaryOpen" class="xr-boundary" role="dialog" aria-label="公开来源边界">
        <button type="button" aria-label="关闭来源边界" @click="boundaryOpen = false">关闭</button>
        <strong>公开阅读窗口</strong>
        <p>{{ publicWindowLabel }}。这是本次 Demo 的产品展示上限，不是法律安全线。</p>
        <small>九个锚点仅含原创衍生摘要与公开章节级定位；源正文、私有 locator 与原文件均未下发。</small>
      </section>

      <div v-if="store.snapshot" class="xr-progress" :aria-label="`阅读进度 ${Math.round(store.readingProgress)}%`">
        <i :style="{ width: `${store.readingProgress}%` }"></i>
        <span>{{ Math.round(store.readingProgress) }}%</span>
      </div>

      <div v-if="store.snapshot && store.readerView === 'text'" class="xr-chapter-bar">
        <button :disabled="activeSectionIndex === 0" aria-label="上一章" @click="setSection(activeSectionIndex - 1)"><ChevronLeft :size="13" /></button>
        <select v-model.number="activeSectionIndex" aria-label="选择章节" @change="onSectionChange">
          <option v-for="(section, index) in store.importedSections" :key="section.id" :value="index">{{ section.title || `第 ${index + 1} 节` }}</option>
        </select>
        <button :disabled="activeSectionIndex >= store.importedSections.length - 1" aria-label="下一章" @click="setSection(activeSectionIndex + 1)"><ChevronRight :size="13" /></button>
      </div>

      <div v-if="store.readerView === 'text'" ref="pagesRef" class="xr-pages" @scroll.passive="onReaderScroll">
        <template v-if="store.snapshot">
          <section v-if="activeSection" class="xr-section" :data-section-id="activeSection.id">
            <h3>{{ activeSection.title || `第 ${activeSectionIndex + 1} 节` }}</h3>
            <button v-for="paragraph in activeSection.paragraphs" :key="paragraph.id"
                    :id="`anchor-${paragraph.id}`" :data-anchor-id="paragraph.id"
                    :class="{ active: store.selectedAnchorId === paragraph.id }"
                    @click="selectAnchor(paragraph.id, true)">
              <p>{{ paragraph.text }}</p><small>段落锚点 {{ paragraph.ordinal + 1 }} · 页码未知</small>
            </button>
          </section>
        </template>
        <article v-else v-for="(anchor, index) in publicAnchors" :key="anchor.id"
                 :id="`anchor-${anchor.id}`" :data-anchor-id="anchor.id"
                 :data-access-state="anchor.accessState"
                 class="xr-public-anchor"
                 :class="{ active: index === store.paragraphIndex }">
          <button class="xr-public-anchor-trigger" type="button"
                  :aria-expanded="index === store.paragraphIndex"
                  :aria-controls="`public-anchor-detail-${anchor.id}`"
                  @click="selectPublicAnchor(anchor, index)">
            <small>{{ anchor.locatorLabel }} · {{ anchor.time }}</small>
            <strong>{{ anchor.derivedSummary }}</strong>
            <span>{{ index === store.paragraphIndex ? '定位已展开' : '查看来源说明' }}</span>
          </button>
          <section v-if="index === store.paragraphIndex"
                   :id="`public-anchor-detail-${anchor.id}`"
                   class="xr-public-anchor-detail" role="region"
                   :aria-label="`${anchor.locatorLabel}来源说明`">
            <dl>
              <div><dt>章节定位</dt><dd>{{ anchor.locatorLabel }}</dd></div>
              <div><dt>原创衍生摘要</dt><dd>{{ anchor.derivedSummary }}</dd></div>
              <div><dt>核心论点</dt><dd>{{ anchor.claim }}</dd></div>
            </dl>
            <p><strong>访问边界 · 原文未公开</strong>源正文、私有 locator 与原文件未下发；此处只提供公开章节级导航与原创衍生内容。</p>
            <button class="xr-copy-locator" type="button" @click="copyPublicLocator(anchor)">
              <Copy :size="12" />复制章节定位
            </button>
            <span v-if="copyStatusFor(anchor.id)" class="xr-copy-status" role="status" aria-live="polite">{{ copyStatusFor(anchor.id) }}</span>
          </section>
        </article>
      </div>

      <div v-else class="xr-anchors">
        <template v-if="store.snapshot">
          <section v-for="(section, sectionIndex) in store.importedSections" :key="section.id">
            <h3>{{ section.title || `第 ${sectionIndex + 1} 节` }}</h3>
            <button v-for="paragraph in section.paragraphs" :key="paragraph.id"
                    :class="{ active: store.selectedAnchorId === paragraph.id }"
                    @click="scrollToAnchor(paragraph.id, sectionIndex)">
              <span>{{ String(paragraph.ordinal + 1).padStart(2, '0') }}</span><strong>{{ paragraph.text.slice(0, 46) }}</strong><small>用户导入段落</small>
            </button>
          </section>
        </template>
        <button v-else v-for="(anchor, index) in publicAnchors" :key="anchor.id"
                :id="`anchor-${anchor.id}`" :data-anchor-id="anchor.id"
                :data-access-state="anchor.accessState"
                :class="{ active: index === store.paragraphIndex }" @click="returnToPublicAnchor(anchor, index)">
          <span>{{ String(index + 1).padStart(2, '0') }} · {{ anchor.time }}</span><strong>{{ anchor.claim }}</strong><small>{{ anchor.locatorLabel }} · 原文未公开</small>
        </button>
      </div>
    </div>

    <div v-else-if="store.sourceTab === 'web'" class="xr-web"
         :class="{ expanded: webSyncOpen }">
      <div class="xr-web-reader">
        <div class="xr-web-entry">
          <span class="xr-web-mark"><Globe :size="20" /></span>
          <strong>微信读书在 Chrome 顶层运行</strong>
          <p>伴读侧边栏只读取你主动选择的段落，并把它加入当前探索；不会后台读取正文。</p>
          <a class="xr-web-launch" href="https://weread.qq.com/" target="_blank" rel="noreferrer">
            打开微信读书 <ExternalLink :size="13" />
          </a>
        </div>
      </div>

      <button class="xr-sync-disclosure" type="button"
              :aria-expanded="webSyncOpen" aria-controls="xr-web-sync-panel"
              @click="toggleWebSync">
        同步阅读位置 <ChevronDown :size="13" :class="{ open: webSyncOpen }" />
      </button>
      <form v-if="webSyncOpen" id="xr-web-sync-panel" class="xr-web-bridge" @submit.prevent="syncWeb">
        <input v-model="webProgress" aria-label="微信读书阅读位置" placeholder="例如：第 3 章 · 42%" />
        <textarea v-model="webExcerpt" aria-label="粘贴微信读书段落" placeholder="可选：粘贴当前段落。只有你主动提交的文字会进入当前探索。"></textarea>
        <button type="submit" :disabled="store.syncingWeb || !webProgress.trim()">{{ store.syncingWeb ? '正在同步' : '同步' }}</button>
        <p v-if="store.snapshot?.external_reading_bridge">已同步：{{ store.webProgressLabel }} · 非自动实时联动</p>
      </form>
    </div>

    <div v-else class="xr-timeline">
      <header><span>共享 Scene</span><strong>{{ store.isSampleWorkspace ? publicDemo.range : '时间待确认' }}</strong></header>
      <p v-if="!store.isSampleWorkspace" class="xr-timeline-empty">尚未建立 Scene。问题与私人文本不会沿用示例书的时间、地点或关系。</p>
      <section v-else class="xr-time-axis" aria-label="安史之乱纵向年代轴" data-testid="exploration-time-axis">
        <div class="xr-time-legend" aria-hidden="true">
          <span><i class="scene"></i>主轨 · 书中 Scene</span>
          <span><i class="reference"></i>参照轨 · 仓库实体</span>
        </div>
        <div class="xr-time-head" aria-hidden="true">
          <span>年</span><strong>主轨</strong><strong>参照轨</strong>
        </div>
        <ol class="xr-time-rows" aria-label="755 至 763 年">
          <li v-for="row in timelineRows" :key="row.year"
              :data-year="row.year" :aria-label="`${row.year} 年`">
            <time :datetime="String(row.year)">{{ row.year }}</time>
            <div class="xr-scene-rail" role="group" :aria-label="`${row.year} 年 Scene 主轨`">
              <button v-for="scene in row.scenes" :key="scene.id"
                      type="button" :data-scene-id="scene.id"
                      :aria-label="`主轨 Scene：${scene.label}；${scene.date}；${scene.place || '无单一可靠地点'}`"
                      :aria-pressed="scene.id === store.selectedSceneId"
                      :class="{
                        active: scene.id === store.selectedSceneId,
                        visited: sceneIndex(scene.id) < store.sceneIndex,
                      }"
                      @click="selectPublicScene(sceneIndex(scene.id))">
                <i>{{ sceneIndex(scene.id) + 1 }}</i>
                <span><strong>{{ scene.label }}</strong><small>{{ scene.date }} · {{ scene.place || '无单一可靠地点' }}</small></span>
              </button>
            </div>
            <div class="xr-reference-rail" role="group" :aria-label="`${row.year} 年历史参照轨`">
              <button v-for="reference in row.references" :key="reference.id"
                      type="button"
                      :data-reference-id="reference.id"
                      :data-entity-id="reference.entityId"
                      :data-entity-type="reference.entityType"
                      :data-year="reference.year"
                      :aria-label="`参照轨：${reference.label}；${reference.year} 年；${reference.kind}`"
                      :aria-pressed="isReferenceSelected(reference)"
                      :class="{ active: isReferenceSelected(reference) }"
                      @click="selectTimelineReference(reference)">
                <small>{{ reference.kind }}</small><strong>{{ reference.label }}</strong>
              </button>
            </div>
          </li>
        </ol>
      </section>
    </div>
    <p v-if="store.apiError" class="xr-error" role="alert">{{ store.apiError }}</p>
  </aside>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import BookOpenText from '@lucide/vue/dist/esm/icons/book-open-text.mjs'
import BookUp from '@lucide/vue/dist/esm/icons/book-up.mjs'
import ChevronDown from '@lucide/vue/dist/esm/icons/chevron-down.mjs'
import ChevronLeft from '@lucide/vue/dist/esm/icons/chevron-left.mjs'
import ChevronRight from '@lucide/vue/dist/esm/icons/chevron-right.mjs'
import Copy from '@lucide/vue/dist/esm/icons/copy.mjs'
import ExternalLink from '@lucide/vue/dist/esm/icons/external-link.mjs'
import Globe from '@lucide/vue/dist/esm/icons/globe.mjs'
import ListTree from '@lucide/vue/dist/esm/icons/list-tree.mjs'
import MessagesSquare from '@lucide/vue/dist/esm/icons/messages-square.mjs'
import {
  ANSHI_PUBLIC_ANCHORS,
  ANSHI_PUBLIC_DEMO,
  ANSHI_PUBLIC_SCENES,
} from '../../data/anshiPublicDemo'
import {
  ANSHI_TIMELINE_REFERENCES,
  ANSHI_TIMELINE_YEARS,
} from '../../data/anshiTimelineReferences'
import { useExplorationStore } from '../../stores/useExplorationStore'
import { useSelectionStore } from '../../stores/useSelectionStore'
import { useTimeStore } from '../../stores/useTimeStore'

defineProps({ mobile: { type: Boolean, default: false } })
const store = useExplorationStore()
const selectionStore = useSelectionStore()
const timeStore = useTimeStore()
const publicDemo = ANSHI_PUBLIC_DEMO
const publicAnchors = ANSHI_PUBLIC_ANCHORS
const scenes = ANSHI_PUBLIC_SCENES
const pagesRef = ref(null)
const activeSectionIndex = ref(0)
const webSyncOpen = ref(false)
const webProgress = ref(store.webProgressLabel)
const webExcerpt = ref('')
const boundaryOpen = ref(false)
const copiedAnchorId = ref('')
const copyNotice = ref('')
let selectionSyncTimer = 0
let copyNoticeTimer = 0

const activeSection = computed(() => store.importedSections[activeSectionIndex.value] || null)
const publicWindowLabel = computed(
  () => `最多${publicDemo.publicPageWindow.maxPages}页，当前${publicDemo.publicPageWindow.publishedPages}页通过权利审查`,
)
const timelineRows = computed(() => ANSHI_TIMELINE_YEARS.map((year) => ({
  year,
  scenes: scenes.filter((scene) => scene.year === year),
  references: ANSHI_TIMELINE_REFERENCES.filter((reference) => reference.year === year),
})))

watch(() => store.snapshot?.id, () => {
  activeSectionIndex.value = 0
})
watch(() => store.selectedAnchorId, (id) => {
  if (!id || !store.snapshot) return
  const index = store.importedSections.findIndex((section) => section.paragraphs.some((paragraph) => paragraph.id === id))
  if (index >= 0 && index !== activeSectionIndex.value) activeSectionIndex.value = index
})
onMounted(() => {
  if (store.isSampleWorkspace) {
    const anchor = publicAnchors[store.paragraphIndex] || publicAnchors[0]
    selectPublicAnchor(anchor, publicAnchors.indexOf(anchor), { pause: false })
  }
})
onBeforeUnmount(() => {
  window.clearTimeout(selectionSyncTimer)
  window.clearTimeout(copyNoticeTimer)
})

function toggleWebSync() {
  webSyncOpen.value = !webSyncOpen.value
}

function globalParagraphIndex(id) {
  return store.importedParagraphRecord(id)?.globalIndex ?? -1
}
function selectPublicScene(index, { pause = true } = {}) {
  store.selectScene(index, { keepPlaying: !pause })
}
function sceneIndex(id) {
  return scenes.findIndex((scene) => scene.id === id)
}
function isReferenceSelected(reference) {
  return reference.entityId === selectionStore.selectedEntityId
    && reference.entityType === selectionStore.selectedEntityType
    && reference.year === timeStore.year
}
function selectTimelineReference(reference) {
  timeStore.requestNavigation({ year: reference.year, precision: 'year' })
  selectionStore.selectEntity(
    reference.entityId,
    reference.entityType,
    'explore-timeline-reference',
  )
}
function selectPublicAnchor(anchor, index, { pause = true } = {}) {
  if (!anchor) return
  store.selectParagraph(index, { keepPlaying: !pause })
}
function publicLocatorText(anchor) {
  return `${publicDemo.title} · ${anchor.locatorLabel}`
}
function copyStatusFor(anchorId) {
  return copiedAnchorId.value === anchorId ? copyNotice.value : ''
}
async function copyPublicLocator(anchor) {
  const value = publicLocatorText(anchor)
  try {
    await navigator.clipboard.writeText(value)
    copyNotice.value = '已复制章节定位'
  } catch {
    copyNotice.value = '复制失败，请手动记录章节定位'
  }
  copiedAnchorId.value = anchor.id
  window.clearTimeout(copyNoticeTimer)
  copyNoticeTimer = window.setTimeout(() => {
    if (copiedAnchorId.value === anchor.id) {
      copiedAnchorId.value = ''
      copyNotice.value = ''
    }
  }, 2200)
}
async function returnToPublicAnchor(anchor, index) {
  store.setReaderView('text')
  selectPublicAnchor(anchor, index)
  await nextTick()
  document.getElementById(`anchor-${anchor.id}`)?.scrollIntoView({ block: 'center' })
}
function updateProgressFor(id) {
  const index = globalParagraphIndex(id)
  if (index >= 0 && store.importedParagraphCount) {
    store.setReadingProgress(((index + 1) / store.importedParagraphCount) * 100)
  }
}
function selectAnchor(id, sync) {
  store.selectImportedAnchor(id, { sync })
  updateProgressFor(id)
}
function onReaderScroll(event) {
  if (!store.snapshot) return
  const root = event.currentTarget
  const candidates = [...root.querySelectorAll('[data-anchor-id]')]
  if (!candidates.length) return
  const rootTop = root.getBoundingClientRect().top
  const target = candidates.reduce((best, node) => {
    const distance = Math.abs(node.getBoundingClientRect().top - rootTop - 20)
    return !best || distance < best.distance ? { node, distance } : best
  }, null)?.node
  const id = target?.dataset.anchorId
  if (id && id !== store.selectedAnchorId) {
    store.selectImportedAnchor(id, { sync: false })
    window.clearTimeout(selectionSyncTimer)
    selectionSyncTimer = window.setTimeout(() => {
      if (store.selectedAnchorId === id) store.selectImportedAnchor(id, { sync: true })
    }, 450)
  }
  const firstId = activeSection.value?.paragraphs?.[0]?.id
  const sectionStart = Math.max(0, globalParagraphIndex(firstId))
  const sectionLength = activeSection.value?.paragraphs?.length || 0
  const scrollRange = Math.max(1, root.scrollHeight - root.clientHeight)
  const sectionFraction = Math.max(0, Math.min(1, root.scrollTop / scrollRange))
  store.setReadingProgress(((sectionStart + sectionLength * sectionFraction) / store.importedParagraphCount) * 100)
}
function setSection(index) {
  const bounded = Math.max(0, Math.min(store.importedSections.length - 1, index))
  activeSectionIndex.value = bounded
  const id = store.importedSections[bounded]?.paragraphs?.[0]?.id
  if (id) {
    selectAnchor(id, true)
    nextTick(() => { if (pagesRef.value) pagesRef.value.scrollTop = 0 })
  }
}
function onSectionChange() { setSection(activeSectionIndex.value) }
function scrollToAnchor(id, sectionIndex) {
  activeSectionIndex.value = sectionIndex
  store.setReaderView('text')
  selectAnchor(id, true)
  nextTick(() => document.getElementById(`anchor-${id}`)?.scrollIntoView({ block: 'center' }))
}
async function syncWeb() {
  await store.syncWebReading({ progressLabel: webProgress.value, excerpt: webExcerpt.value })
}
</script>

<style scoped>
.xr{height:100%;min-width:0;display:grid;grid-template-rows:43px minmax(0,1fr) auto;overflow:hidden;background:var(--paper-el)}
.xr-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;padding:5px;border-bottom:1px solid var(--line)}.xr-tabs button{min-width:0;display:flex;align-items:center;justify-content:center;gap:4px;padding:5px 3px;border:0;background:transparent;color:var(--ink-soft);font-size:10px}.xr-tabs button.active{background:var(--chip);color:var(--accent)}
.xr-body{position:relative;min-height:0;display:flex;flex-direction:column;overflow:hidden}.xr-book{display:flex;align-items:flex-start;gap:9px;padding:12px;border-bottom:1px solid var(--line)}.xr-seal{width:36px;height:44px;display:grid;place-items:center;flex:none;border-radius:5px;background:var(--accent);color:var(--accent-text);font-family:var(--serif);font-weight:800}.xr-book div{min-width:0;display:grid;gap:2px;flex:1}.xr-book strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--serif);font-size:12px}.xr-book span,.xr-book small{color:var(--ink-soft);font-size:9px}.xr-boundary-trigger{flex:none;padding:4px 6px;border-color:var(--line);background:transparent;color:var(--ink-soft);font-size:8px}
.xr-question{display:grid;align-content:center;justify-items:start;gap:9px;padding:22px;color:var(--ink-soft)}.xr-question>svg{color:var(--accent)}.xr-question small{font-size:8px}.xr-question h2{margin:0;color:var(--ink);font-family:var(--serif);font-size:17px;line-height:1.55}.xr-question p{margin:0;font-size:10px;line-height:1.75}.xr-question button{display:flex;align-items:center;gap:5px}
.xr-meta{display:flex;align-items:center;justify-content:space-between;gap:5px;padding:7px 9px;border-bottom:1px solid var(--line);color:var(--ink-soft);font-size:8px}.xr-meta div{display:flex;gap:2px}.xr-meta button{padding:3px 5px;border:0;background:transparent;font-size:8px}.xr-meta button.active{color:var(--accent);background:var(--chip)}
.xr-boundary{position:absolute;z-index:8;top:76px;left:9px;right:9px;display:grid;gap:6px;padding:11px;border:1px solid var(--accent);border-radius:7px;background:var(--paper-el);box-shadow:0 7px 24px rgba(0,0,0,.16)}.xr-boundary>button{position:absolute;right:6px;top:6px;padding:3px 5px;border:0;background:transparent;color:var(--ink-soft);font-size:8px}.xr-boundary strong{font-family:var(--serif);font-size:11px}.xr-boundary p{margin:0;padding-right:30px;color:var(--ink-mid);font-size:9px;line-height:1.65}.xr-boundary small{color:var(--ink-soft);font-size:8px;line-height:1.55}
.xr-progress{position:relative;height:14px;flex:none;background:var(--field)}.xr-progress i{position:absolute;left:0;top:0;bottom:0;background:color-mix(in srgb,var(--accent) 45%,transparent);transition:width .18s}.xr-progress span{position:absolute;right:5px;top:1px;color:var(--ink-soft);font-size:7px}
.xr-chapter-bar{display:grid;grid-template-columns:26px minmax(0,1fr) 26px;gap:3px;padding:5px 8px;border-bottom:1px solid var(--line)}.xr-chapter-bar button{width:26px;height:26px;display:grid;place-items:center;padding:0}.xr-chapter-bar select{min-width:0;height:26px;padding:0 5px;font-size:9px}
.xr-pages,.xr-anchors,.xr-timeline{min-height:0;overflow:auto;padding:9px}.xr-section>h3,.xr-anchors section>h3{position:sticky;top:-9px;z-index:2;margin:0;padding:8px 4px;border-bottom:1px solid var(--line);background:var(--paper-el);font-family:var(--serif);font-size:11px}.xr-section>button{width:100%;display:block;padding:10px;border:0;border-bottom:1px solid var(--hair);background:transparent;text-align:left}.xr-section button.active{background:var(--chip)}.xr-pages p{font-family:var(--serif);font-size:11px;line-height:1.9}.xr-pages small{display:block;margin-top:6px;color:var(--ink-faint);font-size:8px}
.xr-public-anchor{display:grid;border-bottom:1px solid var(--hair);background:transparent}.xr-public-anchor.active{background:var(--chip)}.xr-public-anchor-trigger{width:100%;display:grid;gap:6px;padding:10px;border:0;background:transparent;text-align:left}.xr-public-anchor-trigger>small{margin:0}.xr-public-anchor-trigger>strong{font-family:var(--serif);font-size:11px;line-height:1.7}.xr-public-anchor-trigger>span{width:max-content;padding:2px 5px;border-radius:4px;background:var(--field);color:var(--ink-soft);font-size:8px}.xr-public-anchor.active .xr-public-anchor-trigger>span{background:color-mix(in srgb,var(--accent) 12%,var(--field));color:var(--accent)}
.xr-public-anchor-detail{display:grid;gap:9px;margin:0 10px 10px;padding:10px;border:1px solid var(--line);border-radius:6px;background:var(--paper-el)}.xr-public-anchor-detail dl{display:grid;gap:8px;margin:0}.xr-public-anchor-detail dl>div{display:grid;gap:3px}.xr-public-anchor-detail dt{color:var(--ink-faint);font-size:8px}.xr-public-anchor-detail dd{margin:0;color:var(--ink-mid);font-family:var(--serif);font-size:10px;line-height:1.65}.xr-public-anchor-detail p{display:grid;gap:3px;margin:0;padding-top:8px;border-top:1px solid var(--hair);color:var(--ink-soft);font-family:var(--sans);font-size:8px;line-height:1.65}.xr-public-anchor-detail p>strong{color:var(--ink-mid);font-size:8px}.xr-copy-locator{width:max-content;display:flex;align-items:center;gap:4px;padding:6px 8px;border-color:var(--line);background:transparent;color:var(--ink-mid);font-size:8px}.xr-copy-status{min-height:12px;color:var(--success);font-size:8px}
.xr-anchors button{width:100%;display:grid;gap:4px;padding:9px;text-align:left;border:0;border-bottom:1px solid var(--hair);background:transparent}.xr-anchors button.active{background:var(--chip)}.xr-anchors span,.xr-anchors small{color:var(--ink-faint);font-size:8px}.xr-anchors strong{font-size:10px;line-height:1.5}
.xr-web{min-height:0;display:grid;grid-template-rows:minmax(0,1fr) auto;overflow:hidden;padding:9px}.xr-web.expanded{grid-template-rows:minmax(180px,.72fr) auto minmax(0,1fr)}.xr-web-reader{height:100%;min-height:0;padding:6px;border:1px solid var(--line);border-radius:7px;background:var(--paper);overflow:hidden}.xr-web-entry{height:100%;display:grid;place-content:center;justify-items:center;gap:8px;padding:18px;text-align:center}.xr-web-entry strong{font-family:var(--serif);font-size:13px}.xr-web-entry p{max-width:250px;margin:0;color:var(--ink-soft);font-size:9px;line-height:1.65}.xr-web-mark{width:38px;height:38px;display:grid;place-items:center;border-radius:10px;background:var(--chip);color:var(--accent)}.xr-web-launch{display:flex;align-items:center;justify-content:center;gap:5px;min-width:146px;padding:8px 11px;border-radius:5px;background:var(--accent);color:var(--accent-text);font-size:9px}.xr-sync-disclosure{display:flex;align-items:center;justify-content:space-between;padding:8px 9px;background:transparent;color:var(--ink-mid);font-size:9px}.xr-sync-disclosure svg{transition:transform .16s}.xr-sync-disclosure svg.open{transform:rotate(180deg)}.xr-web-bridge{min-height:0;align-content:start;display:grid;gap:6px;overflow:auto;padding:10px;border:1px solid var(--line);border-radius:7px;background:var(--paper)}.xr-web-bridge textarea{min-height:72px;resize:vertical;padding:7px;border:1px solid var(--line);border-radius:4px;background:var(--paper-el);color:var(--ink);font:inherit;font-size:9px}.xr-web-bridge p{margin:0;color:var(--success);font-size:8px}
.xr-timeline header{display:flex;justify-content:space-between;padding:4px 6px 8px;color:var(--ink-soft);font-size:9px}.xr-time-axis{min-width:280px}.xr-time-legend{display:flex;gap:10px;padding:0 6px 9px;border-bottom:1px solid var(--hair);color:var(--ink-soft);font-size:7px}.xr-time-legend span{display:flex;align-items:center;gap:4px}.xr-time-legend i{width:7px;height:7px;border-radius:50%}.xr-time-legend i.scene{background:var(--accent)}.xr-time-legend i.reference{border:1px solid var(--ink-faint);background:var(--paper-el)}.xr-time-head{position:sticky;top:-9px;z-index:4;display:grid;grid-template-columns:32px minmax(120px,1fr) minmax(92px,.72fr);gap:7px;padding:7px 5px;border-bottom:1px solid var(--line);background:var(--paper-el);color:var(--ink-faint);font-size:7px;letter-spacing:.08em}.xr-time-head strong{font:inherit}.xr-time-rows{margin:0;padding:0;list-style:none}.xr-time-rows>li{position:relative;display:grid;grid-template-columns:32px minmax(120px,1fr) minmax(92px,.72fr);gap:7px;min-height:54px;padding:7px 5px}.xr-time-rows>li:not(:last-child){border-bottom:1px solid var(--hair)}.xr-time-rows>li>time{position:relative;z-index:2;padding-top:5px;color:var(--ink-soft);font-family:var(--serif);font-size:9px;font-variant-numeric:tabular-nums}.xr-time-rows>li>time::after{content:'';position:absolute;top:10px;right:-7px;width:7px;height:1px;background:var(--line)}.xr-scene-rail,.xr-reference-rail{position:relative;display:grid;align-content:start;gap:5px;padding-left:9px}.xr-scene-rail::before,.xr-reference-rail::before{content:'';position:absolute;top:-7px;bottom:-8px;left:0;width:1px;background:var(--line)}.xr-time-rows>li:first-child .xr-scene-rail::before,.xr-time-rows>li:first-child .xr-reference-rail::before{top:10px}.xr-time-rows>li:last-child .xr-scene-rail::before,.xr-time-rows>li:last-child .xr-reference-rail::before{bottom:calc(100% - 11px)}.xr-scene-rail>button,.xr-reference-rail>button{position:relative;width:100%;border:0;border-radius:5px;text-align:left}.xr-scene-rail>button::before,.xr-reference-rail>button::before{content:'';position:absolute;left:-12px;top:10px;width:6px;height:6px;border:1px solid var(--line);border-radius:50%;background:var(--paper-el)}.xr-scene-rail>button{display:grid;grid-template-columns:18px minmax(0,1fr);gap:6px;padding:6px;background:transparent}.xr-scene-rail>button>i{width:18px;height:18px;display:grid;place-items:center;border:1px solid var(--line);border-radius:50%;font-size:7px;font-style:normal}.xr-scene-rail>button>span{min-width:0;display:grid;gap:2px}.xr-scene-rail strong{font-size:9px;line-height:1.45}.xr-scene-rail small{color:var(--ink-soft);font-size:7px;line-height:1.4}.xr-scene-rail>button.active{background:var(--chip)}.xr-scene-rail>button.active::before,.xr-scene-rail>button.active>i{border-color:var(--accent);background:var(--accent);color:var(--accent-text)}.xr-scene-rail>button.visited::before{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 35%,var(--paper-el))}.xr-reference-rail>button{display:grid;gap:2px;padding:6px;background:var(--field)}.xr-reference-rail>button::before{width:5px;height:5px;top:9px;background:var(--paper-el)}.xr-reference-rail>button small{color:var(--ink-faint);font-size:7px}.xr-reference-rail>button strong{font-size:8px;line-height:1.4}.xr-reference-rail>button.active{box-shadow:inset 0 0 0 1px var(--accent);color:var(--accent)}.xr-reference-rail>button.active::before{border-color:var(--accent);background:var(--accent)}.xr-scene-rail>button:focus-visible,.xr-reference-rail>button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.xr-timeline-empty{padding:16px 8px;color:var(--ink-soft);font-size:10px;line-height:1.75}.xr-error{padding:7px 9px;color:var(--danger);background:var(--chip);font-size:9px}
</style>
