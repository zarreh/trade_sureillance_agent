from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SURVEILLANCE_", extra="ignore")

    environment: str = "development"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    offline_mode: bool = False

    langsmith_api_key: str = ""
    langsmith_project: str = "trade-surveillance-agent"

    data_dir: str = "data"
    facts_db_path: str = "data/facts.db"
    policy_db_path: str = "data/policy.db"
    run_store_path: str = "data/runs.db"

    rate_limit_per_minute: int = 20
    max_request_body_bytes: int = 16_384


@lru_cache
def get_settings() -> Settings:
    return Settings()
