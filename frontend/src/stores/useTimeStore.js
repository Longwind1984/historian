import { defineStore } from 'pinia'
import { AXIS_DAYS_PER_MONTH, TIME_YEAR_MIN, TIME_YEAR_MAX, toAxisYear } from '../utils/timeNavigation'

const DEFAULT_YEAR = 750

// 滑停判定:停手多久算「稳定」。180ms 短于常人换向时的停顿,长于滚轮连发的间隔,
// 故连续滑动期间不会误触发,松手后又几乎无感。
const SETTLE_MS = 180
let settleTimer = 0

// 年代播放(Space 快捷键):每 400ms 步进一年,到时间轴下界自停。
// 状态放 store 而非快捷键组件:TimeColumn 的 lens 胶囊要读 playing 画暂停符,
// 手动滚动/方向键也要能拦停 —— 单一真相点才不至于两处计时器打架。
const PLAY_STEP_MS = 400
const PLAY_END = 2026
let playTimer = 0

/** 时间 store：year / settledYear + URL 同步 */
export const useTimeStore = defineStore('time', {
  state: () => ({
    year: DEFAULT_YEAR,
    // 年代播放中标志(C1):Space 启停;lens 胶囊据此显 ⏸
    playing: false,
    // 稳定年份:滑动停下后才跟上。year 每 rAF 一变(~60fps),而地图重绘疆域、右栏取
    // 在世人物都是重活 —— 直接跟 year 就是滑一下重绘几十次、发几十个请求,右侧疯狂
    // 跳动。读数/刻度这类轻活仍用 year(否则数字滞后于手感)。
    settledYear: DEFAULT_YEAR,
    // 精确导航只是一枚瞬时意图：整数 year 继续服务 URL / 地图 / 在世名单。
    // TimeColumn 按 seq 消费 exactYear，不把小数塞回 year。
    navigationRequest: null,
    navigationSeq: 0,
    // 当前时间轴镜头给全局方向键的精度上下文。
    axisExactYear: DEFAULT_YEAR,
    axisUnit: 'year',
  }),
  actions: {
    // 跳转类操作(点朝代快捷/年谱/搜索)也走这里:它们经 scrollToYear 平滑滚动,
    // 滚动本身即触发本 action,停下后自然落定,无需另设「立即落定」的入口。
    setYear(year) {
      this.year = year
      clearTimeout(settleTimer)
      settleTimer = setTimeout(() => { this.settledYear = this.year }, SETTLE_MS)
    },
    requestNavigation(value) {
      const exact = Number.isFinite(value?.exactYear) ? value.exactYear : toAxisYear(value)
      if (!Number.isFinite(exact)) return false
      const bounded = Math.max(TIME_YEAR_MIN, Math.min(TIME_YEAR_MAX, exact))
      const year = Math.floor(bounded)
      this.axisExactYear = bounded
      this.setYear(year)
      this.navigationSeq += 1
      this.navigationRequest = {
        year,
        month: value?.month ?? null,
        day: value?.day ?? null,
        exactYear: bounded,
        precision: value?.precision || (value?.month != null ? 'month' : 'year'),
        seq: this.navigationSeq,
      }
      return true
    },
    setAxisContext(exactYear, unit) {
      if (Number.isFinite(exactYear)) this.axisExactYear = exactYear
      if (unit === 'year' || unit === 'month' || unit === 'day') this.axisUnit = unit
    },
    stepAxis(direction, yearMultiplier = 1) {
      const dir = direction < 0 ? -1 : 1
      let exact
      if (this.axisUnit === 'month') exact = this.axisExactYear + dir / 12
      else if (this.axisUnit === 'day') exact = this.axisExactYear + dir / (12 * AXIS_DAYS_PER_MONTH)
      else exact = this.year + dir * yearMultiplier
      return this.requestNavigation({ exactYear: exact, precision: this.axisUnit })
    },
    // 播放:步进走 setYear,TimeColumn 的外部跳年 watch 自然平滑跟进
    startPlay() {
      if (this.playing) return
      this.playing = true
      playTimer = setInterval(() => {
        if (this.year >= PLAY_END) { this.stopPlay(); return }
        this.setYear(this.year + 1)
      }, PLAY_STEP_MS)
    },
    stopPlay() {
      if (!this.playing) return
      this.playing = false
      clearInterval(playTimer)
    },
    togglePlay() { this.playing ? this.stopPlay() : this.startPlay() },
  },
})
