// 星云 3D 编排：renderer + Worker 力布局 + cameraDirector + labelLOD 拼成 RAF 循环，
// 并实现设计 §3 的星云行为：点击星->电影相机飞抵+档案卡联动、hover 名牌、开场绽放、
// Focus 模式（邻域外调暗至 8%）、Connect-two 六度逐跳飞行。
//
// 装配方式参照 engine-ref/_entry-reference.js（单例+CSS2D 标签+点击/拖拽区分），但：
//   · 数据走 dataAdapter（spacetime + global），不走 buildGraphFromSiteJson
//   · 配色走 inkPalette（朝代色 + CSS 变量主题），非 clusterColorFn
//   · 星径 sizeMode='logLinks'（ln(1+links)）
//   · 行为增 hover 名牌 + Connect-two 逐跳飞行 + 主题热切换
//   · 不做单例：星云 tab 进出由 Vue 挂载/卸载驱动，卸载时全量 dispose（防内存泄漏，设计要求）
//
// 控制器契约（NebulaView 用）：
//   ready:Promise · focusEntity(id) · connectTwo(from,to):Promise · applyTheme(meta) · dispose()

import { AggregateRenderer } from './renderer.js';
import { WorkerForceLayout } from './workerForceLayout.js';
import { CameraDirector } from './cameraDirector.js';
import { readTokens } from './inkPalette.js';
import { dynastyColorFn } from './threePalette.js';
import { seedPosition, seedRadius } from './seed.js';
import { LabelLOD } from './labelLOD.js';
import { fetchNebulaGraph } from './dataAdapter.js';
import { getShortestPath } from '../../api/client.js';
import { Vector3 } from 'three';
import { FLY_TO } from './constants.js';

const HOP_DWELL_MS = 2000; // Connect-two 每跳停留
const CONNECT_MAX_DEPTH = 6; // 六度分隔

export async function mountNebula(host, opts = {}) {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobile = matchMedia('(pointer: coarse)').matches;

  // ---- 数据 ----
  const graph = await fetchNebulaGraph();
  const data = { nodes: graph.nodes, links: graph.links };
  const n = data.nodes.length;
  const indexByEntityId = graph.indexByEntityId;
  const adj = data.nodes.map(() => new Set());
  const linksByNode = data.nodes.map(() => []);
  data.links.forEach((l, i) => {
    adj[l.source].add(l.target);
    adj[l.target].add(l.source);
    linksByNode[l.source].push(i);
    linksByNode[l.target].push(i);
  });

  // ---- 种子坐标（确定性球面散布）----
  const radius = seedRadius(n);
  const positions = new Float32Array(n * 3);
  data.nodes.forEach((node, i) => {
    const [x, y, z] = seedPosition(String(node.origId ?? i), radius);
    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;
  });

  // ---- 渲染器 ----
  const renderer = new AggregateRenderer(host, radius);
  renderer.setColorFn(dynastyColorFn);
  renderer.setSizeMode('logLinks'); // 星径=ln(1+links)，须在 setData 前置
  renderer.setData(data, positions);
  const W0 = host.clientWidth || 800;
  const H0 = host.clientHeight || 600;
  renderer.resize(W0, H0);
  // 标记画布供 E2E 选择
  renderer.renderer.domElement.classList.add('nebula-canvas');
  renderer.renderer.domElement.dataset.testid = 'nebula-canvas';

  // ---- 主题 token ----
  const meta = opts.getPaletteMeta ? opts.getPaletteMeta() : { key: '澄', dark: false };
  const tokens0 = readTokens(host, meta.key, meta);
  renderer.applyTokens(tokens0, renderer.bloomPass.strength);
  if (isMobile || reduced) {
    renderer.applyTier(
      { bloomAllowed: false, pixelRatioCap: isMobile ? 1.5 : 2, starScale: isMobile ? 0.6 : 1 },
      renderer.bloomPass.strength,
    );
  }

  // ---- 布局（Worker）----
  const params = { charge: -42, linkDistance: 34, linkStrength: 1, centerPull: 0.13, flatten: 0, velocityDecay: 0.34 };
  const layout = new WorkerForceLayout();
  layout.init(data, positions, params, 1);

  // ---- 高亮状态 ----
  let state = { type: null, value: null };
  let selected = -1;
  let hoverIdx = -1;

  // ---- 镜头 ----
  const camera = new CameraDirector(
    renderer.camera,
    renderer.renderer.domElement,
    {
      onFlyToSelected: () => { if (selected >= 0) flyToIndex(selected); },
      onResetView: () => camera.resetView(radius),
    },
    {},
  );
  camera.setInitialFraming(radius);

  // ---- 标签 LOD ----
  const baseMax = isMobile ? 28 : 60;
  const lod = new LabelLOD(
    renderer,
    data,
    adj,
    () => ({ w: host.clientWidth, h: host.clientHeight }),
    () => state,
    { baseMax, radius, mini: false },
  );
  lod.setDensity(1);

  // ---- hover 名牌（独立 DOM，RAF 内定位）----
  const hoverLabel = document.createElement('div');
  hoverLabel.className = 'nebula-hover-label';
  hoverLabel.style.cssText =
    'position:absolute;display:none;pointer-events:none;will-change:transform,opacity;' +
    'transform:translate(-50%,calc(-100% - 10px));font-family:var(--serif,serif);font-size:12px;' +
    'padding:1px 6px;border-radius:4px;white-space:nowrap;max-width:240px;text-overflow:ellipsis;overflow:hidden;';
  renderer.labels.root.appendChild(hoverLabel);
  const accentOf = () => (tokens0.accent || '#c24a32');

  // ---- RAF 循环 ----
  let raf = 0;
  let running = false;
  let last = performance.now();
  let lodAccum = 0;
  function frame(now) {
    if (!running) return;
    const deltaS = Math.min((now - last) / 1000, 0.05);
    last = now;
    if (layout.step()) renderer.updatePositions();
    camera.update(now, deltaS);
    renderer.render(deltaS);
    lodAccum += deltaS;
    if (lodAccum >= 0.12) { lodAccum = 0; lod.update(); } else lod.reposition();
    positionHoverLabel();
    raf = requestAnimationFrame(frame);
  }
  function startLoop() { if (!running) { running = true; last = performance.now(); raf = requestAnimationFrame(frame); } }
  function stopLoop() { running = false; cancelAnimationFrame(raf); }
  startLoop();

  function positionHoverLabel() {
    if (hoverIdx < 0) { hoverLabel.style.display = 'none'; return; }
    const { w, h } = { w: host.clientWidth, h: host.clientHeight };
    if (w < 2 || h < 2) return;
    const p = renderer.projectNode(hoverIdx, w, h);
    if (p.behind) { hoverLabel.style.display = 'none'; return; }
    hoverLabel.style.display = '';
    hoverLabel.style.transform = `translate(-50%, calc(-100% - 10px)) translate(${Math.round(p.x)}px, ${Math.round(p.y)}px)`;
  }

  // ---- ready：等首轮布局沉降 ----
  let readyResolve;
  const ready = new Promise((r) => (readyResolve = r));
  const settleWatch = setInterval(() => {
    if (layout.isSettled()) {
      clearInterval(settleWatch);
      renderer.updatePositions();
      camera.resetView(radius);
      if (!reduced) renderer.playReveal();
      lod.update();
      setTimeout(() => readyResolve?.(), reduced ? 30 : 400);
    }
  }, 120);

  // ---- 聚焦 / 飞行 ----
  function applyFocusByIndex(i) {
    selected = i;
    renderer.setFocus(i, adj[i]);
    renderer.setSelectedLinks(linksByNode[i]);
    state = { type: 'node', value: i };
    lod.update();
  }
  function clearFocus() {
    selected = -1;
    renderer.setFocus(-1, null);
    renderer.setSelectedLinks([]);
    state = { type: null, value: null };
    lod.update();
  }
  const _tmpV = new Vector3();
  function flyToIndex(i) {
    return new Promise((resolve) => {
      let done = false;
      const finish = () => { if (!done) { done = true; resolve(); } };
      const pos = renderer.nodePosition(i, _tmpV);
      camera.flyTo(pos, renderer.nodeRadius(i), finish);
      // 兜底：用户输入打断 tween 会使 onDone 不触发，超时强解（防 Connect-two 卡死）
      setTimeout(finish, FLY_TO.maxMs + 400);
    });
  }

  // ---- 拾取（点击：区分拖拽；hover：节流）----
  let downX = 0, downY = 0;
  function onPointerDown(e) { downX = e.clientX; downY = e.clientY; }
  function onClick(e) {
    if (connectActive) return; // Connect-two 巡航中禁用点击导航
    if (Math.hypot(e.clientX - downX, e.clientY - downY) > 6) return; // 拖拽松手
    const rect = host.getBoundingClientRect();
    const idx = renderer.pickNearest(e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height, 18);
    if (idx >= 0) {
      applyFocusByIndex(idx);
      flyToIndex(idx);
      const node = data.nodes[idx];
      opts.onSelect?.(node.origId, node);
    } else {
      clearFocus();
    }
  }
  let hoverRaf = 0;
  function onPointerMove(e) {
    if (hoverRaf) return;
    hoverRaf = requestAnimationFrame(() => {
      hoverRaf = 0;
      const rect = host.getBoundingClientRect();
      const idx = renderer.pickNearest(e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height, 14);
      if (idx !== hoverIdx) {
        hoverIdx = idx;
        const node = idx >= 0 ? data.nodes[idx] : null;
        if (node) {
          hoverLabel.textContent = node.name || node.origId;
          hoverLabel.style.background = tokens0.lightMode ? 'rgba(255,255,255,0.9)' : 'rgba(20,24,31,0.82)';
          hoverLabel.style.color = tokens0.lightMode ? '#2c2721' : '#e9e5d9';
          hoverLabel.style.border = `1px solid ${accentOf()}`;
          hoverLabel.style.display = '';
          renderer.renderer.domElement.style.cursor = 'pointer';
        } else {
          hoverLabel.style.display = 'none';
          renderer.renderer.domElement.style.cursor = 'grab';
        }
        opts.onHover?.(node ? node.origId : null);
      }
    });
  }
  function onPointerLeave() {
    if (hoverIdx >= 0) { hoverIdx = -1; hoverLabel.style.display = 'none'; opts.onHover?.(null); }
    renderer.renderer.domElement.style.cursor = '';
  }
  const dom = renderer.renderer.domElement;
  dom.addEventListener('pointerdown', onPointerDown);
  dom.addEventListener('click', onClick);
  dom.addEventListener('pointermove', onPointerMove);
  dom.addEventListener('pointerleave', onPointerLeave);

  // ---- resize ----
  const ro = new ResizeObserver(() => { renderer.resize(host.clientWidth, host.clientHeight); lod.update(); });
  ro.observe(host);

  // ---- Connect-two：六度逐跳飞行 ----
  let connectActive = false;
  let connectCancel = false;
  async function connectTwo(fromId, toId) {
    if (connectActive) { connectCancel = true; await sleep(60); }
    connectActive = true; connectCancel = false;
    try {
      const r = await getShortestPath(fromId, toId, CONNECT_MAX_DEPTH);
      if (!r || !r.path || !r.path.length) return { ok: false, reason: 'no-path' };
      // 节点序列：起点 + 每跳终点
      const seq = [r.path[0].from];
      for (const hop of r.path) seq.push(hop.to);
      for (const entityId of seq) {
        if (connectCancel) break;
        const idx = indexByEntityId.get(entityId);
        if (idx !== undefined) {
          applyFocusByIndex(idx);
          await flyToIndex(idx); // 飞抵（≤1.8s）
        }
        if (connectCancel) break;
        opts.onSelect?.(entityId); // 档案卡换页
        await sleep(HOP_DWELL_MS); // 停留 2s
      }
      return { ok: true, depth: r.path.length };
    } finally {
      connectActive = false;
      connectCancel = false;
    }
  }
  function cancelConnect() { connectCancel = true; }

  // ---- 主题热切换 ----
  function applyTheme(meta) {
    const tokens = readTokens(host, meta.key, meta);
    // 就地更新 tokens0（hover 名牌引用其 lightMode/accent）
    Object.assign(tokens0, tokens);
    renderer.applyTokens(tokens, renderer.bloomPass.strength);
    lod.update();
  }

  // ---- 控制器 ----
  return {
    ready,
    starCount: n,
    /** 外部选中（store 联动 / 搜索）：聚焦高亮 + 轻飞；不触发 onSelect 回调（避免环路） */
    focusEntity(entityId) {
      const idx = indexByEntityId.get(entityId);
      if (idx === undefined) return false;
      applyFocusByIndex(idx);
      flyToIndex(idx);
      return true;
    },
    connectTwo,
    cancelConnect,
    applyTheme,
    dispose() {
      connectCancel = true;
      stopLoop();
      clearInterval(settleWatch);
      ro.disconnect();
      dom.removeEventListener('pointerdown', onPointerDown);
      dom.removeEventListener('click', onClick);
      dom.removeEventListener('pointermove', onPointerMove);
      dom.removeEventListener('pointerleave', onPointerLeave);
      hoverLabel.remove();
      camera.dispose();
      layout.dispose();
      // 全量释放 three 资源（含 GL context），防内存泄漏（设计要求）
      renderer.dispose({ keepRenderer: false });
      host.replaceChildren();
    },
  };
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
