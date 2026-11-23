from datetime import date
from enum import StrEnum
from pydantic import BaseModel, Field


class MovieLanguage(StrEnum):
    ENGLISH = "English"
    HINDI = "Hindi"
    TELUGU = "Telugu"
    TAMIL = "Tamil"
    KANNADA = "Kannada"
    MALAYALAM = "Malayalam"


class MovieFormat(StrEnum):
    TWO_D = "2D"
    THREE_D = "3D"
    IMAX_2D = "IMAX 2D"
    IMAX_3D = "IMAX 3D"
    FOUR_DX = "4DX"
    DOLBY_ATMOS = "Dolby Atmos"


class ContentRating(StrEnum):
    U = "U"
    UA = "UA"
    A = "A"
    S = "S"


class MovieBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    duration_minutes: int = Field(..., gt=0, le=600)
    rating: ContentRating = ContentRating.UA
    languages: list[MovieLanguage] = Field(default_factory=lambda: [MovieLanguage.ENGLISH])
    formats: list[MovieFormat] = Field(default_factory=lambda: [MovieFormat.TWO_D])
    synopsis: str | None = None
    city_ids: list[str] = Field(default_factory=list)
    release_date: date | None = None
    poster_url: str | None = None
    is_active: bool = True


class MovieCreate(MovieBase):
    id: str | None = Field(default=None, min_length=2, max_length=80)


class MovieUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, gt=0, le=600)
    rating: ContentRating | None = None
    languages: list[MovieLanguage] | None = None
    formats: list[MovieFormat] | None = None
    synopsis: str | None = None
    city_ids: list[str] | None = None
    release_date: date | None = None
    poster_url: str | None = None
    is_active: bool | None = None


class MovieResponse(MovieBase):
    id: str
