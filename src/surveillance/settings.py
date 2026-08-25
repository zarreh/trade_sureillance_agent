from functools import lru_cache

from pydantic_settings import SettingsConfigDict
from zarreh_agentkit.settings import AgentSettings


class Settings(AgentSettings):
    """Application configuration, sourced from the environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SURVEILLANCE_", extra="ignore")

    langsmith_project: str = "trade-surveillance-agent"

    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    offline_mode: bool = False

    facts_db_path: str = "data/facts.db"
    policy_db_path: str = "data/policy.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
