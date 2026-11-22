from fastapi import APIRouter, Depends, Header, Query, Request, status
import httpx
from app.core.db import get_database
from app.models.schemas import (
    CreateHallRequest,
    HallResponse,
    UpdateHallLayoutRequest,
)
from app.services.hall_service import HallService

router = APIRouter(prefix="/api/v1/halls", tags=["halls"])


def _parse_cinema_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_http_client(request: Request) -> httpx.AsyncClient | None:
    return getattr(request.app.state, "http_client", None)


def get_hall_service(
    request: Request,
    db=Depends(get_database),
) -> HallService:
    return HallService(db=db, http_client=get_http_client(request))


@router.get("", response_model=list[HallResponse])
async def list_halls(
    cinema_id: str | None = Query(default=None),
    service: HallService = Depends(get_hall_service),
) -> list[HallResponse]:
    return await service.list_halls(cinema_id=cinema_id)


@router.get("/{hall_id}", response_model=HallResponse)
async def get_hall(
    hall_id: str,
    service: HallService = Depends(get_hall_service),
) -> HallResponse:
    return await service.get_hall(hall_id=hall_id)


@router.get("/{hall_id}/layout", response_model=HallResponse)
async def get_hall_layout(
    hall_id: str,
    service: HallService = Depends(get_hall_service),
) -> HallResponse:
    return await service.get_hall(hall_id=hall_id)


@router.post("", response_model=HallResponse, status_code=status.HTTP_201_CREATED)
async def create_hall(
    payload: CreateHallRequest,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_cinema_ids: str | None = Header(default=None, alias="X-Cinema-Ids"),
    service: HallService = Depends(get_hall_service),
) -> HallResponse:
    return await service.create_hall(
        payload=payload,
        user_role=x_user_role,
        allowed_cinema_ids=_parse_cinema_ids(x_cinema_ids),
    )


@router.put("/{hall_id}/layout", response_model=HallResponse)
async def update_hall_layout(
    hall_id: str,
    payload: UpdateHallLayoutRequest,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_cinema_ids: str | None = Header(default=None, alias="X-Cinema-Ids"),
    service: HallService = Depends(get_hall_service),
) -> HallResponse:
    return await service.update_hall_layout(
        hall_id=hall_id,
        payload=payload,
        user_role=x_user_role,
        allowed_cinema_ids=_parse_cinema_ids(x_cinema_ids),
    )