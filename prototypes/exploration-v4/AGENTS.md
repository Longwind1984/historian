# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Exploration v4 durable product decisions

- This is an isolated desktop prototype. Do not modify production `frontend/`.
- 书籍探索 is the only workspace. 阅读 is the stable shell; 研究 Brief、编织论证链、地图 Scene 播放 and evidence review are inline capabilities. Do not restore 编织态 / 播放态 as top-level entrances or hidden mode pages.
- Do not restore a mode bar below the app header. The single book toolbar owns book identity, research/range, save status, privacy status, and save action.
- The three book columns are user-resizable with accessible separators; default widths are about 280 / fluid / 300, and the workspace must remain horizontally usable at 1117px.
- Book mode's core contract is the built-in reader. WeRead web view is progressive enhancement only: cross-origin body/selection access and reliable third-party login cookies are not assumed. First-version excerpt return uses copy/paste; a browser-extension bridge is a future option.
- The reader has source-level tabs for built-in reader, web source, and shared timeline/event column. The built-in reader separately offers continuous text and anchor-list views; every structural node can return to a highlighted author-summary paragraph.
- Book mode keeps the accepted lightweight relationship-flow component and a marked historical map occupying roughly one third of the center workspace. Paragraph, claim, place, and evidence selections stay linked.
- Evidence relationships are 互证, 补充, 关注层级不同, 直接冲突, or 证据缺口. Do not manufacture pro/con opposition; current examples have no substantive conflict.
- Prototype map backgrounds are supplied raster visuals. Production intent is MapLibre with verified raster tiles and GeoJSON overlays. When a scene has no reliable place, keep the previous extent and show that no point was guessed.
- Annotation IDs follow G01–G04, W01–W05, P01–P05, and B01–B07. W/P IDs now annotate the inline weave/play capabilities inside the single book workspace; every annotation explains positioning, default, interaction, states, data, and acceptance.
- Product rationale is invisible by default. The prototype exposes only a quiet `产品旁注` toggle; enabled notes use tiny title-adjacent blue-gray anchors, a three-part anchored popover (`解决什么 / 为什么这样排 / 边界`), and an optional temporary notebook for states, data, and acceptance. Do not reintroduce numbered pills, a chapter rail, persistent presenter UI, spotlight masks, or a permanent PM side panel.
- The one book workspace preserves scene, place, thread, paragraph, source, evidence, lens, and playback context. Scene playback must update the map popup, timeline, and reader paragraph in the same state transition.
- Playback is map-local and collapsed by default; never restore a persistent bottom playback dock. The evidence-column input is one composer with an add menu, input, and send action.
- Map material associations are native Canvas cubic Bézier overlays with DPR-aware resize redraws. `?route=flow` is the default layered soft curve; `?route=beads` is the review alternative using sparse points along the same curve. Topology must fan out from the current-material hub to independent places, never connect cities into a route. Neither uses straight dashes, arrows, or person/event movement semantics; both avoid place labels and use a neutral legend.
- Prototype state scenarios belong inside the full product-note notebook and affect only their target region. The required local scenarios are `W03 ready / partial / no_location / tile_error`, `P04 paused / playing / buffering / ended`, and `B01 reader_ready / web_limited / login_required`; never restore a global demo-state selector or full-workspace state mask.
- Historical examples must advertise their actual evidence level. Book content is an author-argument summary or prototype placeholder unless a verified edition and page anchor are available; do not present reconstructed prose, page numbers, publishers, map routes, or status labels as verified facts. Material-association lines must not look like person/event movement.
