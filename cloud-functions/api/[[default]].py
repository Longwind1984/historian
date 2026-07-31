"""EdgeOne /api/* entrypoint for the existing FastAPI application."""
from __future__ import annotations

import os
from pathlib import Path
import sys

FUNCTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FUNCTION_ROOT))
os.environ.setdefault("DATA_DIR", str(FUNCTION_ROOT / "runtime_data"))
os.environ.setdefault("SCHEMA_DIR", str(FUNCTION_ROOT / "runtime_data" / "schema"))
os.environ.setdefault("COMPILED_DATA_REQUIRED", "1")
# 公网云函数只服务静态公开 Demo；无认证的私人 Prompt / 上传路由不得注册。
os.environ["PRIVATE_EXPLORATIONS_ENABLED"] = "0"

from history_app.main import create_app  # noqa: E402

app = create_app(api_prefix="", mount_tiles=False)
