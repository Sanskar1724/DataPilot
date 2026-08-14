"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(ROOT_DIR / ".env")


class Settings:
    """Typed access to environment configuration."""

    def __init__(self) -> None:
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.openrouter_model = os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"
        ).strip()
        self.ai_enabled = os.getenv("DATAPILOT_AI_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.log_level = os.getenv("DATAPILOT_LOG_LEVEL", "INFO").strip().upper()
        self.openrouter_base_url = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).strip().rstrip("/")
        self.openrouter_timeout = float(os.getenv("OPENROUTER_TIMEOUT", "60").strip())
        self.openrouter_http_referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
        self.openrouter_app_name = os.getenv("OPENROUTER_APP_NAME", "").strip()

    @property
    def has_api_key(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_api_key != "your_key_here")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()