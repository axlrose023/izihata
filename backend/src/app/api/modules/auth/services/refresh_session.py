from datetime import UTC, datetime
from uuid import uuid4

from app.api.common.exceptions import UnauthorizedError
from app.api.modules.auth.schema import TokenPairResponse
from app.api.modules.auth.services.jwt import JwtService
from app.api.modules.auth.utils import is_expired, parse_refresh_token_identity
from app.database.uow import UnitOfWork


class RefreshSessionService:
    def __init__(self, uow: UnitOfWork, jwt_service: JwtService):
        self._uow = uow
        self._jwt_service = jwt_service

    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        payload = self._jwt_service.validate_refresh_token(refresh_token)
        identity = parse_refresh_token_identity(payload)

        auth_session = await self._uow.auth_sessions.get_for_update(identity.session_id)
        now = datetime.now(UTC)
        if (
            auth_session is None
            or auth_session.user_id != identity.user_id
            or auth_session.refresh_jti != identity.refresh_jti
            or auth_session.revoked_at is not None
            or is_expired(auth_session.expires_at, now)
        ):
            raise UnauthorizedError("Refresh session is not active")

        user = await self._uow.users.get_by_id(identity.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User is not allowed")

        new_refresh_jti = uuid4()
        refresh_expires_at = self._jwt_service.get_refresh_expiration()
        auth_session.refresh_jti = new_refresh_jti
        auth_session.expires_at = refresh_expires_at
        token_pair = self._jwt_service.create_token_pair(
            user,
            session_id=auth_session.id,
            refresh_jti=new_refresh_jti,
            refresh_expires_at=refresh_expires_at,
        )
        await self._uow.commit()
        return token_pair
