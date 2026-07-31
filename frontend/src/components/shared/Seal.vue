<template>
  <span class="seal" :class="['seal-' + sizeClass]" :style="sealStyle" :title="title">
    <span class="seal-glyph">{{ glyph }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { SEALS, EVENT_CATS, catMeta, catHue } from '../../styles/palettes'

const props = defineProps({
  type: { type: String, required: true },
  // 事件类别(schema/event.yaml 的 category);传入则字形取类、配色取族,覆盖 type
  category: { type: String, default: null },
  size: { type: Number, default: 22 },
  variant: { type: String, default: 'solid' }, // solid | outline | ghost
})

// Place/Title 也有 category 字段但枚举不同(capital/central…);只认 Event 的枚举,
// 传错不至于把「地/青绿」静默降级成「事/绿」。
const isCat = computed(() => !!props.category && !!EVENT_CATS[props.category])
const meta = computed(() => SEALS[props.type] || SEALS.Person)
const glyph = computed(() => isCat.value ? catMeta(props.category).glyph : meta.value.glyph)
const title = computed(() => isCat.value
  ? `${catMeta(props.category).family} · ${catMeta(props.category).label}`
  : `${meta.value.label} · ${meta.value.labelEn}`)

const sizeClass = computed(() => {
  if (props.size <= 16) return 'xs'
  if (props.size <= 22) return 'sm'
  if (props.size <= 30) return 'md'
  return 'lg'
})

const sealStyle = computed(() => {
  const catColor = isCat.value ? catHue(props.category) : `var(--cat-${props.type.toLowerCase()})`
  const dim = props.size + 'px'
  const fontSize = Math.round(props.size * 0.58)
  const base = {
    width: dim,
    height: dim,
    fontSize: fontSize + 'px',
  }
  if (props.variant === 'solid') {
    return { ...base, background: catColor, color: 'var(--on-cat)' }
  }
  if (props.variant === 'outline') {
    return { ...base, background: 'transparent', color: catColor, border: '1.5px solid ' + catColor }
  }
  // ghost: faint background
  return { ...base, background: `color-mix(in srgb, ${catColor} 14%, transparent)`, color: catColor }
})
</script>

<style scoped>
.seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  flex-shrink: 0;
  font-family: var(--serif);
  font-weight: 700;
  line-height: 1;
  vertical-align: middle;
  transition: var(--transition-theme);
}
.seal-glyph { line-height: 1; }
</style>
