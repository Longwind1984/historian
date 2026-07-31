import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  ACK_TYPE,
  CAPTURE_RESPONSE_TYPE,
  MAX_SELECTION_LENGTH,
  PROTOCOL_VERSION,
  WORKBENCHES,
  createSelectionPacket,
  isCaptureResponse,
  isSelectionAck,
  isWereadUrl,
  normalizeSelection
} from "../protocol.mjs";

const validCapture = {
  type: CAPTURE_RESPONSE_TYPE,
  version: PROTOCOL_VERSION,
  ok: true,
  payload: {
    title: "安史之乱",
    url: "https://weread.qq.com/web/reader/example",
    locator: "安史之乱 · /web/reader/example",
    selection: "范阳起兵",
    truncated: false
  }
};

const sharedContract = JSON.parse(
  await readFile(
    new URL("../../../contracts/weread-companion/v1-example.json", import.meta.url),
    "utf8"
  )
);

test("accepts only HTTPS weread.qq.com URLs", () => {
  assert.equal(isWereadUrl("https://weread.qq.com/web/reader/abc"), true);
  assert.equal(isWereadUrl("http://weread.qq.com/web/reader/abc"), false);
  assert.equal(isWereadUrl("https://weread.qq.com.evil.example/"), false);
  assert.equal(isWereadUrl("https://user:pass@weread.qq.com/"), false);
  assert.equal(
    isWereadUrl(`https://weread.qq.com/${"x".repeat(2048)}`),
    false
  );
  assert.equal(isWereadUrl("not-a-url"), false);
});

test("local beta exposes only the local workbench", () => {
  assert.deepEqual(Object.keys(WORKBENCHES), ["local"]);
  assert.equal(WORKBENCHES.local.origin, "http://127.0.0.1:5173");
});

test("normalizes line endings and limits Unicode code points", () => {
  const value = `  甲\r\n${"𠮷".repeat(MAX_SELECTION_LENGTH)}尾  `;
  const result = normalizeSelection(value);
  assert.equal(result.startsWith("甲\n𠮷"), true);
  assert.equal(Array.from(result).length, MAX_SELECTION_LENGTH);
  assert.equal(result.endsWith("尾"), false);
});

test("validates capture responses and rejects oversized text", () => {
  assert.equal(isCaptureResponse(validCapture), true);
  assert.equal(
    isCaptureResponse({
      ...validCapture,
      payload: {
        ...validCapture.payload,
        selection: "字".repeat(MAX_SELECTION_LENGTH + 1)
      }
    }),
    false
  );
  assert.equal(
    isCaptureResponse({
      ...validCapture,
      payload: { ...validCapture.payload, url: "https://example.com/" }
    }),
    false
  );
  assert.equal(
    isCaptureResponse({
      ...validCapture,
      payload: { ...validCapture.payload, locator: "" }
    }),
    false
  );
  assert.equal(
    isCaptureResponse({
      ...validCapture,
      payload: { ...validCapture.payload, title: "𠮷".repeat(301) }
    }),
    false
  );
  assert.equal(
    isCaptureResponse({
      ...validCapture,
      payload: { ...validCapture.payload, locator: "𠮷".repeat(1001) }
    }),
    false
  );
});

test("creates a deterministic versioned selection packet", () => {
  const packet = createSelectionPacket(validCapture, {
    id: sharedContract.id
  });

  assert.deepEqual(packet, sharedContract);
});

test("accepts only matching acknowledgements without text fields", () => {
  const ack = {
    type: ACK_TYPE,
    version: PROTOCOL_VERSION,
    id: "request-1",
    status: "synced",
    revision: 2
  };

  assert.equal(isSelectionAck(ack, "request-1"), true);
  assert.equal(isSelectionAck(ack, "request-2"), false);
  assert.equal(
    isSelectionAck(
      { ...ack, text: "不得回传正文" },
      "request-1"
    ),
    false
  );
  assert.equal(
    isSelectionAck({ ...ack, status: "unknown" }, "request-1"),
    false
  );
  assert.equal(
    isSelectionAck({ ...ack, revision: -1 }, "request-1"),
    false
  );
  assert.equal(
    isSelectionAck({ ...ack, revision: 1.5 }, "request-1"),
    false
  );
  assert.equal(
    isSelectionAck({ ...ack, reason: "" }, "request-1"),
    false
  );
  assert.equal(
    isSelectionAck({ ...ack, reason: "字".repeat(201) }, "request-1"),
    false
  );
  assert.equal(
    isSelectionAck({ ...ack, extra: true }, "request-1"),
    false
  );
});
