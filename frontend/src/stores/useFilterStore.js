import { defineStore } from 'pinia'

// T4.6 人物身份/重要性共享筛选状态
// focusMode 默认开（只看重点人物 importance∈{1,2}）；activeRoles 非空=只显 roles 相交的人物（OR）
// 持久化到 localStorage；不进 URL（避免 hash 过长）
const LS_KEY = 'history-kb-filter-v1'

function loadSaved() {
  try {
    const s = JSON.parse(localStorage.getItem(LS_KEY) || '{}')
    return {
      focusMode: typeof s.focusMode === 'boolean' ? s.focusMode : true,
      activeRoles: Array.isArray(s.activeRoles) ? s.activeRoles.filter(x => typeof x === 'string') : [],
    }
  } catch {
    return { focusMode: true, activeRoles: [] }
  }
}

export const useFilterStore = defineStore('filter', {
  state: () => loadSaved(),
  getters: {
    activeRoleSet: (s) => new Set(s.activeRoles),
    hasRoleFilter: (s) => s.activeRoles.length > 0,
  },
  actions: {
    _persist() {
      localStorage.setItem(LS_KEY, JSON.stringify({
        focusMode: this.focusMode,
        activeRoles: this.activeRoles,
      }))
    },
    toggleFocus() { this.focusMode = !this.focusMode; this._persist() },
    setFocus(v) { this.focusMode = !!v; this._persist() },
    toggleRole(key) {
      const i = this.activeRoles.indexOf(key)
      if (i >= 0) this.activeRoles.splice(i, 1)
      else this.activeRoles.push(key)
      this._persist()
    },
    clearRoles() { this.activeRoles.splice(0, this.activeRoles.length); this._persist() },

    // 单个实体是否通过筛选。非 Person 一律放行（仅人物受 role/importance 约束）。
    // e: { type?, roles?, importance? } —— importance 为 null/undefined 视为最低档（CBDB 未标注）
    passes(e) {
      if (!e || e.type !== 'Person') return true
      if (this.focusMode) {
        const imp = e.importance
        if (imp !== 1 && imp !== 2) return false
      }
      if (this.activeRoles.length > 0) {
        const roles = e.roles || []
        if (!roles.some(r => this.activeRoles.indexOf(r) >= 0)) return false
      }
      return true
    },
  },
})
