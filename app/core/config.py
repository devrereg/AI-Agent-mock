from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv

from app.core.secret import SecretsManager
load_dotenv()

from functools import lru_cache


class Settings(BaseSettings):
    ENV: str = Field(..., env="ENV")

    PROJECT_NAME: str = "Wenoa Agent"
    API_V1_STR: str = "/api/v1"

    OPENAI_API_KEY: Optional[str] = None
    MODEL_NAME: str = "gpt-4o"

    JWT_SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRATION: Optional[str] = None

    WENOA_BACKEND_URL: str

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    env_settings = Settings()

    if env_settings.ENV == "local":
        return env_settings

    secret_name = f"{env_settings.ENV}/secret"
    secret = SecretsManager.load(secret_name) or {}

    merged = {
        **env_settings.model_dump(),
        **secret
    }

    return Settings(**merged)


settings = get_settings()
