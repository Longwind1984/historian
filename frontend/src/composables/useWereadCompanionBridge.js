import { onBeforeUnmount, onMounted } from 'vue'

const BRIDGE_VERSION = 1
const MESSAGE_TYPE = 'hkb.weread.selection'
const ACK_TYPE = 'hkb.weread.ack'
const EXTENSION_ORIGIN = /^chrome-extension:\/\/[a-p]{32}$/
const MESSAGE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/
const MAX_TITLE_LENGTH = 300
const MAX_LOCATOR_LENGTH = 1000
const MAX_TEXT_LENGTH = 2_000
const MAX_ACK_CACHE_SIZE = 100
const CONFIGURED_EXTENSION_ORIGIN = String(
  import.meta.env.VITE_WEREAD_COMPANION_ORIGIN || '',
).trim()

function trimmedString(value, maxLength) {
  if (typeof value !== 'string') return null
  const normalized = value.trim()
  if (!normalized || Array.from(normalized).length > maxLength) return null
  return normalized
}

function wereadUrl(value) {
  if (typeof value !== 'string' || value.length > 2_048) return null
  try {
    const parsed = new URL(value)
    if (parsed.protocol !== 'https:' || parsed.hostname !== 'weread.qq.com') return null
    if (parsed.username || parsed.password) return null
    return parsed.href
  } catch {
    return null
  }
}

function validateMessage(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null
  if (data.version !== BRIDGE_VERSION || data.type !== MESSAGE_TYPE) return null
  if (typeof data.id !== 'string' || !MESSAGE_ID.test(data.id)) return null
  const url = wereadUrl(data.url)
  const title = trimmedString(data.title, MAX_TITLE_LENGTH)
  const locator = trimmedString(data.locator, MAX_LOCATOR_LENGTH)
  const text = trimmedString(data.text, MAX_TEXT_LENGTH)
  if (!url || !title || !locator || !text) return null
  return { id: data.id, url, title, locator, text }
}

function ack(id, status, extra = {}) {
  return {
    version: BRIDGE_VERSION,
    type: ACK_TYPE,
    id,
    status,
    ...extra,
  }
}

export function useWereadCompanionBridge(store) {
  const queryEnabled = new URLSearchParams(window.location.search).get('companion') === '1'
  const configuredOriginIsValid = EXTENSION_ORIGIN.test(CONFIGURED_EXTENSION_ORIGIN)
  const enabled = queryEnabled && (import.meta.env.DEV || configuredOriginIsValid)
  const ackCache = new Map()
  const inFlightAcks = new Map()

  function rememberAck(response) {
    const cached = { ...response }
    ackCache.set(response.id, cached)
    if (ackCache.size > MAX_ACK_CACHE_SIZE) {
      ackCache.delete(ackCache.keys().next().value)
    }
    return { ...cached }
  }

  function replyWith(response, source, origin, reply) {
    const safeResponse = { ...response }
    if (reply) source?.postMessage?.(safeResponse, origin)
    return safeResponse
  }

  function originAllowed(origin, exactOrigin = CONFIGURED_EXTENSION_ORIGIN) {
    if (exactOrigin) return EXTENSION_ORIGIN.test(exactOrigin) && origin === exactOrigin
    return import.meta.env.DEV && EXTENSION_ORIGIN.test(origin)
  }

  async function receive(data, origin, source, {
    devTopLevel = false,
    reply = true,
    exactOrigin,
  } = {}) {
    if (!enabled || !originAllowed(origin, exactOrigin)) return null
    if (source !== window.parent || (!devTopLevel && window.parent === window)) return null

    const message = validateMessage(data)
    if (!message) {
      if (typeof data?.id !== 'string' || !MESSAGE_ID.test(data.id)) return null
      const response = ackCache.get(data.id)
        || rememberAck(ack(data.id, 'invalid', { reason: 'invalid_message' }))
      return replyWith(response, source, origin, reply)
    }

    const cached = ackCache.get(message.id)
    if (cached) return replyWith(cached, source, origin, reply)

    let pending = inFlightAcks.get(message.id)
    if (!pending) {
      pending = (async () => {
        const result = await store.receiveCompanionSelection(message)
        return rememberAck(ack(message.id, result.status, {
          ...(result.revision == null ? {} : { revision: result.revision }),
          ...(result.reason ? { reason: result.reason } : {}),
        }))
      })()
      inFlightAcks.set(message.id, pending)
    }
    try {
      const response = await pending
      return replyWith(response, source, origin, reply)
    } finally {
      if (inFlightAcks.get(message.id) === pending) inFlightAcks.delete(message.id)
    }
  }

  function onMessage(event) {
    void receive(event.data, event.origin, event.source)
  }

  onMounted(() => {
    if (!enabled) return
    window.addEventListener('message', onMessage)
    if (import.meta.env.DEV) {
      // E2E-only entry: it exercises the same origin and payload validator without
      // weakening the production requirement that the app is inside an extension iframe.
      window.__hkbCompanionTest = {
        receive: (
          data,
          origin = 'chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
          options = {},
        ) => receive(
          data,
          origin,
          options.source === 'other' ? null : window.parent,
          {
            devTopLevel: true,
            reply: false,
            exactOrigin: options.exactOrigin,
          },
        ),
      }
    }
  })

  onBeforeUnmount(() => {
    if (!enabled) return
    window.removeEventListener('message', onMessage)
    ackCache.clear()
    inFlightAcks.clear()
    if (import.meta.env.DEV) delete window.__hkbCompanionTest
  })

  return { enabled }
}
