export const DEFAULT_BRIDGE_STATUS =
  "只有点击“读取当前选区”时，扩展才会读取微信读书页面。";

export const ACK_MESSAGES = Object.freeze({
  synced: "已加入当前探索。",
  local_only: "已保存在当前浏览器，工作区恢复后可继续同步。",
  no_workspace: "尚未建立探索，请先在工作台创建一个问题。",
  invalid: "选区数据无效，请重新读取。",
  failed: "纪年图谱暂时无法接收，请稍后重试。"
});

export function clearSensitiveBridgeState(status = DEFAULT_BRIDGE_STATUS) {
  return {
    capture: null,
    pendingPacket: null,
    previewVisible: false,
    previewMeta: "",
    previewText: "",
    canSend: false,
    status
  };
}

export function bridgeStateFromCapture(capture) {
  const { title, selection, truncated } = capture.payload;
  return {
    capture,
    pendingPacket: null,
    previewVisible: true,
    previewMeta: `${title || "微信读书"} · ${Array.from(selection).length} 字${truncated ? " · 已截断" : ""}`,
    previewText:
      selection || "当前没有选中文本；请在微信读书中拖选一段文字后重试。",
    canSend: selection.length > 0,
    status: selection
      ? "选区仅保存在当前面板中。确认后才会发送给纪年图谱。"
      : "尚未读取到选区。"
  };
}

export function bridgeStateAwaitingAck(state, pendingPacket) {
  return {
    ...state,
    pendingPacket,
    canSend: false,
    status: "已发送，等待纪年图谱确认…"
  };
}

export function bridgeStateAfterAck(status) {
  return clearSensitiveBridgeState(
    ACK_MESSAGES[status] ?? "纪年图谱已处理当前选区。"
  );
}
