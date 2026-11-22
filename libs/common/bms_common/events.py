from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field


class EventRoutingKey(str, Enum):
    BOOKING_CREATED = "booking.created"
    BOOKING_EXPIRED = "booking.expired"
    BOOKING_CONFIRMED = "booking.confirmed"
    BOOKING_CANCELLED = "booking.cancelled"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None


class BookingCreatedEvent(BaseEvent):
    event_type: Literal["booking.created"] = "booking.created"
    booking_id: str
    user_id: str
    show_id: str
    seats: list[str]
    tier: str
    total_amount: Decimal
    currency: str = "INR"
    hold_expires_at: datetime


class BookingExpiredEvent(BaseEvent):
    event_type: Literal["booking.expired"] = "booking.expired"
    booking_id: str
    user_id: str
    show_id: str
    seats: list[str]


class PaymentCompletedEvent(BaseEvent):
    event_type: Literal["payment.completed"] = "payment.completed"
    payment_id: str
    booking_id: str
    user_id: str
    amount: Decimal
    currency: str = "INR"
    gateway_reference: str


class PaymentFailedEvent(BaseEvent):
    event_type: Literal["payment.failed"] = "payment.failed"
    payment_id: str
    booking_id: str
    user_id: str
    reason: str