import test from "node:test";
import assert from "node:assert/strict";
import {
  ACK_MESSAGES,
  bridgeStateAfterAck,
  bridgeStateAwaitingAck,
  bridgeStateFromCapture,
  clearSensitiveBridgeState
} from "../bridge-state.mjs";

const capture = {
  payload: {
    title: "安史之乱",
    selection: "范阳起兵",
    truncated: false
  }
};

const packet = {
  version: 1,
  type: "hkb.weread.selection",
  id: "request-1",
  url: "https://weread.qq.com/web/reader/example",
  locator: "安史之乱 · /web/reader/example",
  text: "范阳起兵"
};

function assertSensitiveStateCleared(state) {
  assert.equal(state.capture, null);
  assert.equal(state.pendingPacket, null);
  assert.equal(state.previewVisible, false);
  assert.equal(state.previewMeta, "");
  assert.equal(state.previewText, "");
  assert.equal(state.canSend, false);
}

test("environment reset clears capture, pending packet and preview", () => {
  const captured = bridgeStateFromCapture(capture);
  const waiting = bridgeStateAwaitingAck(captured, packet);
  assert.equal(waiting.capture.payload.selection, "范阳起兵");
  assert.equal(waiting.pendingPacket.text, "范阳起兵");
  assert.equal(waiting.previewText, "范阳起兵");

  const cleared = clearSensitiveBridgeState("工作台已切换。");
  assertSensitiveStateCleared(cleared);
  assert.equal(cleared.status, "工作台已切换。");
});

test("every terminal acknowledgement clears selection text and memory", () => {
  for (const [status, message] of Object.entries(ACK_MESSAGES)) {
    const cleared = bridgeStateAfterAck(status);
    assertSensitiveStateCleared(cleared);
    assert.equal(cleared.status, message);
  }
});
