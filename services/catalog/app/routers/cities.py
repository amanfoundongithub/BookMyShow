from fastapi import APIRouter, Depends
from app.core.db import get_database
from app.models.schemas import CityResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/api/v1/catalog/cities", tags=["cities"])


@router.get("", response_model=list[CityResponse])
async def get_cities(db=Depends(get_database)) -> list[CityResponse]:
    return await CatalogService(db).list_cities()