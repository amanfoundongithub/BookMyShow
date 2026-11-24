from fastapi import APIRouter, Depends, Header, status
from app.core.db import get_database
from app.models.schemas import CityResponse, CreateCityRequest, UpdateCityRequest
from app.services.city_service import CityService

router = APIRouter(prefix="/api/v1/cities", tags=["cities"])


def get_city_service(db=Depends(get_database)) -> CityService:
    return CityService(db=db)


@router.get("", response_model=list[CityResponse])
async def list_cities(
    service: CityService = Depends(get_city_service),
) -> list[CityResponse]:
    return await service.list_cities()


@router.get("/{city_id}", response_model=CityResponse)
async def get_city(
    city_id: str,
    service: CityService = Depends(get_city_service),
) -> CityResponse:
    return await service.get_city(city_id=city_id)


@router.post("", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
async def create_city(
    payload: CreateCityRequest,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    service: CityService = Depends(get_city_service),
) -> CityResponse:
    return await service.create_city(payload=payload, user_role=x_user_role)


@router.patch("/{city_id}", response_model=CityResponse)
async def update_city(
    city_id: str,
    payload: UpdateCityRequest,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    service: CityService = Depends(get_city_service),
) -> CityResponse:
    return await service.update_city(
        city_id=city_id,
        payload=payload,
        user_role=x_user_role,
    )


@router.delete("/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_city(
    city_id: str,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    service: CityService = Depends(get_city_service),
) -> None:
    await service.delete_city(city_id=city_id, user_role=x_user_role)
