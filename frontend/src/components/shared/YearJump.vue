<template>
  <!-- 跳年弹层(C1):g 键或时间工具组按钮唤起；居中轻弹层，Esc 关闭、Enter 确认。 -->
  <div class="yj-mask" @mousedown.self="emit('close')">
    <div class="yj-box" :class="{ shake: shaking }">
      <div class="yj-title">跳至时间</div>
      <div class="yj-row">
        <input
          ref="inputRef"
          v-model="text"
          class="yj-input"
          placeholder="755年七月 / 755-07 / 前221"
          @keydown.enter.prevent="confirm"
          @keydown.esc.prevent="emit('close')"
        />
        <button class="yj-ok" @click="confirm">前往</button>
      </div>
      <div class="yj-hint">前2100–2026 · 支持年份或月份</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { parseTimeNavigation } from '../../utils/timeNavigation'

const emit = defineEmits(['confirm', 'close'])
const text = ref('')
const shaking = ref(false)
const inputRef = ref(null)
let shakeTimer = 0

function confirm() {
  const navigation = parseTimeNavigation(text.value)
  if (!navigation) {
    // 非法输入:晃框提示,不关窗不清空
    shaking.value = false
    requestAnimationFrame(() => { shaking.value = true })
    clearTimeout(shakeTimer)
    shakeTimer = setTimeout(() => { shaking.value = false }, 450)
    return
  }
  emit('confirm', navigation)
}

onMounted(() => { inputRef.value && inputRef.value.focus() })
</script>

<style scoped>
.yj-mask {
  position: fixed; inset: 0; z-index: 90;
  background: color-mix(in srgb, var(--ink) 18%, transparent);
  display: flex; align-items: flex-start; justify-content: center;
  padding-top: 18vh;
}
.yj-box {
  width: 280px; padding: 16px 18px 14px;
  background: var(--paper-el); color: var(--ink);
  border: 1px solid var(--line); border-radius: 10px;
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.18);
}
.yj-box.shake { animation: yj-shake 0.4s ease; }
@keyframes yj-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-7px); }
  50% { transform: translateX(6px); }
  75% { transform: translateX(-3px); }
}
.yj-title { font-family: var(--serif); font-weight: 700; font-size: 14px; margin-bottom: 9px; }
.yj-row { display: flex; gap: 7px; }
.yj-input {
  flex: 1; padding: 6px 9px; font-size: 13.5px; font-family: inherit;
  background: var(--field); color: var(--ink);
  border: 1px solid var(--line); border-radius: 6px; outline: none;
}
.yj-input:focus { border-color: var(--accent); }
.yj-ok {
  padding: 6px 13px; border: none; border-radius: 6px; cursor: pointer;
  background: var(--accent); color: var(--accent-text);
  font-family: inherit; font-size: 13px;
}
.yj-hint { margin-top: 8px; font-size: 10.5px; color: var(--ink-soft); }
</style>
