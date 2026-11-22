from decimal import Decimal
from uuid import uuid4


class MockPaymentGatewayClient:
    async def create_order(
        self, booking_id: str, amount: Decimal, currency: str
    ) -> str:
        return f"mock_pay_{booking_id}_{uuid4().hex[:8]}"

    def verify_signature(self, payload_raw: bytes, signature: str | None, secret: str) -> bool:
        if not signature:
            return False
        return signature == secret