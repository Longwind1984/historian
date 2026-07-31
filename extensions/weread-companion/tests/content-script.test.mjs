import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("../content-script.js", import.meta.url),
  "utf8"
);

function loadContentScript() {
  let listener = null;
  const runtimeId = "history-kb-extension";
  const sidepanelUrl = `chrome-extension://${runtimeId}/sidepanel.html`;
  const context = {
    chrome: {
      runtime: {
        id: runtimeId,
        getURL: (path) => `chrome-extension://${runtimeId}/${path}`,
        onMessage: {
          addListener: (value) => {
            listener = value;
          }
        }
      }
    },
    document: {
      title: "安史之乱"
    },
    window: {
      getSelection: () => ({ toString: () => "范阳起兵" }),
      location: {
        href: "https://weread.qq.com/web/reader/example",
        pathname: "/web/reader/example",
        search: "",
        hash: ""
      }
    }
  };

  vm.runInNewContext(source, context);
  return { listener, runtimeId, sidepanelUrl };
}

const message = {
  type: "history-kb/weread-capture-selection/v1",
  version: 1
};

test("content script accepts only its own side panel sender", () => {
  const { listener, runtimeId, sidepanelUrl } = loadContentScript();
  assert.equal(typeof listener, "function");

  let trustedResponse = null;
  listener(
    message,
    { id: runtimeId, url: sidepanelUrl },
    (value) => {
      trustedResponse = value;
    }
  );
  assert.equal(trustedResponse.ok, true);
  assert.equal(trustedResponse.payload.selection, "范阳起兵");

  for (const sender of [
    { id: "another-extension", url: sidepanelUrl },
    { id: runtimeId, url: `chrome-extension://${runtimeId}/popup.html` },
    { id: runtimeId }
  ]) {
    let untrustedResponse = null;
    const result = listener(message, sender, (value) => {
      untrustedResponse = value;
    });
    assert.equal(result, false);
    assert.equal(untrustedResponse, null);
  }
});
