from functools import lru_cache
from urllib.parse import quote_plus
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
    service_name: str = "payment-service"
    service_port: int = 8003

    webhook_secret: str = "local-webhook-secret"

    mongo_connection_uri: str = Field(validation_alias="MONGO_URI")
    mongo_db_name: str = Field(default="BookMyShow", validation_alias="MONGO_DB_NAME")

    rabbitmq_default_user: str = "guest"
    rabbitmq_default_pass: str = "guest"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    payment_exchange: str = "payment.exchange"

    @property
    def mongo_uri(self) -> str:
        return self.mongo_connection_uri

    @property
    def rabbitmq_url(self) -> str:
        user = quote_plus(self.rabbitmq_default_user)
        password = quote_plus(self.rabbitmq_default_pass)
        return f"amqp://{user}:{password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"


@lru_cache
def get_settings() -> Settings:
    return Settings()