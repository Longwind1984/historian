// 星云墨色系统：朝代->色相 + 主题->视觉 token。
// 移植自 Rick 自研 galaxy 引擎（原按 cluster 着色）；
// 本站改按【朝代】着色（设计 §3：星色=朝代），主题走 CSS 变量（夜=深空引擎原生，澄=ink-on-paper）。
//
// 墨色 token 契约（mount -> renderer.applyTokens）：
//   readTokens(hostEl, paletteKey):VisualTokens  —— 与 presets.js 的 DEEP_SPACE/DAYLIGHT 同形

import { DEEP_SPACE } from './presets.js';

// ---- 14 朝代雅色（单一来源：星云/时空柱/图谱三视图共享）----
// 数组顺序只服务 WebGraph 的本地 14 段范围。spacetime API 已含夏商周、民国、共和国
// 共 19 朝代，绝不能再拿 API 数组下标套本数组；星云/时空柱必须走下方稳定 id 映射。
// T3.4 压雅：原色板纸色主题偏糖果感 -> 整体降饱和（HSL S 38–46%）、明度收窄（L 47–57%），
// 色相保持朝代可辨；参考 palettes.js 墨感（赭石/黛青/藤黄/竹青一路）。相邻朝代给相邻色相，
// 时间相近者视觉相近。
// · 夜主题：源色直取 + bloom+白核发光（深空需亮星），S 已收敛不荧光；
// · 纸主题：renderer.recolor 以 nodeLightness 统一压亮度（保色相），时空柱直取源色亦雅。
export const DYNASTY_COLORS = [
  '#c4a25f', // 0  秦      缃黄
  '#b67943', // 1  汉      赭石
  '#bc5849', // 2  三国    朱砂
  '#b9556e', // 3  晋      胭脂
  '#af4b91', // 4  南北朝  紫绛
  '#7f5cbc', // 5  隋      青莲
  '#506dbe', // 6  唐      黛蓝
  '#46a7aa', // 7  五代十国 黛青
  '#46aa7b', // 8  辽      苔绿
  '#81b446', // 9  宋      竹青
  '#beac50', // 10 金      藤黄
  '#bc8249', // 11 元      橙赭
  '#aa6a46', // 12 明      褐墨
  '#844aa5', // 13 清      黛紫
];

export const NEUTRAL_DYNASTY_HEX = '#9aa4b2';

// 稳定的实体 id -> 既有 14 色。夏/商/周/民国/共和国尚无拍板色，诚实落 neutral；
// 未知 id 同样落 neutral。按 id 而非返回顺序取色，后端新增/重排 Dynasty 都不会串色。
export const DYNASTY_ID_ORDER = Object.freeze([
  'd_qin', 'd_han', 'd_sanguo', 'd_jin', 'd_nanbeichao', 'd_sui', 'd_tang',
  'd_wudai', 'd_liao', 'd_song', 'd_jin_jurchen', 'd_yuan', 'd_ming', 'd_qing',
]);

export const DYNASTY_COLOR_BY_ID = Object.freeze(Object.fromEntries(
  DYNASTY_ID_ORDER.map((id, i) => [id, DYNASTY_COLORS[i]]),
));

// 雾环的扇区与颜色使用同一份稳定 id 顺序。API 增删或重排 Dynasty 都不改变既有布局。
export const DYNASTY_SECTOR_BY_ID = Object.freeze(Object.fromEntries(
  DYNASTY_ID_ORDER.map((id, i) => [id, i]),
));

export function dynastySectorIndexById(dynastyId) {
  return DYNASTY_SECTOR_BY_ID[dynastyId] ?? null;
}

export function dynastyHexById(dynastyId) {
  return DYNASTY_COLOR_BY_ID[dynastyId] || NEUTRAL_DYNASTY_HEX;
}

// 14 朝代年份区间（founded 升序；下标与 DYNASTY_COLORS 对齐，故顺序不可改）。
// 图谱(WebGraph) 本地归属用此（global/neighbors API 不返 dynasty 字段）-> 三视图朝代色一致。
//
// 注意：这些区间彼此重叠——辽 916~1125 与宋 960~1279 本就并存。故「按年份取首个命中」
// 判不出 1050 年的人是辽是宋（那取决于他在哪，不取决于何时）；辽排在宋前面时，
// 960~1125 出生的人会全被判成辽人（后端曾因此把 748 人判给辽，而真辽人只有 32 个）。
// 归属的权威依据是 person.dynasty_ref（其所属政权），年份只作缺失时的回落，
// 且回落时并存朝代降级最后再试。见 COEXISTING_DYNASTY_IDX 与 WebGraph.dynastyIdxOf。
export const DYNASTY_RANGES = [
  ['秦', -221, -207],
  ['汉', -202, 220],
  ['三国', 220, 280],
  ['晋', 265, 420],
  ['南北朝', 420, 589],
  ['隋', 581, 618],
  ['唐', 618, 907],
  ['五代十国', 907, 979],
  ['辽', 916, 1125],
  ['宋', 960, 1279],
  ['金', 1115, 1234],
  ['元', 1271, 1368],
  ['明', 1368, 1644],
  ['清', 1636, 1912],
];

// 与中原断代并存者（辽=8、金=10）。年份回落匹配时降级到最后再试，否则它们会因 founded
// 更早而独吞重叠年份里的所有人。这不是「谁是正统」的判断——真正的辽/金人物都带
// dynasty_ref，走不到年份回落这条路。
export const COEXISTING_DYNASTY_IDX = new Set([8, 10]);

/** 朝代名 -> DYNASTY_RANGES 下标（= DYNASTY_COLORS 下标） */
export const DYNASTY_NAME_TO_IDX = Object.fromEntries(
  DYNASTY_RANGES.map(([name], i) => [name, i]),
);

// ---- 主题 -> 视觉 token ----

function readVar(el, name, fallback) {
  const v = getComputedStyle(el).getPropertyValue(name).trim();
  return v || fallback;
}

/**
 * 读 CSS 变量适配主题。
 *   夜（dark）-> DEEP_SPACE（引擎原生深空 + bloom + 星壳）
 *   澄（light）-> ink-on-paper（底=--paper、连线=淡墨--edge、星=朝代色经 nodeLightness 压墨、
 *     选中高亮用 --accent；关 bloom/星壳）
 * @param {HTMLElement} hostEl 星云画布宿主（已应用 palette CSS 变量）
 * @param {string} paletteKey PALETTES 键：'澄'|'夜'
 * @param {{dark:boolean}} meta PALETTES[key].dark
 */
export function readTokens(hostEl, paletteKey, meta) {
  if (meta?.dark || paletteKey === '夜') return DEEP_SPACE;
  const paper = readVar(hostEl, '--paper', '#f2ebdd');
  const edge = readVar(hostEl, '--edge', '#cdc0a4');
  const accent = readVar(hostEl, '--accent', '#c24a32');
  return {
    id: 'ink-on-paper',
    background: paper, // THREE.Color 接受 CSS hex 字符串
    starfield: false, // 纸面无星壳，留白自净
    motes: false,
    bloomEnabled: false, // 亮底辉光=雾霾，强制关
    lightMode: true, // 节点 shader 走墨水圆盘 + rim
    nodeLightness: 0.5, // 朝代色相压成中明度墨色坐回纸面（T3.4：0.4->0.5，落 L 45–60% 区间，保色相）
    linkInk: edge, // 淡墨连线
    linkOpacityScale: 0.7,
    panelClass: 'gx-theme-light',
    accent, // 选中高亮朱印晕（mount 用于 hover/select 强调）
  };
}
