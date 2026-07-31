// 两套配色方案：澄（日间）/ 夜（深色）。主题默认跟随系统色彩偏好。
// 用法:store.commit('setPalette', '澄') → applyPalette() 注入 CSS 变量

export const PALETTES = {
  澄: {
    name: '澄 · 校准暖纸',
    tagline: 'CALIBRATED',
    dark: false,
    paper: '#f2ebdd', paperEl: '#f9f3e7', line: '#e2d9c6', hair: '#ece3d0',
    ink: '#2c2721', inkMid: '#4a4539', inkSoft: '#8b8270', inkFaint: '#a9a08b',
    accent: '#c24a32', accentText: '#f9f3e7',
    hero1: '#f6f1e6', hero2: '#ece3cf', grid: '#d8cdb4', edge: '#cdc0a4',
    caption: 'rgba(249,243,231,0.92)', chip: '#f1e8d6', field: '#ece3d0',
    hover: 'rgba(0,0,0,0.045)', labelInk: '#4a4539',
    // D5 地图专用色:素底水面(mapPaper)与经纬网(mapGrid)随配色走,不再硬编码
    mapPaper: '#ece3cf', mapGrid: '#d8cdb4',
    cat: { Person: '#4a6f88', Polity: '#9c5a4a', Faction: '#78597a', Event: '#5a7d5f', Battle: '#a9743c', Place: '#4e7f7a', Title: '#8a7a3f', Dynasty: '#6d6555' },
    fam: { military: '#94714c', governance: '#70944c', external: '#4c948d', civilization: '#4c5294', power: '#8f4c94', other: '#6d6555' },
    onCat: '#f7f2e6', washMain: 0.20, washSec: 0.12,
    secWash: ['#7d8a6e', '#8a7d8a', '#6e7d8a'],
  },
  夜: {
    name: '夜 · 深色校准',
    tagline: 'OBSERVATORY',
    dark: true,
    paper: '#12181f', paperEl: '#1a212b', line: '#2a3542', hair: '#222c38',
    ink: '#e9e5d9', inkMid: '#b9c2cc', inkSoft: '#8996a3', inkFaint: '#67727e',
    accent: '#c8a24c', accentText: '#12181f',
    hero1: '#182230', hero2: '#0e141c', grid: '#202b38', edge: '#2c3947',
    caption: 'rgba(16,22,31,0.88)', chip: '#1f2833', field: '#141b24',
    hover: 'rgba(255,255,255,0.06)', labelInk: '#c3c9d2',
    mapPaper: '#0e141c', mapGrid: '#202b38',
    cat: { Person: '#7fa8d0', Polity: '#c7554a', Faction: '#a888c0', Event: '#6fb894', Battle: '#cf9a5b', Place: '#79b8b0', Title: '#c8b060', Dynasty: '#8a9ab0' },
    fam: { military: '#bc9a76', governance: '#99bc76', external: '#76bcb5', civilization: '#767cbc', power: '#b776bc', other: '#8a9ab0' },
    onCat: '#12181f', washMain: 0.36, washSec: 0.22,
    secWash: ['#5a7a8c', '#7a6a8c', '#8c7a5a'],
  },
}

export const PALETTE_KEYS = ['澄', '夜']

// 印章符号:7 类实体 + 朝代
export const SEALS = {
  Person: { glyph: '人', label: '人物', labelEn: 'Person' },
  Polity: { glyph: '國', label: '政权', labelEn: 'Polity' },
  Faction: { glyph: '黨', label: '派系', labelEn: 'Faction' },
  Event: { glyph: '事', label: '事件', labelEn: 'Event' },
  Battle: { glyph: '戰', label: '战役', labelEn: 'Battle' },
  Place: { glyph: '地', label: '地点', labelEn: 'Place' },
  Title: { glyph: '官', label: '官职', labelEn: 'Title' },
  Dynasty: { glyph: '朝', label: '朝代', labelEn: 'Dynasty' },
}

// 事件 5 族 18 类 + 兜底(与 schema/event.yaml 的 category 枚举一一对应)
// 族=配色(粗读:这是哪一类历史),类=印章字形(细读:具体是什么)。
// 字形取「一眼可认的单字」,并避开对同一事件的政治修辞:
//   rebellion 用「民」而非「亂」——「乱」是治者视角,辛亥革命非乱;「义」是举事者视角。
//   「民变」只陈述发动者,不预判正当性。
export const EVENT_CATS = {
  battle:      { glyph: '戰', label: '战役',      family: '军事' },
  war:         { glyph: '兵', label: '战争',      family: '军事' },
  conquest:    { glyph: '滅', label: '灭国·分合', family: '军事' },
  rebellion:   { glyph: '民', label: '民变·起义', family: '军事' },
  coup:        { glyph: '變', label: '政变·夺权', family: '权力' },
  succession:  { glyph: '繼', label: '继统·禅代', family: '权力' },
  purge:       { glyph: '禍', label: '党争·清洗', family: '权力' },
  founding:    { glyph: '立', label: '开国·立政', family: '权力' },
  reform:      { glyph: '革', label: '变法·改革', family: '治理' },
  institution: { glyph: '制', label: '制度·律令', family: '治理' },
  prosperity:  { glyph: '治', label: '治世·盛世', family: '治理' },
  diplomacy:   { glyph: '交', label: '外交·交流', family: '对外' },
  treaty:      { glyph: '盟', label: '盟约·条约', family: '对外' },
  territory:   { glyph: '土', label: '疆土·迁徙', family: '对外' },
  culture:     { glyph: '文', label: '文化·盛会', family: '文明' },
  religion:    { glyph: '教', label: '宗教',      family: '文明' },
  science:     { glyph: '工', label: '科技·工程', family: '文明' },
  disaster:    { glyph: '災', label: '灾难·疫荒', family: '文明' },
  other:       { glyph: '事', label: '其他',      family: '其他' },
}

export const EVENT_FAMILIES = ['军事', '权力', '治理', '对外', '文明', '其他']

// 族 -> CSS 变量名(ASCII slug)。注意:变量名必须与 applyPalette 注入的完全一致且全小写,
// 大小写不符会让 color-mix 整条静默失效(取不到色 = 全透明,不报错)。
export const FAMILY_SLUG = {
  军事: 'military', 权力: 'power', 治理: 'governance',
  对外: 'external', 文明: 'civilization', 其他: 'other',
}

// 族色为 5 族专设(不复用 8 类实体色):实体色里 Battle/Polity/Title 三个暖色只差 16-19 度色相,
// 而军事/权力/治理恰是最大的三族(占 71% 事件),复用会让「族」这层粗读彻底失效。
// 专设色按最小 59 度色相间隔排布,军事仍锚在 H=31(≈--cat-battle)以保住 Battle 实体的视觉收口。
export const FAMILY_HUE = Object.fromEntries(
  EVENT_FAMILIES.map(f => [f, `var(--fam-${FAMILY_SLUG[f]})`])
)

export function catMeta(category) {
  return EVENT_CATS[category] || EVENT_CATS.other
}

export function catHue(category) {
  return FAMILY_HUE[catMeta(category).family] || FAMILY_HUE['其他']
}

// 朝代年表(用于时间柱 gutter)
export const ERAS = [
  ['夏', -2070, -1600],
  ['商', -1600, -1046],
  ['西周', -1046, -771],
  ['春秋', -771, -476],
  ['戰國', -476, -221],
  ['秦', -221, -206],
  ['漢', -206, 220],
  ['三國', 220, 280],
  ['兩晉', 280, 420],
  ['南北朝', 420, 589],
  ['隋', 589, 618],
  ['唐', 618, 907],
  ['五代十國', 907, 960],
  ['宋', 960, 1279],
  ['元', 1279, 1368],
  ['明', 1368, 1644],
  ['清', 1644, 1912],
  ['民國', 1912, 1949],
  ['共和國', 1949, 2026],
]

// 主要年号(用于年份读数)
export const NIANHAO = [
  [627, 649, '貞觀'], [690, 705, '天授'], [713, 741, '開元'], [742, 756, '天寶'],
  [1068, 1077, '熙寧'], [1086, 1094, '元祐'], [1573, 1620, '萬曆'],
  [1662, 1722, '康熙'], [1736, 1795, '乾隆'], [1851, 1861, '咸豐'], [1875, 1908, '光緒'],
]

// 把 palette 注入为 CSS 变量
export function applyPalette(rootEl, paletteKey) {
  const p = PALETTES[paletteKey] || PALETTES['澄']
  const s = (k, v) => rootEl.style.setProperty(k, v)
  s('--paper', p.paper)
  s('--paper-el', p.paperEl)
  s('--line', p.line)
  s('--hair', p.hair)
  s('--ink', p.ink)
  s('--ink-mid', p.inkMid)
  s('--ink-soft', p.inkSoft)
  s('--ink-faint', p.inkFaint)
  s('--accent', p.accent)
  s('--accent-text', p.accentText)
  s('--accent-glow', rgba(p.accent, p.dark ? 0.5 : 0.4))
  s('--hero1', p.hero1)
  s('--hero2', p.hero2)
  s('--grid', p.grid)
  s('--edge', p.edge || p.line)
  s('--caption', p.caption)
  s('--chip', p.chip)
  s('--field', p.field)
  s('--hover', p.hover)
  s('--label-ink', p.labelInk)
  // D5 地图专用色(素底水面/经纬网);MapPanel 与标注 halo 读这两个变量
  s('--map-paper', p.mapPaper || p.paper)
  s('--map-grid', p.mapGrid || p.line)
  // 类别色
  for (const [type, color] of Object.entries(p.cat)) {
    s(`--cat-${type.toLowerCase()}`, color)
  }
  // 事件族色(5 族 + 兜底);slug 已是小写,与 FAMILY_SLUG 一一对应
  for (const [slug, color] of Object.entries(p.fam)) {
    s(`--fam-${slug}`, color)
  }
  s('--on-cat', p.onCat)
  // 兼容旧变量(过渡期)
  s('--bg', p.paper)
  s('--bg-elevated', p.paperEl)
  s('--bg-card', p.chip)
  s('--border', p.line)
  s('--text', p.ink)
  s('--text-dim', p.inkSoft)
  s('--accent-dim', p.accent)
  s('--link', p.accent)
  s('--serif', "'Noto Serif SC','Source Han Serif SC','STSong',serif")
  s('--sans', "'Noto Sans SC',-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif")
  // 语义旧变量
  s('--person', p.cat.Person)
  s('--polity', p.cat.Polity)
  s('--faction', p.cat.Faction)
  s('--event', p.cat.Event)
  s('--battle', p.cat.Battle)
  s('--place', p.cat.Place)
  s('--title', p.cat.Title)
  rootEl.setAttribute('data-palette', paletteKey)
  rootEl.setAttribute('data-dark', p.dark ? 'true' : 'false')
}

export function rgba(hex, a) {
  const n = parseInt(hex.slice(1), 16)
  return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')'
}

export function shade(hex, pct) {
  const n = parseInt(hex.slice(1), 16)
  let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255
  const t = pct < 0 ? 0 : 255, p = Math.abs(pct) / 100
  r = Math.round((t - r) * p) + r
  g = Math.round((t - g) * p) + g
  b = Math.round((t - b) * p) + b
  return 'rgb(' + r + ',' + g + ',' + b + ')'
}

// 天干地支
export function ganzhi(y) {
  if (y < 1) return ''
  const g = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'][((y - 4) % 10 + 10) % 10]
  const z = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'][((y - 4) % 12 + 12) % 12]
  return g + z
}

export function cnNum(n) {
  const D = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
  if (n === 1) return '元'
  if (n < 10) return D[n]
  const t = Math.floor(n / 10), o = n % 10
  return (t > 1 ? D[t] : '') + '十' + (o ? D[o] : '')
}

export function nianhao(y) {
  const r = NIANHAO.find(r => y >= r[0] && y <= r[1])
  if (!r) return ''
  const n = y - r[0] + 1
  return r[2] + cnNum(n) + (r[2] === '天寶' ? '載' : '年')
}

export function fmtY(y) {
  return y == null ? '?' : (y < 0 ? '前' + (-y) : '' + y)
}

// === 历法口径(M12) ===
// 1912-01-01 民国改用公历。此前史料所载月份为农历(本库一律原样收录,未换算),
// 此后为公历。两者在时间轴上都按 1/12 年线性摆放 —— 农历正月起点比公历 1 月
// 晚 3~7 周,故亚年档下的位置是近似而非换算结果。
// 不换算是有意的:换算需逐条核对朔闰(《资治通鉴》一条一条查),没核就换算等于
// 凭空造精确;而原载月份本身是史料事实。为不让读者误以为已换算,两种历法用
// 不同字形标记 —— 农历中文月名(正月/二月),公历阿拉伯数字(3月15日)。
export const GREGORIAN_FROM = 1912
const LUNAR_M = ['正月', '二月', '三月', '四月', '五月', '六月',
                 '七月', '八月', '九月', '十月', '十一月', '十二月']
export function isGregorian(y) { return y != null && y >= GREGORIAN_FROM }

// 只出月/日部分,不带年 —— 亚年档下年份由轴刻度给出,卡片上再写一遍纯属挤掉名字。
// 历法字形规则同 fmtYM(农历中文月名 / 公历阿拉伯数字)。
export function fmtMD(y, m, d) {
  if (m == null) return ''
  if (isGregorian(y)) return m + '月' + (d != null ? d + '日' : '')
  return LUNAR_M[m - 1] || m + '月'
}

// 年月日格式化。m/d 为空时退化成 fmtY,故可无条件调用。
export function fmtYM(y, m, d) {
  if (y == null) return '?'
  if (m == null) return fmtY(y)
  if (isGregorian(y)) return fmtY(y) + '年' + m + '月' + (d != null ? d + '日' : '')
  return fmtY(y) + '年' + (LUNAR_M[m - 1] || m + '月')
}
