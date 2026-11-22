from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request
from bms_common.headers import CORRELATION_ID_HEADER
from bms_common.logging import configure_logging, correlation_id_var
from app.core.cache import close_redis, connect_redis
from app.core.config import get_settings
from app.core.db import close_mongo, connect_mongo
from app.routers import cities, halls, movies, health, shows

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect_mongo()
    await connect_redis()
    try:
        yield
    finally:
        await close_redis()
        await close_mongo()


app = FastAPI(title="Catalog Service", version="0.1.0", lifespan=lifespan)


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
app.include_router(cities.router)
app.include_router(movies.router)
app.include_router(shows.router)
app.include_router(halls.router)