<template>
  <!-- 聚合迷你清单(M8 统一交互语言):人物聚合道与事件溢出桶共用同一组件。
       条目可点选(emit select,走既有 selectEntity 通道);hover 留存由父级
       用 enter/leave + 宽限定时器管理,徽标到浮层的短距离移动不闪关。 -->
  <div class="tc-agg-pop" :style="popStyle" role="group" :aria-label="title"
       @mouseenter="$emit('enter')" @mouseleave="$emit('leave')">
    <div class="tc-agg-pop-title">{{ title }}</div>
    <div v-for="it in shown" :key="it.id" class="tc-agg-pop-name"
         role="button" tabindex="0" :aria-label="it.name + (it.label ? '，' + it.label : '')"
         @click="$emit('select', it)"
         @keydown.enter.prevent="$emit('select', it)"
         @keydown.space.prevent="$emit('select', it)">
      <span v-if="it.hue" class="tc-agg-pop-dot" :style="{ background: it.hue }"></span>
      <span class="tc-agg-pop-nm">{{ it.name }}</span>
      <span v-if="it.label" class="tc-agg-pop-yr">{{ it.label }}</span>
    </div>
    <div v-if="items.length > cap" class="tc-agg-pop-more">… 共 {{ items.length }} {{ unit }} · 点击徽标放大回列</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  items: { type: Array, default: () => [] },   // [{id, name, label?, hue?}]
  cap: { type: Number, default: 24 },          // 超出只列前 cap 条 + 折叠脚注
  unit: { type: String, default: '条' },
  popStyle: { type: Object, default: () => ({}) },
})
defineEmits(['select', 'enter', 'leave'])

const shown = computed(() => props.items.slice(0, props.cap))
</script>

<style scoped>
/* 类名沿用 M7 既有选择器(.tc-agg-pop/.tc-agg-pop-name),e2e 钉子不漂;
   与 M7 的差异:浮层可交互(pointer-events:auto),条目可点选 */
.tc-agg-pop {
  position: absolute;
  z-index: 20;
  width: 178px;
  max-height: 300px;
  overflow-y: auto;
  background: var(--paper-el);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 6px 8px;
}
.tc-agg-pop-title { font-size: 10px; color: var(--ink-faint); margin-bottom: 4px; }
.tc-agg-pop-name {
  display: flex;
  align-items: baseline;
  gap: 5px;
  font-family: var(--serif);
  font-size: 11.5px;
  color: var(--ink);
  line-height: 1.7;
  cursor: pointer;
  border-radius: 3px;
  padding: 0 3px;
  white-space: nowrap;
  overflow: hidden;
}
.tc-agg-pop-name:hover { background: var(--hover); color: var(--accent); }
.tc-agg-pop-name:focus-visible { outline: 2px solid var(--accent); outline-offset: -1px; }
.tc-agg-pop-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  align-self: center;
}
.tc-agg-pop-nm { overflow: hidden; text-overflow: ellipsis; }
.tc-agg-pop-yr {
  margin-left: auto;
  font-family: ui-monospace, monospace;
  font-size: 9.5px;
  color: var(--ink-faint);
  flex-shrink: 0;
}
.tc-agg-pop-more {
  margin-top: 4px;
  font-size: 10px;
  color: var(--ink-faint);
  border-top: 1px dashed var(--line);
  padding-top: 4px;
}
</style>
