<template>
  <div class="avatar" :class="['avatar-' + sizeClass, 'avatar-' + type.toLowerCase(), { 'avatar-clickable': clickable }]" :style="boxStyle" @click="$emit('click', $event)">
    <img v-if="src && !broken"
         :src="src"
         :alt="name"
         loading="lazy"
         referrerpolicy="no-referrer"
         @error="onError" />
    <svg v-else :viewBox="`0 0 ${SV} ${SV}`" :width="size" :height="size">
      <defs>
        <linearGradient :id="gradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="topColor" />
          <stop offset="100%" :stop-color="bottomColor" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" :width="SV" :height="SV" :fill="`url(#${gradId})`" />
      <!-- decorative corner brackets for "ancient scroll" feel -->
      <path :d="`M ${SV*0.08} ${SV*0.18} L ${SV*0.08} ${SV*0.08} L ${SV*0.18} ${SV*0.08}`"
            stroke="rgba(255,255,255,0.18)" fill="none" :stroke-width="SV*0.015" />
      <path :d="`M ${SV*0.82} ${SV*0.08} L ${SV*0.92} ${SV*0.08} L ${SV*0.92} ${SV*0.18}`"
            stroke="rgba(255,255,255,0.18)" fill="none" :stroke-width="SV*0.015" />
      <path :d="`M ${SV*0.92} ${SV*0.82} L ${SV*0.92} ${SV*0.92} L ${SV*0.82} ${SV*0.92}`"
            stroke="rgba(255,255,255,0.18)" fill="none" :stroke-width="SV*0.015" />
      <path :d="`M ${SV*0.18} ${SV*0.92} L ${SV*0.08} ${SV*0.92} L ${SV*0.08} ${SV*0.82}`"
            stroke="rgba(255,255,255,0.18)" fill="none" :stroke-width="SV*0.015" />
      <text :x="SV/2" :y="SV/2" :font-size="fontSize" font-family="'Noto Serif SC','STSong',serif"
            fill="rgba(255,255,255,0.92)" text-anchor="middle" dominant-baseline="central" font-weight="500">{{ initial }}</text>
      <text :x="SV/2" :y="SV*0.84" :font-size="SV*0.13" font-family="'Noto Sans SC',sans-serif"
            fill="rgba(255,255,255,0.45)" text-anchor="middle">{{ glyph }}</text>
    </svg>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  name: { type: String, default: '' },
  type: { type: String, default: 'Person' },
  size: { type: Number, default: 64 },
  clickable: { type: Boolean, default: false },
})
defineEmits(['click'])

const broken = ref(false)
watch(() => props.src, () => { broken.value = false })

const SV = 100  // SVG viewBox fixed; we scale by size

const sizeClass = computed(() => {
  if (props.size <= 24) return 'xs'
  if (props.size <= 36) return 'sm'
  if (props.size <= 64) return 'md'
  if (props.size <= 96) return 'lg'
  return 'xl'
})

const gradId = computed(() => `grad-${Math.abs(hashCode(props.name + props.type)) % 100000}`)

function hashCode(s) {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return h
}

// initial = first char of name (for Chinese, the surname)
const initial = computed(() => {
  const n = props.name?.trim() || '?'
  return n.charAt(0)
})

// glyph = a small icon per type
const glyph = computed(() => {
  switch (props.type) {
    case 'Person': return ''  // empty for clean look
    case 'Polity': return '◆'
    case 'Battle': return '⚔'
    case 'Event': return '✦'
    case 'Faction': return '⬡'
    case 'Place': return '◯'
    case 'Dynasty': return '◈'
    case 'Title': return '※'
    default: return '·'
  }
})

// Dynasty/era color mapping (matches our polity colors)
const TYPE_COLORS = {
  Person:   { top: '#3a6fa8', bottom: '#1f3d5c' },
  Polity:   { top: '#c0433a', bottom: '#7a2520' },
  Battle:   { top: '#e68a26', bottom: '#8c4b0c' },
  Event:    { top: '#1ab394', bottom: '#0d6e5b' },
  Faction:  { top: '#a86bbd', bottom: '#5e3370' },
  Place:    { top: '#3adb6f', bottom: '#1a7c3d' },
  Dynasty:  { top: '#5d7185', bottom: '#2d3947' },
  Title:    { top: '#f0a830', bottom: '#8c5e0c' },
}

const topColor = computed(() => TYPE_COLORS[props.type]?.top || '#4a5a70')
const bottomColor = computed(() => TYPE_COLORS[props.type]?.bottom || '#1f2937')

const fontSize = computed(() => {
  // bigger if single-char initial
  return initial.value.length <= 1 ? SV * 0.42 : SV * 0.32
})

const boxStyle = computed(() => ({
  width: props.size + 'px',
  height: props.size + 'px',
}))

function onError() {
  broken.value = true
}
</script>

<style scoped>
.avatar {
  display: inline-block;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  vertical-align: middle;
  position: relative;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.avatar-clickable { cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; }
.avatar-clickable:hover { transform: scale(1.05); box-shadow: 0 0 0 2px var(--accent); }
.avatar svg { display: block; }
</style>
