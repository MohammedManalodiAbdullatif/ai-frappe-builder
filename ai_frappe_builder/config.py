"""
config.py — Application settings loaded from environment / .env file.
Uses pydantic-settings for type-safe, validated configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configurable knobs for the AI Frappe App Builder service."""

    # --- LLM Provider (Ollama Cloud / OpenAI compatible) ---
    LLM_BASE_URL: str = "https://ollama.com/v1"
    LLM_API_KEY: str = "9e2a356ae3e548eda6254d3fadd06852.VcurFZ3OaoRDR7ValomgbB5-"
    LLM_MODEL: str = "gemma4:31b"

    # Backward compatibility aliases
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = ""

    # --- Jev / Experiential Labs (Decision & Judging Layer) ---
    EXPERIENTIAL_API_KEY: str = ""
    DECISION_PROVIDER: str = "jev"

    # --- Frappe / ERPNext site (defaults; can be overridden per-session) ---
    FRAPPE_URL: str = ""
    FRAPPE_API_KEY: str = ""
    FRAPPE_API_SECRET: str = ""

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_frappe.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_effective_llm_key(self) -> str:
        return self.LLM_API_KEY or self.OPENROUTER_API_KEY

    def get_effective_llm_model(self) -> str:
        return self.LLM_MODEL or self.OPENROUTER_MODEL or "gemma4:31b"

    def get_effective_base_url(self) -> str:
        return self.LLM_BASE_URL.rstrip("/")


# Singleton settings object — import this everywhere
settings = Settings()


def get_settings() -> Settings:
    """Return the singleton Settings instance. Useful for dependency injection."""
    return settings
