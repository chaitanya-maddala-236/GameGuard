"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/gameguard.db")
    model_path: Path = Path(
        os.getenv("MODEL_PATH", "artifacts/models/gameguard-if-v1/model.joblib")
    )
    api_key: str = os.getenv("API_KEY", "")
    allowed_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
        if item.strip()
    )
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() == "true"


settings = Settings()
