# 纪年图谱 · 微信读书伴读

这是 history-kb 的 Chrome Companion Extension 本地 Beta。微信读书始终运行在正常的顶层标签页；本地纪年图谱运行在 Chrome Side Panel，避开第三方 iframe 无法继承微信读书登录态的问题。

## 权限与数据边界

- 仅声明 `sidePanel` 和 `https://weread.qq.com/*`。
- 不声明 `cookies`、`webRequest`、全站 `tabs` 或后台网络权限。
- 工作台 iframe 运行在明确的 sandbox 中，不具备顶层导航能力。
- 内容脚本不会自动采集书架、章节或正文。
- 只有用户点击“读取当前选区”时，才读取当前选择文本、页面标题与 URL。
- 选区最多保留 2,000 个 Unicode 字符；用户再次点击“加入当前探索”后才发送给工作台。
- 切换本地/线上工作台，以及收到任一终态确认后，会清空选区正文、预览 DOM 与内存引用。
- 工作台确认包不得包含选区、正文、摘录等文本字段。

## 本地加载

1. 打开 `chrome://extensions`。
2. 开启“开发者模式”。
3. 点击“加载已解压的扩展程序”。
4. 选择本目录：`extensions/weread-companion`。
5. 打开 `https://weread.qq.com/`，登录并进入一本书。
6. 点击扩展工具栏图标打开 Side Panel。

Side Panel 只连接：

```text
http://127.0.0.1:5173/?companion=1#route=explore
```

当前不暴露线上入口。上线是独立发布闸门：必须先获得固定扩展 ID，把该 ID 加入生产站允许来源，并为 Side Panel 配置精确的 `Content-Security-Policy frame-ancestors`；随后完成生产实机核验，才可把生产 origin 加回 manifest 与 UI。

## 交互协议

扩展向 iframe 发送：

```json
{
  "type": "hkb.weread.selection",
  "version": 1,
  "id": "uuid",
  "url": "https://weread.qq.com/...",
  "title": "页面标题",
  "locator": "书名 · /web/reader/...",
  "text": "用户主动选择的文字"
}
```

工作台必须校验 `event.origin`、`event.source`、版本和字段后，返回不含正文的确认：

```json
{
  "type": "hkb.weread.ack",
  "version": 1,
  "id": "原 id",
  "status": "synced",
  "revision": 1
}
```

`status` 只接受 `synced`、`local_only`、`no_workspace`、`invalid`、`failed`。确认包不得回传 `text`、`selection`、`content`、`body` 或 `excerpt`。

## 验证

```bash
cd extensions/weread-companion
npm test
node -e "JSON.parse(require('node:fs').readFileSync('manifest.json', 'utf8')); console.log('manifest ok')"
```

Chrome Side Panel API 要求 Chrome 114+、Manifest V3；`sidePanel` 权限与 `side_panel.default_path`、通过 `setPanelBehavior({ openPanelOnActionClick: true })` 打开面板的用法均按 Chrome 官方文档实现。

- [Chrome Side Panel API](https://developer.chrome.com/docs/extensions/reference/api/sidePanel)
- [Chrome Content scripts](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)
- [Chrome Extension message passing](https://developer.chrome.com/docs/extensions/develop/concepts/messaging)
