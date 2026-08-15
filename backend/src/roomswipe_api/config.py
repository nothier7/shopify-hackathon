from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    allowed_origins: str = "http://localhost:3000"

    openai_api_key: str | None = None
    openai_image_model: str | None = None
    openai_vision_model: str = "gpt-4.1-mini"

    shopify_agent_profile_url: str = (
        "https://shopify.dev/ucp/agent-profiles/2026-04-08/valid-with-capabilities.json"
    )
    shopify_global_catalog_mcp_url: str = "https://catalog.shopify.com/api/ucp/mcp"
    shopify_request_timeout_seconds: float = 20.0
    shopify_reference_image_max_bytes: int = 10_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("allowed_origins")
    @classmethod
    def normalize_allowed_origins(cls, value: str) -> str:
        return ",".join(origin.strip() for origin in value.split(",") if origin.strip())

    @property
    def cors_origins(self) -> list[str]:
        return self.allowed_origins.split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()
