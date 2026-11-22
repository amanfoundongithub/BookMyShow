from uuid import uuid4
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from bms_common.headers import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
from bms_common.logging import correlation_id_var


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        corr_id = (
            request.headers.get(CORRELATION_ID_HEADER)
            or request.headers.get(REQUEST_ID_HEADER)
            or str(uuid4())
        )
        token = correlation_id_var.set(corr_id)
        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = corr_id
            return response
        finally:
            correlation_id_var.reset(token)