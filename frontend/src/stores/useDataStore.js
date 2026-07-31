import { defineStore } from 'pinia'
import { getSchema, getStats, getEntityTypes } from '../api/client'

/** 数据 store：schema / stats / entityTypes，启动加载一次 */
export const useDataStore = defineStore('data', {
  state: () => ({
    schema: null,
    stats: null,
    entityTypes: [],
    loaded: false,
  }),
  getters: {
    typeMeta: (state) => (type) => {
      const node = state.schema?.node_types?.[type] || {}
      const meta = state.entityTypes.find(t => t.type === type) || {}
      return {
        label: node.label || meta.label || type,
        labelEn: node.label_en || meta.label_en || type,
        color: meta.color || `var(--cat-${type.toLowerCase()})`,
      }
    },
    relationMeta: (state) => (type) => {
      const rels = state.schema?.relations || []
      return rels.find(r => r.type === type) || { type, label: type, color: 'var(--edge)' }
    },
  },
  actions: {
    async init() {
      if (this.loaded) return
      try {
        const [schema, stats, types] = await Promise.all([
          getSchema(), getStats(), getEntityTypes(),
        ])
        this.schema = schema
        this.stats = stats
        this.entityTypes = types
        this.loaded = true
      } catch (e) {
        console.error('DataStore init failed:', e)
      }
    },
  },
})
