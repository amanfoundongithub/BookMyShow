from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from bms_common.headers import CORRELATION_ID_HEADER, IDEMPOTENCY_KEY_HEADER
from app.core.config import get_settings
from app.core.db import get_database
from app.models.schemas import (
    CreatePaymentIntentRequest,
    PaymentIntentResponse,
    PaymentWebhookRequest,
    PaymentWebhookResponse,
)
from app.services.gateway_client import MockPaymentGatewayClient
from app.services.payment_service import PaymentService, TransactionNotFoundError

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post(
    "/create-intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment_intent(
    payload: CreatePaymentIntentRequest,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
    db=Depends(get_database),
) -> PaymentIntentResponse:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required {IDEMPOTENCY_KEY_HEADER} header",
        )
    service = PaymentService(db=db)
    return await service.create_intent(payload=payload, idempotency_key=idempotency_key.strip())


@router.post("/webhook", response_model=PaymentWebhookResponse)
async def payment_webhook(
    payload: PaymentWebhookRequest,
    request: Request,
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    db=Depends(get_database),
) -> PaymentWebhookResponse:
    settings = get_settings()
    raw_body = await request.body()
    gateway = MockPaymentGatewayClient()
    if not gateway.verify_signature(raw_body, x_webhook_signature, settings.webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    service = PaymentService(db=db, gateway_client=gateway)
    corr_id = request.headers.get(CORRELATION_ID_HEADER)
    try:
        return await service.handle_webhook(payload=payload, correlation_id=corr_id)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc