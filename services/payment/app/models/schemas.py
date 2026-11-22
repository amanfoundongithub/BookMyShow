from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field
from app.models.transaction import TransactionStatus


class CreatePaymentIntentRequest(BaseModel):
    booking_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="INR", min_length=3, max_length=3)
    payment_gateway: str = Field(default="MOCK_GATEWAY", min_length=1)


class PaymentIntentResponse(BaseModel):
    payment_id: str
    booking_id: str
    idempotency_key: str
    amount: Decimal
    currency: str
    status: TransactionStatus
    payment_gateway: str
    gateway_reference: str
    created_at: datetime


class PaymentWebhookRequest(BaseModel):
    payment_id: str = Field(..., min_length=1)
    booking_id: str = Field(..., min_length=1)
    gateway_reference: str = Field(..., min_length=1)
    event_status: Literal["SUCCESS", "FAILED"]
    failure_reason: str | None = None


class PaymentWebhookResponse(BaseModel):
    payment_id: str
    booking_id: str
    status: TransactionStatus
    published_routing_key: str