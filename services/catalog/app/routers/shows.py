from fastapi import APIRouter, Depends, Query, status
from app.core.db import get_database
from app.models.schemas import CreateShowRequest, ShowResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/api/v1/catalog/shows", tags=["shows"])


@router.get("", response_model=list[ShowResponse])
async def get_shows(
    movie_id: str = Query(..., min_length=1),
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    city: str = Query(..., min_length=1),
    db=Depends(get_database),
) -> list[ShowResponse]:
    return await CatalogService(db).list_shows(
        movie_id=movie_id, date_str=date, city_id=city
    )


@router.post("", response_model=ShowResponse, status_code=status.HTTP_201_CREATED)
async def create_show(
    payload: CreateShowRequest,
    db=Depends(get_database),
) -> ShowResponse:
    return await CatalogService(db).create_show(payload)