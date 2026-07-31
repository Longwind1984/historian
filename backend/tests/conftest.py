"""共享 pytest 配置。

- 在导入 `app` 之前设置 DATA_DIR / SCHEMA_DIR 默认值（指向仓库根的 data/ 与 schema/），
  这样即使不显式传环境变量也能本地跑；显式传入时优先用传入值。
  注意 `app/core/config.py` 的 settings 在模块导入时读取环境变量，所以必须在任何
  `from app...` 之前完成设置——conftest 在收集测试前先被 pytest 加载，满足该顺序。
- session 级 fixture：TestClient 与两个索引全程只构建一次，避免 7000 实体索引被
  每个用例重建导致套件超慢。
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # backend/tests/
BACKEND = HERE.parent                            # backend/
REPO = BACKEND.parent                            # 仓库根

# 本地默认值：仓库根的 data/ 与 schema/。已显式设置则不覆盖。
os.environ.setdefault("DATA_DIR", str(REPO / "data"))
os.environ.setdefault("SCHEMA_DIR", str(REPO / "schema"))

# 让 `import app` 可用（等价于从 backend/ 目录运行）。
sys.path.insert(0, str(BACKEND))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """session 级 TestClient：FastAPI app 只初始化一次。"""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def entity_index():
    """session 级 EntityIndex（已构建，复用模块单例）。"""
    from app.core.data import get_entity_index
    return get_entity_index()


@pytest.fixture(scope="session")
def relation_index():
    """session 级 RelationIndex（已构建，复用模块单例）。"""
    from app.core.data import get_relation_index
    return get_relation_index()
