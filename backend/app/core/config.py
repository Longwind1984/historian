"""Configuration for the history-kb backend."""
import os
from pathlib import Path


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
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


settings = Settings()
