<template>
  <!-- D5 全站统一空态:印章式占位字形(或 icon 插槽)+ 一句话 + 可选行动按钮。
       文案一律简体(UI 层从简),字形取「闕」为默认 —— 缺则言缺,不编造(原则 6)。 -->
  <div class="empty-state" :class="{ 'empty-full': full, 'empty-compact': compact }">
    <div class="empty-glyph"><slot name="icon">{{ glyph }}</slot></div>
    <div class="empty-body">
      <div class="empty-text">{{ text }}</div>
      <div v-if="sub" class="empty-sub">{{ sub }}</div>
      <button v-if="actionText" class="empty-action" @click="emit('action')">{{ actionText }}</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  glyph: { type: String, default: '闕' },      // 占位字形;可被 icon 插槽覆盖
  text: { type: String, required: true },      // 一句话空态文案
  sub: { type: String, default: '' },          // 次级说明(可选)
  actionText: { type: String, default: '' },   // 行动按钮文案;空则不渲染按钮
  full: { type: Boolean, default: false },     // 撑满视口(后端断连等整页空态)
  compact: { type: Boolean, default: false },  // 行内紧凑态(卡片/图例内嵌)
})
const emit = defineEmits(['action'])
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 18px 12px;
  color: var(--ink-soft);
  text-align: center;
}
.empty-glyph {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  border: 1px dashed var(--ink-faint);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--serif);
  font-size: 22px;
  color: var(--ink-faint);
  flex-shrink: 0;
}
.empty-body { display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 0; }
.empty-text { font-size: 12.5px; color: var(--ink-soft); }
.empty-sub { font-size: 11px; color: var(--ink-faint); max-width: 420px; word-break: break-all; }
.empty-action {
  margin-top: 8px;
  padding: 6px 18px;
  border-radius: 6px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: var(--accent-text);
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
}
.empty-action:hover { opacity: 0.88; }

/* 整页空态:与 .splash 同级(fixed 满屏),供后端断连等场景 */
.empty-full {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--paper);
  padding: 0;
}
.empty-full .empty-glyph { width: 64px; height: 64px; font-size: 30px; border-radius: 10px; }
.empty-full .empty-text { font-family: var(--serif); font-weight: 700; font-size: 19px; color: var(--ink-mid); }

/* 紧凑行内态:chips 行/图例/小卡片内嵌,横排小号 */
.empty-compact {
  flex-direction: row;
  gap: 8px;
  padding: 4px 0;
  text-align: left;
}
.empty-compact .empty-glyph { width: 24px; height: 24px; font-size: 12px; border-radius: 5px; }
.empty-compact .empty-body { flex-direction: row; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.empty-compact .empty-text { font-size: 12px; }
.empty-compact .empty-sub { font-size: 10.5px; }
</style>
