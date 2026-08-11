from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.auth.models import AuthSession
from app.api.modules.users.models import User


class AuthSessionGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, auth_session: AuthSession) -> AuthSession:
        self._session.add(auth_session)
        await self._session.flush()
        return auth_session

    async def get_for_update(self, session_id: UUID) -> AuthSession | None:
        stmt = select(AuthSession).where(AuthSession.id == session_id).with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_active_user(
        self,
        session_id: UUID,
        user_id: UUID,
        now: datetime,
    ) -> User | None:
        stmt = (
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                User.is_active.is_(True),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def delete_expired(self, now: datetime) -> int:
        stmt = (
            delete(AuthSession)
            .where(AuthSession.expires_at <= now)
            .returning(AuthSession.id)
        )
        result = await self._session.execute(stmt)
        return len(result.scalars().all())
