import { ref, onMounted, onBeforeUnmount } from 'vue'

/**
 * 全局快捷键(C1 效率层):单一 window keydown 监听。
 * 焦点落在 input/textarea/select/contentEditable 时全部挂起 —— 弹层
 * (跳年框/搜索框)内的 Esc、Enter 由组件自理,不与全局键位抢。
 *
 * 键位表(PRD §5 C批,owner 已批发):
 *   /        聚焦全局搜索
 *   ←/→      年档 ±1 年;月/日档按轴精度 ±1 格(仅时间柱路由)
 *   Space    播放/暂停年代步进(仅时间柱);手动滚动或方向键即停
 *   g        时间跳转(前221 / 755年七月 / 755-07)
 *   1/2/3    星图 tab 网/云/柱(仅星图路由)
 *   t        切到时间柱
 *   Esc      分层:关帮助 -> 关跳年框 -> 清选中(命中即停)
 *   ?        帮助浮层
 */
export function useHotkeys({ timeStore, ui, selectionStore, focusSearch }) {
  const helpOpen = ref(false)
  const jumpOpen = ref(false)

  function isEditable(el) {
    if (!el) return false
    const tag = el.tagName
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
  }

  function isInteractive(el) {
    return !!el?.closest?.('button, a[href], [role="button"], [role="slider"], [role="option"]')
  }

  function stepAxis(direction, yearMultiplier) {
    timeStore.stopPlay()   // 方向键属手动定年,播放即停
    timeStore.stepAxis(direction, yearMultiplier)
  }

  function onJumpConfirm(navigation) {
    jumpOpen.value = false
    timeStore.stopPlay()
    timeStore.requestNavigation(navigation)
  }

  function onKey(e) {
    if (isEditable(document.activeElement)) return
    // 组件已经消费的键位不能再触发全局动作。
    if (e.defaultPrevented) return
    // 修饰键组合(Ctrl/⌘ 系)留给浏览器;Alt 仅在方向键步进时作倍率
    if (e.ctrlKey || e.metaKey) return

    // Esc 分层关闭,命中第一层即停
    if (e.key === 'Escape') {
      if (helpOpen.value) { helpOpen.value = false; return }
      if (jumpOpen.value) { jumpOpen.value = false; return }
      if (selectionStore.selectedEntityId) selectionStore.clearSelection()
      return
    }
    if (e.key === '?') { helpOpen.value = !helpOpen.value; return }
    if (e.key === '/') { e.preventDefault(); focusSearch && focusSearch(); return }
    if (e.key === 'g' && !e.shiftKey && !e.altKey) { jumpOpen.value = true; return }
    if (e.key === 't' && !e.shiftKey && !e.altKey) { ui.setRoute('timeline'); return }

    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      if (ui.route !== 'timeline') return
      e.preventDefault()
      const step = e.altKey ? 100 : e.shiftKey ? 10 : 1
      stepAxis(e.key === 'ArrowRight' ? 1 : -1, timeStore.axisUnit === 'year' ? step : 1)
      return
    }
    if (e.code === 'Space') {
      if (ui.route !== 'timeline') return
      // Space 是原生 button / ARIA 控件的激活键；只屏蔽这一枚冲突键，不能连带
      // 屏蔽 LOD 按钮聚焦后的 ←/→ 时间步进（M13 的既有键盘契约）。
      if (isInteractive(document.activeElement)) return
      e.preventDefault()   // 防页面滚动
      timeStore.togglePlay()
      return
    }
    if (ui.route === 'graph' && ['1', '2', '3'].includes(e.key) && !e.shiftKey && !e.altKey) {
      ui.setView({ 1: 'web', 2: 'nebula', 3: 'column' }[e.key])
    }
  }

  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

  return { helpOpen, jumpOpen, onJumpConfirm }
}
