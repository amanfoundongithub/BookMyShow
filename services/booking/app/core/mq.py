import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractRobustConnection
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_connection: AbstractRobustConnection | None = None
_channel: AbstractChannel | None = None
_booking_exchange: AbstractExchange | None = None
_consumer_task: asyncio.Task | None = None


async def connect_mq(
    on_payment_event: Callable[[str, dict], Awaitable[None]] | None = None,
) -> None:
    global _connection, _channel, _booking_exchange, _consumer_task
    settings = get_settings()

    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()
    await _channel.set_qos(prefetch_count=20)

    _booking_exchange = await _channel.declare_exchange(
        settings.booking_exchange, ExchangeType.TOPIC, durable=True
    )
    payment_exchange = await _channel.declare_exchange(
        settings.payment_exchange, ExchangeType.TOPIC, durable=True
    )

    if on_payment_event is not None:
        queue = await _channel.declare_queue(
            settings.booking_events_queue, durable=True
        )
        await queue.bind(payment_exchange, routing_key="payment.completed")
        await queue.bind(payment_exchange, routing_key="payment.failed")
        _consumer_task = asyncio.create_task(_consume_loop(queue, on_payment_event))


async def _consume_loop(
    queue: aio_pika.abc.AbstractQueue,
    handler: Callable[[str, dict], Awaitable[None]],
) -> None:
    async with queue.iterator() as messages:
        async for message in messages:
            async with message.process(requeue=False):
                payload = json.loads(message.body.decode("utf-8"))
                await handler(message.routing_key or "", payload)


async def publish_booking_event(routing_key: str, payload: dict) -> None:
    if _booking_exchange is None:
        logger.warning("Booking exchange not initialized; skipping publish %s", routing_key)
        return
    msg = Message(
        body=json.dumps(payload, default=str).encode("utf-8"),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await _booking_exchange.publish(msg, routing_key=routing_key)


async def close_mq() -> None:
    global _connection, _channel, _booking_exchange, _consumer_task
    if _consumer_task is not None:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
    if _channel is not None:
        await _channel.close()
        _channel = None
    if _connection is not None:
        await _connection.close()
        _connection = None