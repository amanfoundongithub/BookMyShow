from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class CityDoc(BaseModel):
    id: str = Field(alias="_id")
    name: str
    state: str
    country: str = "India"


class CinemaDoc(BaseModel):
    id: str = Field(alias="_id")
    city_id: str
    name: str
    address: str


class SeatSlot(BaseModel):
    seat_number: int | None = None
    type: Literal["STANDARD", "AISLE", "WHEELCHAIR"] = "STANDARD"


class HallRow(BaseModel):
    row_label: str
    tier: str
    seats: list[SeatSlot]


class HallLayout(BaseModel):
    rows: list[HallRow]


class HallDoc(BaseModel):
    id: str = Field(alias="_id")
    cinema_id: str
    name: str
    total_seats: int
    layout: HallLayout


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