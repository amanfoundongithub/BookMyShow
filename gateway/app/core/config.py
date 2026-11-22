from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"
    service_name: str = "api-gateway"
    service_port: int = 8000

    jwt_secret: str = "change-me-in-local-dev"
    jwt_algorithm: str = "HS256"

    catalog_service_url: str = "http://localhost:8001"
    booking_service_url: str = "http://localhost:8002"
    payment_service_url: str = "http://localhost:8003"
    cors_origins: list[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    upstream_timeout_seconds: float = 10.0

    @property
    def booking_ws_base_url(self) -> str:
        base = self.booking_service_url.rstrip("/")
        if base.startswith("https://"):
            return "wss://" + base.removeprefix("https://")
        if base.startswith("http://"):
            return "ws://" + base.removeprefix("http://")
        return f"ws://{base}"


@lru_cache
def get_settings() -> Settings:
    return Settings()