from datetime import UTC, datetime

from app.api.modules.auth.services.jwt import JwtService
from app.api.modules.auth.utils import parse_refresh_token_identity
from app.database.uow import UnitOfWork


class LogoutSessionService:
    def __init__(self, uow: UnitOfWork, jwt_service: JwtService):
        self._uow = uow
        self._jwt_service = jwt_service

    async def logout(self, refresh_token: str) -> None:
        payload = self._jwt_service.validate_refresh_token(refresh_token)
        if payload.get("actor") not in {None, "staff"}:
            return
        identity = parse_refresh_token_identity(payload)
        auth_session = await self._uow.auth_sessions.get_for_update(identity.session_id)

        # A signed token from the same session may already be rotated. It is still
        # allowed to revoke that session, which makes logout idempotent and safe
        # when it races with an in-flight refresh.
        if auth_session is None or auth_session.user_id != identity.user_id:
            return
        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(UTC)
            await self._uow.commit()
