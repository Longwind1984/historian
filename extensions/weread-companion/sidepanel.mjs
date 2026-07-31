import {
  CAPTURE_REQUEST_TYPE,
  PROTOCOL_VERSION,
  WORKBENCHES,
  createSelectionPacket,
  isCaptureResponse,
  isSelectionAck
} from "./protocol.mjs";
import {
  bridgeStateAfterAck,
  bridgeStateAwaitingAck,
  bridgeStateFromCapture,
  clearSensitiveBridgeState
} from "./bridge-state.mjs";

const workbench = WORKBENCHES.local;
const elements = {
  frame: document.querySelector("#workbenchFrame"),
  frameStatus: document.querySelector("#frameStatus"),
  captureButton: document.querySelector("#captureButton"),
  sendButton: document.querySelector("#sendButton"),
  preview: document.querySelector("#selectionPreview"),
  meta: document.querySelector("#selectionMeta"),
  text: document.querySelector("#selectionText"),
  bridgeStatus: document.querySelector("#bridgeStatus")
};

let bridgeState = clearSensitiveBridgeState();
let frameStatusTimer = null;

function renderBridgeState() {
  elements.preview.hidden = !bridgeState.previewVisible;
  elements.meta.textContent = bridgeState.previewMeta;
  elements.text.textContent = bridgeState.previewText;
  elements.sendButton.disabled = !bridgeState.canSend;
  elements.bridgeStatus.textContent = bridgeState.status;
}

function showFrameStatus(message) {
  window.clearTimeout(frameStatusTimer);
  elements.frameStatus.textContent = message;
  elements.frameStatus.classList.add("visible");
  frameStatusTimer = window.setTimeout(() => {
    elements.frameStatus.classList.remove("visible");
  }, 1800);
}

function renderEnvironment() {
  elements.frame.src = workbench.url;
  showFrameStatus(`正在连接${workbench.label}工作台`);
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });
  return tab;
}

async function captureSelection() {
  elements.captureButton.disabled = true;
  bridgeState = clearSensitiveBridgeState("正在读取当前微信读书选区…");
  renderBridgeState();

  try {
    const tab = await activeTab();
    if (!tab?.id) {
      throw new Error("未找到当前标签页");
    }

    const response = await chrome.tabs.sendMessage(tab.id, {
      type: CAPTURE_REQUEST_TYPE,
      version: PROTOCOL_VERSION
    });
    if (!isCaptureResponse(response)) {
      throw new Error("当前页面不是可读取的微信读书页面");
    }

    bridgeState = bridgeStateFromCapture(response);
  } catch (error) {
    bridgeState = clearSensitiveBridgeState(
      error instanceof Error ? error.message : "读取当前选区失败"
    );
  } finally {
    elements.captureButton.disabled = false;
    renderBridgeState();
  }
}

function sendSelection() {
  if (!bridgeState.capture?.payload.selection) {
    return;
  }

  const pendingPacket = createSelectionPacket(bridgeState.capture);
  bridgeState = bridgeStateAwaitingAck(bridgeState, pendingPacket);
  renderBridgeState();
  elements.frame.contentWindow?.postMessage(
    pendingPacket,
    workbench.origin
  );
}

function receiveAck(event) {
  if (
    event.source !== elements.frame.contentWindow ||
    event.origin !== workbench.origin ||
    !bridgeState.pendingPacket ||
    !isSelectionAck(event.data, bridgeState.pendingPacket.id)
  ) {
    return;
  }

  bridgeState = bridgeStateAfterAck(event.data.status);
  renderBridgeState();
}

elements.captureButton.addEventListener("click", captureSelection);
elements.sendButton.addEventListener("click", sendSelection);
elements.frame.addEventListener("load", () => {
  showFrameStatus(`${workbench.label}工作台已载入`);
});
window.addEventListener("message", receiveAck);

renderBridgeState();
renderEnvironment();
