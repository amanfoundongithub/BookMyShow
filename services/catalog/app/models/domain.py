from datetime import datetime
from pydantic import BaseModel, Field


class CityDoc(BaseModel):
    id: str = Field(alias="_id")
    name: str
    state: str
    country: str = "India"


class MovieDoc(BaseModel):
    id: str = Field(alias="_id")
    title: str
    duration_minutes: int
    rating: str
    languages: list[str]
    formats: list[str]


class ShowDoc(BaseModel):
    id: str = Field(alias="_id")
    movie_id: str
    cinema_id: str
    hall_id: str
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    pricing: dict[str, float]