import logging
from typing import Any
from app.services.ticket_renderer import TicketRenderer

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(self, renderer: TicketRenderer | None = None) -> None:
        self.renderer = renderer or TicketRenderer()

    async def dispatch(self, routing_key: str, payload: dict[str, Any]) -> None:
        user_id = payload.get("user_id", "unknown")
        booking_id = payload.get("booking_id", "unknown")

        if routing_key == "payment.completed":
            rendered = self.renderer.render_confirmation(payload)
            logger.info(
                "Dispatched ticket confirmation to user=%s booking=%s sms='%s'",
                user_id,
                booking_id,
                rendered["sms_text"],
            )
        elif routing_key == "payment.failed":
            logger.info(
                "Dispatched payment failure notice to user=%s booking=%s reason=%s",
                user_id,
                booking_id,
                payload.get("reason", "UNKNOWN"),
            )
        elif routing_key == "booking.expired":
            logger.info(
                "Dispatched seat hold expiry notice to user=%s booking=%s",
                user_id,
                booking_id,
            )
        elif routing_key == "booking.created":
            logger.debug(
                "Recorded booking hold created event for user=%s booking=%s",
                user_id,
                booking_id,
            )
        else:
            logger.warning("Unhandled notification routing key: %s", routing_key)