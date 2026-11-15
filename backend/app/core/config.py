"""Configuration for the history-kb backend."""
import os
from pathlib import Path


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    repo_root: Path = Path(__file__).resolve().parents[3]
    data_dir: Path = Path(os.getenv("DATA_DIR", "/app/data"))
    schema_dir: Path = Path(os.getenv("SCHEMA_DIR", "/app/schema"))
    compiled_data_required: bool = _env_flag("COMPILED_DATA_REQUIRED")
    private_explorations_enabled: bool = _env_flag(
        "PRIVATE_EXPLORATIONS_ENABLED",
        default=not compiled_data_required,
    )
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173",
        ).split(",")
        if o.strip()
    ]
    exploration_state_dir: Path = Path(
        os.getenv(
            "EXPLORATION_STATE_DIR",
            str(repo_root / "external_data" / "explorations"),
        )
    )
    exploration_model_provider: str = os.getenv(
        "EXPLORATION_MODEL_PROVIDER", "none"
    ).strip()
    exploration_model_base_url: str | None = (
        os.getenv("EXPLORATION_MODEL_BASE_URL", "").strip() or None
    )
    exploration_model_api_key: str | None = (
        os.getenv("EXPLORATION_MODEL_API_KEY", "").strip() or None
    )
    exploration_extract_model: str | None = (
        os.getenv("EXPLORATION_EXTRACT_MODEL", "").strip() or None
    )
    exploration_synthesis_model: str | None = (
        os.getenv("EXPLORATION_SYNTHESIS_MODEL", "").strip() or None
    )
    exploration_judge_model: str | None = (
        os.getenv("EXPLORATION_JUDGE_MODEL", "").strip() or None
    )
    exploration_model_connect_timeout_seconds: float = float(
        os.getenv("EXPLORATION_MODEL_CONNECT_TIMEOUT_SECONDS", "5")
    )
    exploration_model_total_timeout_seconds: float = float(
        os.getenv("EXPLORATION_MODEL_TOTAL_TIMEOUT_SECONDS", "45")
    )
    exploration_worker_poll_seconds: float = float(
        os.getenv("EXPLORATION_WORKER_POLL_SECONDS", "1")
    )


settings = Settings()
