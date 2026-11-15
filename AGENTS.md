# history-kb 仓库协作说明

## 项目事实

- 本仓库是中国通史互动知识库，不继承父目录“个人投资副驾”的项目描述。
- 当前事实以 `README.md`、`handoff.json`、`WORKLOG.md` 和当前 Git 状态为准；`PROGRESS.md` 主体是历史构建日志。
- 架构为 Vue 3 / Vite / Pinia 前端 + FastAPI 后端；YAML、GeoJSON 与本地地图瓦片是唯一数据源，不使用 Neo4j。

## 运行与验证

- 开发入口：`scripts/dev.sh`。后端环境只允许仓库内 `backend/.venv`、根 `.venv`，或按 `backend/requirements.txt` 解析的 `uv` 隔离环境；不得默认借用父目录虚拟环境。
- 后端：`uv run --with-requirements backend/requirements-dev.txt python -m pytest backend/tests -q`。
- 数据：`uv run --with-requirements backend/requirements.txt python scripts/validate_data.py`，验收红线是 `errors=0`；warning 不得静默删除或降低等级来过关。
- 前端：`cd frontend && npm run build`；E2E：`cd frontend && npm run test:e2e`，测试自行冷启动隔离服务。
- 修改完成后运行与影响面相称的测试，并在 `WORKLOG.md` 追加结果、未尽事项与文件清单。

## 数据真实性

- 不凭空补历史事实、边界、日期、人物关系、图像或来源；证据不足时留空并说明缺口。
- 数据迁移必须幂等，先验证引用与重复，再修改；禁止用会重排 YAML、丢注释或转义中文的整文件 dump。
- 不通过放宽断言、修改既有验收口径或隐藏 warning/error 来制造通过。

## 外部调用与仓库边界

- 外部网络/API 请求必须有连接与总超时；同一 URL 挂起后换来源或标记待核，不反复死等。
- 未经用户明确确认，不改 CI、部署配置，不发布、不 force push，不删除非本任务产生的文件。
- 保留与当前任务无关的工作区改动；诊断结论必须指向日志、源码、测试或可复现实验。
