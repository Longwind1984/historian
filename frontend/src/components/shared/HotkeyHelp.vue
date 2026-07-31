<template>
  <!-- 快捷键帮助浮层(C1):? 键或 masthead ? 钮开关;Esc 关闭 -->
  <div class="hk-mask" @mousedown.self="emit('close')">
    <div class="hk-panel">
      <div class="hk-head">
        <span class="hk-title">快捷键</span>
        <button class="hk-close" @click="emit('close')">✕</button>
      </div>
      <table class="hk-table">
        <tbody>
          <tr v-for="row in KEYS" :key="row.k">
            <td class="hk-key"><kbd>{{ row.k }}</kbd></td>
            <td class="hk-desc">{{ row.d }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['close'])

// 与 useHotkeys.js 键位表一一对应;改键先改 composable,再同步此表
const KEYS = [
  { k: '/', d: '聚焦搜索框' },
  { k: '← →', d: '年/月/轴日按当前精度步进 · 时间柱' },
  { k: 'Space', d: '播放 / 暂停年代步进 · 时间柱' },
  { k: 'g', d: '跳至时间(前221 / 755年七月 / 755-07)' },
  { k: '1 2 3', d: '星图视图:网 / 云 / 柱 · 星图' },
  { k: 't', d: '回到时间柱' },
  { k: 'f', d: '谱系图适配视野 · 星图' },
  { k: 'Esc', d: '分层关闭:帮助 → 跳年 → 清除选中' },
  { k: '?', d: '本帮助' },
]
</script>

<style scoped>
.hk-mask {
  position: fixed; inset: 0; z-index: 90;
  background: color-mix(in srgb, var(--ink) 18%, transparent);
  display: flex; align-items: flex-start; justify-content: center;
  padding-top: 14vh;
}
.hk-panel {
  width: 340px; padding: 15px 18px 12px;
  background: var(--paper-el); color: var(--ink);
  border: 1px solid var(--line); border-radius: 10px;
  box-shadow: 0 10px 34px rgba(0, 0, 0, 0.18);
}
.hk-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.hk-title { font-family: var(--serif); font-weight: 700; font-size: 15px; }
.hk-close {
  border: none; background: transparent; cursor: pointer;
  color: var(--ink-soft); font-size: 13px; padding: 2px 6px;
}
.hk-close:hover { color: var(--accent); }
.hk-table { width: 100%; border-collapse: collapse; }
.hk-table td { padding: 4.5px 0; border-top: 1px solid var(--line); vertical-align: middle; }
.hk-table tr:first-child td { border-top: none; }
.hk-key { width: 76px; }
.hk-key kbd {
  display: inline-block; padding: 2px 7px;
  background: var(--field); border: 1px solid var(--line); border-radius: 5px;
  font-family: ui-monospace, monospace; font-size: 11px; color: var(--ink-mid);
}
.hk-desc { font-size: 12.5px; color: var(--ink); }
</style>
