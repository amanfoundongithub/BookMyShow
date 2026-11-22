from decimal import Decimal
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from bms_common.headers import CORRELATION_ID_HEADER, USER_ID_HEADER
from app.core.config import get_settings
from app.core.db import get_database
from app.core.redis import get_redis
from app.models.schemas import (
    BookingSummaryResponse,
    HoldSeatsRequest,
    HoldSeatsResponse,
    ReleaseBookingRequest,
    ReleaseBookingResponse,
    SeatMapResponse,
)
from app.redis_lock import SeatLockManager
from app.services.booking_service import (
    BookingNotFoundError,
    BookingService,
    InvalidBookingStateError,
    SeatConflictError,
)
from app.ws_manager import ShowWsManager

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


def get_ws_manager(request: Request) -> ShowWsManager:
    return request.app.state.ws_manager


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def _build_service(request: Request, db) -> BookingService:
    settings = get_settings()
    redis = get_redis()
    lock_manager = SeatLockManager(redis=redis, ttl_seconds=settings.seat_hold_ttl_seconds)
    ws_manager = get_ws_manager(request)
    http_client = get_http_client(request)
    return BookingService(
        db=db,
        lock_manager=lock_manager,
        ws_manager=ws_manager,
        http_client=http_client,
    )


@router.get("", response_model=list[BookingSummaryResponse])
async def list_bookings(
    request: Request,
    user_id: str | None = Query(default=None, min_length=1),
    x_user_id: str | None = Header(default=None, alias=USER_ID_HEADER),
    limit: int = Query(default=50, ge=1, le=200),
    db=Depends(get_database),
) -> list[BookingSummaryResponse]:
    resolved_user_id = user_id or x_user_id
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id query parameter or X-User-ID header is required",
        )
    service = _build_service(request, db)
    return await service.list_user_bookings(user_id=resolved_user_id, limit=limit)


@router.get("/shows/{show_id}/seat-map", response_model=SeatMapResponse)
async def get_seat_map(
    show_id: str,
    request: Request,
    hall_id: str = Query(..., min_length=1),
    db=Depends(get_database),
) -> SeatMapResponse:
    service = _build_service(request, db)
    return await service.get_seat_map(show_id=show_id, hall_id=hall_id)


@router.post("/hold", response_model=HoldSeatsResponse, status_code=status.HTTP_201_CREATED)
async def hold_seats(
    payload: HoldSeatsRequest,
    request: Request,
    tier_price: Decimal = Query(default=Decimal("250.00"), gt=Decimal("0")),
    db=Depends(get_database),
) -> HoldSeatsResponse:
    service = _build_service(request, db)
    corr_id = request.headers.get(CORRELATION_ID_HEADER)
    try:
        return await service.hold_seats(payload=payload, tier_price=tier_price, correlation_id=corr_id)
    except SeatConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Seat {exc.seat_id} unavailable ({exc.reason})",
        ) from exc


@router.post("/release", response_model=ReleaseBookingResponse)
async def release_booking(
    payload: ReleaseBookingRequest,
    request: Request,
    db=Depends(get_database),
) -> ReleaseBookingResponse:
    service = _build_service(request, db)
    try:
        return await service.release_booking(payload=payload)
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidBookingStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc