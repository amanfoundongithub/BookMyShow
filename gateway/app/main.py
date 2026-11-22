from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bms_common.logging import configure_logging
from app.core.config import get_settings
from app.middleware.correlation import CorrelationMiddleware
from app.routers import proxy

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=settings.upstream_timeout_seconds)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(title="BookMyShow API Gateway", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(proxy.router)