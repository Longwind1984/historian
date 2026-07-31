<template>
  <aside class="xe">
    <header>关系化证据</header>
    <div class="xe-scroll">
      <template v-if="store.workspaceKind === 'document' && store.snapshot">
        <article class="xe-imported-state">
          <span>{{ store.selectedEvidenceAnchorId === 'web-bridge' ? '微信读书手动桥接' : '当前段落锚点' }}</span>
          <strong>{{ activeImportedParagraph ? `段落 ${activeImportedParagraph.ordinal + 1}` : store.selectedEvidenceAnchorId === 'web-bridge' ? '用户粘贴段落' : '尚未选择' }}</strong>
          <p>{{ store.selectedContextText || '从左侧选择一个导入段落。' }}</p>
          <small>页码未知 · 未生成证据关系 · 不自动套用示例书判断</small>
        </article>
        <p class="xe-empty-relation"><Info :size="15" />当前只记录问题与段落锚点；关系需由后续结构提议并经复核后出现。</p>
      </template>
      <template v-else-if="store.workspaceKind === 'question'">
        <article class="xe-imported-state">
          <span>用户问题</span>
          <strong>{{ store.questionSyncState === 'synced' ? '范围合同已建立' : '等待服务端建立范围' }}</strong>
          <p>{{ store.questionPrompt }}</p>
          <small>尚无材料 · 尚无证据关系 · 尚未生成历史结论</small>
        </article>
        <div v-if="store.snapshot?.scope_contract" class="xe-scope-contract">
          <small>待确认范围</small>
          <span v-for="field in store.snapshot.scope_contract.fields_needing_confirmation" :key="field">{{ scopeFieldLabel[field] || field }}</span>
          <p v-if="!store.snapshot.scope_contract.fields_needing_confirmation.length">时间、空间与叙事主线均已由用户明确提供。</p>
          <form @submit.prevent="submitScope">
            <label>时间<input v-model="scopeTime" aria-label="确认时间范围" placeholder="例如：1402—1424" /></label>
            <label>空间<input v-model="scopeGeography" aria-label="确认空间范围" placeholder="南京、北京" /></label>
            <label>主线<input v-model="scopeThreads" aria-label="确认叙事主线" placeholder="权力结构、军事进程" /></label>
            <button type="submit" :disabled="store.updatingScope || !hasScopeInput">{{ store.updatingScope ? '正在更新' : '确认范围' }}</button>
          </form>
          <strong>继续追问</strong>
          <p v-for="question in store.snapshot.scope_contract.starter_questions" :key="question">{{ question }}</p>
        </div>
        <p class="xe-empty-relation"><Info :size="15" />添加书籍或材料后，证据会围绕同一个问题和选中段落组织。</p>
      </template>
      <template v-else>
      <article v-if="store.isSampleWorkspace" class="xe-public-state">
        <span>当前公开定位</span>
        <strong>{{ activePublicAnchor.locatorLabel }}</strong>
        <p>{{ activePublicAnchor.claim }}</p>
        <small>原创衍生摘要 · 原文未公开 · 不把不同解释强行排列为正反</small>
      </article>
      <div class="xe-tabs" role="tablist" aria-label="证据透镜">
        <button v-for="item in lenses" :key="item" role="tab" :aria-selected="store.lens === item"
                :class="{ active: store.lens === item }" @click="store.lens = item">{{ item }}</button>
      </div>
      <div class="xe-key"><span v-for="item in relations" :key="item">{{ item }}</span></div>
      <button v-for="item in visibleEvidence" :key="item.id" class="xe-card"
              :class="{ selected: store.selectedEvidenceId === item.id }"
              :aria-pressed="store.selectedEvidenceId === item.id"
              @click="selectEvidence(item)">
        <span>{{ item.relation }}</span><strong>{{ item.title }}</strong><p>{{ item.copy }}</p>
        <small>{{ item.reviewed ? '关系已复核' : '关系待核' }}</small>
      </button>
      <p v-if="reviewedSelection" class="xe-conclusion"><Check :size="14" />所选关系已复核；层级差异不等于直接冲突。</p>
      </template>
      <div v-if="store.snapshot?.composer_entries?.length" class="xe-records">
        <strong>已记录问题</strong>
        <p v-for="entry in store.snapshot.composer_entries.slice(-3)" :key="entry.id">{{ entry.message }}<small>{{ entry.processing_status === 'recorded_no_llm' ? '仅记录，未调用模型' : entry.processing_status }}</small></p>
      </div>
    </div>
    <form v-if="!readonly && store.workspaceKind === 'document' && store.snapshot" class="xe-compose" @submit.prevent="store.submitComposer()">
      <button type="button" aria-label="添加材料" title="导入材料请使用左侧阅读器"><Plus :size="16" /></button>
      <textarea v-model="store.composerText" aria-label="向书籍与材料提问" placeholder="向已导入文本提问；本阶段仅记录，不调用模型"></textarea>
      <button type="submit" :disabled="store.composing" aria-label="记录问题"><Send :size="15" /></button>
      <span aria-live="polite">{{ store.composerNotice }}</span>
    </form>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import Check from '@lucide/vue/dist/esm/icons/check.mjs'
import Info from '@lucide/vue/dist/esm/icons/info.mjs'
import Plus from '@lucide/vue/dist/esm/icons/plus.mjs'
import Send from '@lucide/vue/dist/esm/icons/send.mjs'
import { ANSHI_PUBLIC_ANCHORS, ANSHI_PUBLIC_SCENES } from '../../data/anshiPublicDemo'
import { useExplorationStore } from '../../stores/useExplorationStore'
import { useTimeStore } from '../../stores/useTimeStore'

defineProps({ readonly: { type: Boolean, default: false } })
const store = useExplorationStore()
const timeStore = useTimeStore()
const lenses = ['历史结构', '材料互证', '不同解释']
const relations = ['互证', '补充', '层级不同', '直接冲突', '证据缺口']
if (!lenses.includes(store.lens)) store.lens = lenses[0]
const scopeTime = ref('')
const scopeGeography = ref('')
const scopeThreads = ref('')
const scopeFieldLabel = {
  time_range: '时间范围',
  geography: '空间范围',
  narrative_threads: '叙事主线',
}
const hasScopeInput = computed(() => Boolean(
  scopeTime.value.trim() || scopeGeography.value.trim() || scopeThreads.value.trim(),
))
const activePublicAnchor = computed(() =>
  ANSHI_PUBLIC_ANCHORS.find((anchor) => anchor.id === store.selectedEvidenceAnchorId)
  || ANSHI_PUBLIC_ANCHORS[store.paragraphIndex]
  || ANSHI_PUBLIC_ANCHORS[0])
const allEvidence = computed(() => {
  const anchor = activePublicAnchor.value
  const scene = ANSHI_PUBLIC_SCENES.find((item) => item.id === anchor.sceneId)
  return {
    历史结构: [
      {
        id: `structure-${anchor.id}`,
        anchorId: anchor.id,
        relation: '补充',
        title: anchor.thread,
        reviewed: false,
        copy: anchor.framework,
      },
      {
        id: `scene-${anchor.id}`,
        anchorId: anchor.id,
        relation: scene?.relation || '补充',
        title: scene?.label || anchor.place,
        reviewed: false,
        copy: scene?.detail || anchor.derivedSummary,
      },
    ],
    材料互证: [
      {
        id: `rights-${anchor.id}`,
        anchorId: anchor.id,
        relation: '证据缺口',
        title: '源正文仍待权利审查',
        reviewed: false,
        copy: `${anchor.locatorLabel} 已进入公开结构，但当前 0 页原文通过权利审查，不能显示为公众可核原文。`,
      },
      {
        id: 'independent-source-gap',
        anchorId: anchor.id,
        relation: '证据缺口',
        title: '独立材料尚未完成逐项绑定',
        reviewed: false,
        copy: '当前演示保留结构和来源边界，不用同一本书的重复表述冒充多源互证。',
      },
    ],
    不同解释: [
      {
        id: 'interpretation-levels',
        anchorId: anchor.id,
        relation: '层级不同',
        title: '制度结构、战场过程与历史记忆',
        reviewed: true,
        copy: '三种观察可以同时成立，回答的问题层级不同；差异本身不等于正反对立。',
      },
      {
        id: 'direct-conflict-gap',
        anchorId: anchor.id,
        relation: '证据缺口',
        title: '尚无同命题直接冲突材料',
        reviewed: false,
        copy: '只有材料对同一个 Claim 作出不可同时成立的判断时，才标直接冲突；当前不为填满面板制造反方。',
      },
    ],
  }
})
const visibleEvidence = computed(() => allEvidence.value[store.lens] || allEvidence.value[lenses[0]])
const reviewedSelection = computed(() => visibleEvidence.value.some((item) => item.id === store.selectedEvidenceId && item.reviewed))
const activeImportedParagraph = computed(() =>
  store.importedParagraphRecord(store.selectedEvidenceAnchorId)?.paragraph || null)

watch(() => store.snapshot?.scope_contract, (contract) => {
  if (!contract) return
  scopeTime.value = contract.time_range || ''
  scopeGeography.value = (contract.geography || []).join('、')
  scopeThreads.value = (contract.narrative_threads || []).join('、')
}, { immediate: true })

function splitScopeList(value) {
  return String(value || '').split(/[、,，\n]+/).map((item) => item.trim()).filter(Boolean)
}
async function submitScope() {
  await store.updateScopeContract({
    timeRange: scopeTime.value,
    geography: splitScopeList(scopeGeography.value),
    threads: splitScopeList(scopeThreads.value),
  })
}
function selectEvidence(item) {
  store.selectedEvidenceId = item.id
  if (!store.isSampleWorkspace || !item.anchorId) return
  const anchorIndex = ANSHI_PUBLIC_ANCHORS.findIndex((anchor) => anchor.id === item.anchorId)
  const anchor = ANSHI_PUBLIC_ANCHORS[anchorIndex]
  const sceneIndex = ANSHI_PUBLIC_SCENES.findIndex((scene) => scene.id === anchor.sceneId)
  if (sceneIndex < 0) return
  store.pause()
  store.sceneIndex = sceneIndex
  store.paragraphIndex = anchorIndex
  store.selectedSceneId = anchor.sceneId
  store.selectedAnchorId = anchor.id
  store.selectedEvidenceAnchorId = anchor.id
  store.thread = anchor.thread
  timeStore.requestNavigation({ exactYear: ANSHI_PUBLIC_SCENES[sceneIndex].year, month: null, precision: 'year' })
}
</script>

<style scoped>
.xe{height:100%;min-width:0;display:grid;grid-template-rows:44px minmax(0,1fr) auto;overflow:hidden;background:var(--paper-el)}
.xe>header{display:flex;align-items:center;padding:0 12px;border-bottom:1px solid var(--line);font-family:var(--serif);font-weight:800}
.xe-scroll{min-height:0;overflow:auto;padding:9px}.xe-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:3px}.xe-tabs button{padding:5px 2px;border:0;background:transparent;color:var(--ink-soft);font-size:9px}.xe-tabs button.active{color:var(--accent);background:var(--chip)}
.xe-key{display:flex;flex-wrap:wrap;gap:3px;padding:8px 0}.xe-key span{padding:2px 4px;border:1px solid var(--hair);border-radius:3px;color:var(--ink-faint);font-size:7px}
.xe-public-state{display:grid;gap:5px;margin-bottom:8px;padding:9px;border:1px solid var(--line);border-radius:7px;background:var(--paper)}.xe-public-state span,.xe-public-state small{color:var(--ink-faint);font-size:8px}.xe-public-state strong{font-family:var(--serif);font-size:11px}.xe-public-state p{margin:0;color:var(--ink-mid);font-size:9px;line-height:1.6}
.xe-card{width:100%;display:grid;gap:5px;margin-bottom:7px;padding:10px;text-align:left;background:var(--paper);border:1px solid var(--line);border-radius:7px}.xe-card.selected{border-color:var(--accent)}.xe-card>span{width:max-content;padding:2px 5px;border-radius:4px;background:var(--chip);color:var(--accent);font-size:8px}.xe-card strong{font-family:var(--serif);font-size:11px}.xe-card p{color:var(--ink-mid);font-size:9px;line-height:1.7}.xe-card small{color:var(--ink-faint);font-size:8px}
.xe-imported-state{display:grid;gap:6px;padding:11px;border:1px solid var(--line);border-radius:7px;background:var(--paper)}.xe-imported-state>span,.xe-imported-state>small{color:var(--ink-faint);font-size:8px}.xe-imported-state strong{font-family:var(--serif)}.xe-imported-state p{font-size:10px;line-height:1.7}.xe-empty-relation{display:flex;gap:6px;margin-top:8px;padding:9px;border:1px dashed var(--line);border-radius:6px;color:var(--ink-soft);font-size:9px;line-height:1.6}
.xe-scope-contract{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px;padding:9px;border:1px solid var(--line);border-radius:6px;background:var(--paper)}.xe-scope-contract>small,.xe-scope-contract>strong{width:100%;font-size:8px}.xe-scope-contract>small{color:var(--ink-soft)}.xe-scope-contract>span{padding:3px 5px;border-radius:4px;background:var(--chip);color:var(--accent);font-size:8px}.xe-scope-contract>strong{margin-top:5px}.xe-scope-contract>p{width:100%;margin:0;color:var(--ink-mid);font-size:8px;line-height:1.55}.xe-scope-contract form{width:100%;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;margin:3px 0 5px}.xe-scope-contract label{display:grid;gap:3px;color:var(--ink-soft);font-size:7px}.xe-scope-contract input{min-width:0;height:27px;padding:5px;border:1px solid var(--line);border-radius:4px;background:var(--paper-el);color:var(--ink);font:inherit;font-size:8px}.xe-scope-contract form button{grid-column:1/-1;padding:6px;background:var(--accent);color:var(--accent-text);border-color:var(--accent);font-size:8px}
.xe-conclusion{display:flex;gap:5px;padding:8px;border:1px solid color-mix(in srgb,var(--success) 35%,var(--line));border-radius:6px;color:var(--success);font-size:9px}.xe-records{display:grid;gap:5px;margin-top:9px;padding-top:9px;border-top:1px solid var(--line)}.xe-records>strong{font-size:9px}.xe-records p{display:grid;gap:2px;padding:7px;background:var(--paper);font-size:9px}.xe-records small{color:var(--ink-faint);font-size:7px}
.xe-compose{position:relative;display:grid;grid-template-columns:32px minmax(0,1fr) 32px;gap:5px;padding:8px;border-top:1px solid var(--line)}.xe-compose>button{width:32px;height:32px;display:grid;place-items:center;padding:0;border-radius:50%}.xe-compose>button[type=submit]{background:var(--accent);color:var(--accent-text);border-color:var(--accent)}.xe-compose textarea{min-height:34px;max-height:78px;resize:vertical;padding:7px;border:1px solid var(--line);border-radius:7px;background:var(--paper);color:var(--ink);font:inherit;font-size:9px}.xe-compose>span{grid-column:1/-1;min-height:12px;color:var(--ink-soft);font-size:8px}
</style>
