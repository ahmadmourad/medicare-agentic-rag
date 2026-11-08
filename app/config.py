from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def clean_api_key(key: str) -> str:
    cleaned = key.strip()
    if cleaned.startswith("PASTE_YOUR_"):
        return ""
    return cleaned


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MediCare Assistant"
    frontend_dir: Path = BASE_DIR / "Frontend"
    docs_path: Path = BASE_DIR / "app" / "knowledge" / "docs.md"
    feedback_path: Path = BASE_DIR / "data" / "feedback.jsonl"

    # "auto", "none", "gemini", or "groq"
    llm_provider: str = "auto"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_fallback_model: str = ""
    llm_base_url: str = ""
    llm_timeout: float = 25.0

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    medlineplus_enabled: bool = True
    medlineplus_timeout: float = 6.0

    rate_limit_per_minute: int = 40

    @property
    def provider(self) -> str:
        explicit = self.llm_provider.strip().lower()
        if explicit == "none":
            return "none"
        has_gemini = bool(clean_api_key(self.gemini_api_key))
        has_groq = bool(clean_api_key(self.groq_api_key))
        if has_gemini and has_groq:
            return "gemini+groq"
        if has_gemini:
            return "gemini"
        if has_groq:
            return "groq"
        if explicit and explicit != "auto":
            return explicit
        return "none"


settings = Settings()
