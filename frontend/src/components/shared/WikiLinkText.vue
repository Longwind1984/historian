<template>
  <span class="wiki-link-text">
    <template v-for="(seg, i) in segments" :key="i">
      <a v-if="seg.link" class="wiki-chip" :class="{ 'wiki-self': seg.isSelf }"
         :style="seg.style"
         @click="onClick(seg)"
         @mouseenter="onHover(seg)"
         @mouseleave="onHover(null)">
        <span class="wiki-icon">{{ seg.icon }}</span>
        {{ seg.text }}
      </a>
      <span v-else>{{ seg.text }}</span>
    </template>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useDataStore } from '../../stores'

const props = defineProps({
  text: { type: String, default: '' },
  mentions: { type: Array, default: () => [] },  // [{to_id, to_name, to_type, offset, length}]
  selfId: { type: String, default: '' },
})
const emit = defineEmits(['navigate', 'hover'])

const store = useDataStore()

const segments = computed(() => {
  if (!props.text) return []
  const segs = []
  // Sort mentions by offset
  const sorted = [...props.mentions].sort((a, b) => a.offset - b.offset)
  let cursor = 0
  for (const m of sorted) {
    if (m.offset > cursor) {
      segs.push({ text: props.text.slice(cursor, m.offset) })
    }
    const meta = store.typeMeta(m.to_type || 'Person')
    segs.push({
      link: true,
      text: props.text.slice(m.offset, m.offset + m.length),
      id: m.to_id,
      type: m.to_type,
      icon: meta.icon,
      isSelf: m.to_id === props.selfId,
      style: { '--chip-color': meta.color },
    })
    cursor = m.offset + m.length
  }
  if (cursor < props.text.length) {
    segs.push({ text: props.text.slice(cursor) })
  }
  return segs
})

function onClick(seg) {
  emit('navigate', seg.id)
}
function onHover(seg) {
  emit('hover', seg ? seg.id : null)
}
</script>

<style scoped>
.wiki-link-text { line-height: 1.65; }
.wiki-chip {
  cursor: pointer;
  display: inline-flex;
  align-items: baseline;
  gap: 0.15rem;
  padding: 0.02rem 0.3rem;
  margin: 0 0.05rem;
  border-radius: 4px;
  background: rgba(212,168,67,0.08);
  border-bottom: 1.5px solid var(--chip-color, var(--accent));
  color: var(--chip-color, var(--accent));
  font-weight: 500;
  transition: background 0.12s, transform 0.12s;
  white-space: nowrap;
}
.wiki-chip:hover {
  background: var(--chip-color, var(--accent));
  color: #fff;
  transform: translateY(-1px);
}
.wiki-chip.wiki-self {
  background: rgba(255,255,255,0.05);
  color: var(--text-dim);
  border-bottom-style: dashed;
  cursor: default;
}
.wiki-chip.wiki-self:hover { background: rgba(255,255,255,0.05); color: var(--text-dim); transform: none; }
.wiki-icon { font-size: 0.85em; opacity: 0.8; }
</style>
