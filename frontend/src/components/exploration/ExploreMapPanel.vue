<template>
  <section
    class="explore-map-panel"
    data-testid="explore-map-panel"
    :data-map-state="mapState"
    :data-view-mode="viewMode"
    :data-location-id="activeLocation?.id || ''"
    :data-camera-duration="lastCameraDuration"
    aria-label="书籍叙事地图"
  >
    <div
      ref="mapRef"
      class="explore-map-canvas"
      data-testid="explore-map-canvas"
      role="region"
      aria-label="可缩放的书籍叙事地图"
    ></div>

    <nav
      v-if="isSampleWorkspace"
      class="explore-map-mode"
      role="group"
      aria-label="地图镜头"
    >
      <button
        type="button"
        :class="{ active: viewMode === 'overview' }"
        :aria-pressed="viewMode === 'overview'"
        @click="setViewMode('overview')"
      >
        全览
      </button>
      <button
        type="button"
        :class="{ active: viewMode === 'focus' }"
        :aria-pressed="viewMode === 'focus'"
        @click="setViewMode('focus')"
      >
        聚焦
      </button>
    </nav>

    <article
      v-if="scene"
      class="explore-scene-card"
      data-testid="explore-scene-card"
    >
      <div class="explore-scene-kicker">
        <span>{{ activeLocation?.name || '无可靠地点' }}</span>
        <small>{{ sceneDate }}</small>
      </div>
      <h3>{{ scene.title || scene.label || '当前 Scene' }}</h3>
      <p v-if="scene.summary || scene.detail">{{ scene.summary || scene.detail }}</p>
      <div v-if="viewMode === 'focus' && !activeLocation" class="explore-map-notice" role="status">
        本幕没有可核验坐标；已清除地点与连线，不猜测落点。
      </div>
    </article>

    <ol
      v-if="isSampleWorkspace && viewMode === 'overview'"
      class="explore-map-sequence"
      aria-label="九幕叙事顺序"
    >
      <li
        v-for="item in sceneSequence"
        :key="item.scene.id"
        :class="{ missing: !item.location, active: item.scene.id === activeSceneId }"
      >
        <button
          type="button"
          :aria-current="item.scene.id === activeSceneId ? 'step' : undefined"
          :aria-label="sequenceAriaLabel(item)"
          @click="focusScene(item.index)"
        >
          <b>{{ item.index + 1 }}</b>
          <span>{{ item.scene.title || item.scene.label }}</span>
          <small>{{ item.location ? item.location.name : '未定位' }}</small>
        </button>
      </li>
    </ol>

    <span
      v-if="isSampleWorkspace && viewMode === 'overview' && overviewLineCount"
      class="explore-sequence-caption"
    >
      叙事顺序 · 非行军路线
    </span>
    <span v-if="restrictedMapsEnabled" class="explore-reference-caption">
      历史地理参考 · 1908 · 非当前疆界
    </span>
    <span v-if="viewMode === 'focus' && relatedLocations.length" class="explore-relation-caption">
      材料关联 · 非人物移动
    </span>

    <div
      v-if="playerOpen"
      class="explore-map-player"
      data-testid="explore-map-player"
    >
      <slot name="player" />
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { RESTRICTED_MAPS_ENABLED } from '../../config/distribution'
import { ANSHI_PUBLIC_SCENES } from '../../data/anshiPublicDemo'
import { useExplorationStore } from '../../stores/useExplorationStore'
import { useUIStore } from '../../stores/useUIStore'

const props = defineProps({
  scene: { type: Object, default: null },
  playerOpen: { type: Boolean, default: false },
})

const emit = defineEmits(['manual-interaction'])
const store = useExplorationStore()
const ui = useUIStore()
const restrictedMapsEnabled = RESTRICTED_MAPS_ENABLED

const mapRef = ref(null)
const mapState = ref('initializing')
const viewMode = ref('overview')
const lastCameraDuration = ref(0)
let map = null
let resizeObserver = null
let resizeFrame = 0
let programmaticCamera = false
let cameraSequence = 0
let cameraReleaseTimer = 0

const EMPTY_COLLECTION = Object.freeze({
  type: 'FeatureCollection',
  features: [],
})

function buildGraticule() {
  const features = []
  for (let longitude = 70; longitude <= 140; longitude += 10) {
    features.push({
      type: 'Feature',
      properties: {},
      geometry: { type: 'LineString', coordinates: [[longitude, 10], [longitude, 60]] },
    })
  }
  for (let latitude = 10; latitude <= 60; latitude += 10) {
    features.push({
      type: 'Feature',
      properties: {},
      geometry: { type: 'LineString', coordinates: [[70, latitude], [140, latitude]] },
    })
  }
  return { type: 'FeatureCollection', features }
}

function readToken(name, fallback) {
  if (typeof document === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

function buildStyle() {
  const referenceSources = restrictedMapsEnabled
    ? {
      'explore-reference-basemap': {
        type: 'raster',
        tiles: ['/tiles/atlas/mp05d1/{z}/{x}/{y}.png'],
        tileSize: 256,
        minzoom: 2,
        maxzoom: 6,
      },
    }
    : {}
  return {
    version: 8,
    // CJK 地名由 localIdeographFontFamily 在本机绘制，不依赖远端字形响应。
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      ...referenceSources,
      graticule: { type: 'geojson', data: buildGraticule() },
      'explore-scene-relations': { type: 'geojson', data: EMPTY_COLLECTION },
      'explore-related-places': { type: 'geojson', data: EMPTY_COLLECTION },
      'explore-scene-place': { type: 'geojson', data: EMPTY_COLLECTION },
    },
    layers: [
      {
        id: 'explore-paper',
        type: 'background',
        paint: { 'background-color': readToken('--map-paper', '#eee6d5') },
      },
      ...(restrictedMapsEnabled ? [{
        id: 'explore-reference-basemap',
        type: 'raster',
        source: 'explore-reference-basemap',
        paint: {
          'raster-opacity': ui.palette === '夜' ? 0.28 : 0.52,
          'raster-saturation': -0.45,
          'raster-contrast': -0.08,
          'raster-brightness-min': ui.palette === '夜' ? 0.06 : 0,
          'raster-brightness-max': ui.palette === '夜' ? 0.52 : 1,
          'raster-fade-duration': 0,
        },
      }] : []),
      {
        id: 'explore-graticule',
        type: 'line',
        source: 'graticule',
        paint: {
          'line-color': readToken('--map-grid', '#d8cdb9'),
          'line-width': 1,
          'line-opacity': 0.55,
        },
      },
      {
        id: 'explore-scene-relations-corridor',
        type: 'line',
        source: 'explore-scene-relations',
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
        paint: {
          'line-color': readToken('--paper-el', '#faf6eb'),
          'line-width': 5,
          'line-opacity': 0.58,
          'line-blur': 0.25,
        },
      },
      {
        id: 'explore-scene-relations',
        type: 'line',
        source: 'explore-scene-relations',
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
        paint: {
          'line-color': readToken('--ink-mid', '#4a4539'),
          'line-width': 1.65,
          'line-opacity': 0.62,
        },
      },
      {
        id: 'explore-related-places',
        type: 'circle',
        source: 'explore-related-places',
        paint: {
          'circle-radius': 4.5,
          'circle-color': readToken('--ink-soft', '#756b5e'),
          'circle-stroke-color': readToken('--paper-el', '#faf6eb'),
          'circle-stroke-width': 1.5,
        },
      },
      {
        id: 'explore-related-places-label',
        type: 'symbol',
        source: 'explore-related-places',
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Noto Serif SC'],
          'text-size': 11,
          'text-offset': [0, 1.25],
          'text-anchor': 'top',
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': readToken('--ink-soft', '#756b5e'),
          'text-halo-color': readToken('--paper-el', '#faf6eb'),
          'text-halo-width': 1.3,
        },
      },
      {
        id: 'explore-scene-place-halo',
        type: 'circle',
        source: 'explore-scene-place',
        paint: {
          'circle-radius': [
            'case',
            ['boolean', ['get', 'active'], false],
            14,
            9,
          ],
          'circle-color': readToken('--accent', '#b44b38'),
          'circle-opacity': [
            'case',
            ['boolean', ['get', 'active'], false],
            0.18,
            0.07,
          ],
        },
      },
      {
        id: 'explore-scene-place',
        type: 'circle',
        source: 'explore-scene-place',
        paint: {
          'circle-radius': [
            'case',
            ['boolean', ['get', 'active'], false],
            8,
            6.5,
          ],
          'circle-color': [
            'case',
            ['boolean', ['get', 'active'], false],
            readToken('--accent', '#b44b38'),
            readToken('--ink-mid', '#4a4539'),
          ],
          'circle-stroke-color': readToken('--paper-el', '#faf6eb'),
          'circle-stroke-width': 2,
        },
      },
      {
        id: 'explore-scene-place-order',
        type: 'symbol',
        source: 'explore-scene-place',
        layout: {
          'text-field': ['get', 'orderLabel'],
          'text-font': ['Noto Serif SC'],
          'text-size': 10,
          'text-allow-overlap': true,
          'text-ignore-placement': true,
        },
        paint: {
          'text-color': readToken('--paper-el', '#faf6eb'),
        },
      },
      {
        id: 'explore-scene-place-label',
        type: 'symbol',
        source: 'explore-scene-place',
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Noto Serif SC'],
          'text-size': 11,
          'text-offset': [0, 1.5],
          'text-anchor': 'top',
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': readToken('--ink', '#302b25'),
          'text-halo-color': readToken('--paper-el', '#faf6eb'),
          'text-halo-width': 1.4,
        },
      },
    ],
  }
}

function finiteCoordinate(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function normalizeCjkLabel(value) {
  const label = typeof value === 'string' ? value.trim() : ''
  return label && /^[\p{Script=Han}\s（）()·—-]+$/u.test(label)
    ? label
    : '已核验地点'
}

function normalizeCandidate(candidate) {
  if (!candidate) return null
  const coordinates = Array.isArray(candidate.coordinates) ? candidate.coordinates : null
  const longitude = finiteCoordinate(
    candidate.longitude ?? candidate.lng ?? coordinates?.[0],
  )
  const latitude = finiteCoordinate(
    candidate.latitude ?? candidate.lat ?? coordinates?.[1],
  )
  if (longitude == null || latitude == null) return null
  if (longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) return null
  return {
    id: candidate.id || candidate.place_id || '',
    name: normalizeCjkLabel(candidate.name || candidate.label),
    longitude,
    latitude,
    sourceRef: candidate.source_ref || candidate.sourceRef || null,
    relationLabel: candidate.relation_label || candidate.relationLabel || null,
  }
}

function normalizeLocation(scene) {
  if (!scene) return null
  const candidates = [
    scene.location,
    ...(Array.isArray(scene.locations) ? scene.locations : []),
  ].filter(Boolean)
  for (const candidate of candidates) {
    const location = normalizeCandidate(candidate)
    if (location) return location
  }
  return null
}

const isSampleWorkspace = computed(() => store.isSampleWorkspace)
const activeSceneId = computed(() => props.scene?.id || props.scene?.scene_id || null)
const activeLocation = computed(() => normalizeLocation(props.scene))
const relatedLocations = computed(() => (Array.isArray(props.scene?.relatedLocations)
  ? props.scene.relatedLocations
  : []).map(normalizeCandidate).filter(Boolean))
const sceneSequence = computed(() => ANSHI_PUBLIC_SCENES.map((scene, index) => ({
  scene,
  index,
  location: normalizeLocation(scene),
})))
const locatedSceneSequence = computed(() => sceneSequence.value.filter((item) => item.location))
const overviewLineCount = computed(() => Math.max(0, locatedSceneSequence.value.length - 1))

const sceneDate = computed(() => {
  const scene = props.scene
  if (!scene) return ''
  if (typeof scene.date === 'string') return scene.date
  if (scene.time?.label) return scene.time.label
  const year = scene.time?.year ?? scene.year
  if (!Number.isFinite(Number(year))) return ''
  const month = scene.time?.month ?? scene.month
  const day = scene.time?.day ?? scene.day
  return [year, month, day].filter((value) => value != null).join('.')
})

function sequenceAriaLabel(item) {
  return item.location
    ? `第 ${item.index + 1} 幕地图节点，${item.location.name}，进入聚焦`
    : `第 ${item.index + 1} 幕地图节点，无可靠坐标，进入详情`
}

function prefersReducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

function scenePointFeature(scene, index, location, active) {
  return {
    type: 'Feature',
    id: scene.id,
    properties: {
      id: location.id,
      sceneId: scene.id,
      name: location.name,
      order: index + 1,
      orderLabel: String(index + 1),
      active,
      source_ref: location.sourceRef,
      semantic: 'scene_location',
    },
    geometry: {
      type: 'Point',
      coordinates: [location.longitude, location.latitude],
    },
  }
}

function overviewPointCollection() {
  return {
    type: 'FeatureCollection',
    features: locatedSceneSequence.value.map((item) => scenePointFeature(
      item.scene,
      item.index,
      item.location,
      item.scene.id === activeSceneId.value,
    )),
  }
}

function focusedPointCollection() {
  const location = activeLocation.value
  if (!location || !props.scene) return EMPTY_COLLECTION
  const index = Math.max(
    0,
    ANSHI_PUBLIC_SCENES.findIndex((scene) => scene.id === activeSceneId.value),
  )
  return {
    type: 'FeatureCollection',
    features: [scenePointFeature(props.scene, index, location, true)],
  }
}

function relatedPointCollection(locations) {
  return {
    type: 'FeatureCollection',
    features: locations.map((location) => ({
      type: 'Feature',
      id: location.id,
      properties: {
        id: location.id,
        name: location.name,
        source_ref: location.sourceRef,
        relation_label: location.relationLabel,
        semantic: 'related_material_location',
      },
      geometry: {
        type: 'Point',
        coordinates: [location.longitude, location.latitude],
      },
    })),
  }
}

function curvedCoordinates(origin, destination, index) {
  const start = [origin.longitude, origin.latitude]
  const end = [destination.longitude, destination.latitude]
  const dx = end[0] - start[0]
  const dy = end[1] - start[1]
  const length = Math.hypot(dx, dy)
  if (length < 0.000001) return [start, end]
  const bend = Math.min(length * 0.18, 1.15) * (index % 2 ? -1 : 1)
  const perpendicular = [-dy / length * bend, dx / length * bend]
  const control = [
    start[0] + dx * 0.5 + perpendicular[0],
    start[1] + dy * 0.5 + perpendicular[1],
  ]
  return Array.from({ length: 29 }, (_, step) => {
    const t = step / 28
    const inverse = 1 - t
    return [
      inverse ** 2 * start[0] + 2 * inverse * t * control[0] + t ** 2 * end[0],
      inverse ** 2 * start[1] + 2 * inverse * t * control[1] + t ** 2 * end[1],
    ]
  })
}

function narrativeSequenceCollection() {
  const items = locatedSceneSequence.value
  if (items.length < 2) return EMPTY_COLLECTION
  return {
    type: 'FeatureCollection',
    features: items.slice(0, -1).map((item, index) => {
      const next = items[index + 1]
      return {
        type: 'Feature',
        properties: {
          semantic: 'narrative_sequence',
          claim: 'sequence_not_route',
          fromSceneId: item.scene.id,
          toSceneId: next.scene.id,
          fromOrder: item.index + 1,
          toOrder: next.index + 1,
          skipsUnlocatedScene: next.index - item.index > 1,
        },
        geometry: {
          type: 'LineString',
          coordinates: curvedCoordinates(item.location, next.location, index),
        },
      }
    }),
  }
}

function setSourceData(sourceId, data) {
  // 不复用 style 初始化时的空对象引用，确保连续 overview → empty → overview
  // 都触发 GeoJSONSource 的 worker 更新。
  const nextData = data === EMPTY_COLLECTION
    ? { type: 'FeatureCollection', features: [] }
    : data
  map?.getSource(sourceId)?.setData(nextData)
}

function beginCamera(duration) {
  const sequence = ++cameraSequence
  lastCameraDuration.value = duration
  programmaticCamera = true
  window.clearTimeout(cameraReleaseTimer)
  map.stop()
  map.once('moveend', () => releaseProgrammaticCamera(sequence))
  cameraReleaseTimer = window.setTimeout(
    () => releaseProgrammaticCamera(sequence),
    duration + 140,
  )
}

function releaseProgrammaticCamera(sequence) {
  if (sequence !== cameraSequence) return
  programmaticCamera = false
  if (viewMode.value === 'overview') mapState.value = 'overview:ready'
  else mapState.value = activeLocation.value ? 'focus:ready' : 'no_location'
}

function clearCameraIntent() {
  cameraSequence += 1
  programmaticCamera = false
  lastCameraDuration.value = 0
  window.clearTimeout(cameraReleaseTimer)
  map?.stop()
}

function fitOverview({ immediate = false } = {}) {
  if (!map || !mapRef.value) return
  const unique = new Map()
  for (const { location } of locatedSceneSequence.value) {
    unique.set(`${location.longitude}:${location.latitude}`, location)
  }
  const locations = [...unique.values()]
  if (!locations.length) {
    clearCameraIntent()
    mapState.value = 'no_location'
    return
  }
  const duration = immediate || prefersReducedMotion() ? 0 : 700
  beginCamera(duration)
  if (locations.length === 1) {
    map.easeTo({
      center: [locations[0].longitude, locations[0].latitude],
      zoom: 4.8,
      duration,
      essential: false,
    })
    return
  }
  const longitudes = locations.map((location) => location.longitude)
  const latitudes = locations.map((location) => location.latitude)
  const width = Math.max(240, mapRef.value.clientWidth)
  const height = Math.max(180, mapRef.value.clientHeight)
  const horizontalPadding = Math.round(Math.max(24, Math.min(76, width * 0.11)))
  const verticalPadding = Math.round(Math.max(22, Math.min(58, height * 0.13)))
  map.fitBounds(
    [
      [Math.min(...longitudes), Math.min(...latitudes)],
      [Math.max(...longitudes), Math.max(...latitudes)],
    ],
    {
      padding: {
        top: verticalPadding,
        right: horizontalPadding,
        bottom: verticalPadding,
        left: horizontalPadding,
      },
      maxZoom: 5.4,
      duration,
      essential: false,
    },
  )
}

function focusLocation(location) {
  if (!map || !location) return
  const duration = prefersReducedMotion() ? 0 : 700
  beginCamera(duration)
  map.easeTo({
    center: [location.longitude, location.latitude],
    zoom: Math.max(map.getZoom(), 5.2),
    duration,
    essential: false,
  })
}

function applyOverview({ fit = false, immediate = false } = {}) {
  setSourceData('explore-scene-place', overviewPointCollection())
  setSourceData('explore-related-places', EMPTY_COLLECTION)
  setSourceData('explore-scene-relations', narrativeSequenceCollection())
  mapState.value = 'overview:ready'
  if (fit) fitOverview({ immediate })
}

function applyFocus({ focus = false } = {}) {
  const location = activeLocation.value
  setSourceData('explore-scene-place', focusedPointCollection())
  setSourceData(
    'explore-related-places',
    location ? relatedPointCollection(relatedLocations.value) : EMPTY_COLLECTION,
  )
  setSourceData('explore-scene-relations', EMPTY_COLLECTION)
  if (!location) {
    clearCameraIntent()
    mapState.value = 'no_location'
    return
  }
  mapState.value = 'focus:ready'
  if (focus) focusLocation(location)
}

function applyScene({ forceCamera = false, immediate = false } = {}) {
  // isStyleLoaded() 在参考瓦片尚未结束加载时会短暂返回 false；此时 GeoJSON
  // source 已可写。若把 Scene 同步也挡住，会留下“已进聚焦但仍显示总览”的竞态。
  if (!map?.getSource('explore-scene-place')) return
  if (isSampleWorkspace.value && viewMode.value === 'overview') {
    applyOverview({ fit: forceCamera, immediate })
  } else {
    applyFocus({ focus: forceCamera })
  }
}

async function setViewMode(mode) {
  if (mode !== 'overview' && mode !== 'focus') return
  if (mode === 'overview' && !isSampleWorkspace.value) return
  viewMode.value = mode
  await nextTick()
  applyScene({ forceCamera: true })
}

async function focusScene(index) {
  if (!Number.isInteger(index) || !ANSHI_PUBLIC_SCENES[index]) return
  viewMode.value = 'focus'
  store.selectScene(index, { keepPlaying: store.isPlaying })
  await nextTick()
  applyScene({ forceCamera: true })
}

function onMapSceneClick(event) {
  const sceneId = event.features?.[0]?.properties?.sceneId
  const index = ANSHI_PUBLIC_SCENES.findIndex((scene) => scene.id === sceneId)
  if (index >= 0) focusScene(index)
}

function onManualInteraction(kind, event) {
  if (programmaticCamera) return
  mapState.value = viewMode.value === 'overview'
    ? 'overview:manual'
    : activeLocation.value ? 'focus:manual' : 'no_location'
  emit('manual-interaction', {
    kind,
    sceneId: activeSceneId.value,
    originalEventType: event?.originalEvent?.type || null,
  })
}

function refreshTheme() {
  if (!map?.isStyleLoaded()) return
  const values = [
    ['explore-paper', 'background-color', readToken('--map-paper', '#eee6d5')],
    ['explore-graticule', 'line-color', readToken('--map-grid', '#d8cdb9')],
    ['explore-scene-place-halo', 'circle-color', readToken('--accent', '#b44b38')],
    ['explore-scene-place', 'circle-stroke-color', readToken('--paper-el', '#faf6eb')],
    ['explore-scene-place-order', 'text-color', readToken('--paper-el', '#faf6eb')],
    ['explore-scene-place-label', 'text-color', readToken('--ink', '#302b25')],
    ['explore-scene-place-label', 'text-halo-color', readToken('--paper-el', '#faf6eb')],
    ['explore-scene-relations', 'line-color', readToken('--ink-mid', '#4a4539')],
    ['explore-scene-relations-corridor', 'line-color', readToken('--paper-el', '#faf6eb')],
    ['explore-related-places', 'circle-color', readToken('--ink-soft', '#756b5e')],
    ['explore-related-places', 'circle-stroke-color', readToken('--paper-el', '#faf6eb')],
    ['explore-related-places-label', 'text-color', readToken('--ink-soft', '#756b5e')],
    ['explore-related-places-label', 'text-halo-color', readToken('--paper-el', '#faf6eb')],
  ]
  for (const [layer, property, value] of values) {
    if (map.getLayer(layer)) map.setPaintProperty(layer, property, value)
  }
  if (map.getLayer('explore-scene-place')) {
    map.setPaintProperty('explore-scene-place', 'circle-color', [
      'case',
      ['boolean', ['get', 'active'], false],
      readToken('--accent', '#b44b38'),
      readToken('--ink-mid', '#4a4539'),
    ])
  }
  if (restrictedMapsEnabled && map.getLayer('explore-reference-basemap')) {
    const night = ui.palette === '夜'
    map.setPaintProperty('explore-reference-basemap', 'raster-opacity', night ? 0.28 : 0.52)
    map.setPaintProperty('explore-reference-basemap', 'raster-brightness-min', night ? 0.06 : 0)
    map.setPaintProperty('explore-reference-basemap', 'raster-brightness-max', night ? 0.52 : 1)
  }
}

onMounted(() => {
  viewMode.value = isSampleWorkspace.value ? 'overview' : 'focus'
  map = new maplibregl.Map({
    container: mapRef.value,
    style: buildStyle(),
    center: [104, 34],
    zoom: 3.2,
    minZoom: 2,
    maxZoom: 10,
    attributionControl: false,
    localIdeographFontFamily: "'Noto Serif SC','Source Han Serif SC','STSong',serif",
  })
  if (import.meta.env.DEV) window.__hkbExplorationMap = map
  map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'bottom-left')
  map.on('load', () => {
    map.getCanvas().setAttribute('aria-label', '书籍叙事地图，可拖动与缩放')
    refreshTheme()
    applyScene({ forceCamera: true, immediate: true })
  })
  map.on('click', 'explore-scene-place', onMapSceneClick)
  map.on('mouseenter', 'explore-scene-place', () => {
    map.getCanvas().style.cursor = 'pointer'
  })
  map.on('mouseleave', 'explore-scene-place', () => {
    map.getCanvas().style.cursor = ''
  })
  map.on('dragstart', (event) => onManualInteraction('drag', event))
  map.on('zoomstart', (event) => onManualInteraction('zoom', event))
  map.on('rotatestart', (event) => onManualInteraction('rotate', event))

  resizeObserver = new ResizeObserver(() => {
    window.cancelAnimationFrame(resizeFrame)
    resizeFrame = window.requestAnimationFrame(() => {
      resizeFrame = 0
      map?.resize()
      if (viewMode.value === 'overview') fitOverview({ immediate: true })
    })
  })
  resizeObserver.observe(mapRef.value)
})

watch(
  () => [
    props.scene?.id || props.scene?.scene_id || null,
    props.scene?.location?.id || null,
    props.scene?.location?.longitude ?? null,
    props.scene?.location?.latitude ?? null,
    isSampleWorkspace.value,
  ],
  async (nextState, previousState) => {
    const changedScene = nextState[0] !== previousState?.[0]
    if (!isSampleWorkspace.value) viewMode.value = 'focus'
    else if (
      changedScene
      && previousState?.[0]
      && viewMode.value === 'overview'
      && !store.isPlaying
    ) {
      // 阅读器或时间列表的主动选择应进入 Scene；播放则保留用户当前镜头。
      viewMode.value = 'focus'
    }
    await nextTick()
    applyScene({
      forceCamera: viewMode.value === 'focus' && changedScene,
    })
  },
  { deep: true },
)

watch(
  () => ui.palette,
  () => refreshTheme(),
)

defineExpose({
  getDebugState: () => ({
    mapState: mapState.value,
    viewMode: viewMode.value,
    sceneId: activeSceneId.value,
    location: activeLocation.value,
    relatedLocations: relatedLocations.value,
    overviewLocationCount: locatedSceneSequence.value.length,
    overviewMissingCount: sceneSequence.value.length - locatedSceneSequence.value.length,
    overviewLineCount: overviewLineCount.value,
    lastCameraDuration: lastCameraDuration.value,
  }),
  refreshTheme,
  fitOverview,
})

onBeforeUnmount(() => {
  window.clearTimeout(cameraReleaseTimer)
  window.cancelAnimationFrame(resizeFrame)
  resizeFrame = 0
  resizeObserver?.disconnect()
  resizeObserver = null
  map?.remove()
  map = null
  if (import.meta.env.DEV) delete window.__hkbExplorationMap
})
</script>

<style scoped>
.explore-map-panel {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 260px;
  overflow: hidden;
  color: var(--ink);
  background: var(--map-paper, var(--paper));
}

.explore-map-canvas {
  position: absolute;
  inset: 0;
}

.explore-map-mode {
  position: absolute;
  z-index: 7;
  top: 12px;
  right: 12px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--caption, var(--paper-el));
  box-shadow: 0 3px 12px rgba(48, 39, 29, 0.1);
}

.explore-map-mode button {
  min-width: 46px;
  padding: 4px 8px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--ink-soft);
  font-size: 10px;
}

.explore-map-mode button.active {
  background: var(--accent);
  color: var(--accent-text);
}

.explore-map-mode button:focus-visible,
.explore-map-sequence button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.explore-scene-card {
  position: absolute;
  z-index: 5;
  top: 14px;
  left: 14px;
  width: min(290px, calc(100% - 28px));
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 7px;
  background: var(--caption, var(--paper-el));
  box-shadow: 0 6px 20px rgba(48, 39, 29, 0.15);
  backdrop-filter: blur(7px);
}

.explore-scene-kicker {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--ink-faint);
  font-size: 10px;
}

.explore-scene-kicker span {
  color: var(--accent);
  font-weight: 700;
}

.explore-scene-card h3 {
  margin: 5px 0 0;
  font-family: var(--serif);
  font-size: 12px;
  line-height: 1.45;
}

.explore-scene-card p {
  margin: 6px 0 0;
  color: var(--ink-soft);
  font-size: 11px;
  line-height: 1.6;
}

.explore-map-notice {
  margin-top: 7px;
  padding-top: 7px;
  border-top: 1px solid var(--line);
  color: var(--ink-faint);
  font-size: 10px;
  line-height: 1.5;
}

.explore-map-sequence {
  position: absolute;
  z-index: 6;
  top: 54px;
  right: 12px;
  width: min(190px, 34%);
  max-height: calc(100% - 96px);
  margin: 0;
  padding: 4px;
  overflow: auto;
  list-style: none;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: color-mix(in srgb, var(--caption, var(--paper-el)) 92%, transparent);
  box-shadow: 0 4px 14px rgba(48, 39, 29, 0.1);
  backdrop-filter: blur(7px);
}

.explore-map-sequence li + li {
  border-top: 1px solid var(--hair);
}

.explore-map-sequence button {
  width: 100%;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  grid-template-rows: auto auto;
  column-gap: 6px;
  padding: 5px 6px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--ink);
  text-align: left;
}

.explore-map-sequence button:hover,
.explore-map-sequence li.active button {
  background: var(--chip);
}

.explore-map-sequence b {
  grid-row: 1 / 3;
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  align-self: center;
  border-radius: 50%;
  background: var(--ink-mid);
  color: var(--paper-el);
  font-size: 9px;
}

.explore-map-sequence li.active b {
  background: var(--accent);
  color: var(--accent-text);
}

.explore-map-sequence span {
  overflow: hidden;
  font-family: var(--serif);
  font-size: 9px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.explore-map-sequence small {
  color: var(--ink-faint);
  font-size: 8px;
}

.explore-map-sequence li.missing small {
  color: var(--accent);
}

.explore-map-sequence li.missing b {
  border: 1px solid var(--ink-faint);
  background: transparent;
  color: var(--ink-soft);
}

.explore-sequence-caption,
.explore-reference-caption,
.explore-relation-caption {
  position: absolute;
  z-index: 5;
  padding: 5px 7px;
  border: 1px solid var(--line);
  border-radius: 5px;
  background: var(--caption, var(--paper-el));
  color: var(--ink-soft);
  font-size: 9px;
}

.explore-sequence-caption {
  right: 12px;
  bottom: 12px;
}

.explore-reference-caption {
  right: 116px;
  top: 12px;
}

.explore-relation-caption {
  top: 48px;
  right: 12px;
}

.explore-map-player {
  position: absolute;
  z-index: 8;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
}

:deep(.maplibregl-ctrl-bottom-left) {
  bottom: 8px;
  left: 8px;
}

:deep(.maplibregl-ctrl-group) {
  border: 1px solid var(--line);
  border-radius: 7px;
  background: var(--caption, var(--paper-el));
  box-shadow: 0 3px 12px rgba(48, 39, 29, 0.13);
}

:deep(.maplibregl-ctrl-group button) {
  width: 30px;
  height: 30px;
}

@media (max-width: 720px) {
  .explore-map-mode {
    top: 8px;
    right: 8px;
  }

  .explore-scene-card {
    top: 8px;
    left: 8px;
    width: min(210px, calc(100% - 124px));
    padding: 9px 10px;
  }

  .explore-scene-card p {
    display: none;
  }

  .explore-map-sequence {
    top: 48px;
    right: 8px;
    width: min(156px, 42%);
    max-height: calc(100% - 92px);
  }

  .explore-map-sequence span {
    display: none;
  }

  .explore-map-sequence button {
    grid-template-columns: 22px minmax(0, 1fr);
  }

  .explore-reference-caption {
    display: none;
  }

  .explore-sequence-caption {
    right: 8px;
    bottom: 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .explore-map-panel,
  .explore-scene-card {
    scroll-behavior: auto;
    transition: none;
  }
}
</style>
