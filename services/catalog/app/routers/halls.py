from fastapi import APIRouter, Depends, HTTPException, Path, status
from app.core.db import get_database
from app.models.schemas import HallLayoutResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/api/v1/catalog/halls", tags=["halls"])


@router.get("/{hall_id}/layout", response_model=HallLayoutResponse)
async def get_hall_layout(
    hall_id: str = Path(..., min_length=1),
    db=Depends(get_database),
) -> HallLayoutResponse:
    layout = await CatalogService(db).get_hall_layout(hall_id=hall_id)
    if layout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hall '{hall_id}' not found",
        )
    return layout