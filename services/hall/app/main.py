from contextlib import asynccontextmanager
import logging
import uuid
from fastapi import FastAPI, Request, Response
import httpx
from app.core.config import get_settings
from app.core.db import close_db, connect_db
from app.routers import halls_router

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] corr_id=%(correlation_id)s %(message)s",
)
logger = logging.getLogger(settings.service_name)


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        return True


logger.addFilter(CorrelationFilter())
for handler in logging.getLogger().handlers:
    handler.addFilter(CorrelationFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    try:
        yield
    finally:
        await app.state.http_client.aclose()
        await close_db()


app = FastAPI(title="BMS Hall Service", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = corr_id
    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


app.include_router(halls_router)