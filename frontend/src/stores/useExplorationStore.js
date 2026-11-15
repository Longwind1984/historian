import { defineStore } from 'pinia'
import { useTimeStore } from './useTimeStore'
import {
  ANSHI_PUBLIC_ANCHORS,
  ANSHI_PUBLIC_DEMO,
  ANSHI_PUBLIC_SCENES,
} from '../data/anshiPublicDemo'
import {
  cancelExplorationAnalysisRun,
  composeExploration,
  createExplorationAnalysisRun,
  getExploration,
  getExplorationAnalysisRun,
  getExplorationAnalysisResult,
  importExploration,
  importExplorationEpub,
  listExplorationAnalysisRuns,
  mutateExploration,
  resumeExplorationAnalysisRun,
  startPromptExploration,
  submitExplorationAnalysisReview,
} from '../api/client'
import { PRIVATE_EXPLORATIONS_ENABLED } from '../config/distribution'

const STORAGE_KEY = 'history-kb-exploration-v1'
const PLAY_STEP_MS = 2600
let playbackTimer = 0
let analysisPollTimer = 0
let mutationChain = Promise.resolve()
let paragraphIndexDocumentId = null
let paragraphIndex = new Map()

function getParagraphIndex(state) {
  const document = state.snapshot?.document
  if (!document) {
    paragraphIndexDocumentId = null
    paragraphIndex = new Map()
    return paragraphIndex
  }
  if (paragraphIndexDocumentId === document.id) return paragraphIndex
  const next = new Map()
  let globalIndex = 0
  for (const section of document.sections || []) {
    for (const paragraph of section.paragraphs || []) {
      next.set(paragraph.id, { paragraph, globalIndex })
      globalIndex += 1
    }
  }
  paragraphIndexDocumentId = document.id
  paragraphIndex = next
  return paragraphIndex
}

export const EXPLORATION_SCENES = ANSHI_PUBLIC_SCENES
export const EXPLORATION_PARAGRAPHS = ANSHI_PUBLIC_ANCHORS

const DEFAULT_SAMPLE_SCENE_INDEX = Math.max(
  0,
  EXPLORATION_SCENES.findIndex((scene) => scene.id === ANSHI_PUBLIC_DEMO.defaultSceneId),
)

const PERSISTED_FIELDS = [
  'workspaceKind', 'sampleDemoId', 'questionPrompt', 'sceneIndex', 'paragraphIndex', 'sourceTab',
  'readerView', 'thread', 'lens', 'selectedEvidenceId', 'rate', 'composerText',
  'playerOpen', 'readingProgress', 'webProgressLabel', 'privateExplorationId', 'activeAnalysisRunId',
]

const POLLED_ANALYSIS_STATES = new Set(['planned', 'queued', 'running', 'retry_wait'])
const CANCELLABLE_ANALYSIS_STATES = new Set([
  'planned', 'queued', 'running', 'retry_wait', 'paused', 'waiting_review', 'waiting_input',
])

function exactYear(scene) {
  return scene.year + (scene.month ? (scene.month - 1) / 12 : 0)
}

/** 一本书内部共用的 Scene / 原文 / 证据 / 播放状态。 */
export const useExplorationStore = defineStore('exploration', {
  state: () => ({
    workspaceKind: 'empty',
    sampleDemoId: null,
    entryOpen: true,
    questionPrompt: '',
    title: '',
    range: '',
    sceneIndex: DEFAULT_SAMPLE_SCENE_INDEX,
    paragraphIndex: 0,
    lastPlaceId: null,
    sourceTab: 'reader',
    sourceState: 'reader_ready',
    readerView: 'text',
    thread: '权力与联盟',
    lens: '作者视角',
    selectedEvidenceId: null,
    selectedLogicNode: null,
    playerOpen: false,
    playbackStatus: 'paused',
    rate: 1,
    composerText: '',
    composerNotice: '',
    snapshot: null,
    privateExplorationId: null,
    restoringPrivateWorkspace: false,
    activeImportedAnchorId: null,
    selectedAnchorId: null,
    selectedSceneId: null,
    selectedEvidenceAnchorId: null,
    readingProgress: 0,
    questionSyncState: 'idle',
    startingPrompt: false,
    updatingScope: false,
    epubImporting: false,
    webProgressLabel: '',
    webPastedExcerpt: '',
    syncingWeb: false,
    importing: false,
    composing: false,
    analysisRuns: [],
    activeAnalysisRunId: null,
    analysisRefreshing: false,
    analysisAction: '',
    analysisError: '',
    analysisResult: null,
    analysisReviewDecisions: {},
    publishedAnalysisView: 'argument',
    apiError: '',
    companionNotice: '',
    hydrated: false,
  }),
  getters: {
    hasWorkspace: (state) => state.workspaceKind !== 'empty',
    isSampleWorkspace: (state) => state.workspaceKind === 'sample',
    currentScene: (state) => state.workspaceKind === 'sample'
      ? EXPLORATION_SCENES[state.sceneIndex]
      : null,
    currentParagraph: (state) => state.workspaceKind === 'sample'
      ? EXPLORATION_PARAGRAPHS[state.paragraphIndex]
      : null,
    isPlaying: (state) => state.playbackStatus === 'playing',
    activeAnalysisRun: (state) => state.analysisRuns.find((run) => run.id === state.activeAnalysisRunId)
      || state.analysisRuns.at(-1)
      || null,
    canCancelAnalysis() {
      return CANCELLABLE_ANALYSIS_STATES.has(this.activeAnalysisRun?.state)
        && !this.activeAnalysisRun?.cancel_requested
    },
    canResumeAnalysis() {
      return this.activeAnalysisRun?.state === 'cancelled'
    },
    analysisCandidateItems: (state) => [
      ...(state.analysisResult?.artifacts?.claims || []).map((item) => ({ ...item, artifact_type: 'claim' })),
      ...(state.analysisResult?.artifacts?.events || []).map((item) => ({ ...item, artifact_type: 'event' })),
    ],
    reviewDecisionComplete() {
      return this.analysisCandidateItems.every((item) =>
        ['accepted', 'rejected'].includes(this.analysisReviewDecisions[`${item.artifact_type}:${item.id}`]))
    },
    reviewDependencyError() {
      if (!this.reviewDecisionComplete) return ''
      const acceptedClaims = new Set(this.analysisCandidateItems
        .filter((item) => item.artifact_type === 'claim'
          && this.analysisReviewDecisions[`claim:${item.id}`] === 'accepted')
        .map((item) => item.id))
      for (const item of this.analysisCandidateItems) {
        const accepted = this.analysisReviewDecisions[`${item.artifact_type}:${item.id}`] === 'accepted'
        if (!accepted) continue
        const parents = item.artifact_type === 'claim' ? item.derived_from_claim_ids : item.claim_ids
        if ((parents || []).some((id) => !acceptedClaims.has(id))) {
          return item.artifact_type === 'claim'
            ? '接受平台推断前，需先接受它依据的 Claim'
            : '接受事件前，需先接受它引用的 Claim'
        }
      }
      return ''
    },
    reviewReady() {
      return this.reviewDecisionComplete && !this.reviewDependencyError
    },
    importedSections: (state) => state.snapshot?.document?.sections || [],
    importedParagraphs: (state) => (state.snapshot?.document?.sections || [])
      .flatMap((section) => section.paragraphs || []),
    importedParagraphCount: (state) => state.snapshot?.document?.paragraph_count || 0,
    firstImportedParagraph: (state) => state.snapshot?.document?.sections?.[0]?.paragraphs?.[0] || null,
    importedParagraphRecord: (state) => (id) => getParagraphIndex(state).get(id) || null,
    selectedContextText() {
      if (this.selectedAnchorId === 'web-bridge') return this.webPastedExcerpt
      if (this.workspaceKind === 'question') return this.questionPrompt
      return this.importedParagraphRecord(this.selectedAnchorId)?.paragraph?.text || ''
    },
  },
  actions: {
    hydrate() {
      if (this.hydrated) return
      let saved = {}
      try {
        saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
        for (const field of PERSISTED_FIELDS) {
          if (saved[field] !== undefined) this[field] = saved[field]
        }
      } catch {
        // 本地草案损坏时回到安全默认值，不阻断书籍工作区。
      }
      this.privateExplorationId = typeof this.privateExplorationId === 'string'
        && /^[A-Za-z0-9_-]{1,128}$/.test(this.privateExplorationId)
        ? this.privateExplorationId
        : null
      // 正文仍只存于后端进程；本地只有 exploration id，必须 GET 成功后才恢复。
      if (this.workspaceKind === 'document') this.workspaceKind = 'empty'
      this.entryOpen = this.workspaceKind === 'empty'
      this.sceneIndex = Math.max(0, Math.min(EXPLORATION_SCENES.length - 1, Number(this.sceneIndex) || 0))
      this.paragraphIndex = Math.max(0, Math.min(EXPLORATION_PARAGRAPHS.length - 1, Number(this.paragraphIndex) || 0))
      if (this.workspaceKind === 'sample') {
        const isLegacySample = saved.sampleDemoId !== ANSHI_PUBLIC_DEMO.id
        this.sampleDemoId = ANSHI_PUBLIC_DEMO.id
        this.title = ANSHI_PUBLIC_DEMO.title
        this.range = ANSHI_PUBLIC_DEMO.range
        this.applySampleScene(isLegacySample ? DEFAULT_SAMPLE_SCENE_INDEX : this.sceneIndex)
      } else if (this.workspaceKind === 'question') {
        this.title = '问题探索'
        this.range = '范围待确认'
        this.questionSyncState = 'local_only'
      }
      this.hydrated = true
    },
    persist() {
      try {
        if (this.workspaceKind === 'document' && this.snapshot?.id) {
          this.privateExplorationId = this.snapshot.id
        }
        const snapshot = Object.fromEntries(PERSISTED_FIELDS.map((field) => [field, this[field]]))
        localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
      } catch {
        // 隐私模式可能禁用 localStorage；工作区仍可在当前会话使用。
      }
    },
    async restorePrivateWorkspace() {
      const explorationId = this.privateExplorationId
      if (!explorationId || this.hasWorkspace || this.restoringPrivateWorkspace) return false
      this.restoringPrivateWorkspace = true
      try {
        const snapshot = await getExploration(explorationId)
        if (this.hasWorkspace || this.privateExplorationId !== explorationId) return false
        if (!snapshot?.document || snapshot.id !== explorationId) {
          this.privateExplorationId = null
          this.persist()
          return false
        }
        this.snapshot = snapshot
        this.workspaceKind = 'document'
        this.entryOpen = false
        this.title = snapshot.document.title
        this.range = snapshot.brief?.time_range || '时间与空间待确认'
        this.sourceTab = 'reader'
        this.readerView = 'text'
        this.applyImportedAnchor(snapshot.active_anchor_id || this.firstImportedParagraph?.id || null)
        this.applyReadingProgress(snapshot)
        this.applyExternalReadingBridge(snapshot)
        await this.refreshAnalysisRuns({ silent: true })
        this.startAnalysisPolling()
        this.composerNotice = '已恢复私人阅读会话'
        return true
      } catch (error) {
        if (error?.status === 404 || error?.response?.status === 404) {
          this.privateExplorationId = null
          this.persist()
        }
        return false
      } finally {
        this.restoringPrivateWorkspace = false
      }
    },
    syncTime() {
      if (this.workspaceKind !== 'sample') return
      const scene = this.currentScene
      if (!scene) return
      useTimeStore().requestNavigation({
        exactYear: exactYear(scene),
        month: scene.month ?? null,
        precision: scene.month ? 'month' : 'year',
      })
    },
    applySampleScene(index) {
      const bounded = Math.max(0, Math.min(EXPLORATION_SCENES.length - 1, Number(index) || 0))
      const scene = EXPLORATION_SCENES[bounded]
      if (!scene) return null
      const anchorIndex = EXPLORATION_PARAGRAPHS.findIndex(
        (anchor) => anchor.id === scene.primaryAnchorId && anchor.sceneId === scene.id,
      )
      const anchor = anchorIndex >= 0 ? EXPLORATION_PARAGRAPHS[anchorIndex] : null
      this.sceneIndex = bounded
      this.lastPlaceId = scene.placeId || null
      this.selectedSceneId = scene.id
      this.selectedLogicNode = null
      if (anchor) {
        this.paragraphIndex = anchorIndex
        this.selectedAnchorId = anchor.id
        this.selectedEvidenceAnchorId = anchor.id
        this.thread = anchor.thread
      } else {
        this.paragraphIndex = 0
        this.selectedAnchorId = null
        this.selectedEvidenceAnchorId = null
      }
      return scene
    },
    selectScene(index, { keepPlaying = false } = {}) {
      if (this.workspaceKind !== 'sample') return
      this.applySampleScene(index)
      if (!keepPlaying) this.pause()
      this.syncTime()
    },
    selectSceneById(id) {
      if (this.workspaceKind !== 'sample') return
      const index = EXPLORATION_SCENES.findIndex((scene) => scene.id === id)
      if (index >= 0) this.selectScene(index)
    },
    selectParagraph(index, { keepPlaying = false } = {}) {
      if (this.workspaceKind !== 'sample') return
      const bounded = Math.max(0, Math.min(EXPLORATION_PARAGRAPHS.length - 1, Number(index) || 0))
      const anchor = EXPLORATION_PARAGRAPHS[bounded]
      const sceneIndex = EXPLORATION_SCENES.findIndex((scene) => scene.id === anchor?.sceneId)
      if (sceneIndex < 0 || !anchor) return
      this.selectScene(sceneIndex, { keepPlaying })
      this.paragraphIndex = bounded
      this.selectedAnchorId = anchor.id
      this.selectedEvidenceAnchorId = anchor.id
      this.thread = anchor.thread
    },
    setSourceTab(tab) {
      if (!['reader', 'web', 'timeline'].includes(tab)) return
      this.sourceTab = tab
      if (tab === 'reader') this.sourceState = 'reader_ready'
      if (tab === 'web') this.sourceState = 'web_limited'
    },
    setReaderView(view) {
      if (view === 'text' || view === 'anchors') this.readerView = view
    },
    returnToParagraph(index = this.paragraphIndex) {
      const bounded = Math.max(0, Math.min(EXPLORATION_PARAGRAPHS.length - 1, Number(index) || 0))
      return this.returnToAnchor(EXPLORATION_PARAGRAPHS[bounded]?.id)
    },
    returnToAnchor(id) {
      if (this.workspaceKind !== 'sample') return false
      const anchor = EXPLORATION_PARAGRAPHS.find((item) => item.id === id)
      if (!anchor) return false
      const anchorIndex = EXPLORATION_PARAGRAPHS.indexOf(anchor)
      this.setSourceTab('reader')
      this.setReaderView('text')
      this.selectParagraph(anchorIndex)
      return true
    },
    openLogicNode(node) {
      if (this.workspaceKind === 'sample' && node?.anchorId) {
        const anchorIndex = EXPLORATION_PARAGRAPHS.findIndex((anchor) => anchor.id === node.anchorId)
        if (anchorIndex >= 0) this.selectParagraph(anchorIndex)
      } else if (Number.isInteger(node?.sceneIndex)) {
        this.selectScene(node.sceneIndex)
      }
      this.selectedLogicNode = node
    },
    closeLogicNode() { this.selectedLogicNode = null },
    openEntry() {
      this.pause()
      this.stopAnalysisPolling()
      if (!PRIVATE_EXPLORATIONS_ENABLED) {
        this.openSample()
        return
      }
      this.entryOpen = true
    },
    continueWorkspace() {
      if (this.hasWorkspace) {
        this.entryOpen = false
        this.startAnalysisPolling()
      }
    },
    async startQuestion(prompt) {
      const value = String(prompt || '').trim()
      if (!value) return false
      this.pause()
      this.startingPrompt = true
      this.workspaceKind = 'question'
      this.entryOpen = false
      this.questionPrompt = value
      this.title = '问题探索'
      this.range = '范围待确认'
      this.snapshot = null
      this.privateExplorationId = null
      this.resetAnalysisState()
      this.companionNotice = ''
      this.questionSyncState = 'starting'
      this.selectedAnchorId = 'question'
      this.selectedSceneId = 'question-scope'
      this.selectedEvidenceAnchorId = 'question'
      this.sourceTab = 'reader'
      this.readerView = 'text'
      this.readingProgress = 0
      this.apiError = ''
      try {
        const snapshot = await startPromptExploration({ prompt: value })
        this.snapshot = snapshot
        this.questionSyncState = 'synced'
        this.selectedSceneId = snapshot.active_scene_id || 'question-scope'
        this.range = snapshot.brief?.time_range || '范围待确认'
        this.composerNotice = '研究问题已进入当前进程；等待你确认范围或补充材料'
        return true
      } catch (error) {
        this.questionSyncState = 'failed_local'
        this.apiError = error?.response?.data?.detail
          || '服务端未能建立研究范围；当前只保留本机草案，没有伪装为已同步'
        return false
      } finally {
        this.startingPrompt = false
      }
    },
    openSample() {
      this.pause()
      this.workspaceKind = 'sample'
      this.sampleDemoId = ANSHI_PUBLIC_DEMO.id
      this.entryOpen = false
      this.questionPrompt = ''
      this.title = ANSHI_PUBLIC_DEMO.title
      this.range = ANSHI_PUBLIC_DEMO.range
      this.snapshot = null
      this.privateExplorationId = null
      this.resetAnalysisState()
      this.companionNotice = ''
      this.questionSyncState = 'idle'
      this.activeImportedAnchorId = null
      this.selectedAnchorId = null
      this.selectedSceneId = null
      this.selectedEvidenceAnchorId = null
      this.selectedEvidenceId = null
      this.selectedLogicNode = null
      this.readingProgress = 0
      this.webProgressLabel = ''
      this.webPastedExcerpt = ''
      this.composerText = ''
      this.composerNotice = ''
      this.apiError = ''
      paragraphIndexDocumentId = null
      paragraphIndex = new Map()
      this.sourceTab = 'reader'
      this.sourceState = 'reader_ready'
      this.readerView = 'text'
      this.applySampleScene(DEFAULT_SAMPLE_SCENE_INDEX)
      this.syncTime()
    },
    openPlayer() { this.playerOpen = true },
    closePlayer() {
      this.playerOpen = false
      this.pause()
    },
    pause() {
      this.playbackStatus = 'paused'
      clearInterval(playbackTimer)
      playbackTimer = 0
    },
    stopAnalysisPolling() {
      clearTimeout(analysisPollTimer)
      analysisPollTimer = 0
    },
    resetAnalysisState() {
      this.stopAnalysisPolling()
      this.analysisRuns = []
      this.activeAnalysisRunId = null
      this.analysisRefreshing = false
      this.analysisAction = ''
      this.analysisError = ''
      this.analysisResult = null
      this.analysisReviewDecisions = {}
      this.publishedAnalysisView = 'argument'
    },
    upsertAnalysisRun(run) {
      if (!run?.id) return
      if (this.activeAnalysisRunId && this.activeAnalysisRunId !== run.id) {
        this.analysisResult = null
        this.analysisReviewDecisions = {}
      }
      const index = this.analysisRuns.findIndex((item) => item.id === run.id)
      if (index >= 0) this.analysisRuns.splice(index, 1, run)
      else this.analysisRuns.push(run)
      this.activeAnalysisRunId = run.id
    },
    scheduleAnalysisPoll() {
      this.stopAnalysisPolling()
      const shouldPoll = POLLED_ANALYSIS_STATES.has(this.activeAnalysisRun?.state)
        || (this.activeAnalysisRun?.state === 'waiting_review' && this.analysisResult?.review_submitted)
      if (!shouldPoll) return
      analysisPollTimer = window.setTimeout(async () => {
        await this.refreshActiveAnalysisRun({ silent: true })
        this.scheduleAnalysisPoll()
      }, 1800)
    },
    startAnalysisPolling() {
      if (!PRIVATE_EXPLORATIONS_ENABLED || !this.snapshot?.id) return
      this.scheduleAnalysisPoll()
    },
    async refreshAnalysisRuns({ silent = false } = {}) {
      if (!PRIVATE_EXPLORATIONS_ENABLED || !this.snapshot?.id || this.isSampleWorkspace) return false
      if (!silent) this.analysisRefreshing = true
      this.analysisError = ''
      try {
        const result = await listExplorationAnalysisRuns(this.snapshot.id)
        this.analysisRuns = Array.isArray(result?.items) ? result.items : []
        const activeStillExists = this.analysisRuns.some((run) => run.id === this.activeAnalysisRunId)
        if (!activeStillExists) this.activeAnalysisRunId = this.analysisRuns.at(-1)?.id || null
        if (['waiting_review', 'completed'].includes(this.activeAnalysisRun?.state)) {
          await this.refreshAnalysisResult({ silent: true })
        }
        this.scheduleAnalysisPoll()
        return true
      } catch (error) {
        this.analysisError = error?.response?.data?.detail || '分析状态暂时无法读取'
        return false
      } finally {
        if (!silent) this.analysisRefreshing = false
      }
    },
    async refreshActiveAnalysisRun({ silent = false } = {}) {
      const runId = this.activeAnalysisRunId
      if (!PRIVATE_EXPLORATIONS_ENABLED || !this.snapshot?.id || !runId) return false
      if (!silent) this.analysisRefreshing = true
      this.analysisError = ''
      try {
        const run = await getExplorationAnalysisRun(this.snapshot.id, runId)
        this.upsertAnalysisRun(run)
        if (['waiting_review', 'completed'].includes(run.state)) {
          await this.refreshAnalysisResult({ silent: true })
        }
        return true
      } catch (error) {
        this.analysisError = error?.response?.data?.detail || '分析状态暂时无法读取'
        return false
      } finally {
        if (!silent) this.analysisRefreshing = false
      }
    },
    async createAnalysisRun() {
      if (!PRIVATE_EXPLORATIONS_ENABLED || !this.snapshot?.id || this.isSampleWorkspace) return false
      this.analysisAction = 'creating'
      this.analysisError = ''
      try {
        const run = await createExplorationAnalysisRun(this.snapshot.id, this.snapshot.revision)
        this.analysisResult = null
        this.analysisReviewDecisions = {}
        this.upsertAnalysisRun(run)
        this.composerNotice = '已创建分析任务；等待独立 worker 处理'
        this.scheduleAnalysisPoll()
        return true
      } catch (error) {
        this.analysisError = error?.response?.data?.detail || '无法创建深度分析'
        return false
      } finally {
        this.analysisAction = ''
      }
    },
    async cancelAnalysisRun() {
      const runId = this.activeAnalysisRun?.id
      if (!this.snapshot?.id || !runId || !this.canCancelAnalysis) return false
      this.analysisAction = 'cancelling'
      this.analysisError = ''
      try {
        const run = await cancelExplorationAnalysisRun(this.snapshot.id, runId)
        this.upsertAnalysisRun(run)
        this.stopAnalysisPolling()
        return true
      } catch (error) {
        this.analysisError = error?.response?.data?.detail || '取消失败'
        return false
      } finally {
        this.analysisAction = ''
      }
    },
    async resumeAnalysisRun() {
      const runId = this.activeAnalysisRun?.id
      if (!this.snapshot?.id || !runId || !this.canResumeAnalysis) return false
      this.analysisAction = 'resuming'
      this.analysisError = ''
      try {
        const run = await resumeExplorationAnalysisRun(this.snapshot.id, runId)
        this.upsertAnalysisRun(run)
        this.scheduleAnalysisPoll()
        return true
      } catch (error) {
        this.analysisError = error?.response?.data?.detail || '恢复失败'
        return false
      } finally {
        this.analysisAction = ''
      }
    },
    async refreshAnalysisResult({ silent = false } = {}) {
      const runId = this.activeAnalysisRunId
      if (!PRIVATE_EXPLORATIONS_ENABLED || !this.snapshot?.id || !runId) return false
      if (!silent) this.analysisRefreshing = true
      this.analysisError = ''
      try {
        const result = await getExplorationAnalysisResult(this.snapshot.id, runId)
        const previousToken = this.analysisResult?.review_token
        this.analysisResult = result
        this.upsertAnalysisRun(result.status)
        if (previousToken && previousToken !== result.review_token) this.analysisReviewDecisions = {}
        return true
      } catch (error) {
        this.analysisError = error?.response?.data?.detail || '分析结果暂时无法读取'
        return false
      } finally {
        if (!silent) this.analysisRefreshing = false
      }
    },
    setAnalysisReviewDecision(artifactType, artifactId, decision) {
      if (!['claim', 'event'].includes(artifactType) || !['accepted', 'rejected'].includes(decision)) return
      this.analysisReviewDecisions = {
        ...this.analysisReviewDecisions,
        [`${artifactType}:${artifactId}`]: decision,
      }
    },
    async submitAnalysisReview() {
      const run = this.activeAnalysisRun
      const result = this.analysisResult
      if (!this.snapshot?.id || !run?.id || !result?.review_token || result.review_submitted) return false
      if (!this.reviewReady) {
        this.analysisError = '请先逐项接受或拒绝所有候选'
        if (this.reviewDependencyError) this.analysisError = this.reviewDependencyError
        return false
      }
      this.analysisAction = 'reviewing'
      this.analysisError = ''
      try {
        const decisions = this.analysisCandidateItems.map((item) => ({
          artifact_type: item.artifact_type,
          artifact_id: item.id,
          decision: this.analysisReviewDecisions[`${item.artifact_type}:${item.id}`],
        }))
        const next = await submitExplorationAnalysisReview(this.snapshot.id, run.id, {
          review_token: result.review_token,
          decisions,
        })
        this.analysisResult = next
        this.upsertAnalysisRun(next.status)
        this.composerNotice = '复核决定已提交；等待 worker 生成发布投影'
        this.scheduleAnalysisPoll()
        return true
      } catch (error) {
        this.analysisError = error?.response?.data?.detail || '复核提交失败'
        return false
      } finally {
        this.analysisAction = ''
      }
    },
    start() {
      if (this.sceneIndex >= EXPLORATION_SCENES.length - 1) this.selectScene(0)
      this.playbackStatus = 'playing'
      clearInterval(playbackTimer)
      playbackTimer = setInterval(() => {
        if (this.sceneIndex >= EXPLORATION_SCENES.length - 1) {
          this.playbackStatus = 'ended'
          clearInterval(playbackTimer)
          playbackTimer = 0
          return
        }
        this.selectScene(this.sceneIndex + 1, { keepPlaying: true })
      }, PLAY_STEP_MS / this.rate)
    },
    togglePlayback() {
      if (this.playbackStatus === 'playing') this.pause()
      else this.start()
    },
    setRate(rate) {
      if (![0.5, 1, 1.5].includes(Number(rate))) return
      const wasPlaying = this.isPlaying
      this.rate = Number(rate)
      if (wasPlaying) this.start()
    },
    submitComposer() {
      return this.composeQuestion()
    },
    async importPrivateText({ content, sourceFormat, title, author, versionLabel }) {
      if (!content?.trim()) return false
      this.importing = true
      this.apiError = ''
      try {
        this.snapshot = await importExploration({
          content,
          source_format: sourceFormat,
          title: title || undefined,
          author: author || undefined,
          version_label: versionLabel || undefined,
          brief: {
            question: '这份文本如何组织事件、作者判断与证据关系？',
            time_range: null,
            geography: [],
            threads: ['文本结构', '时空线索', '证据关系'],
            status: 'draft',
          },
        })
        this.workspaceKind = 'document'
        this.privateExplorationId = this.snapshot.id
        this.companionNotice = ''
        this.resetAnalysisState()
        this.questionSyncState = 'idle'
        this.entryOpen = false
        this.title = this.snapshot.document.title
        this.range = '时间与空间待确认'
        this.sourceTab = 'reader'
        this.readerView = 'text'
        const firstAnchorId = this.firstImportedParagraph?.id || null
        this.applyImportedAnchor(firstAnchorId)
        this.readingProgress = 0
        this.composerNotice = `已导入 ${this.snapshot.document.paragraph_count} 个段落锚点`
        return true
      } catch (error) {
        this.apiError = error?.response?.data?.detail || '导入失败，请检查文本后重试'
        return false
      } finally {
        this.importing = false
      }
    },
    async importPrivateEpub({ filename, contentBase64, title }) {
      if (!contentBase64) return false
      this.epubImporting = true
      this.apiError = ''
      try {
        this.snapshot = await importExplorationEpub({
          filename,
          content_base64: contentBase64,
          title: title || filename?.replace(/\.epub$/i, '') || undefined,
          brief: {
            question: '这本书如何组织事件、作者判断与证据关系？',
            time_range: null,
            geography: [],
            threads: ['文本结构', '时空线索', '证据关系'],
            status: 'draft',
          },
        })
        this.workspaceKind = 'document'
        this.privateExplorationId = this.snapshot.id
        this.companionNotice = ''
        this.resetAnalysisState()
        this.questionSyncState = 'idle'
        this.entryOpen = false
        this.title = this.snapshot.document.title
        this.range = '时间与空间待确认'
        this.sourceTab = 'reader'
        this.readerView = 'text'
        this.applyImportedAnchor(this.firstImportedParagraph?.id || null)
        this.readingProgress = 0
        this.composerNotice = `EPUB 已解析为 ${this.snapshot.document.paragraph_count} 个段落锚点`
        return true
      } catch (error) {
        this.apiError = error?.response?.data?.detail || 'EPUB 导入失败，请检查文件后重试'
        return false
      } finally {
        this.epubImporting = false
      }
    },
    async composeQuestion() {
      const message = this.composerText.trim()
      if (!message) return false
      if (!this.snapshot) {
        this.composerNotice = '请先导入一本书或材料；示范摘要不会冒充原文'
        return false
      }
      this.composing = true
      this.apiError = ''
      try {
        await mutationChain
        const anchorId = this.activeImportedAnchorId || this.snapshot.active_anchor_id || this.firstImportedParagraph?.id
        const result = await composeExploration(this.snapshot.id, {
          base_revision: this.snapshot.revision,
          intent: 'question',
          message,
          anchor_ids: anchorId ? [anchorId] : [],
        })
        this.snapshot = result.snapshot
        this.composerText = ''
        this.composerNotice = '问题已记录；尚未调用模型'
        return true
      } catch (error) {
        this.apiError = error?.response?.data?.detail || '记录失败，请重试'
        return false
      } finally {
        this.composing = false
      }
    },
    applyImportedAnchor(id) {
      if (!id) return
      this.activeImportedAnchorId = id
      this.selectedAnchorId = id
      this.selectedSceneId = `anchor-context:${id}`
      this.selectedEvidenceAnchorId = id
    },
    applyReadingProgress(snapshot, { selectAnchor = true } = {}) {
      const progress = snapshot?.reading_progress
      if (!progress) return
      this.setReadingProgress(progress.progression_percent)
      if (selectAnchor && progress.anchor_id) this.applyImportedAnchor(progress.anchor_id)
    },
    applyExternalReadingBridge(snapshot) {
      const bridge = snapshot?.external_reading_bridge
      if (!bridge) return
      this.webProgressLabel = bridge.external_locator || ''
      this.webPastedExcerpt = bridge.user_provided_excerpt || ''
    },
    async enqueueMutation(payload, {
      hydrateReading = false,
      hydrateExternal = false,
      failureNotice = '服务端同步失败；本地选择仍保留',
    } = {}) {
      const explorationId = this.snapshot?.id
      if (!explorationId) return false
      const execute = async () => {
        if (this.snapshot?.id !== explorationId) return false
        const next = await mutateExploration(explorationId, {
          ...payload,
          base_revision: this.snapshot.revision,
        })
        if (this.snapshot?.id !== explorationId) return false
        this.snapshot = next
        if (hydrateReading) this.applyReadingProgress(next)
        if (hydrateExternal) this.applyExternalReadingBridge(next)
        return true
      }
      const queued = mutationChain.then(execute, execute)
      mutationChain = queued.catch(() => false)
      try {
        return await queued
      } catch (error) {
        this.apiError = error?.response?.data?.detail || failureNotice
        this.composerNotice = failureNotice
        return false
      }
    },
    async updateScopeContract({ timeRange, geography, threads }) {
      if (this.workspaceKind !== 'question' || !this.snapshot?.scope_contract) return false
      const suppliedTime = String(timeRange || '').trim()
      const suppliedGeography = [...new Set((geography || []).map((item) => String(item).trim()).filter(Boolean))]
      const suppliedThreads = [...new Set((threads || []).map((item) => String(item).trim()).filter(Boolean))]
      if (!suppliedTime && !suppliedGeography.length && !suppliedThreads.length) return false
      const payload = { type: 'update_scope_contract' }
      if (suppliedTime) payload.user_supplied_time_range = suppliedTime
      if (suppliedGeography.length) payload.user_supplied_geography = suppliedGeography
      if (suppliedThreads.length) payload.user_supplied_threads = suppliedThreads
      this.updatingScope = true
      this.apiError = ''
      try {
        const updated = await this.enqueueMutation(payload, {
          failureNotice: '范围更新未写入服务端；输入仍保留',
        })
        if (updated) {
          this.range = this.snapshot.brief?.time_range || '范围待确认'
          this.composerNotice = this.snapshot.scope_contract.fields_needing_confirmation.length
            ? '范围已更新；仍有字段待确认'
            : '时间、空间与叙事主线已确认'
        }
        return updated
      } finally {
        this.updatingScope = false
      }
    },
    async selectImportedAnchor(id, { sync = true } = {}) {
      if (!this.snapshot || !this.importedParagraphRecord(id)) return
      this.applyImportedAnchor(id)
      if (!sync) return
      // update_reading_progress 同时更新 active_anchor_id；只发一次串行 mutation，
      // 避免它与 set_active_anchor 争用同一个 base_revision。
      return this.enqueueMutation(
        { type: 'update_reading_progress', anchor_id: id },
        { hydrateReading: true, failureNotice: '段落已在本地选中；服务端阅读进度同步失败' },
      )
    },
    setReadingProgress(value) {
      const next = Number(value)
      if (Number.isFinite(next)) this.readingProgress = Math.max(0, Math.min(100, next))
    },
    async syncWebReading({ progressLabel, excerpt }) {
      const nextProgress = String(progressLabel || '').trim()
      const nextExcerpt = String(excerpt || '').trim()
      if (!nextProgress) return false
      if (!this.snapshot) {
        this.apiError = '当前示例没有服务端探索会话；阅读位置未伪装为已同步'
        return false
      }
      this.syncingWeb = true
      this.apiError = ''
      try {
        const synced = await this.enqueueMutation({
          type: 'sync_external_reading_progress',
          provider: 'weread',
          url: 'https://weread.qq.com/',
          external_locator: nextProgress,
          user_provided_excerpt: nextExcerpt || null,
        }, {
          hydrateExternal: true,
          failureNotice: '微信读书阅读位置未同步到服务端；本地输入仍保留',
        })
        if (synced) {
          if (this.webPastedExcerpt) {
            this.selectedAnchorId = 'web-bridge'
            this.selectedSceneId = 'web-context'
            this.selectedEvidenceAnchorId = 'web-bridge'
          }
          this.composerNotice = '已手动同步阅读进度；不会自动读取微信读书 DOM'
        }
        return synced
      } finally {
        this.syncingWeb = false
      }
    },
    async receiveCompanionSelection({ url, title, locator, text }) {
      if (!this.hasWorkspace) {
        return { status: 'no_workspace', reason: 'no_workspace' }
      }
      const progressLabel = locator || title
      if (this.isSampleWorkspace) {
        this.webProgressLabel = progressLabel
        this.webPastedExcerpt = text
        this.selectedAnchorId = 'web-bridge'
        this.selectedSceneId = 'web-context'
        this.selectedEvidenceAnchorId = 'web-bridge'
        this.companionNotice = '微信读书选区 · 仅本地临时联动'
        this.composerNotice = '公开演示只做本地临时联动，未写入服务端'
        return { status: 'local_only' }
      }
      if (!this.snapshot?.id) {
        this.companionNotice = '当前工作区尚未同步，微信读书选区未写入'
        return { status: 'failed', reason: 'workspace_not_synced' }
      }

      const synced = await this.enqueueMutation({
        type: 'sync_external_reading_progress',
        provider: 'weread',
        url,
        external_locator: progressLabel,
        user_provided_excerpt: text,
      }, {
        hydrateExternal: true,
        failureNotice: '微信读书选区未同步到当前会话',
      })
      if (!synced) {
        this.companionNotice = '微信读书选区同步失败'
        return { status: 'failed', reason: 'sync_failed' }
      }
      this.selectedAnchorId = 'web-bridge'
      this.selectedSceneId = 'web-context'
      this.selectedEvidenceAnchorId = 'web-bridge'
      this.companionNotice = '微信读书选区 · 已写入当前会话'
      this.composerNotice = '微信读书选区已同步到当前探索 revision'
      return { status: 'synced', revision: this.snapshot.revision }
    },
  },
})
