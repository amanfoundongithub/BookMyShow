from contextlib import asynccontextmanager
from uuid import uuid4
import httpx
from fastapi import FastAPI, Request
from bms_common.headers import CORRELATION_ID_HEADER
from bms_common.logging import configure_logging, correlation_id_var
from app.core.config import get_settings
from app.core.db import close_mongo, connect_mongo, get_database
from app.core.mq import close_mq, connect_mq
from app.core.redis import close_redis, connect_redis, get_redis
from app.redis_lock import SeatLockManager
from app.routers import bookings, health, ws
from app.services.event_handler import BookingEventHandler
from app.ws_manager import ShowWsManager

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongo()
    await connect_redis()

    redis = get_redis()
    db = get_database()

    ws_manager = ShowWsManager(redis=redis)
    await ws_manager.start()
    app.state.ws_manager = ws_manager
    app.state.http_client = httpx.AsyncClient(timeout=10.0)

    lock_manager = SeatLockManager(
        redis=redis, ttl_seconds=settings.seat_hold_ttl_seconds
    )
    event_handler = BookingEventHandler(
        db=db, lock_manager=lock_manager, ws_manager=ws_manager
    )

    await connect_mq(on_payment_event=event_handler.handle_payment_event)

    try:
        yield
    finally:
        await close_mq()
        await app.state.http_client.aclose()
        await ws_manager.stop()
        await close_redis()
        await close_mongo()


app = FastAPI(title="Booking Service", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    corr_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid4())
    token = correlation_id_var.set(corr_id)
    try:
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = corr_id
        return response
    finally:
        correlation_id_var.reset(token)


app.include_router(health.router)
app.include_router(bookings.router)
app.include_router(ws.router)