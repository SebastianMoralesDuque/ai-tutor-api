"""
Application configuration.

Uses pydantic-settings for env-based config.
Swap DATABASE_URL to postgres://... for production.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Tutor Backend"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database — SQLite by default, PostgreSQL-ready
    DATABASE_URL: str = "sqlite:///./ai_tutor.db"

    # AI provider — OpenCode Zen (DeepSeek V4 Flash Free, no key needed)
    AI_PROVIDER: str = "opencode"  # "mock" | "opencode"
    AI_MODEL: str = "deepseek-v4-flash-free"
    AI_BASE_URL: str = "https://opencode.ai/zen/v1"

    # Spaced repetition defaults
    REVIEW_INTERVAL_BASE_HOURS: int = 24
    MASTERY_INCREASE_ON_CORRECT: float = 10.0
    MASTERY_DECREASE_ON_WRONG: float = -15.0

    @property
    def IS_SQLITE(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
