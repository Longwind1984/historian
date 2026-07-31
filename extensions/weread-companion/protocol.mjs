export const PROTOCOL_VERSION = 1;
export const CAPTURE_REQUEST_TYPE =
  "history-kb/weread-capture-selection/v1";
export const CAPTURE_RESPONSE_TYPE =
  "history-kb/weread-capture-result/v1";
export const PACKET_TYPE = "hkb.weread.selection";
export const ACK_TYPE = "hkb.weread.ack";
export const MAX_SELECTION_LENGTH = 2000;
export const ACK_STATUSES = Object.freeze([
  "synced",
  "local_only",
  "no_workspace",
  "invalid",
  "failed"
]);

export const WORKBENCHES = Object.freeze({
  local: Object.freeze({
    label: "本地",
    origin: "http://127.0.0.1:5173",
    url: "http://127.0.0.1:5173/?companion=1#route=explore"
  })
});

export function normalizeSelection(value) {
  return Array.from(String(value ?? "").replace(/\r\n?/g, "\n").trim())
    .slice(0, MAX_SELECTION_LENGTH)
    .join("");
}

export function isWereadUrl(value) {
  if (typeof value !== "string" || value.length > 2048) {
    return false;
  }
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      url.hostname === "weread.qq.com" &&
      !url.username &&
      !url.password
    );
  } catch {
    return false;
  }
}

export function isCaptureResponse(value) {
  return Boolean(
    value &&
      value.type === CAPTURE_RESPONSE_TYPE &&
      value.version === PROTOCOL_VERSION &&
      value.ok === true &&
      value.payload &&
      typeof value.payload.title === "string" &&
      value.payload.title.trim().length > 0 &&
      Array.from(value.payload.title.trim()).length <= 300 &&
      isWereadUrl(value.payload.url) &&
      typeof value.payload.locator === "string" &&
      value.payload.locator.trim().length > 0 &&
      Array.from(value.payload.locator.trim()).length <= 1000 &&
      typeof value.payload.selection === "string" &&
      Array.from(value.payload.selection).length <= MAX_SELECTION_LENGTH
  );
}

export function createSelectionPacket(capture, options = {}) {
  if (!isCaptureResponse(capture)) {
    throw new TypeError("Invalid WeRead capture response");
  }

  const id =
    options.id ??
    globalThis.crypto?.randomUUID?.() ??
    `weread-${Date.now()}`;

  return {
    type: PACKET_TYPE,
    version: PROTOCOL_VERSION,
    id,
    url: capture.payload.url,
    title: Array.from(capture.payload.title.trim()).slice(0, 300).join(""),
    locator: capture.payload.locator.trim(),
    text: normalizeSelection(capture.payload.selection)
  };
}

export function isSelectionAck(value, id) {
  const allowedKeys = new Set([
    "type",
    "version",
    "id",
    "status",
    "revision",
    "reason"
  ]);
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.keys(value).some((key) => !allowedKeys.has(key)) ||
    value.type !== ACK_TYPE ||
    value.version !== PROTOCOL_VERSION ||
    value.id !== id ||
    !ACK_STATUSES.includes(value.status) ||
    ("revision" in value &&
      (!Number.isInteger(value.revision) || value.revision < 0)) ||
    ("reason" in value &&
      (typeof value.reason !== "string" ||
        value.reason.trim().length === 0 ||
        Array.from(value.reason).length > 200))
  ) {
    return false;
  }

  return true;
}
