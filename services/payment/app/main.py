from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request
from bms_common.headers import CORRELATION_ID_HEADER
from bms_common.logging import configure_logging, correlation_id_var
from app.core.config import get_settings
from app.core.db import close_mongo, connect_mongo
from app.core.mq import close_mq, connect_mq
from app.routers import health, payments

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect_mongo()
    await connect_mq()
    try:
        yield
    finally:
        await close_mq()
        await close_mongo()


app = FastAPI(title="Payment Service", version="0.1.0", lifespan=lifespan)


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
app.include_router(payments.router)