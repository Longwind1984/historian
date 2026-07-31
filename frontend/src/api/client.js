const BASE = (import.meta.env.VITE_API_BASE || '') + '/api'

export const api = {
  async get(path, { params } = {}) {
    const query = new URLSearchParams()
    for (const [key, value] of Object.entries(params || {})) {
      if (value != null) query.set(key, String(value))
    }
    const queryString = query.toString()
    const url = `${BASE}${path}${queryString ? `?${queryString}` : ''}`
    const response = await fetch(url)
    const text = await response.text()
    const mediaType = (response.headers.get('content-type') || '').split(';', 1)[0].trim().toLowerCase()
    const isJson = mediaType === 'application/json' || mediaType === 'text/json' || mediaType.endsWith('+json')
    let data = text || null
    if (text && isJson) {
      try {
        data = JSON.parse(text)
      } catch (parseError) {
        // 错误响应仍须携带 HTTP status/response；成功响应的畸形 JSON 则如实报解析错误。
        if (response.ok) throw parseError
      }
    }
    const result = { data, status: response.status, headers: response.headers }

    if (!response.ok) {
      const error = new Error(`GET ${url} failed with status ${response.status}`)
      error.name = 'HttpError'
      error.status = response.status
      error.response = result
      throw error
    }
    return result
  },
}

async function sendJson(path, { method = 'POST', body } = {}) {
  const url = `${BASE}${path}`
  const response = await fetch(url, {
    method,
    headers: body == null ? undefined : { 'content-type': 'application/json' },
    body: body == null ? undefined : JSON.stringify(body),
  })
  const text = await response.text()
  let data = text || null
  if (text) {
    try { data = JSON.parse(text) } catch {}
  }
  if (!response.ok) {
    const error = new Error(`${method} ${url} failed with status ${response.status}`)
    error.name = 'HttpError'
    error.status = response.status
    error.response = { data, status: response.status, headers: response.headers }
    throw error
  }
  return data
}

// === 实体缓存：同一实体不重复请求 ===
const _entityCache = new Map()

export async function getSchema() {
  const { data } = await api.get('/meta/schema')
  return data
}

export async function getStats() {
  const { data } = await api.get('/meta/stats')
  return data
}

export async function getEntityTypes() {
  const { data } = await api.get('/meta/entity_types')
  return data
}

export async function getEntities(params) {
  const { data } = await api.get('/entities', { params })
  return data
}

export async function getEntity(id) {
  if (_entityCache.has(id)) return _entityCache.get(id)
  const { data } = await api.get(`/entities/${id}`)
  _entityCache.set(id, data)
  return data
}

export function invalidateEntityCache(id) {
  if (id) _entityCache.delete(id)
  else _entityCache.clear()
}

export async function getNeighbors(id, depth = 1) {
  const { data } = await api.get(`/entities/${id}/neighbors`, { params: { depth } })
  return data
}

export async function getRelations({ type, from, to, year, limit = 500, offset = 0 } = {}) {
  const { data } = await api.get('/relations', { params: { type, from, to, year, limit, offset } })
  return data
}

export async function getShortestPath(fromId, toId, maxDepth = 4) {
  const { data } = await api.get('/graph/shortest', { params: { from: fromId, to: toId, max_depth: maxDepth } })
  return data
}

export async function getContemporaries(personId, year, radius = 50) {
  const { data } = await api.get('/graph/contemporaries', { params: { person: personId, year, radius } })
  return data
}

export async function getFactionMembers(factionId, year) {
  const { data } = await api.get('/graph/faction', { params: { id: factionId, year } })
  return data
}

export async function getTerritories(year) {
  const { data } = await api.get('/territories', { params: { year } })
  return data
}

export async function getTimeline(fromYear, toYear, type) {
  const { data } = await api.get('/timeline', { params: { from: fromYear, to: toYear, type } })
  return data
}

export async function getMapStory(fromYear, toYear, limit = 1000) {
  const { data } = await api.get('/timeline/map-story', {
    params: { from: fromYear, to: toYear, limit },
  })
  return data
}

// === 私人书籍探索（进程内临时保存，不写入历史事实库）===
export function importExploration(payload) {
  return sendJson('/explorations/import', { body: payload })
}

export function startPromptExploration(payload) {
  return sendJson('/explorations/from-prompt', { body: payload })
}

// EPUB 保持独立合同，避免把二进制伪装成 text/markdown。
export function importExplorationEpub(payload) {
  return sendJson('/explorations/import-epub', { body: payload })
}

export async function getExploration(id) {
  const { data } = await api.get(`/explorations/${id}`)
  return data
}

export function composeExploration(id, payload) {
  return sendJson(`/explorations/${id}/compose`, { body: payload })
}

export function mutateExploration(id, payload) {
  return sendJson(`/explorations/${id}/mutations`, { body: payload })
}

export function deleteExploration(id) {
  return sendJson(`/explorations/${id}`, { method: 'DELETE' })
}

// === Wiki-style links ===
export async function getOutboundLinks(id) {
  const { data } = await api.get(`/links/scan/${id}`)
  return data
}

export async function getBacklinks(id) {
  const { data } = await api.get(`/links/backlinks/${id}`)
  return data
}

export async function getLinkCounts(id) {
  const { data } = await api.get(`/links/count/${id}`)
  return data
}

export async function fullTextSearch(q, limit = 20) {
  const { data } = await api.get('/links/search', { params: { q, limit } })
  return data
}

export async function getGlobalGraph(limit = 150, minLinks = 1) {
  const { data } = await api.get('/links/global', { params: { limit, min_links: minLinks } })
  return data
}

// === 朝代聚合全局视图（T2.2 渐进加载）===
export async function getGlobalGraphByDynasty() {
  const { data } = await api.get('/links/global_by_dynasty')
  return data
}

export async function getDynastyEntities(dynastyId, limit = 40, offset = 0) {
  const { data } = await api.get(`/links/global_by_dynasty/${dynastyId}`, { params: { limit, offset } })
  return data
}

// === 事件因果链推导（T4.5）===
// 从 neighbors 返回的 edges 推导本事件的「前因 / 后果 / 从属 / 同期」。
// 约定：led_to = from 导致 to；caused_by = from 起因于 to（互为逆语义）；
//       part_of = from 从属 to；concurrent_with 无向。
// 返回 { causes, effects, parts, concurrent }，每项 { id, note }，name 由调用方用 nodeMap 补。
export function deriveEventCausal(edges, selfId) {
  const causes = [], effects = [], parts = [], concurrent = []
  for (const e of edges || []) {
    const t = e.type
    if (t === 'led_to') {
      if (e.from === selfId) effects.push({ id: e.to, note: e.note })
      else if (e.to === selfId) causes.push({ id: e.from, note: e.note })
    } else if (t === 'caused_by') {
      // A caused_by B = B 是 A 的原因
      if (e.from === selfId) causes.push({ id: e.to, note: e.note })
      else if (e.to === selfId) effects.push({ id: e.from, note: e.note })
    } else if (t === 'part_of') {
      if (e.from === selfId) parts.push({ id: e.to, note: e.note })
    } else if (t === 'concurrent_with') {
      const other = e.from === selfId ? e.to : (e.to === selfId ? e.from : null)
      if (other) concurrent.push({ id: other, note: e.note })
    }
  }
  return { causes, effects, parts, concurrent }
}
