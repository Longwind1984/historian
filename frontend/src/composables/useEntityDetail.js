import { ref } from 'vue'
import { getEntity, getNeighbors, getContemporaries, getOutboundLinks, getBacklinks, getLinkCounts, deriveEventCausal } from '../api/client'

/**
 * EntityProfile 的加载层（D2：本文件曾是无人 import 的死代码，复活为唯一档案数据入口）。
 * 统一承载档案卡的四类数据——实体本体、关系（Event 因果链复用同一次 neighbors 推导）、
 * wiki 出入链、同代人物。每类都记 loadedFor：同一实体不重复请求（实体本体另由
 * client.getEntity 的模块级缓存兜底），切走再切回也不闪「读取中」。
 * 何时取数由调用方（EntityProfile）按 tab 惰性策略决定，本层只管「要就拿、拿过不重拿」。
 */
export function useEntityDetail() {
  // === 实体本体 ===
  const entity = ref(null)
  const loading = ref(false)
  const entityLoadedFor = ref(null)

  // === 关系（边级：一个邻居可有多条边；因果链由此推导）===
  const relations = ref([])
  const relationsLoading = ref(false)
  const relationsLoadedFor = ref(null)
  const causal = ref(null)

  // === wiki 出入链 ===
  const outboundLinks = ref([])
  const backlinks = ref([])
  const linkCounts = ref(null)
  const linkCountsFor = ref(null)   // 角标计数属于哪个实体（链接 tab 首次加载后写入）
  const linksLoading = ref(false)
  const linksLoadedFor = ref(null)

  // === 同代人物 ===
  const contemporaries = ref(null)
  const contemporariesLoading = ref(false)
  const contemporariesLoadedFor = ref(null)

  async function loadEntity(id) {
    if (!id) { entity.value = null; entityLoadedFor.value = null; return }
    if (entityLoadedFor.value === id && entity.value) return
    loading.value = true
    try {
      entity.value = await getEntity(id)
      entityLoadedFor.value = id
    } catch {
      entity.value = null
      // 失败不记 loadedFor：下次进入允许重试
    } finally {
      loading.value = false
    }
  }

  async function ensureRelations(id) {
    if (!id || relationsLoadedFor.value === id || relationsLoading.value) return
    relationsLoading.value = true
    try {
      const r = await getNeighbors(id, 1)
      const nodeMap = new Map((r.nodes || []).map(n => [n.id, n]))
      relations.value = (r.edges || []).map((e, i) => {
        const isFrom = e.from === id
        const otherId = isFrom ? e.to : e.from
        const other = nodeMap.get(otherId) || {}
        return {
          // 按边取键而非邻居 id：关系密集的人物（刘秀/卫青实测）同一邻居有多条边，
          // 用邻居 id 作 v-for key 必撞。
          key: `${e.from}|${e.type}|${e.to}|${i}`,
          edgeType: e.type,
          otherId,
          otherName: other.name || otherId,
          otherType: other.type || 'Person',
          otherImage: other.image || null,
          otherBorn: other.born?.year ?? null,
          otherDied: other.died?.year ?? null,
          direction: isFrom ? '→' : '←',
          note: e.note || '',
          since: e.since?.year ?? null,
          until: e.until?.year ?? null,
          sortKey: (isFrom ? '0' : '1') + e.type,
        }
      }).sort((a, b) => a.sortKey.localeCompare(b.sortKey))
      // Event 因果链（T4.5）：复用同一 neighbors 结果，不另发请求
      const derived = deriveEventCausal(r.edges || [], id)
      const withName = (arr) => arr.map(x => ({
        id: x.id,
        name: nodeMap.get(x.id)?.name || x.id,
        note: x.note || '',
      }))
      causal.value = {
        causes: withName(derived.causes),
        effects: withName(derived.effects),
        parts: withName(derived.parts),
        concurrent: withName(derived.concurrent),
      }
      relationsLoadedFor.value = id
    } catch {
      // 落空也记 loadedFor：tab 显示「无关系数据」而非永远转圈
      relations.value = []
      causal.value = null
      relationsLoadedFor.value = id
    } finally {
      relationsLoading.value = false
    }
  }

  // 全量出入链：惰性，切到「链接」tab 才取（既有行为不变）
  async function ensureLinks(id) {
    if (!id || linksLoadedFor.value === id || linksLoading.value) return
    linksLoading.value = true
    try {
      const [out, back, counts] = await Promise.all([
        getOutboundLinks(id), getBacklinks(id), getLinkCounts(id),
      ])
      outboundLinks.value = out.mentions || []
      backlinks.value = back.backlinks || []
      linkCounts.value = counts
      linkCountsFor.value = id
      linksLoadedFor.value = id
    } catch {
      outboundLinks.value = []
      backlinks.value = []
      linksLoadedFor.value = id
    } finally {
      linksLoading.value = false
    }
  }

  async function ensureContemporaries(id, midYear) {
    if (!id || contemporariesLoadedFor.value === id || contemporariesLoading.value) return
    // 无生卒可据时不发请求，直接空态（可能生卒年缺失）
    if (!midYear) { contemporaries.value = []; contemporariesLoadedFor.value = id; return }
    contemporariesLoading.value = true
    try {
      const r = await getContemporaries(id, midYear, 60)
      // 响应形态：{ person, year, count, contemporaries: [...] }
      const list = r.contemporaries || r.items || (Array.isArray(r) ? r : [])
      contemporaries.value = list.filter(p => p.id !== id)
      contemporariesLoadedFor.value = id
    } catch {
      contemporaries.value = []
      contemporariesLoadedFor.value = id
    } finally {
      contemporariesLoading.value = false
    }
  }

  return {
    entity, loading, entityLoadedFor,
    relations, relationsLoading, relationsLoadedFor, causal,
    outboundLinks, backlinks, linkCounts, linkCountsFor, linksLoading, linksLoadedFor,
    contemporaries, contemporariesLoading, contemporariesLoadedFor,
    loadEntity, ensureRelations, ensureLinks, ensureContemporaries,
  }
}
