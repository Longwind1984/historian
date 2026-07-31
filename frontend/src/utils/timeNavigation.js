export const TIME_YEAR_MIN = -2100
export const TIME_YEAR_MAX = 2026
export const AXIS_DAYS_PER_MONTH = 30.44

const CN_MONTHS = Object.freeze({
  一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6,
  七: 7, 八: 8, 九: 9, 十: 10, 十一: 11, 十二: 12,
})

function validNavigation(year, month = null) {
  if (!Number.isInteger(year) || year < TIME_YEAR_MIN || year > TIME_YEAR_MAX) return null
  if (month != null && (!Number.isInteger(month) || month < 1 || month > 12)) return null
  // 轴下界是 2026 年刻度本身；其后的月份已超出可导航范围，不能静默夹回正月。
  if (year === TIME_YEAR_MAX && month != null && month > 1) return null
  return { year, month, day: null }
}

/**
 * 严格解析时间跳转输入。支持既有纯年份，以及明确的年/月两种写法；不接收日，
 * 因为 1912 年前的农历月长与置闰信息不足，无法可靠判断“非法日期”。
 */
export function parseTimeNavigation(input) {
  const text = String(input ?? '').trim().replace(/\s+/g, '')
  if (!text) return null

  let match = text.match(/^前(\d{1,4})年([一二三四五六七八九十]{1,3})月$/)
  if (match) {
    const magnitude = Number(match[1])
    if (magnitude === 0) return null
    const month = CN_MONTHS[match[2]]
    return month == null ? null : validNavigation(-magnitude, month)
  }

  match = text.match(/^(-?\d{1,4})年([一二三四五六七八九十]{1,3})月$/)
  if (match) {
    const month = CN_MONTHS[match[2]]
    return month == null ? null : validNavigation(Number(match[1]), month)
  }

  // ISO-like 年-月；月固定两位，避免把任意连字符数字串误当日期。
  match = text.match(/^(-?\d{1,4})-(\d{2})$/)
  if (match) return validNavigation(Number(match[1]), Number(match[2]))

  match = text.match(/^前(\d{1,4})(?:年)?$/)
  if (match) {
    const magnitude = Number(match[1])
    return magnitude === 0 ? null : validNavigation(-magnitude)
  }

  match = text.match(/^(-?\d{1,4})(?:年)?$/)
  return match ? validNavigation(Number(match[1])) : null
}

/** 时间字段转时间轴小数年；月按 1/12、日按每月 30.44 个轴日，仅是几何口径。 */
export function toAxisYear(value) {
  if (!value || !Number.isInteger(value.year)) return null
  if (value.month == null) return value.year
  if (!Number.isInteger(value.month) || value.month < 1 || value.month > 12) return null
  const dayFraction = value.day != null ? (value.day - 1) / AXIS_DAYS_PER_MONTH : 0
  return value.year + ((value.month - 1) + dayFraction) / 12
}
