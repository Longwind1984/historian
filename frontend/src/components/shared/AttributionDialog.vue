<template>
  <Teleport to="body">
    <div class="credits-backdrop" @click.self="close">
      <section
        id="attribution-dialog"
        ref="dialogRef"
        class="credits-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="credits-title"
        aria-describedby="credits-intro"
        tabindex="-1"
        @keydown.stop="onKeydown"
      >
        <header class="credits-head">
          <div>
            <div class="credits-kicker">来源 · 许可 · 致谢</div>
            <h2 id="credits-title">资料来源与致谢</h2>
          </div>
          <div class="credits-head-meta">
            <span class="credits-version">版本 v{{ release.version }} · {{ releaseRevision }}</span>
            <button class="credits-close" type="button" @click="close">关闭</button>
          </div>
        </header>

        <p id="credits-intro" class="credits-intro">
          历史全景知识台是一个非商业的个人研究与展示项目。感谢以下开放数据、地图资料与开源工具，
          让跨时间、地理与人物关系的探索成为可能。
        </p>

        <div class="credits-list">
          <article class="credit-item">
            <div class="credit-index">壹</div>
            <div>
              <h3>
                <a href="https://cbdb.hsites.harvard.edu/" target="_blank" rel="noopener noreferrer">
                  中国历代人物传记资料库（CBDB）
                </a>
              </h3>
              <p>提供人物、亲属、社会关系、官职与籍贯数据。本站依 CC BY-NC-SA 4.0 用于非商业个人展示，并保留署名与相同方式共享义务。</p>
              <p class="credit-links">
                <a href="https://cbdb.hsites.harvard.edu/exclusive-commercial-license" target="_blank" rel="noopener noreferrer">CBDB 官方许可说明</a>
                <span aria-hidden="true">·</span>
                <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans" target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>
              </p>
            </div>
          </article>

          <article class="credit-item">
            <div class="credit-index">贰</div>
            <div>
              <h3><a href="https://chgis.fas.harvard.edu/" target="_blank" rel="noopener noreferrer">中国历史地理信息系统（CHGIS）</a></h3>
              <p v-if="restrictedMapsEnabled">提供历代府级行政建置与历史地理数据。本站按年份筛选 CHGIS V5 府级时序记录，并移除可能被误解为政权归属的导入字段；不提供原始数据下载。</p>
              <p v-else>本公开分发版不包含 CHGIS 几何；实体模型仍保留历史来源标识，因此继续展示固定署名。</p>
              <p class="credit-citation">CHGIS Version 5. © Fairbank Center for Chinese Studies and the Institute for Chinese Historical Geography at Fudan University, Jan 2012.</p>
            </div>
          </article>

          <article class="credit-item">
            <div class="credit-index">叁</div>
            <div>
              <h3><a href="https://history-map.osgeo.cn/" target="_blank" rel="noopener noreferrer">《中国历史地图集》配准地图</a></h3>
              <p v-if="restrictedMapsEnabled">“古”底图采用 OSGeo 中国中心发布的谭其骧《中国历史地图集》配准瓦片，用于非商业的历史空间浏览与学习。</p>
              <p v-else>本公开分发版不附带或请求这些配准瓦片；这里保留来源记录，供本地研究构建审计。</p>
            </div>
          </article>

          <article class="credit-item credit-item-tools">
            <div class="credit-index">器</div>
            <div>
              <h3>开源技术</h3>
              <p class="tool-links">
                <a href="https://vuejs.org/" target="_blank" rel="noopener noreferrer">Vue</a><span aria-hidden="true">·</span>
                <a href="https://vite.dev/" target="_blank" rel="noopener noreferrer">Vite</a><span aria-hidden="true">·</span>
                <a href="https://fastapi.tiangolo.com/" target="_blank" rel="noopener noreferrer">FastAPI</a><span aria-hidden="true">·</span>
                <a href="https://maplibre.org/maplibre-gl-js/docs/" target="_blank" rel="noopener noreferrer">MapLibre GL JS</a><span aria-hidden="true">·</span>
                <a href="https://www.wikimedia.org/" target="_blank" rel="noopener noreferrer">Wikimedia Commons</a>
              </p>
              <p>感谢开源社区，以及为人物图像保留作者与许可链的 Wikimedia Commons 贡献者。</p>
            </div>
          </article>
        </div>

        <footer class="credits-foot">谨以此页向资料整理者、研究者与开源贡献者致谢。</footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { RESTRICTED_MAPS_ENABLED as restrictedMapsEnabled } from '../../config/distribution'

const release = __APP_RELEASE__
const releaseRevision = release.revision.split('+')[0]
const emit = defineEmits(['close'])
const dialogRef = ref(null)
let returnFocusTo = null
let backgroundRoot = null
let backgroundWasInert = false
const focusableSelector = ['a[href]', 'button:not([disabled])', '[tabindex]:not([tabindex="-1"])'].join(',')

onMounted(async () => {
  returnFocusTo = document.activeElement
  backgroundRoot = document.getElementById('app')
  backgroundWasInert = Boolean(backgroundRoot?.inert)
  if (backgroundRoot) backgroundRoot.inert = true
  await nextTick()
  dialogRef.value?.focus()
})

onBeforeUnmount(() => {
  if (backgroundRoot) backgroundRoot.inert = backgroundWasInert
  if (returnFocusTo instanceof HTMLElement) returnFocusTo.focus()
})

function close() { emit('close') }

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (event.key !== 'Tab') return

  const focusable = Array.from(dialogRef.value?.querySelectorAll(focusableSelector) ?? [])
  if (!focusable.length) {
    event.preventDefault()
    dialogRef.value?.focus()
    return
  }
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}
</script>

<style scoped>
.credits-backdrop {
  position: fixed; inset: 0; z-index: 200; display: grid; place-items: center;
  padding: 24px; background: rgba(30, 25, 20, 0.42); backdrop-filter: blur(3px);
}
.credits-dialog {
  width: min(680px, 100%); max-height: min(760px, calc(100vh - 48px)); overflow-y: auto;
  padding: 28px 30px 24px; border: 1px solid var(--line); border-radius: 10px;
  outline: none; background: var(--paper-el); color: var(--ink);
  box-shadow: 0 24px 64px rgba(28, 22, 16, 0.24);
}
.credits-dialog:focus-visible { box-shadow: 0 0 0 2px var(--accent), 0 24px 64px rgba(28, 22, 16, 0.24); }
.credits-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding-bottom: 18px; border-bottom: 1px solid var(--line); }
.credits-kicker { margin-bottom: 5px; color: var(--accent); font-family: var(--serif); font-size: 10px; letter-spacing: 0.24em; }
h2 { font-family: var(--serif); font-size: 24px; line-height: 1.25; }
.credits-head-meta { display: grid; justify-items: end; gap: 8px; }
.credits-close { flex: 0 0 auto; padding: 5px 9px; color: var(--ink-soft); font-size: 12px; }
.credits-intro { margin: 18px 0 6px; color: var(--ink-mid); font-family: var(--serif); font-size: 14px; line-height: 1.8; }
.credits-list { display: grid; }
.credit-item { display: grid; grid-template-columns: 30px 1fr; gap: 13px; padding: 17px 0; border-bottom: 1px solid var(--hair); }
.credit-index { display: flex; align-items: center; justify-content: center; width: 27px; height: 27px; border: 1px solid color-mix(in srgb, var(--accent) 55%, var(--line)); border-radius: 5px; color: var(--accent); font-family: var(--serif); font-size: 11px; }
h3 { margin: 1px 0 6px; font-family: var(--serif); font-size: 15px; line-height: 1.4; }
h3 a { color: var(--ink); }
.credit-item p { color: var(--ink-mid); font-size: 12.5px; line-height: 1.7; }
.credit-citation { margin-top: 6px; font-size: 11.5px !important; }
.credit-links { margin-top: 6px; font-size: 11.5px; }
.credit-links span, .tool-links span { margin: 0 5px; color: var(--ink-faint); }
.tool-links { margin-bottom: 5px; }
.credits-foot { padding-top: 18px; color: var(--ink-soft); font-family: var(--serif); font-size: 12px; text-align: center; }
.credits-version { color: var(--ink-faint); font-family: var(--mono); font-size: 10px; letter-spacing: 0.06em; }
@media (max-width: 600px) {
  .credits-backdrop { align-items: end; padding: 0; }
  .credits-dialog { max-height: 88vh; padding: 22px 20px 20px; border-radius: 12px 12px 0 0; }
  .credits-head { gap: 14px; padding-bottom: 15px; }
  h2 { font-size: 21px; }
  .credits-intro { margin-top: 15px; font-size: 13px; }
  .credit-item { grid-template-columns: 27px 1fr; gap: 10px; padding: 14px 0; }
}
@media (prefers-reduced-motion: no-preference) {
  .credits-backdrop { animation: credits-fade 0.14s ease-out; }
  .credits-dialog { animation: credits-rise 0.18s ease-out; }
}
@keyframes credits-fade { from { opacity: 0; } }
@keyframes credits-rise { from { transform: translateY(8px); opacity: 0; } }
</style>
