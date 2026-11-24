from fastapi import APIRouter, Depends, Header, Path, Query, Request, status
import httpx
from app.core.db import get_database
from app.models.schemas import CreateShowRequest, CreateShowResponse, ShowResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/api/v1/catalog/shows", tags=["shows"])


def _parse_cinema_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_service(request: Request, db) -> CatalogService:
    http_client: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    return CatalogService(db=db, http_client=http_client)


@router.get("", response_model=list[ShowResponse])
async def get_shows(
    request: Request,
    movie_id: str = Query(..., min_length=1),
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    city: str = Query(..., min_length=1),
    db=Depends(get_database),
) -> list[ShowResponse]:
    return await _get_service(request, db).list_shows(
        movie_id=movie_id, date_str=date, city_id=city
    )


@router.get("/{show_id}", response_model=ShowResponse)
async def get_show_by_id(
    request: Request,
    show_id: str = Path(..., min_length=1),
    db=Depends(get_database),
) -> ShowResponse:
    return await _get_service(request, db).get_show_by_id(show_id=show_id)


@router.post("", response_model=CreateShowResponse, status_code=status.HTTP_201_CREATED)
async def create_show(
    payload: CreateShowRequest,
    request: Request,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    x_cinema_ids: str | None = Header(default=None, alias="X-Cinema-Ids"),
    db=Depends(get_database),
) -> CreateShowResponse:
    return await _get_service(request, db).create_show(
        payload=payload,
        user_role=x_user_role,
        allowed_cinema_ids=_parse_cinema_ids(x_cinema_ids),
    )