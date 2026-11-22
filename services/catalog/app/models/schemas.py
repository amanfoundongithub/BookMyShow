from datetime import datetime
from pydantic import BaseModel


class CityResponse(BaseModel):
    id: str
    name: str
    state: str
    country: str


class MovieResponse(BaseModel):
    id: str
    title: str
    duration_minutes: int
    rating: str
    languages: list[str]
    formats: list[str]


class ShowResponse(BaseModel):
    id: str
    movie_id: str
    cinema_id: str
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