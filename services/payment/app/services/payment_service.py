from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorDatabase
from bms_common.events import (
    EventRoutingKey,
    PaymentCompletedEvent,
    PaymentFailedEvent,
)
from app.core.mq import publish_payment_event
from app.models.schemas import (
    CreatePaymentIntentRequest,
    PaymentIntentResponse,
    PaymentWebhookRequest,
    PaymentWebhookResponse,
)
from app.models.transaction import TransactionStatus
from app.services.gateway_client import MockPaymentGatewayClient


class TransactionNotFoundError(Exception):
    pass


class PaymentService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        gateway_client: MockPaymentGatewayClient | None = None,
    ) -> None:
        self.db = db
        self.gateway = gateway_client or MockPaymentGatewayClient()

    @staticmethod
    def _to_response(doc: dict) -> PaymentIntentResponse:
        return PaymentIntentResponse(
            payment_id=doc["_id"],
            booking_id=doc["booking_id"],
            idempotency_key=doc["idempotency_key"],
            amount=Decimal(str(doc["amount"])),
            currency=doc.get("currency", "INR"),
            status=TransactionStatus(doc["status"]),
            payment_gateway=doc.get("payment_gateway", "MOCK_GATEWAY"),
            gateway_reference=doc["gateway_reference"],
            created_at=doc["created_at"],
        )

    async def create_intent(
        self,
        payload: CreatePaymentIntentRequest,
        idempotency_key: str,
    ) -> PaymentIntentResponse:
        existing = await self.db.transactions.find_one(
            {"idempotency_key": idempotency_key}
        )
        if existing:
            return self._to_response(existing)

        payment_id = f"txn_{uuid4().hex[:12]}"
        gateway_ref = await self.gateway.create_order(
            booking_id=payload.booking_id,
            amount=payload.amount,
            currency=payload.currency,
        )
        now = datetime.now(timezone.utc)
        doc = {
            "_id": payment_id,
            "booking_id": payload.booking_id,
            "user_id": payload.user_id,
            "idempotency_key": idempotency_key,
            "amount": float(payload.amount.quantize(Decimal("0.01"))),
            "currency": payload.currency,
            "status": TransactionStatus.PENDING.value,
            "payment_gateway": payload.payment_gateway,
            "gateway_reference": gateway_ref,
            "created_at": now,
        }
        try:
            await self.db.transactions.insert_one(doc)
        except DuplicateKeyError:
            concurrent = await self.db.transactions.find_one(
                {"idempotency_key": idempotency_key}
            )
            if concurrent:
                return self._to_response(concurrent)
            raise

        return self._to_response(doc)

    async def handle_webhook(
        self,
        payload: PaymentWebhookRequest,
        correlation_id: str | None = None,
    ) -> PaymentWebhookResponse:
        txn = await self.db.transactions.find_one({"_id": payload.payment_id})
        if not txn:
            raise TransactionNotFoundError(f"Transaction {payload.payment_id} not found")

        new_status = (
            TransactionStatus.SUCCESS
            if payload.event_status == "SUCCESS"
            else TransactionStatus.FAILED
        )

        # Idempotent transition: if already settled in same target state, avoid duplicate events
        if txn.get("status") != new_status.value:
            await self.db.transactions.update_one(
                {"_id": payload.payment_id},
                {
                    "$set": {
                        "status": new_status.value,
                        "gateway_reference": payload.gateway_reference,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

        amount = Decimal(str(txn["amount"]))
        user_id = txn.get("user_id", "")
        currency = txn.get("currency", "INR")

        if new_status == TransactionStatus.SUCCESS:
            event = PaymentCompletedEvent(
                correlation_id=correlation_id,
                payment_id=payload.payment_id,
                booking_id=payload.booking_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                gateway_reference=payload.gateway_reference,
            )
            routing_key = EventRoutingKey.PAYMENT_COMPLETED.value
        else:
            event = PaymentFailedEvent(
                correlation_id=correlation_id,
                payment_id=payload.payment_id,
                booking_id=payload.booking_id,
                user_id=user_id,
                reason=payload.failure_reason or "PAYMENT_DECLINED",
            )
            routing_key = EventRoutingKey.PAYMENT_FAILED.value

        await publish_payment_event(routing_key, event.model_dump(mode="json"))

        return PaymentWebhookResponse(
            payment_id=payload.payment_id,
            booking_id=payload.booking_id,
            status=new_status,
            published_routing_key=routing_key,
        )