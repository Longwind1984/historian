<template>
  <section class="xentry" data-testid="exploration-entry">
    <div class="xentry-intro">
      <span class="xentry-seal">探</span>
      <p>从一个历史问题，或一份你真正拥有的材料开始。系统先建立可回看的范围与锚点，不预设已有书籍，也不把模型建议写成史实。</p>
    </div>

    <button v-if="store.hasWorkspace" class="xentry-current" @click="store.continueWorkspace()">
      <span>继续当前探索</span>
      <strong>{{ currentWorkspaceLabel }}</strong>
      <ArrowRight :size="16" />
    </button>

    <div class="xentry-main">
      <form class="xentry-card question" @submit.prevent="startQuestion">
        <div class="xentry-icon"><MessagesSquare :size="21" /></div>
        <small>从问题开始</small>
        <h2>你想理解哪段历史？</h2>
        <p>先记录问题，再确认时间、空间与叙事主线。当前步骤不会调用模型或生成结论。</p>
        <textarea v-model="question" aria-label="输入历史问题" placeholder="例如：靖难之役如何改变明初的权力结构？"></textarea>
        <div class="xentry-actions">
          <button class="primary" type="submit" :disabled="!question.trim() || store.startingPrompt">
            <LoaderCircle v-if="store.startingPrompt" class="spin" :size="15" />
            <template v-else>开始框定范围 <ArrowRight :size="15" /></template>
            <template v-if="store.startingPrompt">正在建立范围</template>
          </button>
          <button ref="uploadTriggerRef" class="secondary" type="button" aria-haspopup="dialog" @click="openUpload">
            <BookUp :size="15" />上传本地书籍
          </button>
          <small>EPUB · TXT · Markdown</small>
        </div>
      </form>
    </div>

    <p v-if="store.apiError" class="xentry-error" role="alert">{{ store.apiError }}</p>

    <button class="xentry-demo" type="button" @click="openPublicDemo">
      <PlayCircle :size="16" />
      <span><strong>打开《安史之乱：历史、宣传与神话》公开演示</strong><small>九幕时空编排 · 原创衍生摘要 · 原文受限</small></span>
      <ArrowRight :size="15" />
    </button>

    <Teleport to="body">
      <div v-if="uploadOpen" class="xupload-backdrop" @click.self="closeUpload">
        <section ref="uploadDialogRef" class="xupload-dialog" role="dialog" aria-modal="true" aria-labelledby="xupload-title" tabindex="-1" @keydown.esc="closeUpload">
          <header>
            <div>
              <small>私人材料 · 当前进程临时保存</small>
              <h2 id="xupload-title">上传本地书籍</h2>
            </div>
            <button type="button" aria-label="关闭上传窗口" @click="closeUpload"><X :size="16" /></button>
          </header>
          <p>支持 EPUB、TXT、Markdown。文件只用于当前探索；EPUB 保留章节顺序，纯文本建立段落锚点。</p>
          <label class="file-picker" :class="{ selected: selectedFile }">
            <input type="file" accept=".txt,.md,.markdown,.epub,text/plain,text/markdown,application/epub+zip" @change="onFile" />
            <FileUp :size="19" />
            <span>{{ selectedFile ? selectedFile.name : '选择本地书籍' }}</span>
            <small>{{ selectedFile ? `${formatLabel} · ${readableSize}` : 'EPUB · TXT · Markdown' }}</small>
          </label>
          <p v-if="store.apiError" class="xupload-error" role="alert">{{ store.apiError }}</p>
          <footer>
            <button type="button" @click="closeUpload">取消</button>
            <button class="primary" type="button" :disabled="!selectedFile || busy" @click="importSelected">
              <LoaderCircle v-if="busy" class="spin" :size="15" />
              <BookOpen v-else :size="15" />
              {{ busy ? '正在建立锚点' : '导入并进入阅读器' }}
            </button>
          </footer>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import ArrowRight from '@lucide/vue/dist/esm/icons/arrow-right.mjs'
import BookOpen from '@lucide/vue/dist/esm/icons/book-open.mjs'
import BookUp from '@lucide/vue/dist/esm/icons/book-up.mjs'
import FileUp from '@lucide/vue/dist/esm/icons/file-up.mjs'
import LoaderCircle from '@lucide/vue/dist/esm/icons/loader-circle.mjs'
import MessagesSquare from '@lucide/vue/dist/esm/icons/messages-square.mjs'
import PlayCircle from '@lucide/vue/dist/esm/icons/circle-play.mjs'
import X from '@lucide/vue/dist/esm/icons/x.mjs'
import { ANSHI_PUBLIC_DEMO, ANSHI_PUBLIC_SCENES } from '../../data/anshiPublicDemo'
import { useExplorationStore } from '../../stores/useExplorationStore'

const store = useExplorationStore()
const question = ref('')
const selectedFile = ref(null)
const format = ref('')
const uploadOpen = ref(false)
const uploadDialogRef = ref(null)
const uploadTriggerRef = ref(null)
const busy = computed(() => store.importing || store.epubImporting)
const formatLabel = computed(() => format.value === 'epub' ? 'EPUB' : format.value === 'markdown' ? 'Markdown' : 'TXT')
const readableSize = computed(() => {
  const size = selectedFile.value?.size || 0
  return size < 1024 * 1024 ? `${Math.max(1, Math.round(size / 1024))} KB` : `${(size / 1024 / 1024).toFixed(1)} MB`
})
const currentWorkspaceLabel = computed(() => {
  if (store.workspaceKind === 'sample') return `${ANSHI_PUBLIC_DEMO.title}公开演示`
  if (store.workspaceKind === 'question') return store.questionPrompt
  return store.snapshot?.document?.title || '私人材料'
})

function openPublicDemo() {
  store.openSample()
  store.title = '安史之乱'
  store.range = ANSHI_PUBLIC_DEMO.range
  store.sceneIndex = Math.max(
    0,
    ANSHI_PUBLIC_SCENES.findIndex((scene) => scene.id === ANSHI_PUBLIC_DEMO.defaultSceneId),
  )
}

async function startQuestion() {
  if (await store.startQuestion(question.value)) question.value = ''
}
async function openUpload() {
  store.apiError = ''
  uploadOpen.value = true
  await nextTick()
  uploadDialogRef.value?.focus()
}
async function closeUpload() {
  if (busy.value) return
  uploadOpen.value = false
  selectedFile.value = null
  format.value = ''
  store.apiError = ''
  await nextTick()
  uploadTriggerRef.value?.focus()
}
function onFile(event) {
  const file = event.target.files?.[0] || null
  selectedFile.value = file
  const name = file?.name || ''
  format.value = /\.epub$/i.test(name) || file?.type === 'application/epub+zip'
    ? 'epub'
    : /\.md(?:own)?$/i.test(name) || file?.type === 'text/markdown'
      ? 'markdown'
      : 'text'
  store.apiError = ''
}
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  const chunkSize = 0x8000
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize))
  }
  return btoa(binary)
}
async function importSelected() {
  const file = selectedFile.value
  if (!file) return
  let ok = false
  if (format.value === 'epub') {
    const contentBase64 = arrayBufferToBase64(await file.arrayBuffer())
    ok = await store.importPrivateEpub({
      filename: file.name,
      contentBase64,
      title: file.name.replace(/\.epub$/i, ''),
    })
  } else {
    ok = await store.importPrivateText({
      content: await file.text(),
      sourceFormat: format.value,
      title: file.name.replace(/\.(txt|md|markdown)$/i, ''),
    })
  }
  if (ok) {
    selectedFile.value = null
    uploadOpen.value = false
  }
}
</script>

<style scoped>
.xentry{height:100%;overflow:auto;padding:clamp(24px,5vh,56px) clamp(18px,6vw,76px);background:linear-gradient(135deg,var(--paper),var(--paper-el))}
.xentry-intro{max-width:760px;display:flex;align-items:flex-start;gap:13px;margin:0 auto 24px}.xentry-seal{width:42px;height:42px;display:grid;place-items:center;flex:none;border-radius:7px;background:var(--accent);color:var(--accent-text);font-family:var(--serif);font-size:18px;font-weight:900}.xentry-intro p{margin:3px 0 0;color:var(--ink-mid);font-family:var(--serif);font-size:14px;line-height:1.8}
.xentry-current,.xentry-demo{width:min(760px,100%);display:flex;align-items:center;gap:11px;margin:0 auto 16px;padding:11px 14px;text-align:left;border-radius:8px}.xentry-current span{color:var(--ink-soft);font-size:9px}.xentry-current strong{min-width:0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}
.xentry-main{width:min(760px,100%);margin:0 auto}.xentry-card{display:flex;min-height:330px;flex-direction:column;align-items:flex-start;padding:26px;border:1px solid var(--line);border-radius:12px;background:var(--paper-el);box-shadow:0 8px 28px rgba(42,34,24,.07)}.xentry-icon{width:38px;height:38px;display:grid;place-items:center;margin-bottom:16px;border-radius:9px;background:var(--chip);color:var(--accent)}.xentry-card>small{color:var(--accent);font-size:9px;letter-spacing:.12em}.xentry-card h2{margin:6px 0 8px;font-family:var(--serif);font-size:20px}.xentry-card>p{margin:0 0 16px;color:var(--ink-soft);font-size:10px;line-height:1.7}.xentry-card textarea{width:100%;min-height:120px;flex:1;resize:vertical;padding:13px;border:1px solid var(--line);border-radius:7px;background:var(--paper);color:var(--ink);font:inherit;font-size:12px;line-height:1.7}.xentry-actions{width:100%;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,.72fr);gap:8px;margin-top:12px}.xentry-actions button{display:flex;align-items:center;justify-content:center;gap:6px;padding:10px}.xentry-actions .secondary{background:var(--paper)}.xentry-actions>small{grid-column:2;color:var(--ink-faint);font-size:8px;text-align:center}
.file-picker{width:100%;min-height:128px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;padding:15px;border:1px dashed var(--line);border-radius:7px;background:var(--paper);color:var(--ink-soft);cursor:pointer}.file-picker.selected{border-color:var(--accent);color:var(--accent)}.file-picker input{display:none}.file-picker span{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}.file-picker small{font-size:8px}
.xentry-error{max-width:900px;margin:10px auto 0;padding:9px 11px;border:1px solid color-mix(in srgb,var(--danger) 35%,var(--line));border-radius:7px;color:var(--danger);background:var(--paper-el);font-size:10px}.xentry-demo{margin-top:16px;background:transparent}.xentry-demo>span{min-width:0;display:grid;gap:2px;flex:1}.xentry-demo strong{font-family:var(--serif);font-size:11px}.xentry-demo small{color:var(--ink-soft);font-size:8px}.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.xupload-backdrop{position:fixed;z-index:1200;inset:0;display:grid;place-items:center;padding:18px;background:rgba(24,20,16,.38);backdrop-filter:blur(3px)}.xupload-dialog{width:min(520px,100%);display:grid;gap:13px;padding:18px;border:1px solid var(--line);border-radius:11px;background:var(--paper-el);color:var(--ink);box-shadow:0 18px 60px rgba(0,0,0,.24);outline:none}.xupload-dialog>header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.xupload-dialog>header div{display:grid;gap:3px}.xupload-dialog>header small{color:var(--accent);font-size:8px;letter-spacing:.08em}.xupload-dialog h2{margin:0;font-family:var(--serif);font-size:18px}.xupload-dialog>header button{width:30px;height:30px;display:grid;place-items:center;padding:0}.xupload-dialog>p{margin:0;color:var(--ink-soft);font-size:10px;line-height:1.65}.xupload-dialog>footer{display:flex;justify-content:flex-end;gap:7px}.xupload-dialog>footer button{display:flex;align-items:center;justify-content:center;gap:5px;min-width:96px}.xupload-error{padding:8px;border:1px solid color-mix(in srgb,var(--danger) 35%,var(--line));border-radius:6px;color:var(--danger)!important;background:var(--paper);font-size:9px!important}
@media(max-width:720px){.xentry{padding:18px 12px}.xentry-intro{margin-bottom:14px}.xentry-intro p{font-size:12px}.xentry-card{min-height:300px;padding:17px}.xentry-actions{grid-template-columns:1fr}.xentry-actions>small{grid-column:1}.xentry-demo{align-items:flex-start}.xupload-backdrop{padding:10px}.xupload-dialog{padding:15px}}
</style>
