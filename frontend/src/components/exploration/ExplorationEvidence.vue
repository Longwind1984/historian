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
        <section class="xe-analysis" data-testid="analysis-run-panel">
          <template v-if="activeRun">
            <header>
              <div><small>深度分析</small><strong>{{ runState.label }}</strong></div>
              <button type="button" :disabled="store.analysisRefreshing" aria-label="刷新分析状态" @click="store.refreshActiveAnalysisRun()"><RefreshCw :size="13" /></button>
            </header>
            <div class="xe-analysis-progress" :aria-label="`分析进度 ${succeededWorkItems} / ${totalWorkItems}`">
              <i :style="{ width: `${workProgress}%` }"></i>
            </div>
            <p>{{ runState.copy }}</p>
            <small>{{ succeededWorkItems }} / {{ totalWorkItems }} 个工作项完成</small>
            <template v-if="analysisResult">
              <div class="xe-quality">
                <strong>质量门</strong>
                <span :class="{ failed: blockingGateFailures }">{{ blockingGateFailures ? `${blockingGateFailures} 项阻断` : '已通过' }}</span>
                <small>{{ analysisResult.quality_report.claim_count }} 条 Claim · {{ analysisResult.quality_report.event_count }} 个事件 · {{ analysisResult.quality_report.gap_count }} 个缺口</small>
              </div>
              <details v-if="analysisResult.quality_report.gates?.length" class="xe-quality-detail">
                <summary>查看质量门</summary>
                <p v-for="gate in analysisResult.quality_report.gates" :key="gate.code"><b>{{ gate.passed ? '通过' : gate.blocking ? '阻断' : '提醒' }}</b>{{ gate.detail }}</p>
              </details>
              <details v-if="analysisResult.artifacts.gaps?.length" class="xe-quality-detail">
                <summary>证据缺口 · {{ analysisResult.artifacts.gaps.length }}</summary>
                <p v-for="gap in analysisResult.artifacts.gaps" :key="gap.id"><b>{{ gap.code }}</b>{{ gap.detail }}</p>
              </details>
              <div v-if="activeRun.state === 'waiting_review' && !analysisResult.review_submitted" class="xe-review">
                <header><strong>逐项复核</strong><small>{{ decidedCandidateCount }} / {{ candidateItems.length }}</small></header>
                <article v-for="item in candidateItems" :key="`${item.artifact_type}:${item.id}`">
                  <small>{{ item.artifact_type === 'claim' ? claimKindLabel(item.kind) : '事件候选' }}</small>
                  <strong>{{ item.artifact_type === 'claim' ? item.statement : item.title }}</strong>
                  <p v-if="item.artifact_type === 'event'">{{ item.summary }}</p>
                  <span v-if="item.source_anchor_ids?.length">{{ item.source_anchor_ids.length }} 个原文锚点</span>
                  <div>
                    <button type="button" :class="{ active: decisionFor(item) === 'accepted' }" :aria-pressed="decisionFor(item) === 'accepted'" :aria-label="`接受${candidateName(item)}`" @click="store.setAnalysisReviewDecision(item.artifact_type, item.id, 'accepted')">接受</button>
                    <button type="button" :class="{ active: decisionFor(item) === 'rejected' }" :aria-pressed="decisionFor(item) === 'rejected'" :aria-label="`拒绝${candidateName(item)}`" @click="store.setAnalysisReviewDecision(item.artifact_type, item.id, 'rejected')">拒绝</button>
                  </div>
                </article>
                <p v-if="!candidateItems.length" class="xe-review-empty">此轮只产生证据缺口，没有可采纳候选。</p>
                <p v-if="store.reviewDependencyError" class="xe-review-empty">{{ store.reviewDependencyError }}</p>
                <button type="button" class="xe-review-submit" :disabled="!store.reviewReady || store.analysisAction === 'reviewing'" @click="store.submitAnalysisReview()">{{ candidateItems.length ? '提交复核' : '确认无候选并继续' }}</button>
              </div>
              <p v-else-if="analysisResult.review_submitted && activeRun.state !== 'completed'" class="xe-review-wait">复核已提交，等待 worker 应用决定。</p>
              <section v-if="activeRun.state === 'completed'" class="xe-published">
                <header><strong>已发布投影</strong><small>{{ publishedTotal }} 项</small></header>
                <nav aria-label="分析投影">
                  <button v-for="item in publishedViews" :key="item.id" type="button" :class="{ active: store.publishedAnalysisView === item.id }" @click="store.publishedAnalysisView = item.id">{{ item.label }} {{ item.count }}</button>
                </nav>
                <div class="xe-published-list">
                  <p v-for="item in activePublishedItems.slice(0, 8)" :key="item.id"><strong>{{ publishedItemTitle(item) }}</strong><small>{{ publishedItemMeta(item) }}</small></p>
                  <small v-if="!activePublishedItems.length">该投影暂无已采纳项。</small>
                </div>
              </section>
            </template>
            <div v-if="store.canCancelAnalysis || store.canResumeAnalysis" class="xe-analysis-actions">
              <button v-if="store.canCancelAnalysis" type="button" :disabled="Boolean(store.analysisAction)" @click="store.cancelAnalysisRun()">取消</button>
              <button v-if="store.canResumeAnalysis" type="button" :disabled="Boolean(store.analysisAction)" @click="store.resumeAnalysisRun()">恢复</button>
            </div>
          </template>
          <template v-else>
            <div><small>深度分析</small><strong>尚未开始</strong></div>
            <p>建立可恢复的分析计划，结果经复核后才会进入论证、时间与地图。</p>
            <button type="button" class="xe-analysis-start" :disabled="store.analysisAction === 'creating'" @click="store.createAnalysisRun()">{{ store.analysisAction === 'creating' ? '正在创建' : '开始深度分析' }}</button>
          </template>
          <span v-if="store.analysisError" role="alert">{{ store.analysisError }}</span>
        </section>
        <p v-if="!activeRun" class="xe-empty-relation"><Info :size="15" />运行分析后，关系候选仍需复核才会出现。</p>
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
import RefreshCw from '@lucide/vue/dist/esm/icons/refresh-cw.mjs'
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
const activeRun = computed(() => store.activeAnalysisRun)
const analysisResult = computed(() => store.analysisResult)
const candidateItems = computed(() => store.analysisCandidateItems)
const decidedCandidateCount = computed(() => candidateItems.value.filter((item) => decisionFor(item)).length)
const totalWorkItems = computed(() => activeRun.value?.work_items?.length || 0)
const succeededWorkItems = computed(() => activeRun.value?.work_items?.filter((item) => item.state === 'succeeded').length || 0)
const workProgress = computed(() => totalWorkItems.value
  ? Math.round((succeededWorkItems.value / totalWorkItems.value) * 100)
  : 0)
const runState = computed(() => ({
  planned: { label: '计划已建立', copy: '正在等待工作项入队。' },
  queued: { label: '排队中', copy: '任务已入队，等待独立 worker 处理。' },
  running: { label: '分析中', copy: '工作项正在按计划执行。' },
  retry_wait: { label: '等待重试', copy: '可恢复错误已隔离，系统将重试未完成工作项。' },
  paused: { label: '已暂停', copy: '已保留检查点，尚未继续执行。' },
  waiting_review: { label: '待复核', copy: '候选结果已生成；尚未人工接受，不会自动写入工作台。' },
  waiting_input: { label: '待补充', copy: '缺少继续分析所需的范围或来源。' },
  failed: { label: '分析失败', copy: '运行已停止；错误未被隐藏或伪装为结果。' },
  cancelled: { label: '已取消', copy: '已保留完成项与检查点，可从原计划恢复。' },
  completed: { label: '已完成', copy: '计划中的工作项已完成。' },
}[activeRun.value?.state] || { label: '状态未知', copy: '请刷新运行状态。' }))
const blockingGateFailures = computed(() => analysisResult.value?.quality_report?.gates
  ?.filter((gate) => gate.blocking && !gate.passed).length || 0)
const publishedViews = computed(() => {
  const projections = analysisResult.value?.published_projections
  return [
    { id: 'argument', label: '论证', count: projections?.argument?.nodes?.length || 0 },
    { id: 'timeline', label: '时间', count: projections?.timeline?.items?.length || 0 },
    { id: 'map', label: '地图', count: projections?.map?.points?.length || 0 },
    { id: 'insights', label: '洞见', count: projections?.insights?.items?.length || 0 },
  ]
})
const publishedTotal = computed(() => publishedViews.value.reduce((sum, item) => sum + item.count, 0))
const activePublishedItems = computed(() => {
  const projections = analysisResult.value?.published_projections
  if (!projections) return []
  if (store.publishedAnalysisView === 'argument') return projections.argument?.nodes || []
  if (store.publishedAnalysisView === 'timeline') return projections.timeline?.items || []
  if (store.publishedAnalysisView === 'map') return projections.map?.points || []
  return projections.insights?.items || []
})

function decisionFor(item) {
  return store.analysisReviewDecisions[`${item.artifact_type}:${item.id}`] || ''
}
function candidateName(item) {
  const text = item.artifact_type === 'claim' ? item.statement : item.title
  return String(text || '候选').slice(0, 36)
}
function claimKindLabel(kind) {
  return ({
    source_statement: '原文陈述',
    author_judgment: '作者判断',
    platform_inference: '平台推断',
    external_evidence: '外部材料',
  })[kind] || 'Claim 候选'
}
function publishedItemTitle(item) {
  return item.statement || item.title || item.label || item.id
}
function publishedItemMeta(item) {
  if (item.epistemic_layer) return claimKindLabel(item.epistemic_layer)
  if (item.original_time_labels?.length) return item.original_time_labels.join(' · ')
  if (Number.isFinite(item.longitude) && Number.isFinite(item.latitude)) return `${item.longitude.toFixed(2)}, ${item.latitude.toFixed(2)}`
  return item.review_status || ''
}

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
.xe-analysis{display:grid;gap:7px;margin-top:8px;padding:10px;border:1px solid var(--line);border-radius:7px;background:var(--paper)}.xe-analysis>header{display:flex;align-items:center;justify-content:space-between}.xe-analysis>header>div,.xe-analysis>div:first-child{display:grid;gap:3px}.xe-analysis small{color:var(--ink-faint);font-size:8px}.xe-analysis strong{font-family:var(--serif);font-size:11px}.xe-analysis p{margin:0;color:var(--ink-mid);font-size:9px;line-height:1.6}.xe-analysis>header button{width:27px;height:27px;display:grid;place-items:center;padding:0}.xe-analysis-progress{height:3px;overflow:hidden;border-radius:3px;background:var(--hair)}.xe-analysis-progress i{display:block;height:100%;background:var(--accent);transition:width .2s ease}.xe-analysis-actions{display:flex;gap:5px}.xe-analysis-actions button,.xe-analysis-start{padding:6px 8px;font-size:8px}.xe-analysis-start{background:var(--accent);color:var(--accent-text);border-color:var(--accent)}.xe-analysis>span[role=alert]{color:var(--danger,var(--accent));font-size:8px}
.xe-quality{display:grid;grid-template-columns:1fr auto;gap:3px 6px;padding:7px;border-radius:5px;background:var(--chip)}.xe-quality>span{color:var(--success);font-size:8px}.xe-quality>span.failed{color:var(--accent)}.xe-quality>small{grid-column:1/-1}.xe-quality-detail{border-top:1px solid var(--hair);padding-top:5px}.xe-quality-detail summary{cursor:pointer;color:var(--ink-soft);font-size:8px}.xe-quality-detail p{display:grid;grid-template-columns:42px 1fr;gap:5px;margin-top:5px;font-size:8px}.xe-quality-detail b{color:var(--accent);font-size:7px}.xe-review{display:grid;gap:7px;padding-top:7px;border-top:1px solid var(--line)}.xe-review>header,.xe-published>header{display:flex;justify-content:space-between;align-items:center}.xe-review article{display:grid;gap:5px;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--paper-el)}.xe-review article>small{color:var(--accent)}.xe-review article>strong{font-size:9px;line-height:1.5}.xe-review article>span{color:var(--ink-faint);font-size:7px}.xe-review article>div{display:flex;gap:5px}.xe-review article button{flex:1;padding:5px;font-size:8px}.xe-review article button.active{border-color:var(--accent);background:var(--chip);color:var(--accent)}.xe-review-submit{padding:7px;background:var(--accent);color:var(--accent-text);border-color:var(--accent);font-size:8px}.xe-review-empty,.xe-review-wait{padding:7px;border:1px dashed var(--line);border-radius:5px}.xe-published{display:grid;gap:7px;padding-top:7px;border-top:1px solid var(--line)}.xe-published nav{display:grid;grid-template-columns:repeat(4,1fr);gap:3px}.xe-published nav button{padding:5px 2px;font-size:7px}.xe-published nav button.active{border-color:var(--accent);background:var(--chip);color:var(--accent)}.xe-published-list{display:grid;gap:4px}.xe-published-list>p{display:grid;gap:2px;padding:6px;border-left:2px solid var(--line);background:var(--paper-el)}.xe-published-list strong{font-size:8px}.xe-published-list small{font-size:7px}
.xe-scope-contract{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px;padding:9px;border:1px solid var(--line);border-radius:6px;background:var(--paper)}.xe-scope-contract>small,.xe-scope-contract>strong{width:100%;font-size:8px}.xe-scope-contract>small{color:var(--ink-soft)}.xe-scope-contract>span{padding:3px 5px;border-radius:4px;background:var(--chip);color:var(--accent);font-size:8px}.xe-scope-contract>strong{margin-top:5px}.xe-scope-contract>p{width:100%;margin:0;color:var(--ink-mid);font-size:8px;line-height:1.55}.xe-scope-contract form{width:100%;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;margin:3px 0 5px}.xe-scope-contract label{display:grid;gap:3px;color:var(--ink-soft);font-size:7px}.xe-scope-contract input{min-width:0;height:27px;padding:5px;border:1px solid var(--line);border-radius:4px;background:var(--paper-el);color:var(--ink);font:inherit;font-size:8px}.xe-scope-contract form button{grid-column:1/-1;padding:6px;background:var(--accent);color:var(--accent-text);border-color:var(--accent);font-size:8px}
.xe-conclusion{display:flex;gap:5px;padding:8px;border:1px solid color-mix(in srgb,var(--success) 35%,var(--line));border-radius:6px;color:var(--success);font-size:9px}.xe-records{display:grid;gap:5px;margin-top:9px;padding-top:9px;border-top:1px solid var(--line)}.xe-records>strong{font-size:9px}.xe-records p{display:grid;gap:2px;padding:7px;background:var(--paper);font-size:9px}.xe-records small{color:var(--ink-faint);font-size:7px}
.xe-compose{position:relative;display:grid;grid-template-columns:32px minmax(0,1fr) 32px;gap:5px;padding:8px;border-top:1px solid var(--line)}.xe-compose>button{width:32px;height:32px;display:grid;place-items:center;padding:0;border-radius:50%}.xe-compose>button[type=submit]{background:var(--accent);color:var(--accent-text);border-color:var(--accent)}.xe-compose textarea{min-height:34px;max-height:78px;resize:vertical;padding:7px;border:1px solid var(--line);border-radius:7px;background:var(--paper);color:var(--ink);font:inherit;font-size:9px}.xe-compose>span{grid-column:1/-1;min-height:12px;color:var(--ink-soft);font-size:8px}
</style>
