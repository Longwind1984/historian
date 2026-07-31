// 实体的代表年份:任何「选中实体」若带时间属性,都能把用户带回它的年代(原则2·一年一世界)。
// 按类型取第一个非空时间锚 —— Person 与 TimeColumn 的四态时间锚同源(born 最确,
// floruit/died/reign 递降);Event/Battle 取事发年;Polity/Faction 取建国年;
// Place 等其余类型没有可依据的年份,返回 null(不滚柱,仅地图飞行)。
// B1 起为共享真源:MomentPanel 地图定位、SearchBar 搜索跳年均走这里,优先级只许改一处。
export function repYear(e) {
  if (!e) return null
  if (e.type === 'Person') {
    return e.born?.year ?? e.floruit_start?.year ?? e.died?.year ?? e.reign_start?.year ?? null
  }
  if (e.type === 'Event' || e.type === 'Battle') return e.date?.year ?? null
  if (e.type === 'Polity' || e.type === 'Faction') return e.founded?.year ?? null
  return null
}
