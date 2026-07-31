<template>
  <div class="fb-bar">
    <button class="fb-focus" :class="{ active: filter.focusMode }"
            :title="filter.focusMode ? '只看核心+重要人物（importance 1/2）' : '显示全部人物（含 CBDB）'"
            @click="filter.toggleFocus()">重点人物</button>
    <button class="fb-role-toggle" type="button"
            :class="{ active: filter.hasRoleFilter }"
            :aria-expanded="rolesOpen"
            aria-controls="person-role-filters"
            @click="rolesOpen = !rolesOpen">
      <Filter :size="14" :stroke-width="1.8" aria-hidden="true" />
      <span>人物类型<span v-if="filter.hasRoleFilter"> · {{ filter.activeRoles.length }}</span></span>
      <ChevronDown class="fb-chevron" :class="{ open: rolesOpen }" :size="14" aria-hidden="true" />
    </button>
    <div v-if="rolesOpen" id="person-role-filters" class="fb-roles">
      <button v-for="r in ROLES" :key="r.key"
              class="fb-chip" :class="{ active: filter.activeRoles.includes(r.key) }"
              @click="filter.toggleRole(r.key)">{{ r.label }}</button>
    </div>
    <button v-if="rolesOpen && filter.hasRoleFilter" class="fb-clear" @click="filter.clearRoles()">清除</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChevronDown from '@lucide/vue/dist/esm/icons/chevron-down.mjs'
import Filter from '@lucide/vue/dist/esm/icons/funnel.mjs'
import { useFilterStore } from '../../stores'

const filter = useFilterStore()
const rolesOpen = ref(false)

// 13 身份枚举，与 schema/person.yaml -> fields.roles.items.options 对齐（中文 label 前端维护）
const ROLES = [
  { key: 'emperor', label: '帝王' },
  { key: 'monarch', label: '君主' },
  { key: 'imperial_kin', label: '宗室' },
  { key: 'consort', label: '后妃' },
  { key: 'consort_kin', label: '外戚' },
  { key: 'general', label: '将领' },
  { key: 'civil_official', label: '文臣' },
  { key: 'scholar', label: '学者' },
  { key: 'literatus', label: '文人' },
  { key: 'eunuch', label: '宦官' },
  { key: 'rebel_leader', label: '起义领袖' },
  { key: 'clergy', label: '僧道' },
  { key: 'recluse', label: '隐逸' },
]
</script>

<style scoped>
.fb-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 20px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-el);
  flex-wrap: wrap;
  transition: var(--transition-theme);
}
.fb-focus {
  flex: 0 0 auto;
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  font-family: var(--serif);
  font-size: 12.5px;
  font-weight: 600;
  background: var(--caption);
  color: var(--ink-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.fb-focus.active {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-text);
}
.fb-role-toggle {
  flex: 0 0 auto;
  min-height: 28px;
  padding: 4px 9px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--caption);
  color: var(--ink-mid);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}
.fb-role-toggle:hover,
.fb-role-toggle.active { color: var(--accent); border-color: var(--accent); }
.fb-chevron { transition: transform 0.15s ease; }
.fb-chevron.open { transform: rotate(180deg); }
.fb-roles {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.fb-chip {
  padding: 3px 10px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 12px;
  background: transparent;
  color: var(--ink-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.fb-chip:hover { background: var(--hover); }
.fb-chip.active {
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}
.fb-clear {
  padding: 3px 9px;
  border: none;
  border-radius: 11px;
  font-size: 11.5px;
  background: transparent;
  color: var(--ink-soft);
  cursor: pointer;
}
.fb-clear:hover { color: var(--accent); }

@media (max-width: 720px) {
  .fb-bar {
    flex-wrap: nowrap;
    gap: 7px;
    padding: 7px 10px;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
  }
  .fb-bar::-webkit-scrollbar { display: none; }
  .fb-focus { padding: 5px 11px; white-space: nowrap; }
  .fb-role-toggle { white-space: nowrap; }
  .fb-roles { flex: 0 0 auto; flex-wrap: nowrap; gap: 5px; }
  .fb-chip { padding: 4px 10px; white-space: nowrap; }
  .fb-clear { flex: 0 0 auto; white-space: nowrap; }
}
</style>
