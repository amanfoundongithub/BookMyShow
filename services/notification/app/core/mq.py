import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractQueue, AbstractRobustConnection
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_connection: AbstractRobustConnection | None = None
_channel: AbstractChannel | None = None


async def setup_consumer(
    on_message: Callable[[str, dict], Awaitable[None]],
) -> tuple[AbstractRobustConnection, AbstractChannel, AbstractQueue]:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    booking_exchange = await channel.declare_exchange(
        settings.booking_exchange, ExchangeType.TOPIC, durable=True
    )
    payment_exchange = await channel.declare_exchange(
        settings.payment_exchange, ExchangeType.TOPIC, durable=True
    )

    dlq = await channel.declare_queue(settings.notification_dlq, durable=True)
    queue = await channel.declare_queue(
        settings.booking_notifications_queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": dlq.name,
        },
    )

    await queue.bind(booking_exchange, routing_key="booking.created")
    await queue.bind(booking_exchange, routing_key="booking.expired")
    await queue.bind(payment_exchange, routing_key="payment.completed")
    await queue.bind(payment_exchange, routing_key="payment.failed")

    return connection, channel, queue


async def consume_forever(
    queue: AbstractQueue,
    on_message: Callable[[str, dict], Awaitable[None]],
    stop_event: asyncio.Event,
) -> None:
    async with queue.iterator() as messages:
        async for message in messages:
            if stop_event.is_set():
                break
            routing_key = message.routing_key or ""
            try:
                payload = json.loads(message.body.decode("utf-8"))
                await on_message(routing_key, payload)
                await message.ack()
            except Exception as exc:
                logger.exception(
                    "Failed processing notification event %s; rejecting to DLQ: %s",
                    routing_key,
                    exc,
                )
                await message.nack(requeue=False)