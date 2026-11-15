<template>
  <section class="explore" :class="{ 'entry-mode': store.entryOpen }" data-testid="exploration-workspace">
    <header class="explore-bar">
      <button v-if="PRIVATE_EXPLORATIONS_ENABLED && store.hasWorkspace && !store.entryOpen" class="back" @click="store.openEntry()"><ArrowLeft :size="14" />返回</button>
      <span v-else class="entry-label">{{ PRIVATE_EXPLORATIONS_ENABLED ? '探索入口' : '公开演示' }}</span>
      <div class="book-id">
        <strong>{{ workspaceTitle }}</strong>
        <span>{{ workspaceSubtitle }}</span>
      </div>
      <span v-if="store.hasWorkspace && !store.entryOpen" class="privacy"><ShieldCheck :size="13" />{{ privacyLabel }}</span>
      <span v-if="store.hasWorkspace && !store.entryOpen && saveLabel" class="save"><Check :size="13" />{{ saveLabel }}</span>
      <span v-if="store.companionNotice" class="companion-status">{{ store.companionNotice }}</span>
    </header>

    <ExplorationEntry v-if="store.entryOpen" />

    <template v-else-if="!isMobile">
      <div class="explore-desktop">
        <SplitPane storage-key="split-explore-reader" :min="230" :default="0.23" label="调整书籍阅读栏宽度">
          <template #left><ExplorationReader /></template>
          <template #right>
            <SplitPane storage-key="split-explore-evidence" :min="260" :default="0.68" label="调整关系化证据栏宽度">
              <template #left><div class="center"><CenterWorkspace /></div></template>
              <template #right><ExplorationEvidence /></template>
            </SplitPane>
          </template>
        </SplitPane>
      </div>
    </template>

    <template v-else>
      <nav class="mobile-tabs" :class="{ 'companion-tabs': companionMode }" aria-label="书籍探索视图">
        <button v-if="!companionMode" :class="{ active: mobileTab === 'reader' }" @click="mobileTab = 'reader'"><BookOpenText :size="15" />{{ store.isSampleWorkspace ? '阅读窗口' : '阅读' }}</button>
        <button :class="{ active: mobileTab === 'logic' }" @click="mobileTab = 'logic'"><GitBranch :size="15" />论证</button>
        <button :class="{ active: mobileTab === 'map' }" @click="mobileTab = 'map'"><Map :size="15" />时空</button>
        <button :class="{ active: mobileTab === 'evidence' }" @click="mobileTab = 'evidence'"><Files :size="15" />{{ mobileEvidenceLabel }}</button>
      </nav>
      <div class="explore-mobile">
        <div v-if="mobileTab === 'logic'" class="companion-center"><CenterWorkspace /></div>
        <ExplorationReader v-else-if="mobileTab === 'reader'" mobile />
        <div v-else-if="mobileTab === 'map'" class="mobile-map" :class="{ 'single-row': !store.isSampleWorkspace }">
          <div v-if="store.isSampleWorkspace" class="mobile-scene-strip">
            <button v-for="(scene, index) in scenes" :key="scene.id" :class="{ active: index === store.sceneIndex }"
                    :aria-label="`切换到${scene.label}`" @click="selectDemoScene(index)">{{ index + 1 }}</button>
          </div>
          <MapWorkspace />
        </div>
        <ExplorationEvidence v-else readonly />
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import ArrowLeft from '@lucide/vue/dist/esm/icons/arrow-left.mjs'
import BookOpenText from '@lucide/vue/dist/esm/icons/book-open-text.mjs'
import Check from '@lucide/vue/dist/esm/icons/check.mjs'
import Files from '@lucide/vue/dist/esm/icons/files.mjs'
import GitBranch from '@lucide/vue/dist/esm/icons/git-branch.mjs'
import Map from '@lucide/vue/dist/esm/icons/map.mjs'
import Pause from '@lucide/vue/dist/esm/icons/pause.mjs'
import Play from '@lucide/vue/dist/esm/icons/play.mjs'
import RotateCcw from '@lucide/vue/dist/esm/icons/rotate-ccw.mjs'
import ShieldCheck from '@lucide/vue/dist/esm/icons/shield-check.mjs'
import SkipBack from '@lucide/vue/dist/esm/icons/skip-back.mjs'
import SkipForward from '@lucide/vue/dist/esm/icons/skip-forward.mjs'
import X from '@lucide/vue/dist/esm/icons/x.mjs'
import SplitPane from '../components/shared/SplitPane.vue'
import ExplorationReader from '../components/exploration/ExplorationReader.vue'
import ExplorationEvidence from '../components/exploration/ExplorationEvidence.vue'
import ExplorationEntry from '../components/exploration/ExplorationEntry.vue'
import {
  ANSHI_PUBLIC_ANCHORS,
  ANSHI_PUBLIC_DEMO,
  ANSHI_PUBLIC_SCENES,
} from '../data/anshiPublicDemo'
import { useExplorationStore } from '../stores/useExplorationStore'
import { useWereadCompanionBridge } from '../composables/useWereadCompanionBridge'
import { PRIVATE_EXPLORATIONS_ENABLED } from '../config/distribution'

const ExploreMapPanel = defineAsyncComponent(() => import('../components/exploration/ExploreMapPanel.vue'))
const store = useExplorationStore()
useWereadCompanionBridge(store)
const publicDemo = ANSHI_PUBLIC_DEMO
const scenes = ANSHI_PUBLIC_SCENES
const paragraphs = ANSHI_PUBLIC_ANCHORS
const ARGUMENT_NODE_LABELS = Object.freeze({
  question: '问题',
  material_observation: '材料观察 · 原创衍生摘要',
  reasoning_mechanism: '推理机制',
  action_or_turn: '行动或转折',
  consequence: '后果',
  limitation: '限制或不确定性',
})
const EPISTEMIC_LAYER_LABELS = Object.freeze({
  historical_fact: '事实层',
  author_judgment: '作者判断',
  platform_inference: '平台推断',
  uncertainty: '证据边界',
})
const companionMode = new URLSearchParams(window.location.search).get('companion') === '1'
const mobileTab = ref(companionMode ? 'logic' : 'reader')
const isMobile = ref(false)
let mobileMedia = null
let unsubscribe = null

const selected = computed(() => paragraphs[store.paragraphIndex] || paragraphs[0])
const privacyLabel = computed(() => {
  if (store.isSampleWorkspace) return '公开演示 · 原文受限'
  return store.snapshot ? '当前进程临时会话' : '本地草案'
})
const saveLabel = computed(() => {
  if (store.isSampleWorkspace) return ''
  return store.snapshot ? '重启后清除' : '未同步服务端'
})
const importedParagraph = computed(() =>
  store.importedParagraphRecord(store.activeImportedAnchorId)?.paragraph
  || store.firstImportedParagraph
  || null)
const questionScopeConfirmed = computed(() =>
  store.workspaceKind === 'question'
  && store.snapshot?.scope_contract?.fields_needing_confirmation?.length === 0)
const mobileEvidenceLabel = computed(() => {
  if (companionMode) return '出处'
  return store.workspaceKind === 'question' ? '范围' : '证据'
})
const workspaceTitle = computed(() => {
  if (store.entryOpen) return '开启一次历史探索'
  if (store.workspaceKind === 'document') return store.snapshot?.document?.title || '私人材料'
  if (store.workspaceKind === 'question') return '问题探索'
  return publicDemo.title
})
const workspaceSubtitle = computed(() => {
  if (store.entryOpen) return '从历史问题或本地材料开始'
  if (store.workspaceKind === 'document') return '私人文本 · 连续阅读 · 时间与空间待确认'
  if (store.workspaceKind === 'question') {
    return questionScopeConfirmed.value
      ? `${store.questionPrompt} · ${store.snapshot?.brief?.time_range || '时间范围已确认'}`
      : `${store.questionPrompt} · 范围待确认`
  }
  return `${publicDemo.authorLabel} · ${publicDemo.range} · 公开原创衍生摘要`
})
const scene = computed(() => {
  if (store.isSampleWorkspace) return scenes[store.sceneIndex] || scenes[0]
  return {
    id: store.selectedSceneId || (store.workspaceKind === 'question' ? 'question-scope' : 'imported-unstructured'),
    date: questionScopeConfirmed.value ? store.snapshot?.brief?.time_range || '范围已确认' : '时间待确认',
    label: store.workspaceKind === 'question'
      ? questionScopeConfirmed.value ? '等待材料与编织' : '等待确认时空范围'
      : '尚未建立 Scene',
    placeId: null,
    place: null,
    location: null,
    detail: store.workspaceKind === 'question'
      ? questionScopeConfirmed.value
        ? '问题范围已经确认。下一步可添加材料并建立来源包；当前没有生成历史结论或猜测地点。'
        : `已记录问题：“${store.questionPrompt}”。下一步需要确认时间、空间与叙事主线；当前没有生成历史结论。`
      : `${store.selectedContextText || '文本已经建立段落锚点'}；尚未生成或采纳时空结构，地图不会沿用示例地点。`,
    status: store.workspaceKind === 'question'
      ? questionScopeConfirmed.value ? '范围已确认 · 尚未调用模型' : '用户问题 · 尚未调用模型'
      : '私人文本 · 未结构化',
    relation: '证据缺口',
  }
})
const activeArgumentGraph = computed(() =>
  store.isSampleWorkspace ? scene.value.argumentGraph || null : null)

function selectDemoScene(index) {
  store.selectScene(index)
}
function defaultMobileTab() {
  if (companionMode) return 'logic'
  return store.workspaceKind === 'question' ? 'evidence' : 'reader'
}
async function returnToDemoAnchor(anchorId) {
  const anchor = paragraphs.find((item) => item.id === anchorId) || selected.value
  store.returnToAnchor(anchor.id)
  await new Promise((resolve) => requestAnimationFrame(resolve))
  document.getElementById(`anchor-${anchor.id}`)?.scrollIntoView({ block: 'center' })
}

onMounted(() => {
  store.hydrate()
  unsubscribe = store.$subscribe(() => store.persist())
  mobileMedia = window.matchMedia('(max-width: 720px)')
  const sync = () => { isMobile.value = mobileMedia.matches }
  sync()
  mobileMedia.addEventListener('change', sync)
  mobileMedia._explorationSync = sync
  if (store.workspaceKind === 'document' && store.snapshot?.id) {
    store.refreshAnalysisRuns({ silent: true })
  }
  if (import.meta.env.DEV) window.__hkbExploration = store
})
watch(
  [() => store.entryOpen, () => store.workspaceKind, () => store.sampleDemoId, () => store.snapshot?.id],
  () => { mobileTab.value = defaultMobileTab() },
)
watch(() => store.snapshot?.id, (id, previousId) => {
  if (!id || id === previousId || store.isSampleWorkspace) return
  store.refreshAnalysisRuns({ silent: true })
})
onBeforeUnmount(() => {
  store.pause()
  store.stopAnalysisPolling()
  unsubscribe?.()
  if (mobileMedia?._explorationSync) mobileMedia.removeEventListener('change', mobileMedia._explorationSync)
  if (import.meta.env.DEV && window.__hkbExploration === store) delete window.__hkbExploration
})

function logicNode(node) {
  return h('button', {
    class: 'logic-node',
    onClick: () => store.openLogicNode(node),
  }, [h('small', node.kind), node.title])
}

function argumentNode(node, graph) {
  const incoming = graph.edges.find((edge) => edge.to === node.id)
  return h('button', {
    class: ['logic-node', 'argument-node', `argument-node-${node.type}`],
    'data-node-type': node.type,
    'data-epistemic-layer': node.epistemicLayer,
    onClick: () => store.openLogicNode(node),
  }, [
    incoming
      ? h('span', {
        class: 'argument-incoming',
        'data-edge-relation': incoming.relation,
      }, `← ${incoming.label}`)
      : h('span', { class: 'argument-incoming root' }, '起点'),
    h('small', ARGUMENT_NODE_LABELS[node.type] || node.type),
    h('strong', node.title),
    h('p', node.summary),
  ])
}

const CenterWorkspace = {
  setup() {
    const importedLogicNode = () => h('button', {
      class: 'logic-node imported-source',
      onClick: async () => {
        const paragraph = importedParagraph.value
        if (!paragraph) return
        store.setSourceTab('reader')
        store.setReaderView('text')
        await store.selectImportedAnchor(paragraph.id)
        requestAnimationFrame(() => document.getElementById(`anchor-${paragraph.id}`)?.scrollIntoView({ block: 'center' }))
      },
    }, [
      h('small', '原文段落'),
      importedParagraph.value?.text || '请从左侧选择一个段落锚点',
      h('span', '回到文本'),
    ])

    const briefPanel = () => h('section', { class: 'brief' }, [
        h('div', [
          h('small', '研究 Brief · 草案'),
          h('strong', store.isSampleWorkspace
            ? '安史之乱如何从边镇结构风险演变为跨地域战争，并在后世形成多层历史记忆？'
            : store.workspaceKind === 'question'
              ? store.questionPrompt
              : store.snapshot?.brief?.question || '这份文本如何组织事件、作者判断与证据关系？'),
        ]),
        h('div', { class: 'brief-scope' }, [
          h('span', [h('small', '时间'), store.isSampleWorkspace ? publicDemo.range : store.snapshot?.brief?.time_range || '待确认']),
          h('span', [h('small', '空间'), store.isSampleWorkspace ? '河北 · 两京 · 河洛' : store.snapshot?.brief?.geography?.join(' · ') || '待确认']),
          h('span', [h('small', '对象'), store.isSampleWorkspace ? '军政 · 联盟 · 记忆' : store.workspaceKind === 'question' ? '用户问题' : '段落锚点']),
        ]),
      ])

    const logicPanel = () => h('section', { class: 'logic' }, [
        h('header', [
          h('small', store.isSampleWorkspace ? '论证链路' : '结构化状态'),
          h('strong', store.isSampleWorkspace
            ? `${selected.value.time} · ${selected.value.claim}`
            : store.workspaceKind === 'question'
              ? questionScopeConfirmed.value ? '用户问题 · 范围已确认' : '用户问题 · 等待范围确认'
              : `当前段落 · ${importedParagraph.value ? `段落 ${importedParagraph.value.ordinal + 1}` : '尚未选择'}`),
        ]),
        !store.isSampleWorkspace
          ? h('div', { class: 'logic-flow imported-flow' }, [
            store.workspaceKind === 'document'
              ? importedLogicNode()
              : logicNode({ id: 'question', kind: '用户问题', title: store.questionPrompt }),
            h('i', '→'),
            h('div', { class: 'logic-empty' }, [
              h('small', '尚未建立关系'),
              h('strong', store.workspaceKind === 'question'
                ? questionScopeConfirmed.value ? '等待材料与结构提议' : '等待确认范围与叙事主线'
                : '等待结构提议与人工复核'),
              h('p', '不会把示例书的论证、地点或时间套入当前探索。'),
            ]),
          ])
          : activeArgumentGraph.value
            ? h('div', {
              class: 'argument-graph',
              'data-testid': 'argument-graph',
              'data-argument-graph-id': activeArgumentGraph.value.id,
            }, [
              h('div', { class: 'argument-nodes' },
                activeArgumentGraph.value.nodes.map((node) =>
                  argumentNode(node, activeArgumentGraph.value))),
              h('div', {
                class: 'argument-edge-list',
                'aria-label': '论证关系语义',
              }, activeArgumentGraph.value.edges.map((edge) => {
                const fromNode = activeArgumentGraph.value.nodes.find((node) => node.id === edge.from)
                const toNode = activeArgumentGraph.value.nodes.find((node) => node.id === edge.to)
                return h('span', {
                  key: edge.id,
                  'data-edge-relation': edge.relation,
                }, [
                  h('small', `${ARGUMENT_NODE_LABELS[fromNode?.type] || '节点'} → ${ARGUMENT_NODE_LABELS[toNode?.type] || '节点'}`),
                  h('strong', edge.label),
                ])
              })),
            ])
            : h('div', { class: 'logic-empty' }, [
              h('small', '论证图缺口'),
              h('strong', '当前 Scene 尚未绑定 argumentGraph'),
            ]),
        store.isSampleWorkspace && store.selectedLogicNode ? h('article', { class: 'logic-detail', role: 'dialog', 'aria-label': '论证节点详情' }, [
          h('button', { 'aria-label': '关闭节点详情', onClick: () => store.closeLogicNode() }, [h(X, { size: 14 })]),
          h('small', ARGUMENT_NODE_LABELS[store.selectedLogicNode.type] || store.selectedLogicNode.kind),
          h('strong', store.selectedLogicNode.title),
          h('span', { class: 'logic-layer' }, EPISTEMIC_LAYER_LABELS[store.selectedLogicNode.epistemicLayer] || '层级待标'),
          h('p', store.selectedLogicNode.detail || store.selectedLogicNode.summary),
          h('div', { class: 'logic-boundary' }, [
            h('small', store.selectedLogicNode.locatorLabel || selected.value.locatorLabel),
            h('span', '原文未公开 · 仅保留不可逆原创衍生摘要'),
          ]),
          h('button', { class: 'back-source', onClick: () => returnToDemoAnchor(store.selectedLogicNode.anchorId) }, '回到定位'),
        ]) : null,
      ])

    return () => h('div', { class: 'center-grid' }, [
      h(SplitPane, {
        vertical: true,
        storageKey: 'split-explore-brief',
        minLead: 76,
        // 下层还要容纳 190px 论证图、6px 手柄与 240px 地图。
        minTrail: 436,
        default: 0.15,
        label: '调整研究 Brief 高度',
      }, {
        left: briefPanel,
        right: () => h(SplitPane, {
          vertical: true,
          storageKey: 'split-explore-logic-map',
          minLead: 190,
          minTrail: 240,
          default: 0.38,
          label: '调整论证与地图高度',
        }, {
          left: logicPanel,
          right: () => h(MapWorkspace),
        }),
      }),
    ])
  },
}

const MapWorkspace = {
  setup() {
    return () => h('section', { class: 'map-section' }, [
      h('header', [h('div', [h('small', '时空脉络'), h('strong', `${scene.value.date} · ${scene.value.label}`)]),
        h('span', scene.value.status)]),
      h('div', { class: 'map-shell', 'data-testid': 'exploration-map-shell' }, [
        h(ExploreMapPanel, {
          scene: scene.value,
          playerOpen: store.playerOpen,
          onManualInteraction: () => store.pause(),
        }),
        !store.isSampleWorkspace
          ? h('span', { class: 'player-unavailable' }, '建立并复核 Scene 后可播放')
          : !store.playerOpen
          ? h('button', { class: 'player-entry', 'aria-expanded': 'false', onClick: () => store.openPlayer() }, [h(Play, { size: 14, fill: 'currentColor' }), '播放脉络'])
          : h('div', { class: 'player', role: 'group', 'aria-label': '书籍场景播放' }, [
            h('button', { 'aria-label': '收起播放控制', onClick: () => store.closePlayer() }, [h(X, { size: 14 })]),
            h('button', { 'aria-label': '上一个 Scene', disabled: store.sceneIndex === 0, onClick: () => selectDemoScene(store.sceneIndex - 1) }, [h(SkipBack, { size: 14 })]),
            h('button', { class: 'play-main', 'aria-label': store.playbackStatus === 'ended' ? '重新播放' : store.isPlaying ? '暂停播放' : '开始播放', onClick: () => store.togglePlayback() },
              [h(store.playbackStatus === 'ended' ? RotateCcw : store.isPlaying ? Pause : Play, { size: 15, fill: store.isPlaying ? 'currentColor' : 'none' })]),
            h('button', { 'aria-label': '下一个 Scene', disabled: store.sceneIndex === scenes.length - 1, onClick: () => selectDemoScene(store.sceneIndex + 1) }, [h(SkipForward, { size: 14 })]),
            h('select', { 'aria-label': '播放速度', value: store.rate, onChange: (event) => store.setRate(event.target.value) },
              [0.5, 1, 1.5].map((rate) => h('option', { value: rate }, `${rate}×`))),
            h('span', `${store.sceneIndex + 1} / ${scenes.length}`),
          ]),
      ]),
    ])
  },
}
</script>

<style>
.explore{height:100%;min-height:0;display:grid;grid-template-rows:50px minmax(0,1fr);overflow:hidden;background:var(--paper)}.entry-label{color:var(--ink-soft);font-size:10px;white-space:nowrap}
.explore-bar{display:flex;align-items:center;gap:10px;padding:0 12px;border-bottom:1px solid var(--line);background:var(--paper-el)}
.back{display:flex;align-items:center;gap:4px;white-space:nowrap}.book-id{min-width:0;display:grid;gap:2px;flex:1}.book-id strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--serif);font-size:13px}.book-id span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink-soft);font-size:9px}.privacy,.save{display:flex;align-items:center;gap:4px;white-space:nowrap;color:var(--ink-soft);font-size:9px}.save{color:var(--success)}
.companion-status{max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--accent);font-size:9px}
.explore-desktop{min-height:0;overflow:hidden}.center{height:100%;min-width:0}.center-grid{height:100%;overflow:hidden}
.brief{height:100%;display:grid;grid-template-columns:minmax(220px,1fr) minmax(210px,.85fr);align-items:center;gap:8px;padding:9px 11px;background:var(--paper-el)}.brief>div:first-child{display:grid;gap:4px}.brief small,.logic header small,.map-section header small{color:var(--ink-soft);font-size:8px}.brief strong{font-size:11px}.brief-scope{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--line);border-radius:5px}.brief-scope span{display:grid;grid-template-rows:auto minmax(1.15em,auto);align-content:center;gap:2px;min-width:0;padding:5px;border-right:1px solid var(--hair);font-size:8px}.brief-scope span:last-child{border:0}
.logic{position:relative;height:100%;min-height:0;display:grid;grid-template-rows:auto minmax(0,1fr);overflow:hidden;padding:9px 11px}.logic header{display:grid;gap:3px}.logic header strong{font-size:11px}.logic-flow{height:100%;display:grid;grid-template-columns:minmax(95px,1fr) 12px minmax(110px,1.2fr) 12px minmax(110px,1fr) 12px minmax(80px,.8fr);align-items:center;gap:5px}.logic-flow>i{color:var(--ink-faint);font-style:normal}.logic-node{min-width:0;display:grid;gap:5px;padding:8px;text-align:left;border:1px solid var(--line);border-radius:6px;background:var(--paper-el);font-size:9px;line-height:1.45}.logic-node small{color:var(--accent);font-size:7px}.argument-graph{min-height:0;overflow:auto;padding:7px 1px 3px}.argument-nodes{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:6px}.argument-node{position:relative;min-height:88px;align-content:start}.argument-node:hover,.argument-node:focus-visible{border-color:var(--accent);background:var(--chip)}.argument-node strong{font-family:var(--serif);font-size:10px;line-height:1.35}.argument-node p{display:-webkit-box;overflow:hidden;margin:0;color:var(--ink-soft);font-size:8px;line-height:1.5;-webkit-box-orient:vertical;-webkit-line-clamp:2}.argument-node-limitation{border-style:dashed}.argument-incoming{width:max-content;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ink-faint);font-size:7px}.argument-incoming.root{color:var(--success)}.argument-edge-list{display:flex;flex-wrap:wrap;gap:4px;margin-top:7px;padding-top:6px;border-top:1px solid var(--hair)}.argument-edge-list>span{display:grid;gap:1px;padding:3px 5px;border-radius:4px;background:var(--chip)}.argument-edge-list small{color:var(--ink-faint);font-size:6px}.argument-edge-list strong{color:var(--ink-mid);font-size:7px;font-weight:600}.logic-detail{position:absolute;z-index:6;right:12px;bottom:9px;width:min(420px,64%);display:grid;gap:6px;padding:12px;border:1px solid var(--accent);border-radius:7px;background:var(--paper-el);box-shadow:0 5px 20px rgba(0,0,0,.14)}.logic-detail>button:first-child{position:absolute;right:6px;top:6px;width:25px;height:25px;padding:0}.logic-detail>small{color:var(--accent);font-size:8px}.logic-detail p{margin:0;font-size:9px;line-height:1.65}.logic-layer{width:max-content;padding:2px 5px;border-radius:4px;background:var(--chip);color:var(--accent);font-size:8px}.logic-boundary{display:grid;gap:2px;padding:7px;border-left:2px solid var(--line);color:var(--ink-soft);font-size:8px}.logic-boundary small{color:var(--ink-mid)}.back-source{width:max-content;padding:3px 0;border:0;background:transparent;color:var(--accent);font-size:9px}
.logic-flow.imported-flow{grid-template-columns:minmax(180px,.9fr) 20px minmax(240px,1.4fr);max-width:620px}.logic-node.imported-source span{color:var(--accent);font-size:8px}.logic-empty{display:grid;gap:5px;padding:12px;border:1px dashed var(--line);border-radius:6px;color:var(--ink-soft)}.logic-empty small{font-size:8px}.logic-empty strong{color:var(--ink);font-size:11px}.logic-empty p{font-size:9px;line-height:1.55}
.map-section{height:100%;min-height:0;display:grid;grid-template-rows:40px minmax(0,1fr);padding:0 10px 10px}.map-section>header{display:flex;align-items:center;justify-content:space-between;gap:8px}.map-section>header>div{display:grid;gap:2px}.map-section header span{color:var(--ink-soft);font-size:8px}.map-shell{position:relative;min-height:0;overflow:hidden;border:1px solid var(--line);border-radius:7px;background:var(--field)}.player-entry,.player,.player-unavailable{position:absolute;z-index:7;left:10px;bottom:10px}.player-entry{display:flex;align-items:center;gap:5px;background:var(--caption)}.player-unavailable{padding:6px 8px;border:1px solid var(--line);border-radius:5px;background:var(--caption);color:var(--ink-soft);font-size:9px}.player{display:flex;align-items:center;gap:4px;padding:5px;border:1px solid var(--line);border-radius:8px;background:var(--caption);box-shadow:0 3px 12px rgba(0,0,0,.14)}.player button{width:28px;height:28px;display:grid;place-items:center;padding:0}.player .play-main{background:var(--accent);color:var(--accent-text);border-color:var(--accent)}.player select{height:28px;padding:0 4px;font-size:9px}.player span{padding:0 4px;color:var(--ink-soft);font-size:9px}
.mobile-tabs{display:none}.explore-mobile{min-height:0}.companion-center{height:100%;min-height:0;overflow:hidden}.companion-center .center-grid{height:100%;min-height:0}
@media(max-width:720px){
  .explore{grid-template-rows:48px 42px minmax(0,1fr)}.explore-bar{padding:0 8px;gap:6px}.back{padding:5px;font-size:0}.book-id strong{font-size:11px}.book-id span{font-size:8px}.privacy{display:none}.save{font-size:8px}
  .explore.entry-mode{grid-template-rows:48px minmax(0,1fr)}
  .mobile-tabs{display:grid;grid-template-columns:repeat(4,1fr);padding:4px;border-bottom:1px solid var(--line);background:var(--paper-el)}.mobile-tabs.companion-tabs{grid-template-columns:repeat(3,1fr)}.mobile-tabs button{display:flex;align-items:center;justify-content:center;gap:5px;border:0;background:transparent;color:var(--ink-soft)}.mobile-tabs button.active{color:var(--accent);background:var(--chip)}
  .explore-mobile{overflow:hidden}.explore-mobile>*{height:100%}.mobile-map{min-height:0;display:grid;grid-template-rows:38px minmax(0,1fr)}.mobile-map.single-row{grid-template-rows:minmax(0,1fr)}.mobile-scene-strip{display:flex;align-items:center;justify-content:center;gap:6px;border-bottom:1px solid var(--line)}.mobile-scene-strip button{width:25px;height:25px;padding:0;border-radius:50%;font-size:9px}.mobile-scene-strip button.active{background:var(--accent);color:var(--accent-text);border-color:var(--accent)}
  .map-section{padding:0;grid-template-rows:36px minmax(0,1fr)}.map-section>header{padding:0 8px}.map-shell{border:0;border-radius:0}.player-entry,.player,.player-unavailable{left:8px;bottom:8px}
}
</style>
