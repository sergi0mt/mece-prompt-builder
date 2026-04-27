"""Backend configuration — loads from environment or .env file.

Path resolution honors Railway's persistent-volume convention: when
`RAILWAY_VOLUME_MOUNT_PATH` is set (e.g. `/data`), the SQLite database
and uploads all live under that mount so they survive deploys
and container restarts. Locally the paths fall back to the repo tree.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

_ROOT = Path(__file__).parent.parent  # repo root

_VOLUME = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
_DATA_BASE = Path(_VOLUME) if _VOLUME else _ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        extra="ignore",
    )

    # LLM — OpenRouter
    openrouter_api_key: str = ""

    # Model routing — 2-tier system (no model_powerful needed for Stage 1+2)
    #   fast:     problem definition, classification
    #   balanced: MECE structuring, research synthesis
    model_fast: str = "deepseek/deepseek-v3.2"        # $0.38/M — stage 1
    model_balanced: str = "google/gemini-2.5-flash"    # $2.50/M — stage 2
    max_tokens: int = 4096

    # Web search
    tavily_api_key: str = ""
    brave_api_key: str = ""
    search_provider: str = "auto"  # "brave" | "tavily" | "auto"

    # Database
    database_path: str = str(_DATA_BASE / "data" / "mece_prompt_builder.db")

    # File storage
    upload_dir: str = str(_DATA_BASE / "uploads")

    # Server
    host: str = "0.0.0.0"
    port: int = int(os.environ.get("PORT", "8000"))
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
