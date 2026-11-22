from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.booking import BookingStatus


class SeatStateItem(BaseModel):
    seat_id: str
    status: str  # AVAILABLE | HELD | CONFIRMED
    holder_id: str | None = None


class SeatMapResponse(BaseModel):
    show_id: str
    hall_id: str
    seats: dict[str, str]  # seat_id -> AVAILABLE | HELD | CONFIRMED


class HoldSeatsRequest(BaseModel):
    show_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    seats: list[str] = Field(..., min_length=1, max_length=10)
    tier: str = Field(..., min_length=1)


class HoldSeatsResponse(BaseModel):
    booking_id: str
    show_id: str
    user_id: str
    seats: list[str]
    tier: str
    total_amount: Decimal
    currency: str = "INR"
    status: BookingStatus
    hold_expires_at: datetime


class ReleaseBookingRequest(BaseModel):
    booking_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class ReleaseBookingResponse(BaseModel):
    booking_id: str
    status: BookingStatus
    released_seats: list[str]