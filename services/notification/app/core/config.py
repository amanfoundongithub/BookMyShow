from functools import lru_cache
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"
    service_name: str = "notification-service"
    service_port: int = 8004

    rabbitmq_default_user: str = "guest"
    rabbitmq_default_pass: str = "guest"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    booking_exchange: str = "booking.exchange"
    payment_exchange: str = "payment.exchange"
    booking_notifications_queue: str = "q.booking.notifications"
    notification_dlq: str = "q.booking.notifications.dlq"

    @property
    def rabbitmq_url(self) -> str:
        user = quote_plus(self.rabbitmq_default_user)
        password = quote_plus(self.rabbitmq_default_pass)
        return f"amqp://{user}:{password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"


@lru_cache
def get_settings() -> Settings:
    return Settings()