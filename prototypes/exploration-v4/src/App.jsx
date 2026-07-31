import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  ArrowClockwise, ArrowLeft, ArrowRight, BookOpenText, Browser, CaretDown,
  CaretLeft, CaretRight, Check, CircleNotch, GearSix, Info, MagnifyingGlass,
  ClockCounterClockwise, Link, ListBullets, MapPin, Moon, NotePencil, Pause,
  Play, Plus, Quotes, SealCheck, Sun, TextAlignLeft, UsersThree, Warning, X,
} from "@phosphor-icons/react";

const makeNote = ({ title, solves, why, boundary, states, data, acceptance }) => ({
  title, solves, why, boundary, states, data, acceptance,
});

const productNotes = {
  G01: makeNote({
    title: "探索成为一级工作空间",
    solves: "把尚未结构化的历史问题，变成一份可保存、可复核、可继续的探索对象。",
    why: "它改变的是知识组织方式，而不是在旧工作台右侧追加一个聊天框，所以与时间柱、谱系星图、地图集并列。",
    boundary: "离开探索不删除草案；Explore 使用独立路由，不包裹或改写旧工作台。",
    states: [["默认", "探索高亮，当前草案自动保存。"], ["离开", "未保存变更先保护，已保存草案可恢复。"]],
    data: ["route", "explorationId", "draftStatus", "lastWorkspace"],
    acceptance: "返回旧模块再进入探索，研究对象与最后工作位置仍在。",
  }),
  G02: makeNote({
    title: "一本书，就是完整的探索工作空间",
    solves: "消除模式切换，让阅读、立题、编织和播放围绕同一段原文连续发生。",
    why: "书籍是稳定的上下文锚点；研究 Brief、论证链、地图播放和证据透镜都在页内就近出现，不再拆成三个入口。",
    boundary: "编织与播放是书内能力，不再拥有一级导航，也不保留不可达的隐藏页面。",
    states: [["阅读", "原文与段落锚点是起点。"], ["编织", "所选段落生成可检查链路。"], ["播放", "地图沿 Scene 推进并反向联动原文。"]],
    data: ["bookId", "sceneIndex", "thread", "paragraphIndex", "place", "evidenceSelection"],
    acceptance: "不离开书籍页即可完成选段、编织、播放、核证的完整闭环。",
  }),
  G03: makeNote({
    title: "产品旁注只服务评审",
    solves: "让产品判断随原型交付，同时保持默认体验完全没有 PM 占位。",
    why: "默认关闭；开启后只在标题旁出现安静锚点。先读三句产品判断，需要时再进入完整依据。",
    boundary: "旁注不进入生产构建，不使用编号药丸、常驻侧栏、聚光暗幕或页面重排。",
    states: [["关闭", "原型保持真实产品密度。"], ["短注", "轻量浮层解释价值。"], ["完整依据", "临时 notebook 展示合同。"]],
    data: ["noteId", "anchorRect", "activeLayer"],
    acceptance: "关闭旁注后，界面尺寸和功能与开启前一致。",
  }),
  G04: makeNote({
    title: "探索身份与时间语境",
    solves: "始终说明正在研究什么、当前 Scene 位于何时，以及草案是否安全保存。",
    why: "书籍是当前工作空间身份，探索时间跟随当前 Scene；不再让无关的全局纪年与研究对象争夺解释权。",
    boundary: "标题区不堆模型、Token 或内部任务状态；不把模糊时间伪装成精确日期。",
    states: [["正常", "显示探索名、范围、当前 Scene 日期。"], ["保存中", "只改变保存状态，不阻断浏览。"]],
    data: ["title", "timeRange", "activeScene.date", "saveStatus", "visibility"],
    acceptance: "顶部时间、当前 Scene 和底部时间带语义一致。",
  }),
  W01: makeNote({
    title: "研究约定，不是聊天记录",
    solves: "在模型生成前，让用户确认时间、空间、对象和真正想解释的问题。",
    why: "把自然语言收敛成书籍页顶部的紧凑 Brief，让立题留在原文、论证链与地图共同视野中。",
    boundary: "只追问一轮高价值问题；范围过宽或冲突时先修约定，不直接生成结论。",
    states: [["待确认", "范围仍可逐项编辑。"], ["已确认", "允许渐进编织。"], ["冲突", "指出具体冲突项。"]],
    data: ["query", "timeRange", "geoScope", "actors", "researchQuestion"],
    acceptance: "地图播放与论证链都复用同一份已确认 Brief。",
  }),
  W02: makeNote({
    title: "叙事主线是阅读路径",
    solves: "让同一批材料从组织变化、思想讨论或个体处境等不同问题进入，而不是生成唯一长答案。",
    why: "时间骨架先给共同 Scene，主线按钮只改变解释重心；事实节点本身不会被暗中改写。",
    boundary: "切主线只局部重编织；证据不足时明确标记，不凑满节点。",
    states: [["推荐", "展示默认解释路径。"], ["已选择", "地图和详情同步。"], ["待核", "关系尚未进入事实态。"]],
    data: ["threadId", "sceneIds", "rationale", "provenance"],
    acceptance: "切换主线不改变 Scene 日期、地点来源和原始证据。",
  }),
  W03: makeNote({
    title: "地图是当前 Scene 的空间证据",
    solves: "把抽象叙述落到有依据的地点、范围和材料关联上。",
    why: "地图占中央主画布；先让用户看到“发生在哪里”，再在下方解释“为何重要”。",
    boundary: "无可靠地点不猜点；材料关联线不冒充人物移动。原型 raster 只定义视觉目标，生产使用 MapLibre 与核验 GeoJSON。",
    states: [["ready", "当前地点与研究范围可见。"], ["partial", "只展示已定位部分。"], ["no_location", "保留上一范围，不落假点。"], ["tile_error", "底图失败但地点层和研究上下文保留。"]],
    data: ["scene.place", "lastPlace", "geometry", "geometrySource", "mapState"],
    acceptance: "四种状态只改变地图区域，不清空 Brief、Scene 或证据。",
  }),
  W04: makeNote({
    title: "事件详情是一幕，不是一篇文章",
    solves: "用最小叙事单元回答这一刻发生了什么、前因是什么、接下来通向哪里。",
    why: "详情作为地图内浮窗跟随当前 Scene，空间定位与叙事解释在同一视线内完成。",
    boundary: "解释框架、作者判断、待核材料不能显示成已核验史实。",
    states: [["史实条目", "必须可回出处。"], ["解释框架", "明确主体和层级。"], ["待核", "允许继续探索但不能晋升。"]],
    data: ["sceneId", "summary", "role", "previousSceneId", "nextSceneId", "status"],
    acceptance: "每条事实陈述都有出处入口，状态标签与数据层级一致。",
  }),
  W05: makeNote({
    title: "证据透镜描述关系，不制造对立",
    solves: "把史实、作者判断和研究差异放回具体 Claim，解释材料怎样互相作用。",
    why: "右栏只展开最相关材料；关系词比笼统的正方、反方更接近真实研究。",
    boundary: "只有同一命题不可同时为真才叫直接冲突；没有复核选择时不显示“无实质冲突”。",
    states: [["互证", "独立材料支持同一命题。"], ["补充", "补足另一层面。"], ["关注层级不同", "回答不同问题。"], ["直接冲突", "同一 Claim 不可同时成立。"], ["证据缺口", "材料不足。"]],
    data: ["claimId", "evidenceId", "relationType", "reviewed", "citations"],
    acceptance: "结论只在用户选中已复核关系时出现。",
  }),
  P01: makeNote({
    title: "场景轨是可读剪辑",
    solves: "把复杂进程拆成可以跳转、回看和分支的 Scene 顺序。",
    why: "横向 Scene 轨贴在地图下方，与步进和变速控制组成同一播放 dock；已读、当前、未读一眼可辨。",
    boundary: "它不是完整事件目录；没有可靠地点的 Scene 仍可存在。",
    states: [["已读", "保留完成标记。"], ["当前", "同帧驱动所有区域。"], ["未读", "可直接跳转。"]],
    data: ["sceneId", "date", "label", "status", "focusPlace"],
    acceptance: "跳转后场景轨、地图浮窗和时间带同帧更新。",
  }),
  P02: makeNote({
    title: "书内播放让地图成为动态舞台",
    solves: "直观看见研究对象如何随 Scene 在空间和时间中展开。",
    why: "地图占主体，浮窗只保留当前一幕；前序范围仍可辨认，帮助理解变化而非瞬移。",
    boundary: "无地点时保留上一范围并解释原因；用户点选或漫游会暂停自动推进。",
    states: [["聚焦", "当前地点突出。"], ["过渡", "相机与数据同帧。"], ["无地点", "不猜坐标。"], ["地图失败", "保留覆盖层。"]],
    data: ["activeScene", "camera", "lastPlace", "visibleLayers", "geometrySource"],
    acceptance: "任何一帧的日期、地点、浮窗和当前 Scene 都一致。",
  }),
  P03: makeNote({
    title: "解释透镜跟随当前命题",
    solves: "播放过程中随时回答：这是事实、作者判断，还是一种解释路径。",
    why: "复用书籍页右侧证据透镜，以命题为中心比较材料关系，不让证据抢走地图主舞台。",
    boundary: "制度解释与个体经验可以同时成立；不得默认红蓝对打。",
    states: [["已复核", "可显示关系结论。"], ["待核", "只展示建议关系。"], ["缺口", "明确尚无材料。"]],
    data: ["activeClaim", "relationType", "evidenceRefs", "reviewStatus"],
    acceptance: "切 Scene 后透镜更新，旧命题不残留。",
  }),
  P04: makeNote({
    title: "书内播放永远不夺走控制权",
    solves: "让用户按自己的阅读节奏播放、暂停、步进、变速和重播。",
    why: "地图内只保留安静的次级入口，按需展开紧凑控制；动作与结果同处一张地图。",
    boundary: "缓冲时不推进；结束态主动作变为重播；手动跳转立即暂停。",
    states: [["paused", "可逐步查看。"], ["playing", "按 rate 自动推进。"], ["buffering", "保留当前 Scene。"], ["ended", "停在最后一幕，可重播。"]],
    data: ["sceneIndex", "playbackStatus", "rate", "timer", "autoFollow"],
    acceptance: "0.5×/1×/1.5×真实改变 timer，结束与重播完整闭环。",
  }),
  P05: makeNote({
    title: "时间带是唯一时间真相",
    solves: "同时说明当前 Scene 在 1941—1945 全范围中的位置。",
    why: "左栏时间 · 事件柱承载完整 Scene 顺序；地图播放只显示当前进度，不再常驻第二条时间轨。",
    boundary: "模糊日期保持模糊；播放速度不改变标注日期。",
    states: [["当前", "当前点突出。"], ["跨期", "范围保持完整。"], ["越界", "不允许推进到范围之外。"]],
    data: ["timeDomain", "sceneTicks", "activeScene.date", "precision"],
    acceptance: "时间带与顶部纪年、场景轨完全一致。",
  }),
  B01: makeNote({
    title: "内置阅读器是核心，来源与时间是并列入口",
    solves: "既保证稳定的段落锚点，也允许回到网页来源或沿共享 Scene 浏览时间事件。",
    why: "默认内置阅读器；网页来源是增强，时间 · 事件柱复用共享 Scene。只有内置文本能可靠驱动段落回跳。",
    boundary: "不声称可读取跨域 iframe 正文或选区；受限时始终提供原站打开和复制粘贴回流。",
    states: [["reader_ready", "本地文本可联动。"], ["web_limited", "可预览但选区不回流。"], ["login_required", "不伪造登录态。"], ["timeline", "事件选择同步地图与逻辑。"]],
    data: ["bookSource", "sourceUrl", "sourceState", "importedText", "syncCapability"],
    acceptance: "三种状态只影响来源区域，中央结构与已选段落仍保留。",
  }),
  B02: makeNote({
    title: "连续阅读仍然是第一动作",
    solves: "不把一本书拆成碎片卡片；用户阅读时可随时选择段落进入探索。",
    why: "书籍身份、章节、进度、正文和页脚保持阅读器语法；点击段落才联动其他区域。",
    boundary: "原文与用户导入文本不被模型改写；本原型摘要明确标为待版本复核。",
    states: [["解析中", "保留书籍身份。"], ["可读", "段落可选。"], ["缺页", "暴露页码缺口。"], ["无文本层", "引导更换格式。"]],
    data: ["bookId", "chapterId", "paragraphId", "selection", "progress", "pageAnchor"],
    acceptance: "选择段落后仍可一键回到原文位置。",
  }),
  B03: makeNote({
    title: "把段落翻译成可检查的论证链",
    solves: "连接原文要点、作者观察、相关 Scene、人物与地点，又不抹去表达主体。",
    why: "采用从左到右的一跳链路，顺着阅读方向展示“原文如何成为结构”。",
    boundary: "作者观察不能升格为事实；模型推断必须允许接受、驳回或改写。",
    states: [["原文摘要", "绑定版本与页码。"], ["作者观察", "显示作者主体。"], ["模型提议", "尚未采纳。"], ["证据缺口", "不补写。"]],
    data: ["passageId", "claimId", "provenance", "entityRefs", "edgeType"],
    acceptance: "每个结构节点可回到段落或具体来源。",
  }),
  B04: makeNote({
    title: "书籍也有可核验的空间",
    solves: "让段落中的地点、相关材料地点和影响范围参与同一时空探索。",
    why: "地图占中央约三分之一，位于论证链之后；先理解作者说什么，再看它落在哪里。",
    boundary: "当前段落地点与补充材料地点必须区分；关联线不等于人物移动。",
    states: [["单地点", "聚焦当前段落。"], ["多地点", "保留层级。"], ["歧义", "展示候选。"], ["无地点", "保留范围不猜点。"]],
    data: ["passagePlaces", "chapterExtent", "placeRole", "geometry", "source"],
    acceptance: "点地点能反向联动段落和证据，且来源可追溯。",
  }),
  B05: makeNote({
    title: "区分书中的几种时间",
    solves: "避免把叙述时间、史料写成时间和作者回忆时间混成一条精确时间线。",
    why: "时间 · 事件柱作为左栏一级入口，与正文共享 Scene；当前段落和地图只读取同一时间状态。",
    boundary: "模糊年份、回忆与跨期背景保留各自精度。",
    states: [["精确", "按来源精度显示。"], ["约", "明确模糊。"], ["回忆", "与事件时间分开。"], ["跨期", "显示范围。"]],
    data: ["narrativeTime", "sourceTime", "precision", "range"],
    acceptance: "时间精度在正文、结构和时间带中一致。",
  }),
  B06: makeNote({
    title: "关系化证据忠实保留作者",
    solves: "在忠实呈现作者论证的同时，按需加入互证、补充、不同层级、冲突或缺口。",
    why: "右栏以当前段落 Claim 为中心；关系切换比固定正反栏更准确，也允许没有冲突。",
    boundary: "当前示例不自动判定冲突；只有选中已复核材料，才显示关系结论。",
    states: [["互证", "独立材料支持。"], ["补充", "补足层面。"], ["关注层级不同", "不自动冲突。"], ["直接冲突", "命题不可同时为真。"], ["证据缺口", "尚待补证。"]],
    data: ["claimId", "relationType", "evidenceRefs", "reviewed", "rationale"],
    acceptance: "作者判断、外部材料和模型建议在视觉与数据上分层。",
  }),
  B07: makeNote({
    title: "私人书籍默认不离开个人空间",
    solves: "让用户清楚知道原文是否发送、保存或进入导出成果。",
    why: "私密状态紧邻书籍身份，先建立信任，再允许结构化处理。",
    boundary: "导出探索不自动携带长篇原文；发送模型前明确本次使用片段。",
    states: [["本地", "全文留在浏览器。"], ["本次发送", "只发送明确片段。"], ["已清除", "移除会话文本。"]],
    data: ["visibility", "copyrightStatus", "sentRanges", "allowedExports"],
    acceptance: "用户能检查、清除本次发送片段，并在导出前再次确认。",
  }),
};

const scenes = [
  {
    date: "1941", label: "前史与问题形成", place: null,
    detail: "本场景是解释框架：整理整风进入集中阶段前的组织与思想背景，并不把复杂前史压成一个地点或单一事件。",
    status: "解释框架 · 待逐条引证", relation: "证据缺口",
  },
  {
    date: "1942.02", label: "整风进入集中阶段", place: "延安",
    detail: "原型以延安为研究中心，呈现学习、组织与思想整顿如何进入同一观察范围；具体表述须回到版本与史料逐条复核。",
    status: "书中叙述 · 待版本复核", relation: "互证",
  },
  {
    date: "1942.05", label: "文艺与思想讨论", place: "延安",
    detail: "这一幕用于展示文艺讨论与整风语境的关联；它是待核验的结构提议，不自动等同于单一因果关系。",
    status: "结构提议 · 尚未采纳", relation: "关注层级不同",
  },
  {
    date: "1943", label: "审干与抢救运动", place: "延安",
    detail: "原型把作者对组织审查与干部处境的讨论标成作者解释层，避免把论证直接升格为无主体史实。",
    status: "作者解释 · 已标主体", relation: "补充",
  },
  {
    date: "1944", label: "材料核对与经验总结", place: null,
    detail: "本场景代表跨来源核对阶段，没有单一可靠地点；地图保留上一研究范围，不为完整动画猜测落点。",
    status: "研究过程 · 无单一地点", relation: "证据缺口",
  },
  {
    date: "1945.04", label: "七大与阶段性总结", place: "延安",
    detail: "这一幕把阶段性组织总结放回 1945 年的研究范围；原型不替代正式史实条目的来源审定。",
    status: "史实骨架 · 待正式库核验", relation: "互证",
  },
];

const paragraphs = [
  {
    id: "sample-1", time: "1941—1942", place: "延安", sceneIndex: 1,
    claim: "组织整顿与思想学习被作者放在同一解释框架中",
    text: "【作者论证摘要 · 待按所选版本逐页复核】本章把组织整顿、思想学习及权力关系的变化连接为一个持续过程。",
  },
  {
    id: "sample-2", time: "1942—1943", place: "延安", sceneIndex: 3,
    claim: "作者关注制度过程如何作用于干部与知识分子",
    text: "【作者论证摘要 · 待按所选版本逐页复核】作者通过组织生活、审查与个体处境等材料，讨论制度过程如何进入日常经验。",
  },
  {
    id: "sample-3", time: "1943—1945", place: "延安", sceneIndex: 5,
    claim: "阶段性总结与组织叙事仍需区分事实和解释",
    text: "【研究摘记 · 尚未采纳为事实】当前结构把阶段性总结与组织叙事相连；关系仍需回到原文和独立材料核对。",
  },
];

const relationTypes = ["互证", "补充", "关注层级不同", "直接冲突", "证据缺口"];

const initialExploration = {
  id: "explore-yanan-1941-1945",
  title: "延安整风",
  range: "1941—1945",
  entrySource: "question",
  sceneIndex: 1,
  lastPlace: "延安",
  place: "延安",
  thread: "组织与思想",
  paragraphIndex: 0,
  bookSource: "reader",
  lens: "作者视角",
  rate: 1,
  playbackStatus: "paused",
  mapState: "ready",
  sourceState: "reader_ready",
  evidenceSelection: null,
};

function NoteAnchor({ id, enabled, onOpen }) {
  if (!enabled) return null;
  return (
    <button
      className="note-anchor"
      type="button"
      aria-label={`查看${productNotes[id].title}的产品旁注`}
      onClick={(event) => onOpen(id, event)}
    >
      <Info size={11} weight="fill" />
    </button>
  );
}

function QuickNote({ noteState, onClose, onOpenNotebook }) {
  if (!noteState) return null;
  const note = productNotes[noteState.id];
  return (
    <>
      <button className="popover-dismiss" aria-label="关闭产品旁注" onClick={onClose} />
      <section
        className="product-popover"
        role="dialog"
        aria-modal="false"
        aria-label={`${note.title}产品旁注`}
        style={{ left: noteState.x, top: noteState.y }}
      >
        <header>
          <div><small>产品旁注</small><h2>{note.title}</h2></div>
          <button className="icon-btn" aria-label="关闭产品旁注" onClick={onClose}><X size={15} /></button>
        </header>
        <div className="quick-note-row"><span>解决什么</span><p>{note.solves}</p></div>
        <div className="quick-note-row"><span>为什么这样排</span><p>{note.why}</p></div>
        <div className="quick-note-row"><span>边界</span><p>{note.boundary}</p></div>
        <button className="full-rationale" onClick={() => onOpenNotebook(noteState.id)}>
          查看完整依据 <ArrowRight size={13} />
        </button>
      </section>
    </>
  );
}

function ScenarioControls({ id, exploration, updateExploration }) {
  const definitions = {
    W03: {
      label: "地图状态",
      key: "mapState",
      options: [["ready", "Ready"], ["partial", "Partial"], ["no_location", "No location"], ["tile_error", "Tile error"]],
    },
    P04: {
      label: "播放状态",
      key: "playbackStatus",
      options: [["paused", "Paused"], ["playing", "Playing"], ["buffering", "Buffering"], ["ended", "Ended"]],
    },
    B01: {
      label: "来源状态",
      key: "sourceState",
      options: [["reader_ready", "Reader ready"], ["web_limited", "Web limited"], ["login_required", "Login required"]],
    },
  };
  const definition = definitions[id];
  if (!definition) return null;
  const apply = (value) => {
    if (id === "B01") {
      updateExploration({
        sourceState: value,
        bookSource: value === "reader_ready" ? "reader" : "web",
      });
      return;
    }
    if (id === "P04") {
      updateExploration({
        playbackStatus: value,
        sceneIndex: value === "ended" ? scenes.length - 1 : exploration.sceneIndex,
      });
      return;
    }
    updateExploration({ [definition.key]: value });
  };
  return (
    <section className="scenario-controls">
      <div><small>真实局部场景</small><strong>{definition.label}</strong></div>
      <div role="group" aria-label={definition.label}>
        {definition.options.map(([value, label]) => (
          <button
            key={value}
            className={exploration[definition.key] === value ? "active" : ""}
            onClick={() => apply(value)}
          >
            {label}
          </button>
        ))}
      </div>
      <p>状态只作用于对应区域；阅读位置、研究约定和已完成结构保持不变。</p>
    </section>
  );
}

function Notebook({ id, noteOrder, exploration, updateExploration, onNavigate, onClose }) {
  if (!id) return null;
  const note = productNotes[id];
  const index = noteOrder.indexOf(id);
  return (
    <div className="notebook-overlay" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="notebook-sheet" role="dialog" aria-modal="true" aria-labelledby="notebook-title">
        <header>
          <div><small>PRODUCT RATIONALE · {id}</small><h2 id="notebook-title">{note.title}</h2></div>
          <button className="icon-btn" aria-label="关闭完整产品依据" onClick={onClose}><X size={18} /></button>
        </header>
        <div className="notebook-scroll">
          <div className="notebook-thesis">
            <section><span>解决什么</span><p>{note.solves}</p></section>
            <section><span>为什么这样排</span><p>{note.why}</p></section>
            <section><span>边界</span><p>{note.boundary}</p></section>
          </div>
          <details open>
            <summary>状态定义 <CaretDown /></summary>
            <div className="state-contract">
              {note.states.map(([label, copy]) => <div key={label}><strong>{label}</strong><p>{copy}</p></div>)}
            </div>
          </details>
          <details open>
            <summary>数据合同 <CaretDown /></summary>
            <div className="data-contract">{note.data.map((item) => <code key={item}>{item}</code>)}</div>
          </details>
          <details open>
            <summary>开发验收 <CaretDown /></summary>
            <p className="acceptance-copy"><SealCheck />{note.acceptance}</p>
          </details>
          <ScenarioControls id={id} exploration={exploration} updateExploration={updateExploration} />
        </div>
        <footer>
          <button disabled={index <= 0} onClick={() => onNavigate(noteOrder[index - 1])}><CaretLeft />上一处</button>
          <span>{index + 1} / {noteOrder.length}</span>
          <button disabled={index >= noteOrder.length - 1} onClick={() => onNavigate(noteOrder[index + 1])}>下一处<CaretRight /></button>
        </footer>
      </section>
    </div>
  );
}

function MapPoint({ label, x, y, active, onClick, brown = false }) {
  return (
    <button className={`map-point ${active ? "active" : ""} ${brown ? "brown" : ""}`} style={{ left: `${x}%`, top: `${y}%` }} onClick={onClick}>
      <MapPin size={active ? 24 : 19} weight="fill" /><span>{label}</span>
    </button>
  );
}

function RelationKey() {
  return <div className="relation-key" aria-label="五类证据关系">{relationTypes.map((item) => <span key={item}>{item}</span>)}</div>;
}

function Evidence({ id, relation, title, children, reviewed = false, selectedId, onSelect }) {
  return (
    <article className={`evidence-card ${selectedId === id ? "selected" : ""}`}>
      <button className="evidence-select" onClick={() => onSelect(id)} aria-pressed={selectedId === id}>
        <div className="evidence-meta"><span>{relation}</span></div>
        <h3>{title}</h3><p>{children}</p>
        <small>{reviewed ? <><SealCheck /> 已复核关系</> : <><CircleNotch /> 待核关系</>}</small>
      </button>
      <button className="source-link">查看出处 <CaretRight size={12} /></button>
    </article>
  );
}

function RelationConclusion({ selectedId, reviewedIds, copy = "所选材料已复核，当前 Claim 尚无实质冲突" }) {
  if (!selectedId || !reviewedIds.includes(selectedId)) return null;
  return <div className="no-conflict"><Check />{copy}</div>;
}

const mapPoints = {
  延安: { x: 63, y: 36 },
  西安: { x: 55, y: 58 },
  重庆: { x: 43, y: 78 },
};

const associationCurves = [
  {
    start: [0.39, 0.40],
    control1: [0.45, 0.33],
    control2: [0.54, 0.29],
    end: [0.63, 0.36],
  },
  {
    start: [0.39, 0.40],
    control1: [0.44, 0.45],
    control2: [0.49, 0.50],
    end: [0.55, 0.58],
  },
  {
    start: [0.39, 0.40],
    control1: [0.36, 0.51],
    control2: [0.36, 0.68],
    end: [0.43, 0.78],
  },
];

function cubicPoint(curve, t, width, height) {
  const inverse = 1 - t;
  const weights = [
    inverse ** 3,
    3 * inverse ** 2 * t,
    3 * inverse * t ** 2,
    t ** 3,
  ];
  const points = [curve.start, curve.control1, curve.control2, curve.end];
  return points.reduce((result, point, index) => ({
    x: result.x + point[0] * width * weights[index],
    y: result.y + point[1] * height * weights[index],
  }), { x: 0, y: 0 });
}

function AssociationCanvas({ variant = "flow" }) {
  const canvasRef = useRef(null);
  const [size, setSize] = useState({ width: 0, height: 0, dpr: 1 });

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const mapStage = canvas.closest(".book-map");
    if (!mapStage) return undefined;
    const updateSize = (width, height) => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      const next = {
        width: Math.max(0, Math.round(width * 10) / 10),
        height: Math.max(0, Math.round(height * 10) / 10),
        dpr: ratio,
      };
      setSize((current) => (
        current.width === next.width && current.height === next.height && current.dpr === next.dpr
          ? current
          : next
      ));
    };
    const observer = new ResizeObserver(([entry]) => {
      updateSize(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(mapStage);
    updateSize(mapStage.clientWidth, mapStage.clientHeight);
    return () => observer.disconnect();
  }, []);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || size.width <= 0 || size.height <= 0) return;
    const context = canvas.getContext("2d");
    context.setTransform(size.dpr, 0, 0, size.dpr, 0, 0);
    context.clearRect(0, 0, size.width, size.height);
    context.globalCompositeOperation = "source-over";
    context.globalAlpha = 1;
    context.lineCap = "round";
    context.lineJoin = "round";

    associationCurves.forEach((curve, curveIndex) => {
      if (variant === "beads") {
        const beadPositions = curveIndex === 0
          ? [0.08, 0.17, 0.29, 0.38, 0.52, 0.64, 0.79, 0.91]
          : [0.10, 0.23, 0.39, 0.55, 0.72, 0.90];
        beadPositions.forEach((t) => {
          const point = cubicPoint(curve, t, size.width, size.height);
          context.beginPath();
          context.arc(point.x, point.y, curveIndex === 0 ? 5.6 : 4.8, 0, Math.PI * 2);
          context.fillStyle = curveIndex === 0 ? "rgba(250,246,235,.58)" : "rgba(250,246,235,.46)";
          context.fill();
          context.beginPath();
          context.arc(point.x, point.y, curveIndex === 0 ? 2.9 : 2.5, 0, Math.PI * 2);
          context.fillStyle = curveIndex === 0 ? "rgba(112,78,48,.82)" : "rgba(112,78,48,.62)";
          context.fill();
        });
        return;
      }

      const drawCurve = (strokeStyle, lineWidth) => {
        context.beginPath();
        context.moveTo(curve.start[0] * size.width, curve.start[1] * size.height);
        context.bezierCurveTo(
          curve.control1[0] * size.width,
          curve.control1[1] * size.height,
          curve.control2[0] * size.width,
          curve.control2[1] * size.height,
          curve.end[0] * size.width,
          curve.end[1] * size.height,
        );
        context.strokeStyle = strokeStyle;
        context.lineWidth = lineWidth;
        context.stroke();
      };
      drawCurve(
        curveIndex === 0 ? "rgba(250,246,235,.72)" : "rgba(250,246,235,.64)",
        curveIndex === 0 ? 8 : 6,
      );
      drawCurve(
        curveIndex === 0 ? "rgba(112,78,48,.80)" : "rgba(112,78,48,.62)",
        curveIndex === 0 ? 3 : 2.2,
      );
    });
    const sourceHub = {
      x: associationCurves[0].start[0] * size.width,
      y: associationCurves[0].start[1] * size.height,
    };
    context.beginPath();
    context.arc(sourceHub.x, sourceHub.y, 7, 0, Math.PI * 2);
    context.fillStyle = "rgba(250,246,235,.78)";
    context.fill();
    context.beginPath();
    context.arc(sourceHub.x, sourceHub.y, 3.6, 0, Math.PI * 2);
    context.fillStyle = "rgba(112,78,48,.88)";
    context.fill();
    canvas.dataset.rendered = variant;
    canvas.dataset.size = `${size.width}x${size.height}@${size.dpr}`;
  }, [variant, size.width, size.height, size.dpr]);

  const backingWidth = Math.max(1, Math.round(size.width * size.dpr));
  const backingHeight = Math.max(1, Math.round(size.height * size.dpr));
  return (
    <canvas
      className="association-canvas"
      ref={canvasRef}
      width={backingWidth}
      height={backingHeight}
      data-rendered="pending"
      data-size={`${size.width}x${size.height}@${size.dpr}`}
      aria-hidden="true"
    />
  );
}

function MapStatus({ state }) {
  if (state === "ready") return null;
  const copy = {
    partial: ["部分定位", "只显示有明确出处的地点；未定位材料仍保留在证据层。"],
    no_location: ["无可靠地点", "保留上一研究范围，本 Scene 不猜测落点。"],
    tile_error: ["底图暂不可用", "地点与研究范围覆盖层仍保留，可稍后重试底图。"],
  };
  return <div className={`local-state map-local-state ${state}`}><Info /><div><strong>{copy[state][0]}</strong><span>{copy[state][1]}</span></div></div>;
}

function WebSource({ sourceState }) {
  if (sourceState === "login_required") {
    return (
      <div className="web-preview">
        <div className="browser-bar"><span><Browser />微信读书网页来源</span><a href="https://weread.qq.com/" target="_blank" rel="noreferrer">在原站登录<ArrowRight /></a></div>
        <div className="source-local-state"><Warning size={28} /><h3>原站需要登录</h3><p>当前探索和已导入摘要仍然可用；登录不会被伪装为已完成。</p></div>
        <div className="web-capability"><Info />登录状态只影响网页来源</div>
      </div>
    );
  }
  return (
    <div className="web-preview">
      <div className="browser-bar"><span><Browser />微信读书网页来源</span><a href="https://weread.qq.com/" target="_blank" rel="noreferrer">在原站打开<ArrowRight /></a></div>
      <div className="web-book"><div className="web-tools"><NotePencil /><GearSix /><BookOpenText /></div><div className="web-columns"><section><h3>延安整风 · 网页阅读入口</h3><p>网页来源用于连续阅读与回到原站。原型不读取跨域正文，也不假装能同步网页选区。</p></section><section><p>需要进入探索的段落，可复制到内置阅读器，再由页码或段落锚点连接结构、地图与证据。</p></section></div></div>
      <div className="web-capability"><Info />Web limited · 正文选区不自动回流</div>
    </div>
  );
}

function ColumnResizer({ label, keyboardDirection, onDelta, onReset }) {
  const lastX = useRef(null);
  return (
    <button
      className="column-resizer"
      type="button"
      role="separator"
      aria-label={label}
      aria-orientation="vertical"
      title={`${label}；双击复位`}
      onDoubleClick={onReset}
      onPointerDown={(event) => {
        lastX.current = event.clientX;
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        if (lastX.current === null) return;
        const delta = event.clientX - lastX.current;
        lastX.current = event.clientX;
        onDelta(delta);
      }}
      onPointerUp={(event) => {
        if (lastX.current !== null) {
          const finalDelta = event.clientX - lastX.current;
          if (finalDelta) onDelta(finalDelta);
        }
        lastX.current = null;
        event.currentTarget.releasePointerCapture(event.pointerId);
      }}
      onPointerCancel={() => {
        lastX.current = null;
      }}
      onKeyDown={(event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const direction = event.key === "ArrowRight" ? 1 : -1;
        onDelta(direction * keyboardDirection * 12);
      }}
    >
      <i />
    </button>
  );
}

function BookMode({ notesEnabled, onOpenNote, exploration, updateExploration, selectScene, togglePlayback, routeVariant }) {
  const selected = paragraphs[exploration.paragraphIndex];
  const scene = scenes[exploration.sceneIndex];
  const gridRef = useRef(null);
  const readerParagraphRefs = useRef([]);
  const composerRef = useRef(null);
  const [columns, setColumns] = useState({ left: 280, right: 300 });
  const [readerView, setReaderView] = useState("text");
  const [logicDetail, setLogicDetail] = useState(null);
  const [playControlsOpen, setPlayControlsOpen] = useState(false);
  const [composerMenuOpen, setComposerMenuOpen] = useState(false);
  const [composerValue, setComposerValue] = useState("");
  const [composerSent, setComposerSent] = useState(false);
  const selectedEvidence = exploration.evidenceSelection?.scope === "book" ? exploration.evidenceSelection.id : null;
  const selectEvidence = (id) => updateExploration({ evidenceSelection: { scope: "book", id } });
  const isPlaying = exploration.playbackStatus === "playing";
  const isBuffering = exploration.playbackStatus === "buffering";
  const isEnded = exploration.playbackStatus === "ended";
  const visiblePlaces = exploration.mapState === "partial" ? ["延安"] : Object.keys(mapPoints);
  const resizeColumn = (column, delta) => {
    setColumns((current) => {
      const total = Math.max(980, (gridRef.current?.clientWidth || 1117) - 10);
      if (column === "left") {
        const maxLeft = Math.max(260, total - current.right - 430);
        return { ...current, left: Math.min(maxLeft, Math.max(230, current.left + delta)) };
      }
      const maxRight = Math.max(280, total - current.left - 430);
      return { ...current, right: Math.min(maxRight, Math.max(250, current.right + delta)) };
    });
  };
  const selectParagraph = (index) => {
    const paragraph = paragraphs[index];
    updateExploration({
      paragraphIndex: index,
      sceneIndex: paragraph.sceneIndex,
      place: paragraph.place,
      lastPlace: paragraph.place,
      playbackStatus: "paused",
    });
  };
  const returnToParagraph = (index = exploration.paragraphIndex) => {
    updateExploration({ bookSource: "reader", sourceState: "reader_ready" });
    setReaderView("text");
    selectParagraph(index);
    setLogicDetail(null);
    window.requestAnimationFrame(() => {
      const target = readerParagraphRefs.current[index];
      target?.scrollIntoView({ block: "center", behavior: "smooth" });
      target?.focus({ preventScroll: true });
    });
  };
  const openLogicDetail = (detail) => {
    if (Number.isInteger(detail.sceneIndex)) selectScene(detail.sceneIndex);
    if (detail.place) updateExploration({ place: detail.place, lastPlace: detail.place, playbackStatus: "paused" });
    setLogicDetail(detail);
  };
  const addToComposer = (type) => {
    const copy = {
      quote: `摘录：${selected.claim}\n`,
      source: "外部材料：",
      entity: `关联人物 / 事件：${scene.label}\n`,
    };
    setComposerValue((current) => `${current}${copy[type]}`);
    setComposerMenuOpen(false);
    if (type === "quote") {
      updateExploration({ bookSource: "reader", sourceState: "reader_ready" });
      setReaderView("text");
    }
    window.requestAnimationFrame(() => composerRef.current?.focus());
  };
  const submitComposer = () => {
    if (!composerValue.trim()) {
      composerRef.current?.focus();
      return;
    }
    setComposerSent(true);
    setComposerValue("");
    window.setTimeout(() => setComposerSent(false), 1400);
  };
  return (
    <section className="book-view">
      <div className="book-bar">
        <button className="soft-btn"><ArrowLeft />返回书库</button>
        <div className="book-title">
          <strong>高华《红太阳是怎样升起的》 <NoteAnchor id="G02" enabled={notesEnabled} onOpen={onOpenNote} /></strong>
          <span>{exploration.title} · {exploration.range} · 作者论证摘要 / 版本待绑定</span>
        </div>
        <span className="privacy compact" title="私人会话；原文默认留在本地"><SealCheck />本地 <NoteAnchor id="B07" enabled={notesEnabled} onOpen={onOpenNote} /></span>
        <span className="save-state"><Check />已保存</span>
        <button className="primary-btn">保存探索 <CaretDown /></button>
      </div>
      <div
        className="book-grid"
        ref={gridRef}
        style={{ gridTemplateColumns: `${columns.left}px 6px minmax(0,1fr) 6px ${columns.right}px` }}
      >
        <aside className="reader-panel">
          <div className="reader-source">
            <button className={exploration.bookSource === "reader" ? "active" : ""} onClick={() => updateExploration({ bookSource: "reader", sourceState: "reader_ready" })}><BookOpenText />内置阅读器</button>
            <button className={exploration.bookSource === "web" ? "active" : ""} onClick={() => updateExploration({ bookSource: "web", sourceState: "web_limited" })}><Browser />网页来源</button>
            <button className={exploration.bookSource === "timeline" ? "active" : ""} onClick={() => updateExploration({ bookSource: "timeline" })}><ClockCounterClockwise />时间 · 事件柱</button>
            <NoteAnchor id="B01" enabled={notesEnabled} onOpen={onOpenNote} />
          </div>
          {exploration.bookSource === "reader" && <div className="reader-content">
            <div className="reader-book-card">
              <img src="/assets/red-sun-cover.png" alt="《红太阳是怎样升起的》书封" />
              <div><strong>红太阳是怎样升起的</strong><span>延安整风运动的来龙去脉</span><small>高华 · 版本信息待用户确认</small></div>
              <i><SealCheck /> 私人导入</i>
            </div>
            <div className="reader-meta">
              <span>作者论证摘要 · 版本待绑定 <NoteAnchor id="B02" enabled={notesEnabled} onOpen={onOpenNote} /></span>
              <div className="reader-view-toggle" role="group" aria-label="阅读器视图">
                <button className={readerView === "text" ? "active" : ""} onClick={() => setReaderView("text")}><TextAlignLeft />正文</button>
                <button className={readerView === "anchors" ? "active" : ""} onClick={() => setReaderView("anchors")}><ListBullets />锚点</button>
              </div>
            </div>
            <div className="reader-progress"><i /></div>
            {readerView === "text" ? <div className="reader-page">
              <h2>红太阳是怎样升起的</h2><h3>延安整风 · 研究样本</h3>
              {paragraphs.map((item, index) => (
                <button
                  ref={(node) => { readerParagraphRefs.current[index] = node; }}
                  className={index === exploration.paragraphIndex ? "active" : ""}
                  onClick={() => selectParagraph(index)}
                  key={item.id}
                >
                  {item.text}
                  <span>{item.time} · 锚点 {index + 1}</span>
                </button>
              ))}
            </div> : <div className="reader-anchor-list">
              {paragraphs.map((item, index) => (
                <button className={index === exploration.paragraphIndex ? "active" : ""} onClick={() => returnToParagraph(index)} key={item.id}>
                  <span>{String(index + 1).padStart(2, "0")} · {item.time}</span><strong>{item.claim}</strong><small>作者论证摘要</small>
                </button>
              ))}
            </div>}
            <div className="reader-footer"><button disabled={exploration.paragraphIndex === 0} onClick={() => returnToParagraph(exploration.paragraphIndex - 1)}><ArrowLeft />上一处</button><span>{exploration.paragraphIndex + 1} / {paragraphs.length}</span><button disabled={exploration.paragraphIndex === paragraphs.length - 1} onClick={() => returnToParagraph(exploration.paragraphIndex + 1)}>下一处<ArrowRight /></button></div>
          </div>}
          {exploration.bookSource === "web" && <WebSource sourceState={exploration.sourceState} />}
          {exploration.bookSource === "timeline" && <div className="reader-timeline">
            <header><small>共享 Scene</small><strong>{exploration.range}</strong></header>
            {scenes.map((item, index) => (
              <button className={index === exploration.sceneIndex ? "active" : index < exploration.sceneIndex ? "visited" : ""} onClick={() => selectScene(index)} key={`${item.date}-${item.label}`}>
                <i>{index < exploration.sceneIndex ? <Check /> : index + 1}</i>
                <span><strong>{item.label}</strong><small>{item.date} · {item.place || "无单一可靠地点"}</small></span>
              </button>
            ))}
          </div>}
        </aside>
        <ColumnResizer label="调整阅读栏宽度" keyboardDirection={1} onDelta={(delta) => resizeColumn("left", delta)} onReset={() => setColumns((current) => ({ ...current, left: 280 }))} />
        <main className="book-center">
          <section className="book-brief">
            <div className="brief-title">
              <span>研究 Brief · 已确认 <NoteAnchor id="W01" enabled={notesEnabled} onOpen={onOpenNote} /></span>
              <strong>作者如何连接组织整顿、思想学习与个体处境？</strong>
            </div>
            <div className="brief-facts" aria-label="研究范围">
              <span><small>时间</small>1941—1945</span>
              <span><small>空间</small>延安为中心</span>
              <span><small>对象</small>组织 · 思想 · 个体</span>
            </div>
            <div className="brief-threads" aria-label="叙事主线">
              <span>叙事主线 <NoteAnchor id="W02" enabled={notesEnabled} onOpen={onOpenNote} /></span>
              {["组织与思想", "材料关系", "个体处境"].map((item) => (
                <button className={exploration.thread === item ? "active" : ""} onClick={() => updateExploration({ thread: item })} key={item}>{item}</button>
              ))}
            </div>
          </section>
          <section className="book-graph">
            <div className="book-section-head"><div><small>论证链路</small><h2>{selected.time} · {selected.claim} <NoteAnchor id="B03" enabled={notesEnabled} onOpen={onOpenNote} /></h2></div></div>
            <div className="logic-flow">
              <button className="logic-node source" onClick={() => openLogicDetail({ id: "source", kind: "作者论证摘要", title: selected.claim, summary: selected.text, paragraphIndex: exploration.paragraphIndex })}><span>段落摘要</span>{selected.claim}</button><CaretRight />
              <button className="logic-node observation" onClick={() => {
                updateExploration({ lens: "作者视角" });
                openLogicDetail({ id: "observation", kind: "作者观察", title: "组织、思想与个体处境", summary: "当前结构忠实保留作者把组织整顿、思想学习与个体处境放入同一解释过程的观察；它不是无主体史实。", paragraphIndex: exploration.paragraphIndex });
              }}><span>作者观察</span>组织、思想与个体处境被放入同一解释过程</button><CaretRight />
              <div className="logic-stack">
                <button className="logic-node" onClick={() => openLogicDetail({ id: "scene-1", kind: "相关 Scene · 待版本复核", title: "学习与整顿部署", summary: scenes[1].detail, sceneIndex: 1, paragraphIndex: 0 })}>学习与整顿部署</button>
                <button className="logic-node" onClick={() => openLogicDetail({ id: "scene-3", kind: "作者解释 · 已标主体", title: "审干与组织审查", summary: scenes[3].detail, sceneIndex: 3, paragraphIndex: 1 })}>审干与组织审查</button>
                <button className="logic-node" onClick={() => openLogicDetail({ id: "scene-5", kind: "研究摘记 · 尚未采纳", title: "阶段性总结", summary: scenes[5].detail, sceneIndex: 5, paragraphIndex: 2 })}>阶段性总结</button>
              </div><CaretRight />
              <div className="logic-stack">
                <button className="logic-node person" onClick={() => openLogicDetail({ id: "leaders", kind: "实体集合 · 待逐项绑定", title: "领导者与组织", summary: "这里只表示作者论证涉及的实体层级；人物、组织关系仍需回到所选版本与独立材料逐项绑定。", paragraphIndex: exploration.paragraphIndex })}>领导者与组织</button>
                <button className="logic-node person" onClick={() => openLogicDetail({ id: "cadres", kind: "观察对象 · 非单一群体结论", title: "干部与知识分子", summary: "当前节点保留作者关注的观察对象，不把样本经验扩写为全体结论。", paragraphIndex: exploration.paragraphIndex })}>干部与知识分子</button>
                <button className="logic-node place" onClick={() => openLogicDetail({ id: "place", kind: "段落关联地点", title: selected.place, summary: "地点来自当前结构化摘要；正式几何与出处仍需绑定核验数据。", paragraphIndex: exploration.paragraphIndex, place: selected.place })}>{selected.place}</button>
              </div>
            </div>
            {logicDetail && <article className="logic-popover" role="dialog" aria-label={`${logicDetail.title}节点详情`}>
              <header><div><small>{logicDetail.kind}</small><strong>{logicDetail.title}</strong></div><button className="icon-btn" aria-label="关闭节点详情" onClick={() => setLogicDetail(null)}><X /></button></header>
              <p>{logicDetail.summary}</p>
              <button className="return-source" onClick={() => returnToParagraph(logicDetail.paragraphIndex)}><BookOpenText />回到原文</button>
            </article>}
          </section>
          <section className="book-map-section">
            <div className="book-section-head compact"><div><small>时空脉络</small><h2>{scene.date} · {scene.label} <NoteAnchor id="B04" enabled={notesEnabled} onOpen={onOpenNote} /></h2></div></div>
            <div className={`map-stage book-map ${exploration.mapState === "tile_error" ? "tile-error" : ""}`}>
              <AssociationCanvas variant={routeVariant} />
              <span className="route-label" title="从当前材料映射到相关地点，不表示人物、事件或物资的移动路线" aria-label="材料关联；不代表移动">材料关联</span>
              {visiblePlaces.map((place) => <MapPoint key={place} label={place} {...mapPoints[place]} active={Boolean(scene.place) && scene.place === place} onClick={() => updateExploration({ place, lastPlace: place, playbackStatus: "paused" })} brown={place !== "延安"} />)}
              <article className="map-popup book-map-popup">
                <div><span>{scene.place || exploration.lastPlace}</span><small>{scene.place ? "当前 Scene 聚焦" : "保留上一可靠范围"}</small></div>
                <h2>{scene.label} · {scene.date}</h2>
                <p>{scene.detail}</p>
                {!scene.place && <aside><Info />本 Scene 没有单一可靠地点，地图没有猜测落点。</aside>}
              </article>
              <div className="map-selection"><MapPin weight="fill" /><div><strong>{scene.place || exploration.place}</strong><span>{scene.place ? "当前 Scene 地点" : "补充材料地点 · 非当前事件"}</span></div></div>
              <div className={`map-player ${playControlsOpen ? "open" : ""}`}>
                {!playControlsOpen ? <button className="map-play-entry" onClick={() => setPlayControlsOpen(true)} aria-expanded="false"><Play weight="fill" />播放脉络</button> : <div className="map-play-controls">
                  <button className="icon-btn" aria-label="收起播放控制" onClick={() => setPlayControlsOpen(false)}><X /></button>
                  <button className="icon-btn" aria-label="上一个 Scene" disabled={exploration.sceneIndex === 0 || isBuffering} onClick={() => selectScene(exploration.sceneIndex - 1)}><ArrowLeft /></button>
                  <button className="play-btn compact" aria-label={isEnded ? "重新播放" : isPlaying ? "暂停播放" : "开始播放"} onClick={togglePlayback} disabled={isBuffering}>
                    {isEnded ? <ArrowClockwise weight="bold" /> : isPlaying ? <Pause weight="fill" /> : <Play weight="fill" />}
                  </button>
                  <button className="icon-btn" aria-label="下一个 Scene" disabled={exploration.sceneIndex === scenes.length - 1 || isBuffering} onClick={() => selectScene(exploration.sceneIndex + 1)}><ArrowRight /></button>
                  <select aria-label="播放速度" value={exploration.rate} onChange={(event) => updateExploration({ rate: Number(event.target.value) })}>
                    <option value=".5">0.5×</option><option value="1">1×</option><option value="1.5">1.5×</option>
                  </select>
                  <span>{exploration.sceneIndex + 1} / {scenes.length}</span>
                  <NoteAnchor id="P04" enabled={notesEnabled} onOpen={onOpenNote} />
                </div>}
              </div>
              <MapStatus state={exploration.mapState} />
            </div>
          </section>
        </main>
        <ColumnResizer label="调整证据栏宽度" keyboardDirection={1} onDelta={(delta) => resizeColumn("right", -delta)} onReset={() => setColumns((current) => ({ ...current, right: 300 }))} />
        <aside className="book-lens">
          <div className="panel-title"><span>关系化证据</span><NoteAnchor id="B06" enabled={notesEnabled} onOpen={onOpenNote} /></div>
          <div className="lens-scroll">
            <div className="lens-tabs">{["作者视角", "材料互证", "不同解释"].map((item) => <button className={exploration.lens === item ? "active" : ""} onClick={() => updateExploration({ lens: item })} key={item}>{item}</button>)}</div>
            <RelationKey />
            {exploration.lens === "作者视角" && <><Evidence id="b-author-reviewed" relation="补充" title="作者的解释框架" reviewed selectedId={selectedEvidence} onSelect={selectEvidence}>作者把组织整顿、思想学习和个体处境连接起来；这是作者论证摘要，不是无主体史实。</Evidence><Evidence id="b-author-gap" relation="证据缺口" title="版本与页码仍待绑定" selectedId={selectedEvidence} onSelect={selectEvidence}>原型不为缺失页码生成伪出处。</Evidence></>}
            {exploration.lens === "材料互证" && <><Evidence id="b-source-reviewed" relation="互证" title="可核对的组织过程材料" reviewed selectedId={selectedEvidence} onSelect={selectEvidence}>独立材料可支持部分组织过程的事实层描述；仍需逐条定位。</Evidence><Evidence id="b-source-gap" relation="证据缺口" title="个体经验的代表性" selectedId={selectedEvidence} onSelect={selectEvidence}>不同群体经验仍需更多日记、回忆和地方材料。</Evidence></>}
            {exploration.lens === "不同解释" && <><Evidence id="b-level-reviewed" relation="关注层级不同" title="组织史、思想史与社会史" reviewed selectedId={selectedEvidence} onSelect={selectEvidence}>不同研究路径回答的问题不同，当前没有理由把它们判为直接冲突。</Evidence><Evidence id="b-conflict-gap" relation="直接冲突" title="尚未获得同命题冲突材料" selectedId={selectedEvidence} onSelect={selectEvidence}>关系仍为空，不为填满面板制造对立。</Evidence></>}
            <RelationConclusion selectedId={selectedEvidence} reviewedIds={["b-author-reviewed", "b-source-reviewed", "b-level-reviewed"]} copy="所选关系已复核；当前材料尚无实质冲突" />
          </div>
          <div className="composer">
            {composerMenuOpen && <div className="composer-menu" role="menu">
              <button role="menuitem" onClick={() => addToComposer("quote")}><Quotes />添加摘录</button>
              <button role="menuitem" onClick={() => addToComposer("source")}><Link />添加外部材料</button>
              <button role="menuitem" onClick={() => addToComposer("entity")}><UsersThree />关联人物事件</button>
            </div>}
            <button className="composer-add" aria-label="添加材料或关联" aria-expanded={composerMenuOpen} onClick={() => setComposerMenuOpen((value) => !value)}><Plus /></button>
            <textarea
              ref={composerRef}
              value={composerValue}
              onChange={(event) => {
                setComposerValue(event.target.value);
                setComposerSent(false);
              }}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") submitComposer();
              }}
              placeholder="向书籍与材料提问…"
              aria-label="向书籍与材料提问"
            />
            <button className="composer-send" aria-label="发送" onClick={submitComposer}>{composerSent ? <Check /> : <ArrowRight />}</button>
            <span className="composer-live" aria-live="polite">{composerSent ? "已加入探索" : ""}</span>
          </div>
        </aside>
      </div>
    </section>
  );
}

export function App() {
  const [exploration, setExploration] = useState(initialExploration);
  const [theme, setTheme] = useState("clear");
  const [notesEnabled, setNotesEnabled] = useState(false);
  const [quickNote, setQuickNote] = useState(null);
  const [notebookId, setNotebookId] = useState(null);

  const updateExploration = (patch) => setExploration((current) => ({ ...current, ...patch }));
  const activeScene = scenes[exploration.sceneIndex];
  const noteOrder = useMemo(() => Object.keys(productNotes), []);
  const routeVariant = useMemo(() => {
    if (typeof window === "undefined") return "flow";
    return new URLSearchParams(window.location.search).get("route") === "beads" ? "beads" : "flow";
  }, []);

  useEffect(() => {
    if (exploration.playbackStatus !== "playing") return undefined;
    const timer = window.setInterval(() => {
      setExploration((current) => {
        if (current.playbackStatus !== "playing") return current;
        const nextIndex = current.sceneIndex + 1;
        if (nextIndex >= scenes.length) return { ...current, playbackStatus: "ended" };
        const next = scenes[nextIndex];
        return {
          ...current,
          sceneIndex: nextIndex,
          paragraphIndex: paragraphs.reduce((result, paragraph, index) => paragraph.sceneIndex <= nextIndex ? index : result, 0),
          place: next.place || current.place,
          lastPlace: next.place || current.lastPlace,
          playbackStatus: nextIndex === scenes.length - 1 ? "ended" : "playing",
        };
      });
    }, 1800 / exploration.rate);
    return () => window.clearInterval(timer);
  }, [exploration.playbackStatus, exploration.rate]);

  useEffect(() => {
    const handleEscape = (event) => {
      if (event.key !== "Escape") return;
      if (notebookId) setNotebookId(null);
      else if (quickNote) setQuickNote(null);
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [notebookId, quickNote]);

  const selectScene = (index) => {
    const boundedIndex = Math.max(0, Math.min(index, scenes.length - 1));
    const next = scenes[boundedIndex];
    updateExploration({
      sceneIndex: boundedIndex,
      paragraphIndex: paragraphs.reduce((result, paragraph, paragraphIndex) => paragraph.sceneIndex <= boundedIndex ? paragraphIndex : result, 0),
      place: next.place || exploration.place,
      lastPlace: next.place || exploration.lastPlace,
      playbackStatus: "paused",
    });
  };

  const togglePlayback = () => {
    if (exploration.playbackStatus === "buffering") return;
    if (exploration.playbackStatus === "playing") {
      updateExploration({ playbackStatus: "paused" });
      return;
    }
    if (exploration.playbackStatus === "ended" || exploration.sceneIndex === scenes.length - 1) {
      const first = scenes[0];
      updateExploration({
        sceneIndex: 0,
        paragraphIndex: 0,
        place: first.place || exploration.place,
        lastPlace: first.place || exploration.lastPlace,
        playbackStatus: "playing",
      });
      return;
    }
    updateExploration({ playbackStatus: "playing" });
  };

  const openQuickNote = (id, event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const width = 330;
    const height = 300;
    const x = Math.max(12, Math.min(rect.left - 12, window.innerWidth - width - 12));
    const y = rect.bottom + height > window.innerHeight ? Math.max(12, rect.top - height + 4) : rect.bottom + 8;
    setQuickNote({ id, x, y });
  };

  return (
    <div className={`app-shell theme-${theme}`}>
      <header className="app-header">
        <div className="brand"><b>纪</b><div><strong>纪年图谱 · 时间柱</strong><small>以时为纲　以事见因</small></div></div>
        <nav className="primary-nav" aria-label="一级导航">
          <button>时间柱</button><button>谱系星图</button><button>地图集</button>
          <button className="active">探索</button><NoteAnchor id="G01" enabled={notesEnabled} onOpen={openQuickNote} />
        </nav>
        <label className="global-search"><MagnifyingGlass /><input placeholder="搜索人物 / 政权 / 派系 / 事件 / 书籍 / 地点" /></label>
        <div className="header-actions">
          <button className={`annotation-toggle ${notesEnabled ? "active" : ""}`} aria-pressed={notesEnabled} onClick={() => {
            setNotesEnabled((value) => !value);
            setQuickNote(null);
            setNotebookId(null);
          }}><NotePencil />产品旁注<i>{notesEnabled ? "开" : "关"}</i></button>
          <NoteAnchor id="G03" enabled={notesEnabled} onOpen={openQuickNote} />
          <button className="theme-toggle" aria-label={`切换到${theme === "clear" ? "夜" : "澄"}主题`} onClick={() => setTheme((value) => value === "clear" ? "night" : "clear")}>{theme === "clear" ? <Sun /> : <Moon />}{theme === "clear" ? "澄" : "夜"}</button>
          <div className="era"><span>{activeScene.date}</span><small>{exploration.range} · 当前 Scene</small><NoteAnchor id="G04" enabled={notesEnabled} onOpen={openQuickNote} /></div>
        </div>
      </header>
      <div className="workspace">
        <BookMode notesEnabled={notesEnabled} onOpenNote={openQuickNote} exploration={exploration} updateExploration={updateExploration} selectScene={selectScene} togglePlayback={togglePlayback} routeVariant={routeVariant} />
      </div>
      <QuickNote noteState={quickNote} onClose={() => setQuickNote(null)} onOpenNotebook={(id) => {
        setQuickNote(null);
        setNotebookId(id);
      }} />
      <Notebook id={notebookId} noteOrder={noteOrder} exploration={exploration} updateExploration={updateExploration} onNavigate={setNotebookId} onClose={() => setNotebookId(null)} />
    </div>
  );
}
