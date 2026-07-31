# Exploration v5 后端 checkpoint

日期：2026-07-27

## 本轮完成

- 新增 `POST /api/explorations/from-prompt`：不依赖书籍即可建立探索；返回原始问题、待确认时间/空间/主线、starter questions，以及一枚明确标记为 `evidence_gap` / `pending_review` 的“研究问题” Scene/Claim。
- 新增 `POST /api/explorations/import-epub`：接收 base64 EPUB，解析 container.xml、OPF 元数据、manifest、spine、章节和段落锚点；OPF 标题/作者单独标记来源，版本标签仍只接受用户填写。
- EPUB 锚点包含 `spine_index`、`href`、章节/段落序号和 0—100 的 progression；`page_label` 始终为 null，不虚构印刷页码。
- `update_reading_progress`、`set_active_anchor` 和 `update_scope_contract` 均沿用 revision 乐观并发合同。
- 微信读书桥接合同固定为 `provider=weread`、`sync_mode=manual_sync`、`access_boundary=cross_origin_no_dom_access`、`dom_access=false`；只保存用户主动提交的 locator/短摘录，不读取第三方 DOM。
- 深度分析请求只进入 `analysis_queue`，保存所选锚点和请求视图；输出保持 null，等待真正的模型/研究流程，不生成引文、页码、时间、地点或“反方观点”。

## EPUB 不可信输入边界

- base64 字符串上限：16,000,000 字符。
- 压缩包上限：12 MiB；ZIP entry 上限：500。
- 单 entry 解压上限：8 MiB；总解压上限：64 MiB；spine 上限：2,000 项。
- 可保留的 EPUB 正文上限：1,500,000 字符。
- 只允许 stored/deflate；拒绝加密 entry、symlink、重复规范化路径、绝对路径、URL、反斜线及任意 `..` 路径段。
- XML/HTML 在解析前拒绝 DOCTYPE/ENTITY；只读取容器、OPF 与 OPF spine 指向的 XHTML/HTML，不执行脚本、不请求远程资源、不把 ZIP 解压到磁盘。
- 解析结束不保留 base64 或 ZIP bytes，只保留段落与定位信息。

## 进程内隐私与容量

- 默认 TTL 21,600 秒、最多 64 个探索、全部会话合计最多 8,000,000 个来源字符；超限按最近访问时间淘汰最旧会话。
- snapshot 显式返回上述 session boundary；进程重启或 DELETE 会清空会话。
- 当前仍一次返回完整段落。真实样本的 snapshot JSON 为 2,789,080 bytes；这对 v5 单书原型可接受，但若放宽 1,500,000 字符上限，必须先改为章节目录 + 按需章节 endpoint，不能继续线性放大默认响应。

## 验证

- 依赖实测：Python 3.12.13、FastAPI 0.115.0、Pydantic 2.9.2；EPUB 解析只使用标准库。
- 生成的最小 EPUB fixture：OPF 元数据、2 个 spine 章节、3 个段落、locator/progression、脚本忽略、DOCTYPE 与路径穿越拒绝均通过。
- `uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests/test_api_explorations.py -q`
  - 18 passed, 1 skipped（私有 EPUB 测试默认需显式 opt-in）。
- 使用 `HISTORY_KB_TEST_EPUB` 指向用户给出的本机 EPUB：
  - 1 passed；不输出正文。
  - 6,703,749 压缩 bytes；解析为 28 个含正文的章节、4,445 个段落、541,066 个正文字符。
  - 单次解析约 85 ms；完整 snapshot JSON 约 2.79 MB。
- `uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q`
  - 214 passed, 1 skipped，11.19s。

## 文件

- `backend/app/schemas/exploration.py`
- `backend/app/services/exploration_service.py`
- `backend/app/api/explorations.py`
- `backend/app/main.py`
- `backend/tests/test_api_explorations.py`

未复制 EPUB、全文或正文摘录进仓库；未新增依赖；未提交 Git。
