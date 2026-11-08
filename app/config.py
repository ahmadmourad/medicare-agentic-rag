from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MediCare Assistant"
    frontend_dir: Path = BASE_DIR / "Frontend"
    docs_path: Path = BASE_DIR / "app" / "knowledge" / "docs.md"
    feedback_path: Path = BASE_DIR / "data" / "feedback.jsonl"

    # "none", "gemini", or "groq"
    llm_provider: str = "none"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_fallback_model: str = ""
    llm_base_url: str = ""
    llm_timeout: float = 25.0

    medlineplus_enabled: bool = True
    medlineplus_timeout: float = 6.0

    rate_limit_per_minute: int = 40

    @property
    def provider(self) -> str:
        return self.llm_provider.strip().lower()


settings = Settings()
