import hashlib
import json
import secrets
from datetime import UTC, datetime

from app.api.modules.orders.schema import CreateOrderRequest


def request_digest(request: CreateOrderRequest) -> str:
    payload = json.dumps(
        # Quote acknowledgment is not part of the business request. A retry
        # after a lost response must find the existing order even if prices
        # changed while the customer reloaded checkout.
        request.model_dump(mode="json", exclude={"expected_total"}),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def new_order_number() -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"IZI-{date_part}-{secrets.token_hex(5).upper()}"
