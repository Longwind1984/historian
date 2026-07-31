/** Build-time capability shared by store, map UI, and attribution copy. */
export const RESTRICTED_MAPS_ENABLED = import.meta.env.VITE_RESTRICTED_MAPS !== '0'

// 私人 Prompt / 上传只在本地开发或显式受控环境开放。生产构建默认 demo-only；
// 即使误传 VITE_PRIVATE_EXPLORATIONS=1，EdgeOne 打包器也会拒绝该产物。
const privateExplorationMode = import.meta.env.VITE_PRIVATE_EXPLORATIONS
export const PRIVATE_EXPLORATIONS_ENABLED = privateExplorationMode === '1'
  || (import.meta.env.DEV && privateExplorationMode !== '0')

export const PUBLIC_EXPLORATION_DEMO_SLUG = 'anshi'
