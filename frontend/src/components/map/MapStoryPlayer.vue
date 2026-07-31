<template>
  <div class="map-story-controls" data-testid="map-story-controls"
       role="group" aria-label="地图历史播放">
    <button class="map-story-button" type="button" aria-label="上一个历史条目"
            :disabled="storyStore.loading || !storyStore.entries.length || storyStore.index <= 0"
            @click="previousStory">
      <SkipBack :size="17" :stroke-width="1.9" aria-hidden="true" />
    </button>
    <button class="map-story-button map-story-primary" type="button"
            :aria-label="storyStore.playing ? '暂停地图历史播放' : '播放地图历史'"
            :aria-pressed="storyStore.playing" :disabled="storyStore.loading"
            @click="toggleStory">
      <Pause v-if="storyStore.playing" :size="18" :stroke-width="1.9" aria-hidden="true" />
      <Play v-else :size="18" :stroke-width="1.9" aria-hidden="true" />
    </button>
    <button class="map-story-button" type="button" aria-label="下一个历史条目"
            :disabled="storyStore.loading || !storyStore.entries.length || storyStore.index >= storyStore.entries.length - 1"
            @click="nextStory">
      <SkipForward :size="17" :stroke-width="1.9" aria-hidden="true" />
    </button>
    <span class="map-story-position" aria-label="播放位置">{{ storyStore.loading ? '载入中' : storyStore.position }}</span>
  </div>

  <div v-if="currentStory" class="map-story-card" data-testid="map-story-card"
       aria-live="polite" aria-atomic="true">
    <div class="map-story-kicker">
      <span>{{ currentStory.kind === 'life_event' ? `${currentStory.person_name} · 生平` : '历史事件' }}</span>
      <strong>{{ fmtY(currentStory.year) }}</strong>
    </div>
    <div class="map-story-title">{{ currentStory.title }}</div>
    <div v-if="currentStory.summary" class="map-story-summary">{{ currentStory.summary }}</div>
    <div v-if="currentStory.focus_note" class="map-story-focus-note">{{ currentStory.focus_note }}</div>
    <div v-if="currentStory.source" class="map-story-source">据 {{ currentStory.source }}</div>
  </div>
  <div v-else-if="storyStore.error" class="map-story-card map-story-error" role="status">
    {{ storyStore.error }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Pause from '@lucide/vue/dist/esm/icons/pause.mjs'
import Play from '@lucide/vue/dist/esm/icons/play.mjs'
import SkipBack from '@lucide/vue/dist/esm/icons/skip-back.mjs'
import SkipForward from '@lucide/vue/dist/esm/icons/skip-forward.mjs'
import { useMapStoryStore, useTimeStore } from '../../stores'
import { fmtY } from '../../styles/palettes'

const storyStore = useMapStoryStore()
const timeStore = useTimeStore()
const currentStory = computed(() => storyStore.current)

async function ensureReady() {
  await storyStore.ensureLoaded()
  return storyStore.entries.length > 0
}

async function toggleStory() {
  if (storyStore.playing) { storyStore.pause(); return }
  if (!await ensureReady()) return
  timeStore.stopPlay()
  storyStore.playFrom(timeStore.year)
}

async function nextStory() {
  if (!await ensureReady()) return
  timeStore.stopPlay()
  storyStore.next(timeStore.year)
}

async function previousStory() {
  if (!await ensureReady()) return
  timeStore.stopPlay()
  storyStore.previous(timeStore.year)
}
</script>

<style scoped>
.map-story-controls {
  position: absolute;
  left: 50%;
  bottom: 0.8rem;
  z-index: 7;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--caption);
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.16);
  backdrop-filter: blur(8px);
}
.map-story-button {
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-mid);
  background: transparent;
  cursor: pointer;
}
.map-story-button:hover { background: var(--hover); }
.map-story-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.map-story-button:disabled { opacity: 0.35; cursor: not-allowed; }
.map-story-button:disabled:hover { background: transparent; }
.map-story-primary { color: var(--accent-text); background: var(--accent); }
.map-story-primary:hover { background: var(--accent); opacity: 0.88; }
.map-story-position {
  min-width: 52px;
  padding: 0 7px 0 3px;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  text-align: center;
}
.map-story-card {
  position: absolute;
  right: 0.8rem;
  bottom: 3.9rem;
  z-index: 6;
  width: min(310px, calc(100% - 1.6rem));
  padding: 13px 15px;
  color: var(--ink);
  background: var(--caption);
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.16);
  backdrop-filter: blur(8px);
  pointer-events: none;
}
.map-story-kicker {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
}
.map-story-kicker strong { color: var(--accent); font-weight: 650; }
.map-story-title {
  margin-top: 5px;
  font-family: var(--serif);
  font-weight: 800;
  font-size: 17px;
  line-height: 1.35;
}
.map-story-summary {
  margin-top: 6px;
  color: var(--ink-soft);
  font-size: 12px;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.map-story-focus-note,
.map-story-source {
  margin-top: 6px;
  color: var(--ink-faint);
  font-size: 10px;
  line-height: 1.4;
}
.map-story-error { color: var(--ink-soft); }

/* 移动抽屉展开后地图净高约 220px：桌面四行卡会从容器顶部被裁掉。
   保留标题、年份、两行简介与来源，压缩留白而不是把浮窗整体隐藏。 */
@media (max-width: 720px) {
  .map-story-controls {
    bottom: 0.45rem;
    padding: 3px;
  }
  .map-story-button { width: 30px; height: 30px; }
  .map-story-position { min-width: 46px; padding-right: 4px; font-size: 10px; }
  .map-story-card {
    right: 0.55rem;
    bottom: 3.25rem;
    width: min(310px, calc(100% - 4.8rem));
    padding: 6px 9px;
  }
  .map-story-kicker { font-size: 9px; }
  .map-story-title { margin-top: 2px; font-size: 14px; line-height: 1.25; }
  .map-story-summary {
    margin-top: 3px;
    font-size: 11px;
    line-height: 1.35;
    -webkit-line-clamp: 1;
  }
  .map-story-focus-note,
  .map-story-source {
    margin-top: 3px;
    overflow: hidden;
    font-size: 9px;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
