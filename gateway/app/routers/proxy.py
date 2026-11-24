import asyncio
import httpx
import websockets
from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from bms_common.headers import CORRELATION_ID_HEADER, IDEMPOTENCY_KEY_HEADER, USER_ID_HEADER
from app.core.config import get_settings
from app.core.security import decode_bearer_token

router = APIRouter(tags=["gateway"])

USER_ROLE_HEADER = "X-User-Role"
CINEMA_IDS_HEADER = "X-Cinema-Ids"

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


def _forward_headers(
    request: Request,
    corr_id: str | None,
    user_id: str | None = None,
    user_role: str | None = None,
    cinema_ids: list[str] | None = None,
    forward_authorization: bool = False,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    for k, v in request.headers.items():
        if k.lower() not in _HOP_BY_HOP_HEADERS and (
            forward_authorization or k.lower() != "authorization"
        ):
            headers[k] = v

    if corr_id:
        headers[CORRELATION_ID_HEADER] = corr_id

    idem = request.headers.get(IDEMPOTENCY_KEY_HEADER)
    if idem:
        headers[IDEMPOTENCY_KEY_HEADER] = idem

    if user_id:
        headers[USER_ID_HEADER] = user_id

    if user_role:
        headers[USER_ROLE_HEADER] = user_role

    if cinema_ids:
        headers[CINEMA_IDS_HEADER] = ",".join(cinema_ids)

    return headers


def _enforce_allowed_roles(
    role: str,
    allowed_roles: set[str] | None,
    corr_id: str | None,
) -> None:
    if allowed_roles and role not in allowed_roles:
        headers = {CORRELATION_ID_HEADER: corr_id} if corr_id else None
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized to access this resource",
            headers=headers,
        )


async def _proxy_http(
    request: Request,
    target_base_url: str,
    path: str,
    require_auth: bool,
    allowed_roles: set[str] | None = None,
    forward_authorization: bool = False,
) -> Response:
    corr_id = request.headers.get(CORRELATION_ID_HEADER) or getattr(
        request.state, "correlation_id", None
    )
    user_id: str | None = None
    user_role: str | None = None
    cinema_ids: list[str] | None = None

    if require_auth:
        claims = decode_bearer_token(request.headers.get("Authorization"))
        user_id = str(claims["sub"])
        user_role = str(claims.get("role") or "USER")
        raw_cinema_ids = claims.get("cinema_ids")
        if isinstance(raw_cinema_ids, list):
            cinema_ids = [str(c) for c in raw_cinema_ids if c]
        _enforce_allowed_roles(role=user_role, allowed_roles=allowed_roles, corr_id=corr_id)

    query_str = request.url.query
    url = f"{target_base_url.rstrip('/')}{path}"
    if query_str:
        url = f"{url}?{query_str}"

    body = await request.body()
    headers = _forward_headers(
        request=request,
        corr_id=corr_id,
        user_id=user_id,
        user_role=user_role,
        cinema_ids=cinema_ids,
        forward_authorization=forward_authorization,
    )

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        upstream_resp = await client.request(
            method=request.method,
            url=url,
            content=body,
            headers=headers,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream service unreachable: {exc}",
        ) from exc

    resp_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in _HOP_BY_HOP_HEADERS and k.lower() != "content-length"
    }
    if corr_id:
        resp_headers[CORRELATION_ID_HEADER] = corr_id

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )


@router.get("/health")
async def gateway_health() -> dict[str, str]:
    return {"status": "ok", "service": "api-gateway"}


@router.api_route(
    "/api/v1/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_auth(request: Request, path: str) -> Response:
    settings = get_settings()
    return await _proxy_http(
        request=request,
        target_base_url=settings.user_service_url,
        path=f"/api/v1/auth/{path}",
        require_auth=False,
    )


@router.api_route(
    "/api/v1/users/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_users(request: Request, path: str) -> Response:
    settings = get_settings()
    normalized = path.strip("/")
    allowed_roles = {"ADMIN"} if normalized == "" and request.method == "POST" else None
    return await _proxy_http(
        request=request,
        target_base_url=settings.user_service_url,
        path=f"/api/v1/users/{path}",
        require_auth=True,
        allowed_roles=allowed_roles,
        forward_authorization=True,
    )


@router.api_route(
    "/api/v1/cinemas",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/api/v1/cinemas/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_cinemas_root(request: Request) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.cinema_service_url,
        path="/api/v1/cinemas",
        require_auth=is_write,
        allowed_roles={"ADMIN", "CINEMA"} if is_write else None,
    )


@router.api_route(
    "/api/v1/cinemas/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_cinemas(request: Request, path: str) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.cinema_service_url,
        path=f"/api/v1/cinemas/{path}",
        require_auth=is_write,
        allowed_roles={"ADMIN", "CINEMA"} if is_write else None,
    )


@router.api_route(
    "/api/v1/halls",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/api/v1/halls/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_halls_root(request: Request) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.hall_service_url,
        path="/api/v1/halls",
        require_auth=is_write,
        allowed_roles={"ADMIN", "CINEMA"} if is_write else None,
    )


@router.api_route(
    "/api/v1/halls/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_halls(request: Request, path: str) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.hall_service_url,
        path=f"/api/v1/halls/{path}",
        require_auth=is_write,
        allowed_roles={"ADMIN", "CINEMA"} if is_write else None,
    )


@router.api_route(
    "/api/v1/cities",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/api/v1/cities/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_cities_root(request: Request) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.city_service_url,
        path="/api/v1/cities",
        require_auth=is_write,
        allowed_roles={"ADMIN"} if is_write else None,
    )


@router.api_route(
    "/api/v1/cities/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_cities(request: Request, path: str) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.city_service_url,
        path=f"/api/v1/cities/{path}",
        require_auth=is_write,
        allowed_roles={"ADMIN"} if is_write else None,
    )


@router.api_route(
    "/api/v1/movies",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/api/v1/movies/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_movies_root(request: Request) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.movie_service_url,
        path="/api/v1/movies",
        require_auth=is_write,
        allowed_roles={"ADMIN"} if is_write else None,
    )


@router.api_route(
    "/api/v1/movies/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_movies(request: Request, path: str) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    return await _proxy_http(
        request=request,
        target_base_url=settings.movie_service_url,
        path=f"/api/v1/movies/{path}",
        require_auth=is_write,
        allowed_roles={"ADMIN"} if is_write else None,
    )


@router.api_route(
    "/api/v1/catalog/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_catalog(request: Request, path: str) -> Response:
    settings = get_settings()
    is_write = request.method != "GET"
    if path.strip("/") == "cities":
        return await _proxy_http(
            request=request,
            target_base_url=settings.city_service_url,
            path="/api/v1/cities",
            require_auth=is_write,
            allowed_roles={"ADMIN"} if is_write else None,
        )
    return await _proxy_http(
        request=request,
        target_base_url=settings.catalog_service_url,
        path=f"/api/v1/catalog/{path}",
        require_auth=is_write,
        allowed_roles={"ADMIN", "CINEMA"} if is_write else None,
    )


@router.api_route(
    "/api/v1/bookings",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/api/v1/bookings/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_bookings_root(request: Request) -> Response:
    settings = get_settings()
    return await _proxy_http(
        request=request,
        target_base_url=settings.booking_service_url,
        path="/api/v1/bookings",
        require_auth=True,
    )


@router.api_route(
    "/api/v1/bookings/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_bookings(request: Request, path: str) -> Response:
    settings = get_settings()
    return await _proxy_http(
        request=request,
        target_base_url=settings.booking_service_url,
        path=f"/api/v1/bookings/{path}",
        require_auth=True,
    )


@router.api_route(
    "/api/v1/payments/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_payments(request: Request, path: str) -> Response:
    settings = get_settings()
    require_auth = not path.startswith("webhook")
    return await _proxy_http(
        request=request,
        target_base_url=settings.payment_service_url,
        path=f"/api/v1/payments/{path}",
        require_auth=require_auth,
    )


@router.websocket("/ws/shows/{show_id}")
async def proxy_show_ws(websocket: WebSocket, show_id: str) -> None:
    settings = get_settings()
    token = websocket.query_params.get("token")
    if token:
        try:
            decode_bearer_token(f"Bearer {token}")
        except HTTPException:
            await websocket.close(code=4401)
            return

    await websocket.accept()
    upstream_url = f"{settings.booking_ws_base_url}/ws/shows/{show_id}"

    try:
        async with websockets.connect(upstream_url) as upstream_ws:
            async def client_to_upstream() -> None:
                while True:
                    msg = await websocket.receive_text()
                    await upstream_ws.send(msg)

            async def upstream_to_client() -> None:
                while True:
                    msg = await upstream_ws.recv()
                    await websocket.send_text(msg)

            tasks = [
                asyncio.create_task(client_to_upstream()),
                asyncio.create_task(upstream_to_client()),
            ]
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc and not isinstance(exc, WebSocketDisconnect):
                    raise exc
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close(code=1011)