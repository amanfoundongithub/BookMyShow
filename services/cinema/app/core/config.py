from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"
    service_name: str = "cinema-service"
    service_port: int = Field(default=8005, validation_alias="CINEMA_SERVICE_PORT")

    mongo_uri: str = Field(validation_alias="MONGO_URI")
    mongo_db_name: str = Field(default="BookMyShow", validation_alias="MONGO_DB_NAME")


@lru_cache
def get_settings() -> Settings:
    return Settings()