import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const manifestUrl = new URL("../manifest.json", import.meta.url);
const sidepanelUrl = new URL("../sidepanel.html", import.meta.url);
const manifest = JSON.parse(await readFile(manifestUrl, "utf8"));

test("manifest keeps the accepted single-domain permission boundary", () => {
  assert.deepEqual(manifest.permissions, ["sidePanel"]);
  assert.deepEqual(manifest.host_permissions, ["https://weread.qq.com/*"]);
  assert.deepEqual(manifest.content_scripts[0].matches, [
    "https://weread.qq.com/*"
  ]);

  const forbiddenPermissions = new Set([
    "cookies",
    "webRequest",
    "debugger",
    "nativeMessaging",
    "clipboardRead",
    "clipboardWrite"
  ]);
  const declaredPermissions = [
    ...(manifest.permissions ?? []),
    ...(manifest.optional_permissions ?? [])
  ];
  for (const permission of declaredPermissions) {
    assert.equal(
      forbiddenPermissions.has(permission),
      false,
      `forbidden permission: ${permission}`
    );
  }

  assert.equal(JSON.stringify(manifest).includes("<all_urls>"), false);
  assert.equal("externally_connectable" in manifest, false);
  assert.equal("web_accessible_resources" in manifest, false);
});

test("extension CSP denies objects and limits remote frames", () => {
  assert.equal(
    manifest.content_security_policy.extension_pages,
    "default-src 'self'; script-src 'self'; object-src 'none'; frame-src http://127.0.0.1:5173;"
  );
});

test("side panel iframe sandbox cannot navigate the top-level page", async () => {
  const html = await readFile(sidepanelUrl, "utf8");
  const sandboxMatch = html.match(/sandbox="([^"]+)"/);
  assert.ok(sandboxMatch);

  const capabilities = new Set(sandboxMatch[1].split(/\s+/));
  assert.deepEqual(capabilities, new Set([
    "allow-scripts",
    "allow-same-origin",
    "allow-forms",
    "allow-popups"
  ]));
  assert.equal(capabilities.has("allow-top-navigation"), false);
  assert.equal(capabilities.has("allow-top-navigation-by-user-activation"), false);
});
