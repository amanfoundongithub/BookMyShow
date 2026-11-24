from datetime import date
from pydantic import BaseModel, Field


class MovieBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    duration_minutes: int = Field(..., gt=0, le=600)
    rating: str = "UA"
    languages: list[str] = Field(default_factory=lambda: ["English"])
    formats: list[str] = Field(default_factory=lambda: ["2D"])
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
    rating: str | None = None
    languages: list[str] | None = None
    formats: list[str] | None = None
    synopsis: str | None = None
    city_ids: list[str] | None = None
    release_date: date | None = None
    poster_url: str | None = None
    is_active: bool | None = None


class MovieResponse(MovieBase):
    id: str
