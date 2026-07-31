// 星云数据适配器：拉 spacetime（节点/朝代/双链度）+ links/global（边）-> galaxy GraphData。
// 设计 §3：星=实体，只取 links≥1 入图（约 1100 个）；星径=ln(1+links)（renderer sizeMode='logLinks'）；
// 星色=朝代（threePalette.dynastyColorFn 读稳定 node.dynasty id）。
//
// 数据源：
//   GET /api/graph/spacetime -> { meta, dynasties:[{id,name,from,to}], nodes:[{id,name,type,born,died,x,y,dynasty,links}] }
//     节点已含 links=out+in 双链度；朝代实体本身不进 nodes（时空柱轴）。
//   GET /api/links/global?limit=2000&min_links=1 -> { nodes, edges:[{from,to,type}] }
//     后端 limit 上限 400（Query le=400）：limit=2000 会 422，兜底降为 400 取顶部连通子图。
//     星仍来自 spacetime 全量（~1100），仅边受 400 上限约束--未取到边的星以电荷斥力浮游成晕。

import { api, getGlobalGraph } from '../../api/client.js';

/**
 * 拉取并装配星云图。
 * @returns {Promise<{
 *   nodes: any[], links: {source:number,target:number}[],
 *   indexByEntityId: Map<string,number>, dynastyOrder: string[], meta: any
 * }>}
 */
export async function fetchNebulaGraph() {
  // 并行拉两份数据
  const [stRes, globalRes] = await Promise.all([
    api.get('/graph/spacetime').then((r) => r.data),
    fetchGlobalEdges(),
  ]);

  const dynasties = stRes.dynasties || [];
  // 朝代顺序只服务 labelLOD 的 cluster 分组，不参与颜色语义。颜色按 dynasty id 查表，
  // 否则 API 加入夏商周后，秦会从 idx=0 变 idx=3，整张色板随之错位。
  const dynastyOrder = dynasties
    .map((d) => ({ id: d.id, from: d.from }))
    .sort((a, b) => (a.from ?? 1e9) - (b.from ?? 1e9))
    .map((d) => d.id);
  const dynastyIdxMap = new Map(dynastyOrder.map((id, i) => [id, i]));

  // 节点：spacetime 全量中 links≥1 者（设计 §3 硬性过滤）
  const rawNodes = (stRes.nodes || []).filter((n) => (n.links || 0) >= 1);
  const indexByEntityId = new Map();
  const nodes = rawNodes.map((n, i) => {
    indexByEntityId.set(n.id, i);
    const did = n.dynasty || null;
    return {
      id: i, // galaxy 内部按数组下标引用
      origId: n.id,
      name: n.name || n.id,
      title: n.name || n.id,
      slug: n.id, // focusNode / connect-two 按 entityId 查
      dynasty: did,
      dynastyIdx: did != null ? (dynastyIdxMap.has(did) ? dynastyIdxMap.get(did) : -1) : -1,
      type: n.type || 'Person',
      links: n.links || 0, // logLinks 星径
      degree: n.links || 0, // hub 排序/锚定备用
      cluster: did != null ? (dynastyIdxMap.get(did) ?? -1) : -1, // 复用 labelLOD cluster 通道
      born: n.born,
      died: n.died,
      created: null,
      inDegree: 0,
      outDegree: 0,
      fileSize: 0,
      unresolved: false,
    };
  });

  // 边：global edges，仅保留两端都在星集中的（spacetime 已排除 Dynasty，故朝代边天然丢弃）
  const links = [];
  for (const e of globalRes.edges || []) {
    const s = indexByEntityId.get(e.from);
    const t = indexByEntityId.get(e.to);
    if (s === undefined || t === undefined || s === t) continue;
    links.push({ source: s, target: t });
  }

  return { nodes, links, indexByEntityId, dynastyOrder, meta: stRes.meta || {} };
}

/**
 * 拉 global 边：先按设计要求 limit=2000（若后端放宽上限则一次拿全），
 * 422（当前 le=400 上限）则降级 limit=400 取顶部连通子图。
 */
async function fetchGlobalEdges() {
  try {
    return await getGlobalGraph(2000, 1);
  } catch (e) {
    // 422 / 400 校验失败 -> 退到后端硬上限
    return getGlobalGraph(400, 1);
  }
}
