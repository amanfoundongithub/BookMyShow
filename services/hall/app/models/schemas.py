from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

SeatType = Literal["STANDARD", "PREMIUM", "RECLINER", "AISLE"]


class SeatCell(BaseModel):
    seat_number: int | None = None
    type: SeatType = "STANDARD"
    tier: str = "STANDARD"


class SeatRow(BaseModel):
    row_label: str = Field(..., min_length=1, max_length=5)
    seats: list[SeatCell] = Field(default_factory=list)


class HallLayout(BaseModel):
    rows: list[SeatRow] = Field(default_factory=list)


class CreateHallRequest(BaseModel):
    cinema_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=80)
    screen_format: str = Field(default="2D", min_length=1, max_length=30)
    layout: HallLayout = Field(default_factory=HallLayout)


class UpdateHallLayoutRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    screen_format: str | None = Field(default=None, min_length=1, max_length=30)
    layout: HallLayout


class HallResponse(BaseModel):
    hall_id: str
    cinema_id: str
    name: str
    screen_format: str
    total_seats: int
    layout: HallLayout
    created_at: datetime