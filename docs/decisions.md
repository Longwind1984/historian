# 架构决策记录 · Architecture Decision Records

本文件记录影响项目结构的方向性决策。倒序排列（最新在上）。仅记录决策、理由与恢复路径；讨论过程见 `docs/roadmap-v2.md` 与 `WORKLOG.md`。

---

## ADR-001 · 移除 Neo4j 图数据库

- **日期**：2026-07-11
- **状态**：已执行
- **背景**：项目自诞生起包含一条 Neo4j 图数据库路径——`backend/app/core/neo4j.py`（driver 单例）+ `backend/scripts/import_to_neo4j.py`（幂等导入脚本）+ `docker-compose.yml` 的 neo4j 服务。该路径**从未被实测**：本机无 Docker，所有查询长期走 YAML 内存索引 fallback（见旧版 PROGRESS.md "Known limitations #6"）。
- **决策**：移除 Neo4j 的全部代码、依赖、配置与导入脚本。
- **理由**：
  1. **未验证**——Neo4j 路径自始至终未跑通，是死重；
  2. **内存索引够用**——7,011 实体规模下，启动时构建的内存索引已满足当前查询需求；
  3. **YAML 为唯一真相源**——数据本源在 `data/**/*.yaml`，Neo4j 仅是可重建的缓存，移除不损失任何数据；
  4. **可随时重建**——未来若真需要图数据库（多跳图查询、更大规模），可从 git 历史恢复导入脚本重建。
- **影响范围**：删除 `backend/app/core/neo4j.py`、`backend/scripts/import_to_neo4j.py`；移除 `neo4j==5.24.0` 依赖、docker-compose 的 neo4j 服务、`backend/app/core/config.py` 的 `NEO4J_*` 配置项、`backend/app/main.py` 的 driver lifespan；同步清理 `README.md` 与 `schema/_registry.md` 中的相关说明。
- **恢复路径**：导入脚本与 driver 保留在 git 历史中。需要时从 `git tag v1.0.0` 之前的提交检出 `backend/scripts/import_to_neo4j.py` 与 `backend/app/core/neo4j.py`，配合 `data/**/*.yaml` 即可重建图数据库。
