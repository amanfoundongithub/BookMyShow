from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"
    service_name: str = "catalog-service"
    service_port: int = 8001

    mongo_connection_uri: str = Field(validation_alias="MONGO_URI")
    mongo_db_name: str = Field(default="BookMyShow", validation_alias="MONGO_DB_NAME")

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    catalog_cache_ttl_seconds: int = 120

    cinema_service_url: str = Field(
        default="http://localhost:8005", validation_alias="CINEMA_SERVICE_URL"
    )
    hall_service_url: str = Field(
        default="http://localhost:8006", validation_alias="HALL_SERVICE_URL"
    )

    @property
    def mongo_uri(self) -> str:
        return self.mongo_connection_uri

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()