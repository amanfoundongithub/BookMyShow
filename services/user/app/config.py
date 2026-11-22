from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVICE_NAME: str = "user-service"
    PORT: int = Field(default=8004, validation_alias="USER_SERVICE_PORT")

    MONGO_URI: str = Field(validation_alias="MONGO_URI")
    MONGO_DB: str = Field(default="BookMyShow", validation_alias="MONGO_DB_NAME")

    JWT_SECRET: str = "change-me-in-local-dev"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 1440


settings = Settings()