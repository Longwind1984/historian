// 时空柱 3D 编排（T3.3）：Z=时间·XY=方位 的原创轴系。
// 设计 docs/starmap-redesign.md §4。装配模式参照 mount.js（NebulaView），但场景/相机/渲染器
// 独立搭建--不复用 AggregateRenderer（那是星云 instanced 星点专用），只为时空柱合批光丝。
//
// T3.5 真机反馈打磨（2026-07-11）：
//   1) 朝代/hover 名牌走 CSS 变量（--ink/--paper-el/--accent），夜=深墨底亮字、纸=纸底墨字，四主题自适配;
//   2) 底盘地理示意图（geoSketch：海岸/双河/太行 + 地名），每层朝代盘叠极淡海岸线;
//   3) 材质墨感化：FogExp2 距离雾 + 光丝纵向渐变(顶端稍亮) + 朝代盘透明度降到 5.5% 去「亚克力片」感;
//   4) 事件环/战役点 raycast 可交互（hover 名牌带「事/战」徽记,click 联动档案卡）+ 左下图例(ColumnView);
//   5) 人物关联弧：选中人物画 Person↔Person 关系弧（getNeighbors 的 since/note），常态「关联脉络」toggle
//      画全库 Top60 双链人物对淡弧。
//
// 控制器契约（ColumnView 用）：
//   ready:Promise · threadCount:number · presetView(name) · onYearChange(year) ·
//   focusEntity(id) · canFollow(id) · applyTheme(meta) · setAmbientArcs(on) · getArcCount() · getDrawCalls() · dispose()
//
// 时间联动防环路：扫描环位置由 onYearChange（外部 store 变化）驱动 target z；
// 拖拽扫描环时由本引擎直接控位并经 opts.onYearDrag 反写 store，拖拽期间 onYearChange 被
// draggingScan guard 跳过，不回灌 target（见 frame / onYearChange / 拖拽段）。

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { api, getNeighbors, getGlobalGraph } from '../../api/client.js';
import { DYNASTY_COLORS, dynastyHexById, dynastySectorIndexById, readTokens } from './inkPalette.js';
import { unit } from './seed.js';
import { COASTLINE, YELLOW_RIVER, YANGTZE, TAIHANG, GEO_LABELS, smooth } from './geoSketch.js';

// ---- 空间参数（设计 §4 落地参数，任务书硬指定）----
export const COLUMN_YEAR_MIN = -221; // BC221 -> z=0（柱底）
export const COLUMN_YEAR_MAX = 1912; // AD1912 -> z=H（柱顶）
const H = 2400;                    // 柱高单位（每年≈1.125）
const R = 480;                     // XY 截面半径（光丝柱）
const RING_R = 520;                // 朝代带 / 底盘半径（略大于柱，如年轮）
const K = 22;                      // 经纬->世界单位
const LNG0 = 105, LAT0 = 34;      // 投影中心（中国大致中心）
const FOG_R_MIN = 500, FOG_R_MAX = 540;  // 雾环半径带
const FOG_DENSITY = 0.00026;       // FogExp2 密度：近端清晰、远端光丝朦胧（调参见 T3.5 报告）
const ARC_LIFT = 86;               // 关联弧顶向柱外抬升量（≈R*0.18）
const ARC_SEG = 16;                // 关联弧 Bezier 采样段数
const ACCENT_FALLBACK = '#c24a32';
const MAX_SEL_ARCS = 40;           // 选中人物关系弧上限
const MAX_AMBIENT_PAIRS = 60;      // 常态脉络人物对上限

function yearToZ(year) {
  if (year == null) return null;
  return ((year - COLUMN_YEAR_MIN) / (COLUMN_YEAR_MAX - COLUMN_YEAR_MIN)) * H;
}
function zToYear(z) {
  return Math.round(COLUMN_YEAR_MIN + (z / H) * (COLUMN_YEAR_MAX - COLUMN_YEAR_MIN));
}
// 仅扫描环需要“柱内”判定。yearToZ 本身故意不 clamp：数据节点若在轴外，
// 不能被挤到 -221/1912 端面冒充成边界年代。
export function columnScanZ(year) {
  const z = yearToZ(year);
  return Number.isFinite(z) && z >= 0 && z <= H ? z : null;
}
function lngLatToXY(lng, lat) {
  let x = (lng - LNG0) * K;
  let y = (lat - LAT0) * K;
  const d = Math.hypot(x, y);
  if (d > R - 6) { const s = (R - 6) / d; x *= s; y *= s; } // 截面内 clamp
  return [x, y];
}
/** 朝代色按 HSL 压亮度（lFactor=0.6 即 60% 亮度），保色相--对齐设计「朝代色 60% 亮度」 */
function dimColor(hex, lFactor) {
  const c = new THREE.Color(hex);
  const hsl = { h: 0, s: 0, l: 0 };
  c.getHSL(hsl);
  c.setHSL(hsl.h, hsl.s, Math.min(hsl.l * lFactor, 1));
  return c;
}
function easeIO(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export async function mountColumn(host, opts = {}) {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobile = matchMedia('(pointer: coarse)').matches;

  // ---- 主题 token（跟随 ui.palette：夜=深空，澄=纸墨）----
  let meta = opts.getPaletteMeta ? opts.getPaletteMeta() : { key: '澄', dark: false };
  let tokens = readTokens(host, meta.key, meta);
  let isDark = tokens.id === 'deep-space';
  let accent = tokens.accent || ACCENT_FALLBACK;
  const bgColor = () => (isDark ? 0x05060a : 0xf2ebdd);
  const paperColor = () => (isDark ? 0x0a0d14 : 0xf2ebdd);
  const gridColor = () => (isDark ? 0x2a3340 : 0xd8cdb6);

  // ---- 数据 ----
  const stRes = await api.get('/graph/spacetime').then((r) => r.data);
  const dynasties = stRes.dynasties || [];
  const allNodes = stRes.nodes || [];

  // 分类：人物=光丝 / 事件=环 / 战役=红球 / 无坐标=雾环
  const persons = [];
  const events = [];
  const battles = [];
  const fog = [];
  const nodeById = new Map();
  for (const n of allNodes) {
    nodeById.set(n.id, n);
    const hasGeo = n.x != null && n.y != null;
    const hasTime = n.born != null || n.died != null;
    if (n.type === 'Event' && hasGeo && n.born != null) events.push(n);
    else if (n.type === 'Battle' && hasGeo && n.born != null) battles.push(n);
    else if (n.type === 'Person' && hasGeo && hasTime) persons.push(n);
    else if (!hasGeo) fog.push(n);
  }
  const threadCount = persons.length;

  // ---- 场景 / 相机 / 渲染器 ----
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(bgColor());
  scene.fog = new THREE.FogExp2(bgColor(), FOG_DENSITY); // 距离雾：远端光丝朦胧、近端清晰

  const camera = new THREE.PerspectiveCamera(50, 1, 1, 12000);
  const colCenter = new THREE.Vector3(0, 0, H / 2);
  camera.position.set(R * 2.2, R * 2.2, H * 0.62);
  camera.lookAt(colCenter);

  const renderer = new THREE.WebGLRenderer({ antialias: !isMobile, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2)); // 提到 min(dpr,2)，去锯齿
  renderer.setSize(host.clientWidth || 800, host.clientHeight || 600);
  renderer.domElement.classList.add('column-canvas');
  renderer.domElement.dataset.testid = 'column-canvas';
  renderer.domElement.style.cssText = 'position:absolute;inset:0;display:block;cursor:grab;';
  host.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(colCenter);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.update();

  // ---- 底盘 ----
  const baseDisk = buildBaseDisk(RING_R, paperColor());
  scene.add(baseDisk);

  // ---- 朝代带（InstancedMesh 圆盘，朝代色 5.5%，1 draw call）--透明度降到 5-6% 去「亚克力片」感 ----
  const { bandMesh, bandData } = buildDynastyBands(dynasties, RING_R);
  scene.add(bandMesh);
  // ---- 经纬网格 + 朝代盘缘描边 + 每层盘极淡海岸线（合并 LineSegments，1 draw call）----
  scene.add(buildLines(RING_R, gridColor(), dynasties));

  // ---- 地理示意图（底盘完整版：海岸墨 + 双河黛蓝 + 太行赭，合并单批次 vertexColors，1 draw call）----
  let geoMesh = null;
  function addGeo() {
    if (geoMesh) { scene.remove(geoMesh); geoMesh.geometry.dispose(); geoMesh.material.dispose(); }
    geoMesh = buildGeo(isDark);
    scene.add(geoMesh);
  }
  addGeo();

  // ---- 光丝（InstancedMesh Box，长轴 z，纵向渐变，1 draw call）----
  const { threadMesh, threadNodes, threadIdxById } = buildThreads(persons);
  scene.add(threadMesh);

  // ---- 雾环（Points，1 draw call）----
  scene.add(buildFog(fog));

  // ---- 事件环 / 战役球（各 1 InstancedMesh）----
  const eventMesh = buildEventRings(events);
  const battleMesh = buildBattleSpheres(battles);
  scene.add(eventMesh.mesh);
  scene.add(battleMesh.mesh);
  const eventNodes = eventMesh.nodes; // [{id,name,born,type:'Event'}]
  const battleNodes = battleMesh.nodes;
  eventMesh.mesh.scale.setScalar(0.01); // 入场动画 0->1
  battleMesh.mesh.scale.setScalar(0.01);

  // ---- 当前年扫描环 + 不可见命中环 ----
  const scanRing = new THREE.Mesh(
    new THREE.TorusGeometry(R, 4, 8, 80),
    new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.9 }),
  );
  const scanHit = new THREE.Mesh(
    new THREE.TorusGeometry(R, 22, 6, 80),
    new THREE.MeshBasicMaterial({ visible: false }),
  );
  // material 不渲染，object.visible 只表达能否命中：年份在柱外时扫描环与命中环一起隐藏。
  const initYear = opts.getCurrentYear ? opts.getCurrentYear() : 750;
  const initScanZ = columnScanZ(initYear);
  let scanTargetZ = initScanZ ?? H / 2;
  scanRing.position.z = scanTargetZ;
  scanHit.position.z = scanTargetZ;
  scanRing.visible = initScanZ != null;
  scanHit.visible = initScanZ != null;
  scene.add(scanRing, scanHit);

  // ---- 脉冲 overlay（跟随一生途经事件/战役时涟漪）----
  const pulseRing = new THREE.Mesh(
    new THREE.TorusGeometry(16, 2.5, 8, 32),
    new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0, depthWrite: false }),
  );
  pulseRing.visible = false;
  scene.add(pulseRing);
  const pulse = { t0: 0, dur: 700, active: false };

  // ---- hover 高亮丝 overlay（不改 instanceColor buffer，单 mesh 跟随）----
  const hoverThread = new THREE.Mesh(
    new THREE.BoxGeometry(1, 1, 1),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95, depthWrite: false }),
  );
  hoverThread.visible = false;
  scene.add(hoverThread);

  // ---- DOM 标签层（朝代名 + hover 名牌 + 地名,0 draw call,全走 CSS 变量随主题）----
  const labelLayer = document.createElement('div');
  labelLayer.style.cssText = 'position:absolute;inset:0;pointer-events:none;overflow:hidden;';
  host.appendChild(labelLayer);
  // 朝代盘缘名牌：夜=深墨底亮字 / 纸=纸底墨字（color-mix 半透明,随主题热切换）
  const dynLabels = dynasties
    .filter((d) => d.from != null && d.to != null && yearToZ((d.from + d.to) / 2) != null)
    .map((d) => {
      const el = document.createElement('div');
      el.className = 'col-dyn-label';
      el.style.cssText =
        'position:absolute;transform:translate(-50%,-50%);font-family:var(--serif,serif);font-size:12px;' +
        'color:var(--ink);background:color-mix(in srgb,var(--paper-el) 86%,transparent);padding:1px 6px;' +
        'border-radius:3px;white-space:nowrap;letter-spacing:0.05em;' +
        'border:1px solid color-mix(in srgb,var(--line) 70%,transparent);';
      el.textContent = d.name;
      labelLayer.appendChild(el);
      return { el, z: yearToZ((d.from + d.to) / 2) };
    });
  // 地名小字（衬线 10px,随主题）
  const geoLabelEls = GEO_LABELS.map((g) => {
    const el = document.createElement('div');
    el.className = 'col-geo-label';
    el.style.cssText =
      'position:absolute;transform:translate(-50%,-50%);font-family:var(--serif,serif);font-size:10px;' +
      'color:var(--ink-soft);pointer-events:none;white-space:nowrap;letter-spacing:0.04em;opacity:0.72;';
    el.textContent = g.name;
    labelLayer.appendChild(el);
    const [x, y] = lngLatToXY(g.lng, g.lat);
    return { el, x, y };
  });
  // hover 名牌（丝/环/点/弧共用）
  const hoverLabel = document.createElement('div');
  hoverLabel.style.cssText =
    'position:absolute;display:none;pointer-events:none;transform:translate(-50%,calc(-100% - 10px));' +
    'font-family:var(--serif,serif);font-size:12px;padding:2px 8px;border-radius:4px;white-space:nowrap;' +
    'max-width:260px;overflow:hidden;text-overflow:ellipsis;' +
    'color:var(--ink);background:color-mix(in srgb,var(--paper-el) 90%,transparent);border:1px solid var(--accent);';
  labelLayer.appendChild(hoverLabel);

  // ---- 关联弧（选中人物关系弧 + 常态脉络淡弧）----
  let selectedArcLine = null;     // 选中人物 Person↔Person 关系弧（accent 45%）
  let ambientArcLine = null;      // 常态 Top60 双链人物对淡弧（墨色 9%）
  let ambientArcsOn = true;       // 「关联脉络」toggle，默认开
  let disposed = false;

  function buildArcs(arcEdges, color, opacity) {
    const positions = [];
    for (const e of arcEdges) {
      const { p0, p1 } = e;
      const mid = new THREE.Vector3((p0.x + p1.x) / 2, (p0.y + p1.y) / 2, (p0.z + p1.z) / 2);
      const r = Math.hypot(mid.x, mid.y) || 1;
      // 弧顶向柱外（径向）抬升
      const cp = new THREE.Vector3(mid.x + (mid.x / r) * ARC_LIFT, mid.y + (mid.y / r) * ARC_LIFT, mid.z);
      const curve = new THREE.QuadraticBezierCurve3(p0, cp, p1);
      const pts = curve.getPoints(ARC_SEG); // ARC_SEG+1 点
      for (let i = 0; i < pts.length - 1; i++) {
        positions.push(pts[i].x, pts[i].y, pts[i].z, pts[i + 1].x, pts[i + 1].y, pts[i + 1].z);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    const m = new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false });
    const line = new THREE.LineSegments(g, m);
    line.frustumCulled = false;
    line.userData.segPerArc = ARC_SEG;
    return line;
  }

  /** 选中人物关系弧：getNeighbors 取 Person-Person 边，关系年代取 since.year 或双方生年重叠中点 */
  async function rebuildSelectedArcs(personId) {
    if (selectedArcLine) {
      scene.remove(selectedArcLine);
      selectedArcLine.geometry.dispose();
      selectedArcLine.material.dispose();
      selectedArcLine = null;
    }
    if (!personId || disposed) return;
    const node = nodeById.get(personId);
    if (!node || node.type !== 'Person') return;
    const selfIdx = threadIdxById.get(personId);
    if (selfIdx == null) return; // 无坐标人物不画弧
    const self = threadNodes[selfIdx];
    let arcEdges = [];
    let arcMetas = [];
    try {
      const nb = await getNeighbors(personId, 1);
      const nbByType = new Map((nb.nodes || []).map((n) => [n.id, n]));
      const cand = (nb.edges || [])
        .filter((e) => e.from === personId || e.to === personId)
        .map((e) => {
          const otherId = e.from === personId ? e.to : e.from;
          const otherNode = nbByType.get(otherId);
          if (!otherNode || otherNode.type !== 'Person') return null;
          const otherIdx = threadIdxById.get(otherId);
          if (otherIdx == null) return null; // 邻居无坐标不入弧
          return { e, other: threadNodes[otherIdx] };
        })
        .filter(Boolean)
        .slice(0, MAX_SEL_ARCS);
      for (const { e, other } of cand) {
        const sinceYear = e?.since?.year;
        let z;
        if (sinceYear != null) z = yearToZ(sinceYear);
        else {
          // since 缺失：双方生年重叠中点；不重叠取生年均值
          const lo = Math.max(self.born ?? -9999, other.born ?? -9999);
          const hi = Math.min(self.died ?? 9999, other.died ?? 9999);
          z = lo <= hi ? yearToZ((lo + hi) / 2) : yearToZ(((self.born ?? 0) + (other.born ?? 0)) / 2);
        }
        if (z == null) z = (self._zB + other._zB) / 2;
        arcEdges.push({
          p0: new THREE.Vector3(self._x, self._y, z),
          p1: new THREE.Vector3(other._x, other._y, z),
        });
        arcMetas.push({
          name: other.name || other.id,
          type: e.type || '关联',
          note: e.note || '',
          year: sinceYear ?? null,
        });
      }
    } catch { /* 无邻居则无弧 */ }
    if (disposed) return;
    if (arcEdges.length) {
      selectedArcLine = buildArcs(arcEdges, accent, 0.45);
      selectedArcLine.userData.arcs = arcMetas;
      scene.add(selectedArcLine);
    }
  }

  /** 常态脉络：全库双链 Top60 人物对淡弧（柱体呈现组织感）*/
  async function buildAmbientArcs() {
    let res;
    try { res = await getGlobalGraph(120, 2); }
    catch { return; }
    if (disposed) return;
    const idType = new Map((res.nodes || []).map((n) => [n.id, n.type]));
    const idLinks = new Map((res.nodes || []).map((n) => [n.id, (n.out || 0) + (n.in || 0)]));
    const pairs = [];
    for (const e of res.edges || []) {
      if (idType.get(e.from) !== 'Person' || idType.get(e.to) !== 'Person') continue;
      const ia = threadIdxById.get(e.from), ib = threadIdxById.get(e.to);
      if (ia == null || ib == null) continue;
      const a = threadNodes[ia], b = threadNodes[ib];
      pairs.push({ a, b, w: (idLinks.get(e.from) || 0) + (idLinks.get(e.to) || 0) });
    }
    pairs.sort((x, y) => y.w - x.w);
    const top = pairs.slice(0, MAX_AMBIENT_PAIRS);
    if (!top.length) return;
    const arcEdges = top.map(({ a, b }) => ({
      p0: new THREE.Vector3(a._x, a._y, (a._zB + a._zD) / 2),
      p1: new THREE.Vector3(b._x, b._y, (b._zB + b._zD) / 2),
    }));
    ambientArcLine = buildArcs(arcEdges, isDark ? '#cfd6df' : '#5b544a', 0.09);
    ambientArcLine.userData.arcs = top.map(({ a, b }) => ({ name: `${a.name}·${b.name}`, type: '双链', note: '' }));
    ambientArcLine.visible = ambientArcsOn;
    scene.add(ambientArcLine);
  }
  buildAmbientArcs(); // 异步,不阻塞 ready

  // ---- raycaster / 指针 ----
  const raycaster = new THREE.Raycaster();
  raycaster.params.Line.threshold = 8; // 弧线命中阈值（世界单位）
  const ndc = new THREE.Vector2();
  const tmpV = new THREE.Vector3();
  const hoverAnchor = new THREE.Vector3(); // 名牌投影锚点（world）
  let hoverKind = 'none';                  // 'none'|'thread'|'event'|'battle'|'arc'
  let downX = 0, downY = 0;
  let hoverRaf = 0;

  function setNDC(e) {
    const rect = renderer.domElement.getBoundingClientRect();
    ndc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    ndc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  }
  /** ray 与 z 轴(x=0,y=0) 最近点的 z--用于拖拽扫描环时把指针投到柱轴 */
  function rayToZAxis() {
    const o = raycaster.ray.origin, d = raycaster.ray.direction;
    const denom = d.x * d.x + d.y * d.y;
    if (denom < 1e-8) return null; // ray 近似平行 z 轴：z 无法定
    const t = -(o.x * d.x + o.y * d.y) / denom;
    return o.z + t * d.z;
  }

  // ---- 扫描环拖拽（防环路）----
  let draggingScan = false;
  function onPointerDown(e) {
    setNDC(e);
    raycaster.setFromCamera(ndc, camera);
    if (raycaster.intersectObject(scanHit)[0]) {
      draggingScan = true;
      controls.enabled = false;
      renderer.domElement.style.cursor = 'ns-resize';
      e.preventDefault();
      return;
    }
    downX = e.clientX; downY = e.clientY;
    markInput();
  }
  function onPointerMove(e) {
    setNDC(e);
    if (draggingScan) {
      const z = rayToZAxis();
      if (z != null) {
        const zc = Math.max(0, Math.min(H, z));
        scanRing.position.z = zc;     // 拖拽中直接控位
        scanHit.position.z = zc;
        scanTargetZ = zc;             // target 同步，松手后无跳变
        opts.onYearDrag?.(zToYear(zc)); // 反写 store（store 变化触发的 onYearChange 被 draggingScan guard 挡住）
      }
      return;
    }
    if (hoverRaf) return; // rAF 节流 hover raycast
    hoverRaf = requestAnimationFrame(() => {
      hoverRaf = 0;
      raycaster.setFromCamera(ndc, camera);
      // 一次 raycast 全部可交互对象，按距离取最近
      const targets = [threadMesh];
      if (eventMesh.mesh.isInstancedMesh) targets.push(eventMesh.mesh);
      if (battleMesh.mesh.isInstancedMesh) targets.push(battleMesh.mesh);
      if (selectedArcLine && selectedArcLine.visible) targets.push(selectedArcLine);
      const its = raycaster.intersectObjects(targets, false);
      applyHover(its.length ? its[0] : null);
    });
  }
  function onPointerUp() {
    if (draggingScan) {
      draggingScan = false;
      controls.enabled = true;
      renderer.domElement.style.cursor = 'grab';
      scanTargetZ = scanRing.position.z;
    }
  }
  function onClick(e) {
    if (Math.hypot(e.clientX - downX, e.clientY - downY) > 6) return; // 拖拽松手不触发点击
    if (draggingScan) return;
    setNDC(e);
    raycaster.setFromCamera(ndc, camera);
    // 弧不触发 selectEntity（关系非实体）
    if (selectedArcLine && selectedArcLine.visible && raycaster.intersectObject(selectedArcLine).length) return;
    const targets = [threadMesh];
    if (eventMesh.mesh.isInstancedMesh) targets.push(eventMesh.mesh);
    if (battleMesh.mesh.isInstancedMesh) targets.push(battleMesh.mesh);
    const its = raycaster.intersectObjects(targets, false);
    if (!its.length) return;
    const it = its[0];
    if (it.object === eventMesh.mesh) {
      const node = eventNodes[it.instanceId];
      if (node) opts.onSelect?.(node.id, 'Event');
    } else if (it.object === battleMesh.mesh) {
      const node = battleNodes[it.instanceId];
      if (node) opts.onSelect?.(node.id, 'Battle');
    } else {
      const node = threadNodes[it.instanceId];
      if (node) { opts.onSelect?.(node.id, 'Person'); setHoverThread(it.instanceId, true); }
    }
  }

  function badgeHTML(ch) {
    return `<span style="display:inline-block;margin:0 3px;padding:0 4px;border-radius:3px;font-size:10px;` +
      `line-height:14px;background:var(--accent);color:var(--accent-text);vertical-align:1px;">${ch}</span>`;
  }
  function applyHover(it) {
    if (!it) {
      hoverKind = 'none';
      hoverLabel.style.display = 'none';
      hoverThread.visible = false;
      renderer.domElement.style.cursor = draggingScan ? 'ns-resize' : 'grab';
      return;
    }
    renderer.domElement.style.cursor = 'pointer';
    if (it.object === selectedArcLine) {
      const idx = Math.floor(it.index / (ARC_SEG * 2));
      const arc = (selectedArcLine.userData.arcs || [])[idx];
      if (arc) {
        const parts = [`<b>${arc.name}</b>`, badgeHTML('关') + arc.type];
        if (arc.year != null) parts.push(String(arc.year));
        if (arc.note) parts.push(arc.note);
        hoverLabel.innerHTML = parts.join(' · ');
      }
      hoverThread.visible = false;
      hoverAnchor.copy(it.point);
      hoverKind = 'arc';
    } else if (it.object === eventMesh.mesh) {
      const node = eventNodes[it.instanceId];
      hoverLabel.innerHTML = `<b>${node?.name || node?.id || ''}</b> ${badgeHTML('事')}` +
        (node?.born != null ? ` · ${node.born}` : '');
      hoverThread.visible = false;
      hoverAnchor.copy(it.point);
      hoverKind = 'event';
    } else if (it.object === battleMesh.mesh) {
      const node = battleNodes[it.instanceId];
      hoverLabel.innerHTML = `<b>${node?.name || node?.id || ''}</b> ${badgeHTML('战')}` +
        (node?.born != null ? ` · ${node.born}` : '');
      hoverThread.visible = false;
      hoverAnchor.copy(it.point);
      hoverKind = 'battle';
    } else {
      const node = threadNodes[it.instanceId];
      hoverLabel.innerHTML = `<b>${node?.name || node?.id || ''}</b>`;
      hoverThread.visible = true;
      hoverThread.material.color.set(0xffffff);
      threadMesh.getMatrixAt(it.instanceId, hoverThread.matrix);
      hoverThread.matrixAutoUpdate = false;
      hoverAnchor.set(node._x, node._y, (node._zB + node._zD) / 2);
      hoverKind = 'thread';
    }
    hoverLabel.style.display = '';
  }
  function setHoverThread(idx, selected) {
    if (idx < 0 || idx >= threadNodes.length) { hoverThread.visible = false; return; }
    threadMesh.getMatrixAt(idx, hoverThread.matrix); // 复用该丝的 matrix（位置+尺寸）
    hoverThread.matrixAutoUpdate = false;
    hoverThread.visible = true;
    hoverThread.material.color.set(selected ? accent : 0xffffff);
  }

  const dom = renderer.domElement;
  dom.addEventListener('pointerdown', onPointerDown);
  dom.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp); // 松手可能在画布外
  dom.addEventListener('click', onClick);

  // ---- 相机预设 ----
  let tween = null;
  let cruiseMode = false;
  let cruiseAngle = 0;
  let followState = null;
  function markInput() {
    tween = null;
    cruiseMode = false;
    if (followState) followState.active = false;
  }
  function startTween(toPos, toTarget, durMs, onDone) {
    tween = {
      t0: performance.now(), durMs,
      fromPos: camera.position.clone(), toPos,
      fromTarget: controls.target.clone(), toTarget,
      onDone,
    };
  }

  function presetView(name) {
    if (name === 'overview') {
      cruiseMode = false; followState = null; tween = null;
      startTween(new THREE.Vector3(R * 2.2, R * 2.2, H * 0.62), colCenter.clone(), 1200);
      return true;
    }
    if (name === 'cruise') {
      tween = null; followState = null;
      cruiseAngle = Math.atan2(camera.position.y, camera.position.x);
      cruiseMode = true; // rAF 内贴 z(year)+40、半径 R*1.5 环绕；交互即停（markInput）
      return true;
    }
    if (name === 'follow') {
      const id = opts.getSelectedEntityId?.();
      if (!id) return false;
      startFollowLife(id);
      return true;
    }
    return false;
  }

  async function startFollowLife(personId) {
    const node = nodeById.get(personId);
    if (!node || node.type !== 'Person' || node.x == null) return false;
    const [px, py] = lngLatToXY(node.x, node.y);
    const zB = yearToZ(node.born ?? node.died);
    const zD = yearToZ(node.died ?? node.born);
    if (zB == null || zD == null) return false;
    // 查参与的事件/战役（participated_in 邻域过滤 Event/Battle）
    let evs = [];
    try {
      const nb = await getNeighbors(personId, 1);
      evs = nb.nodes
        .filter((n) => n.type === 'Event' || n.type === 'Battle')
        .map((n) => {
          const en = nodeById.get(n.id);
          if (!en || en.x == null || en.born == null) return null;
          const [ex, ey] = lngLatToXY(en.x, en.y);
          return { x: ex, y: ey, z: yearToZ(en.born) };
        })
        .filter(Boolean)
        .sort((a, b) => a.z - b.z);
    } catch { /* 无邻居则纯爬升 */ }
    tween = null; cruiseMode = false;
    hoverThread.visible = false; // follow 期间相机跟随已表达选中,释放 hoverThread 的 draw call 给 pulse
    followState = { px, py, zB, zD, evs, evIdx: 0, t0: performance.now(), dur: 8000, active: true };
    return true;
  }

  function triggerPulse(x, y, z) {
    pulseRing.position.set(x, y, z);
    pulseRing.visible = true;
    pulse.active = true;
    pulse.t0 = performance.now();
  }

  // ---- 时间联动（防环路入口）----
  function onYearChange(year) {
    if (draggingScan) return true; // 拖拽中：本引擎在写 store，跳过回灌
    const z = columnScanZ(year);
    const visible = z != null;
    scanRing.visible = visible;
    scanHit.visible = visible;
    if (visible) scanTargetZ = z;
    return visible;
  }

  // ---- RAF ----
  let raf = 0, running = false, last = performance.now();
  const revealT0 = performance.now();
  function frame(now) {
    if (!running) return;
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;

    // 入场：事件环/战役球整体 scale 0->1（一次性）
    const rk = easeIO(Math.min((now - revealT0) / 600, 1));
    eventMesh.mesh.scale.setScalar(rk);
    battleMesh.mesh.scale.setScalar(rk);

    // 扫描环平滑跟随 target（外部 store 变化经 onYearChange 设 target）
    scanRing.position.z += (scanTargetZ - scanRing.position.z) * 0.18;
    scanHit.position.z = scanRing.position.z;

    // 相机驱动优先级：tween > follow > cruise > controls
    if (tween) {
      const t = Math.min((now - tween.t0) / tween.durMs, 1);
      const k = easeIO(t);
      camera.position.lerpVectors(tween.fromPos, tween.toPos, k);
      controls.target.lerpVectors(tween.fromTarget, tween.toTarget, k);
      if (t >= 1) { const cb = tween.onDone; tween = null; cb?.(); }
    } else if (followState && followState.active) {
      const t = Math.min((now - followState.t0) / followState.dur, 1);
      const z = followState.zB + (followState.zD - followState.zB) * t;
      camera.position.set(followState.px + 70, followState.py + 70, z);
      controls.target.set(followState.px, followState.py, z);
      camera.lookAt(controls.target);
      while (followState.evIdx < followState.evs.length && followState.evs[followState.evIdx].z <= z) {
        const ev = followState.evs[followState.evIdx++];
        triggerPulse(ev.x, ev.y, ev.z);
      }
      if (t >= 1) followState.active = false;
    } else if (cruiseMode) {
      cruiseAngle += dt * 0.25;
      const z = scanRing.position.z + 40;
      camera.position.set(R * 1.5 * Math.cos(cruiseAngle), R * 1.5 * Math.sin(cruiseAngle), z);
      controls.target.set(0, 0, z);
      camera.lookAt(controls.target);
    } else {
      controls.update();
    }

    // 脉冲 overlay 涟漪
    if (pulse.active) {
      const pt = (now - pulse.t0) / pulse.dur;
      if (pt >= 1) { pulse.active = false; pulseRing.visible = false; }
      else {
        pulseRing.scale.setScalar(1 + Math.sin(pt * Math.PI) * 0.9);
        pulseRing.material.opacity = 0.8 * (1 - pt);
      }
    }

    renderer.render(scene, camera);
    updateLabels();
    raf = requestAnimationFrame(frame);
  }
  function startLoop() { if (!running) { running = true; last = performance.now(); raf = requestAnimationFrame(frame); } }
  function stopLoop() { running = false; cancelAnimationFrame(raf); }
  startLoop();

  function updateLabels() {
    const w = host.clientWidth, h = host.clientHeight;
    if (w < 2 || h < 2) return;
    for (const lb of dynLabels) {
      tmpV.set(RING_R * 0.92, 0, lb.z).project(camera);
      if (tmpV.z > 1 || tmpV.z < -1) { lb.el.style.display = 'none'; continue; }
      lb.el.style.display = '';
      lb.el.style.left = ((tmpV.x * 0.5 + 0.5) * w) + 'px';
      lb.el.style.top = ((-tmpV.y * 0.5 + 0.5) * h) + 'px';
    }
    for (const lb of geoLabelEls) {
      tmpV.set(lb.x, lb.y, 0.6).project(camera);
      if (tmpV.z > 1 || tmpV.z < -1) { lb.el.style.display = 'none'; continue; }
      lb.el.style.display = '';
      lb.el.style.left = ((tmpV.x * 0.5 + 0.5) * w) + 'px';
      lb.el.style.top = ((-tmpV.y * 0.5 + 0.5) * h) + 'px';
    }
    if (hoverKind !== 'none' && hoverLabel.style.display !== 'none') {
      tmpV.copy(hoverAnchor).project(camera);
      if (tmpV.z > 1) hoverLabel.style.display = 'none';
      else {
        hoverLabel.style.left = ((tmpV.x * 0.5 + 0.5) * w) + 'px';
        hoverLabel.style.top = ((-tmpV.y * 0.5 + 0.5) * h) + 'px';
      }
    }
  }

  // ---- resize ----
  const ro = new ResizeObserver(() => {
    const w = host.clientWidth, h = host.clientHeight;
    if (w < 2 || h < 2) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
  ro.observe(host);

  // ---- ready ----
  let readyResolve;
  const ready = new Promise((r) => (readyResolve = r));
  setTimeout(() => readyResolve?.(), reduced ? 30 : 300);

  // ---- 控制器 ----
  return {
    ready,
    threadCount,
    presetView,
    onYearChange,
    getScanState: () => ({
      visible: scanRing.visible,
      targetZ: scanTargetZ,
      minYear: COLUMN_YEAR_MIN,
      maxYear: COLUMN_YEAR_MAX,
    }),
    getDynastyColors: () => Object.fromEntries(
      dynasties.map((d) => [d.id, dynastyHexById(d.id)]),
    ),
    getDrawCalls: () => renderer.info.render.calls,
    getArcCount: () => {
      let n = 0;
      if (selectedArcLine && selectedArcLine.visible) n += (selectedArcLine.userData.arcs || []).length;
      if (ambientArcLine && ambientArcLine.visible) n += (ambientArcLine.userData.arcs || []).length;
      return n;
    },
    setAmbientArcs(on) {
      ambientArcsOn = !!on;
      if (ambientArcLine) ambientArcLine.visible = ambientArcsOn;
    },
    focusEntity(id) {
      const idx = threadIdxById.get(id);
      setHoverThread(idx == null ? -1 : idx, true); // 选中联动：高亮丝（不触发 onSelect，防环路）
      rebuildSelectedArcs(id); // 异步画 Person↔Person 关系弧
      return true;
    },
    /** B2:同步判定该实体可否「跟随一生」（与 startFollowLife 的前置守卫同源:
     *  场景内 Person、有坐标、有年份）。供 ColumnView 在外部选中时决定是否自动起飞;
     *  非人物/不在场景者只留 focusEntity 的高亮丝。 */
    canFollow(id) {
      const n = nodeById.get(id);
      return !!(n && n.type === 'Person' && n.x != null && (n.born != null || n.died != null));
    },
    applyTheme(meta2) {
      // 主题热切换：底色/雾/扫描环/geo/弧色重应用（标签色靠 CSS 变量自动跟）
      tokens = readTokens(host, meta2.key, meta2);
      isDark = tokens.id === 'deep-space';
      accent = tokens.accent || ACCENT_FALLBACK;
      const bg2 = bgColor();
      scene.background = new THREE.Color(bg2);
      scene.fog.color.set(bg2);
      baseDisk.material.color.set(paperColor());
      scanRing.material.color.set(accent);
      pulseRing.material.color.set(accent);
      hoverThread.material.color.set(accent);
      addGeo(); // 地理轮廓颜色主题化重建
      if (selectedArcLine) selectedArcLine.material.color.set(accent);
      if (ambientArcLine) ambientArcLine.material.color.set(isDark ? '#cfd6df' : '#5b544a');
    },
    dispose() {
      disposed = true;
      stopLoop();
      ro.disconnect();
      dom.removeEventListener('pointerdown', onPointerDown);
      dom.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      dom.removeEventListener('click', onClick);
      labelLayer.remove();
      controls.dispose();
      scene.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) {
          if (Array.isArray(o.material)) o.material.forEach((m) => m.dispose());
          else o.material.dispose();
        }
      });
      renderer.dispose();
      host.replaceChildren();
    },
  };
}

// ============ 构建函数 ============

function buildBaseDisk(radius, paperColor) {
  const disk = new THREE.Mesh(
    new THREE.CircleGeometry(radius, 96),
    new THREE.MeshBasicMaterial({ color: paperColor, transparent: true, opacity: 0.92, side: THREE.DoubleSide }),
  );
  disk.position.z = 0.5; // 略离 z=0 避让网格
  return disk;
}

/** 经纬网格 + 朝代盘缘描边 + 每层盘极淡海岸线：合并到单个 LineSegments（vertexColors），1 draw call */
function buildLines(radius, gridColor, dynasties) {
  const positions = [], colors = [];
  const gc = new THREE.Color(gridColor);
  const pushLine = (x1, y1, z1, x2, y2, z2, c) => {
    positions.push(x1, y1, z1, x2, y2, z2);
    colors.push(c.r, c.g, c.b, c.r, c.g, c.b);
  };
  // 放射线（每 10°）
  for (let i = 0; i < 36; i++) {
    const a = (i / 36) * Math.PI * 2;
    pushLine(0, 0, 0.4, Math.cos(a) * radius, Math.sin(a) * radius, 0.4, gc);
  }
  // 同心圆（每 80 单位，最大圈即盘缘）
  for (let r = 80; r <= radius; r += 80) {
    for (let i = 0; i < 72; i++) {
      const a1 = (i / 72) * Math.PI * 2, a2 = ((i + 1) / 72) * Math.PI * 2;
      pushLine(Math.cos(a1) * r, Math.sin(a1) * r, 0.4, Math.cos(a2) * r, Math.sin(a2) * r, 0.4, gc);
    }
  }
  // 朝代盘缘描边（各朝代色，在朝代带 z 处）
  for (const d of dynasties) {
    if (d.from == null || d.to == null) continue;
    const z = yearToZ((d.from + d.to) / 2);
    if (z == null) continue;
    const col = new THREE.Color(dynastyHexById(d.id));
    const seg = 64;
    for (let i = 0; i < seg; i++) {
      const a1 = (i / seg) * Math.PI * 2, a2 = ((i + 1) / seg) * Math.PI * 2;
      pushLine(Math.cos(a1) * radius, Math.sin(a1) * radius, z, Math.cos(a2) * radius, Math.sin(a2) * radius, z, col);
    }
  }
  // 每层朝代盘：极淡海岸线轮廓（墨色×0.22 预乘,整体 opacity 0.45 后 ≈ 10%，优雅不喧宾夺主）
  const coastPts = smooth(COASTLINE).map((p) => lngLatToXY(p[0], p[1]));
  const coastCol = new THREE.Color('#2c2721').multiplyScalar(0.22);
  for (const d of dynasties) {
    if (d.from == null || d.to == null) continue;
    const z = yearToZ((d.from + d.to) / 2);
    if (z == null) continue;
    for (let i = 0; i < coastPts.length - 1; i++) {
      pushLine(coastPts[i][0], coastPts[i][1], z, coastPts[i + 1][0], coastPts[i + 1][1], z, coastCol);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.45 }));
}

/** 朝代带：InstancedMesh 圆盘（朝代色 5.5% via material.opacity）+ 盘缘描边 LineSegments */
function buildDynastyBands(dynasties, radius) {
  const valid = dynasties.filter((d) => d.from != null && d.to != null && yearToZ((d.from + d.to) / 2) != null);
  const geo = new THREE.CircleGeometry(radius, 64);
  const mat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.055, side: THREE.DoubleSide, depthWrite: false });
  const bandMesh = new THREE.InstancedMesh(geo, mat, valid.length);
  bandMesh.frustumCulled = false;
  const m = new THREE.Matrix4();
  const bandData = [];
  valid.forEach((d, i) => {
    const z = yearToZ((d.from + d.to) / 2);
    m.makeTranslation(0, 0, z);
    bandMesh.setMatrixAt(i, m);
    bandMesh.setColorAt(i, new THREE.Color(dynastyHexById(d.id)));
    bandData.push({ id: d.id, z });
  });
  bandMesh.instanceMatrix.needsUpdate = true;
  if (bandMesh.instanceColor) bandMesh.instanceColor.needsUpdate = true;
  return { bandMesh, bandData };
}

/** 光丝：InstancedMesh Box(1,1,1)，长轴 z 由 scale.z 给；顶点纵向渐变（顶端稍亮）+ 朝代色 instanceColor。
 *  1 draw call，5000+ 根。最终色 = vertexColor(顶亮1/底暗0.74) × instanceColor(朝代色 60%) */
function buildThreads(persons) {
  const N = persons.length;
  const geo = new THREE.BoxGeometry(1, 1, 1);
  // 纵向渐变：z≥0 顶点亮 (1,1,1)，z<0 底端暗 (0.74,0.74,0.74) -- 极轻纵向渐变去塑料感
  const pos = geo.attributes.position;
  const vcol = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const k = pos.getZ(i) >= 0 ? 1.0 : 0.74;
    vcol[i * 3] = k; vcol[i * 3 + 1] = k; vcol[i * 3 + 2] = k;
  }
  geo.setAttribute('color', new THREE.Float32BufferAttribute(vcol, 3));
  const mat = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.82 });
  const mesh = new THREE.InstancedMesh(geo, mat, Math.max(N, 1));
  mesh.frustumCulled = false;
  mesh.count = N;
  const m = new THREE.Matrix4();
  const threadNodes = [];
  const threadIdxById = new Map();
  persons.forEach((n, i) => {
    const [x, y] = lngLatToXY(n.x, n.y);
    let zB = n.born != null ? yearToZ(n.born) : null;
    let zD = n.died != null ? yearToZ(n.died) : null;
    if (zB == null && zD != null) zB = zD - 2; // 缺一端长度=2
    if (zD == null && zB != null) zD = zB + 2;
    if (zB == null) { zB = 0; zD = 2; }
    const zMid = (zB + zD) / 2;
    const len = Math.max(Math.abs(zD - zB), 2);
    const thick = 1.8 + Math.min(Math.log(1 + (n.links || 0)) * 0.45, 3.2); // 粗细=重要度（ln 双链度）
    m.makeScale(thick, thick, len);
    m.setPosition(x, y, zMid);
    mesh.setMatrixAt(i, m);
    mesh.setColorAt(i, dimColor(dynastyHexById(n.dynasty), 0.6)); // 朝代色 60% 亮度
    const node = { ...n, _x: x, _y: y, _zB: zB, _zD: zD };
    threadNodes.push(node);
    threadIdxById.set(n.id, i);
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  return { threadMesh: mesh, threadNodes, threadIdxById };
}

/**
 * 雾环角度：既有 14 朝按稳定 id 扇区；暂无专属扇区的朝代与未知项按实体 id
 * 稳定散布到整圆。后者不固定冒充任一既有朝代扇区，也不会因 API 顺序变化漂移。
 */
export function fogAngleForNode(entityId, dynastyId) {
  const didx = dynastySectorIndexById(dynastyId);
  if (didx == null) return unit(`${entityId}:sec`) * Math.PI * 2;
  const sectorW = (Math.PI * 2) / DYNASTY_COLORS.length;
  return didx * sectorW + (unit(`${entityId}:a`) - 0.5) * sectorW * 0.8;
}

/** 雾环：无坐标实体按稳定朝代扇区/实体散列分布到半径 500–540 外壳，Points 1 draw call */
function buildFog(fogNodes) {
  const N = fogNodes.length;
  const pos = new Float32Array(Math.max(N, 1) * 3);
  const col = new Float32Array(Math.max(N, 1) * 3);
  fogNodes.forEach((n, i) => {
    const ang = fogAngleForNode(n.id, n.dynasty);
    const r = FOG_R_MIN + unit(n.id + ':r') * (FOG_R_MAX - FOG_R_MIN);
    pos[i * 3] = Math.cos(ang) * r;
    pos[i * 3 + 1] = Math.sin(ang) * r;
    const yr = n.born ?? n.died;
    pos[i * 3 + 2] = yr != null ? yearToZ(yr) : unit(n.id + ':z') * H;
    const c = new THREE.Color(dynastyHexById(n.dynasty));
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const m = new THREE.PointsMaterial({
    size: 3, sizeAttenuation: true, transparent: true, opacity: 0.3,
    vertexColors: true, depthWrite: false,
  });
  return new THREE.Points(g, m);
}

/** 事件环：InstancedMesh Torus（水平环），朝代色。1 draw call。返回 nodes 供 raycast 名牌 */
function buildEventRings(events) {
  const N = events.length;
  if (N === 0) return { mesh: new THREE.Group(), nodes: [] };
  const geo = new THREE.TorusGeometry(14, 2, 8, 28);
  const mat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.75, depthWrite: false });
  const mesh = new THREE.InstancedMesh(geo, mat, N);
  mesh.frustumCulled = false;
  const m = new THREE.Matrix4();
  const nodes = [];
  events.forEach((n, i) => {
    const [x, y] = lngLatToXY(n.x, n.y);
    m.makeTranslation(x, y, yearToZ(n.born));
    mesh.setMatrixAt(i, m);
    mesh.setColorAt(i, new THREE.Color(dynastyHexById(n.dynasty)));
    nodes.push({ id: n.id, name: n.name, born: n.born, type: 'Event' });
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  return { mesh, nodes };
}

/** 战役红球：InstancedMesh Sphere。1 draw call。返回 nodes 供 raycast 名牌 */
function buildBattleSpheres(battles) {
  const N = battles.length;
  if (N === 0) return { mesh: new THREE.Group(), nodes: [] };
  const geo = new THREE.SphereGeometry(6, 12, 8);
  const mat = new THREE.MeshBasicMaterial({ color: 0xcc3a3a, transparent: true, opacity: 0.9, depthWrite: false });
  const mesh = new THREE.InstancedMesh(geo, mat, N);
  mesh.frustumCulled = false;
  const m = new THREE.Matrix4();
  const nodes = [];
  battles.forEach((n, i) => {
    const [x, y] = lngLatToXY(n.x, n.y);
    m.makeTranslation(x, y, yearToZ(n.born));
    mesh.setMatrixAt(i, m);
    nodes.push({ id: n.id, name: n.name, born: n.born, type: 'Battle' });
  });
  mesh.instanceMatrix.needsUpdate = true;
  return { mesh, nodes };
}

// ---- 地理示意图构建（geoSketch 折线投影到 XY，z=0.6 底盘层）----
/** 海岸(墨)+双河(黛蓝)+太行(赭) 合并单批次：vertexColors 主题化原色,统一 opacity 0.4（45/33 折中,压 draw call）*/
function buildGeo(isDark) {
  const ink = isDark ? 0xdfe3ea : 0x2c2721;     // 海岸墨（夜=亮墨,纸=深墨）
  const river = isDark ? 0x7e93b8 : 0x3a4a6a;   // 黛蓝
  const taihang = isDark ? 0xb07a4a : 0x8a5a3a; // 赭
  const positions = [], colors = [];
  const pushPoly = (anchors, hex) => {
    const c = new THREE.Color(hex);
    const pts = smooth(anchors).map((p) => lngLatToXY(p[0], p[1]));
    for (let i = 0; i < pts.length - 1; i++) {
      positions.push(pts[i][0], pts[i][1], 0.6, pts[i + 1][0], pts[i + 1][1], 0.6);
      colors.push(c.r, c.g, c.b, c.r, c.g, c.b);
    }
  };
  pushPoly(COASTLINE, ink);
  pushPoly(YELLOW_RIVER, river);
  pushPoly(YANGTZE, river);
  pushPoly(TAIHANG, taihang);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  const m = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.4, depthWrite: false });
  return new THREE.LineSegments(g, m);
}
