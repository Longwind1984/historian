import { defineStore } from 'pinia'
import { getMapStory } from '../api/client'

const STORY_STEP_MS = 5200
let storyTimer = 0

function clearStoryTimer() {
  clearInterval(storyTimer)
  storyTimer = 0
}

/** 展开地图的历史播放单源；地图相机与时间轴只消费 current，不各自计时。 */
export const useMapStoryStore = defineStore('mapStory', {
  state: () => ({
    entries: [],
    index: -1,
    loaded: false,
    loading: false,
    playing: false,
    error: '',
  }),
  getters: {
    current: (state) => state.index >= 0 ? state.entries[state.index] || null : null,
    position: (state) => state.index >= 0 ? `${state.index + 1} / ${state.entries.length}` : `0 / ${state.entries.length}`,
  },
  actions: {
    async ensureLoaded() {
      if (this.loaded || this.loading) return
      this.loading = true
      this.error = ''
      try {
        const result = await getMapStory()
        this.entries = Array.isArray(result?.items) ? result.items : []
        this.loaded = true
      } catch {
        this.error = '历史播放清单暂不可用'
      } finally {
        this.loading = false
      }
    },
    seekFromYear(year) {
      if (!this.entries.length) { this.index = -1; return false }
      const found = this.entries.findIndex((entry) => entry.year >= year)
      this.index = found >= 0 ? found : 0
      return true
    },
    selectIndex(index) {
      if (!this.entries.length) { this.index = -1; return false }
      this.index = Math.max(0, Math.min(this.entries.length - 1, index))
      return true
    },
    playFrom(year) {
      if (!this.entries.length) return false
      if (this.index < 0) this.seekFromYear(year)
      if (this.playing) return true
      this.playing = true
      clearStoryTimer()
      storyTimer = setInterval(() => {
        if (this.index >= this.entries.length - 1) { this.pause(); return }
        this.index += 1
      }, STORY_STEP_MS)
      return true
    },
    pause() {
      this.playing = false
      clearStoryTimer()
    },
    next(year) {
      this.pause()
      if (this.index < 0) return this.seekFromYear(year)
      return this.selectIndex(this.index + 1)
    },
    previous(year) {
      this.pause()
      if (this.index < 0) return this.seekFromYear(year)
      return this.selectIndex(this.index - 1)
    },
    reset() {
      this.pause()
      this.index = -1
    },
  },
})
