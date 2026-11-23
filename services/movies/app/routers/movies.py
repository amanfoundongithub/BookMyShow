from fastapi import APIRouter, Depends, Header, Query, status
from app.core.db import get_database
from app.models.schemas import (
    ContentRating,
    MovieCreate,
    MovieFormat,
    MovieLanguage,
    MovieResponse,
    MovieUpdate,
)
from app.services.movie_service import MovieService

router = APIRouter(prefix="/api/v1/movies", tags=["movies"])


def get_movie_service(db=Depends(get_database)) -> MovieService:
    return MovieService(db=db)


@router.get("/meta", summary="List supported movie enums")
async def get_movie_enums() -> dict[str, list[str]]:
    return {
        "languages": [item.value for item in MovieLanguage],
        "formats": [item.value for item in MovieFormat],
        "ratings": [item.value for item in ContentRating],
    }


@router.get("", response_model=list[MovieResponse])
async def list_movies(
    city: str | None = Query(default=None, min_length=1),
    city_id: str | None = Query(default=None, min_length=1),
    language: str | None = Query(default=None, min_length=1),
    format: str | None = Query(default=None, min_length=1),
    active_only: bool = Query(default=True),
    service: MovieService = Depends(get_movie_service),
) -> list[MovieResponse]:
    return await service.list_movies(
        city_id=city_id or city,
        language=language,
        movie_format=format,
        active_only=active_only,
    )


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: str,
    service: MovieService = Depends(get_movie_service),
) -> MovieResponse:
    return await service.get_movie(movie_id=movie_id)


@router.post("", response_model=MovieResponse, status_code=status.HTTP_201_CREATED)
async def create_movie(
    payload: MovieCreate,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    service: MovieService = Depends(get_movie_service),
) -> MovieResponse:
    return await service.create_movie(payload=payload, user_role=x_user_role)


@router.patch("/{movie_id}", response_model=MovieResponse)
async def update_movie(
    movie_id: str,
    payload: MovieUpdate,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    service: MovieService = Depends(get_movie_service),
) -> MovieResponse:
    return await service.update_movie(
        movie_id=movie_id,
        payload=payload,
        user_role=x_user_role,
    )


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: str,
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    service: MovieService = Depends(get_movie_service),
) -> None:
    await service.delete_movie(movie_id=movie_id, user_role=x_user_role)
