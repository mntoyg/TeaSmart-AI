"""Application configuration, read once from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Every tunable the backend has. Override any field via TEASMART_<FIELD>."""

    model_config = SettingsConfigDict(
        env_prefix="TEASMART_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    app_name: str = "TeaSmart AI"
    model_version: str = "teasmart-v1"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Upload hardening (see docs/superpowers/specs, section 10).
    max_upload_bytes: int = 8388608
    max_image_pixels: int = 40000000

    # Stage 1 quality gate thresholds.
    blur_threshold: float = 80.0
    exposure_min_mean: float = 40.0
    exposure_max_mean: float = 215.0
    clip_max_pct: float = 0.10

    # Absolute by default so the knowledge base loads whatever the process cwd is.
    kb_path: Path = _APP_DIR / "kb" / "diseases.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
