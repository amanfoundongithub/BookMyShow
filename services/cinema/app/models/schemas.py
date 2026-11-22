from datetime import datetime
from pydantic import BaseModel, Field


class CreateCinemaRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    city_id: str = Field(..., min_length=1)
    state: str | None = None
    address: str = Field(..., min_length=3, max_length=250)
    amenities: list[str] = Field(default_factory=list)


class UpdateCinemaRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    address: str | None = Field(default=None, min_length=3, max_length=250)
    amenities: list[str] | None = None
    is_active: bool | None = None


class CinemaResponse(BaseModel):
    cinema_id: str
    name: str
    city_id: str
    state: str | None = None
    address: str
    amenities: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime