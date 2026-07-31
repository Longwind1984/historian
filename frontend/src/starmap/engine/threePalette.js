// Three.js 渲染适配层：把纯数据色板转换为引擎使用的 Color 实例。
// WebGraph / 时空柱只应依赖 inkPalette；星云 renderer 才加载本模块。

import { Color } from 'three';
import { DYNASTY_COLOR_BY_ID, NEUTRAL_DYNASTY_HEX } from './inkPalette.js';

// 预解析缓存，避免每帧 new Color。
const NEUTRAL = new Color(NEUTRAL_DYNASTY_HEX); // 未分类朝代 = 雾灰（设计 §3：未分类=灰雾色）
const UNRESOLVED = new Color('#7a8499');
const PALETTE_BY_ID = Object.fromEntries(
  Object.entries(DYNASTY_COLOR_BY_ID).map(([id, hex]) => [id, new Color(hex)]),
);

/**
 * 朝代着色函数（renderer.colorFn）。
 * node.dynasty：稳定 Dynasty 实体 id。dynastyIdx 只供布局 cluster，不能参与颜色语义。
 */
export function dynastyColorFn(node) {
  if (node && node.unresolved) return UNRESOLVED;
  return (node && PALETTE_BY_ID[node.dynasty]) || NEUTRAL;
}

/** renderer.setColorFn 的兜底（与 dynastyColorFn 同义，保留原命名对照 engine-ref） */
export const fallbackColorFn = dynastyColorFn;

/**
 * 链接色（深空模式用）：端点色 50/50 混 -> 去饱和 60% + 压亮度（NASA 细灰线，辉光由 bloom 给）。
 * 纸墨模式不调本函数——renderer.recolor 检测 tokens.linkInk 后统一用墨色画线。
 */
export function linkColor(a, b) {
  const c = a.clone().lerp(b, 0.5);
  const hsl = { h: 0, s: 0, l: 0 };
  c.getHSL(hsl);
  c.setHSL(hsl.h, hsl.s * 0.4, Math.min(hsl.l, 0.35));
  return c;
}
