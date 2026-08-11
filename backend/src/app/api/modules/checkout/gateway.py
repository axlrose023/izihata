from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.checkout.models import Promotion


class PromotionGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_active_by_code(
        self,
        code: str,
        now: datetime,
    ) -> Promotion | None:
        stmt = select(Promotion).where(
            Promotion.code == code.upper(),
            Promotion.is_active.is_(True),
            or_(Promotion.starts_at.is_(None), Promotion.starts_at <= now),
            or_(Promotion.ends_at.is_(None), Promotion.ends_at >= now),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
