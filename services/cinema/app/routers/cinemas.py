from fastapi import APIRouter, Depends, Header, Query, status
from app.core.db import get_database
from app.models.schemas import (
    CinemaResponse,
    CreateCinemaRequest,
    UpdateCinemaRequest,
)
from app.services.cinema_service import CinemaService

router = APIRouter(prefix="/api/v1/cinemas", tags=["cinemas"])


def _parse_cinema_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_cinema_service(db=Depends(get_database)) -> CinemaService:
    return CinemaService(db=db)


@router.get("", response_model=list[CinemaResponse])
async def list_cinemas(
    city_id: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    service: CinemaService = Depends(get_cinema_service),
) -> list[CinemaResponse]:
    return await service.list_cinemas(city_id=city_id, include_inactive=include_inactive)


@router.get("/{cinema_id}", response_model=CinemaResponse)
async def get_cinema(
    cinema_id: str,
    service: CinemaService = Depends(get_cinema_service),
) -> CinemaResponse:
    return await service.get_cinema(cinema_id=cinema_id)


@router.post("", response_model=CinemaResponse, status_code=status.HTTP_201_CREATED)
async def create_cinema(
    payload: CreateCinemaRequest,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_cinema_ids: str | None = Header(default=None, alias="X-Cinema-Ids"),
    service: CinemaService = Depends(get_cinema_service),
) -> CinemaResponse:
    return await service.create_cinema(
        payload=payload,
        user_role=x_user_role,
        allowed_cinema_ids=_parse_cinema_ids(x_cinema_ids),
    )


@router.patch("/{cinema_id}", response_model=CinemaResponse)
async def update_cinema(
    cinema_id: str,
    payload: UpdateCinemaRequest,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_cinema_ids: str | None = Header(default=None, alias="X-Cinema-Ids"),
    service: CinemaService = Depends(get_cinema_service),
) -> CinemaResponse:
    return await service.update_cinema(
        cinema_id=cinema_id,
        payload=payload,
        user_role=x_user_role,
        allowed_cinema_ids=_parse_cinema_ids(x_cinema_ids),
    )