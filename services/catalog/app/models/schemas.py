from datetime import datetime
from pydantic import BaseModel, Field


class CinemaResponse(BaseModel):
    cinema_id: str
    name: str
    city_id: str
    state: str | None = None
    address: str
    amenities: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime


class ShowResponse(BaseModel):
    id: str
    movie_id: str
    cinema: CinemaResponse | None = None
    hall_id: str
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    pricing: dict[str, float]


class CreateShowRequest(BaseModel):
    id: str
    movie_id: str
    cinema_id: str
    hall_id: str
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    pricing: dict[str, float]


class CreateShowResponse(BaseModel):
    id: str
    movie_id: str
    cinema_id: str
    hall_id: str
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    pricing: dict[str, float]