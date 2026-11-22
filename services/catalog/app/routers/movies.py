from fastapi import APIRouter, Depends, Query
from app.core.db import get_database
from app.models.schemas import MovieResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/api/v1/catalog/movies", tags=["movies"])


@router.get("", response_model=list[MovieResponse])
async def get_movies(
    city: str = Query(..., min_length=1),
    db=Depends(get_database),
) -> list[MovieResponse]:
    return await CatalogService(db).list_movies_by_city(city_id=city)