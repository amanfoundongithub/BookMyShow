from pathlib import Path
from typing import Any

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class TicketRenderer:
    def __init__(self, templates_dir: Path = _TEMPLATES_DIR) -> None:
        self._email_tpl = (templates_dir / "ticket_email.html").read_text(encoding="utf-8")
        self._sms_tpl = (templates_dir / "ticket_sms.txt").read_text(encoding="utf-8")

    def render_confirmation(self, payload: dict[str, Any]) -> dict[str, str]:
        seats = payload.get("seats", [])
        seats_str = ", ".join(seats) if isinstance(seats, list) else str(seats)
        context = {
            "booking_id": str(payload.get("booking_id", "")),
            "show_id": str(payload.get("show_id", "")),
            "seats": seats_str,
            "currency": str(payload.get("currency", "INR")),
            "amount": str(payload.get("amount", "")),
            "gateway_reference": str(payload.get("gateway_reference", "")),
        }
        html = self._email_tpl
        sms = self._sms_tpl
        for key, value in context.items():
            html = html.replace(f"{{{{ {key} }}}}", value)
            sms = sms.replace(f"{{{{ {key} }}}}", value)
        return {"email_html": html.strip(), "sms_text": sms.strip()}