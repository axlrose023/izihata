from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.api.modules.checkout.models import Promotion


@pytest.mark.asyncio
async def test_promotion_time_window_is_inclusive(uow):
    boundary = datetime.now(UTC)
    active = Promotion(
        code="BOUNDARY",
        discount_rate=Decimal("0.1000"),
        is_active=True,
        starts_at=boundary,
        ends_at=boundary,
    )
    expired = Promotion(
        code="EXPIRED-BOUNDARY",
        discount_rate=Decimal("0.1000"),
        is_active=True,
        starts_at=boundary - timedelta(days=1),
        ends_at=boundary - timedelta(microseconds=1),
    )
    uow.session.add_all([active, expired])
    await uow.commit()

    assert await uow.promotions.get_active_by_code("boundary", boundary) is not None
    assert await uow.promotions.get_active_by_code("expired-boundary", boundary) is None
