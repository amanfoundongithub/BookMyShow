import asyncio
import signal
from bms_common.logging import configure_logging, correlation_id_var
from app.core.config import get_settings
from app.core.mq import consume_forever, setup_consumer
from app.services.dispatcher import NotificationDispatcher


async def run_worker() -> None:
    settings = get_settings()
    configure_logging(service_name=settings.service_name, level=settings.log_level)

    dispatcher = NotificationDispatcher()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    async def handle_event(routing_key: str, payload: dict) -> None:
        corr_id = payload.get("correlation_id")
        token = correlation_id_var.set(corr_id)
        try:
            await dispatcher.dispatch(routing_key=routing_key, payload=payload)
        finally:
            correlation_id_var.reset(token)

    connection, channel, queue = await setup_consumer(on_message=handle_event)
    try:
        await consume_forever(queue=queue, on_message=handle_event, stop_event=stop_event)
    finally:
        await channel.close()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_worker())