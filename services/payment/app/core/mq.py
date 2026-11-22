import json
import logging
import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractRobustConnection
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_connection: AbstractRobustConnection | None = None
_channel: AbstractChannel | None = None
_payment_exchange: AbstractExchange | None = None


async def connect_mq() -> None:
    global _connection, _channel, _payment_exchange
    settings = get_settings()

    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()
    _payment_exchange = await _channel.declare_exchange(
        settings.payment_exchange, ExchangeType.TOPIC, durable=True
    )


async def publish_payment_event(routing_key: str, payload: dict) -> None:
    if _payment_exchange is None:
        logger.warning("Payment exchange not initialized; skipping %s", routing_key)
        return
    msg = Message(
        body=json.dumps(payload, default=str).encode("utf-8"),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await _payment_exchange.publish(msg, routing_key=routing_key)


async def close_mq() -> None:
    global _connection, _channel, _payment_exchange
    if _channel is not None:
        await _channel.close()
        _channel = None
    if _connection is not None:
        await _connection.close()
        _connection = None