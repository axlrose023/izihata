from uuid import uuid4

from app.api.common.exceptions import UnauthorizedError
from app.api.common.security import password_matches
from app.api.modules.auth.models import AuthSession
from app.api.modules.auth.schema import LoginRequest, TokenPairResponse
from app.api.modules.auth.services.jwt import JwtService
from app.database.uow import UnitOfWork


class LoginService:
    def __init__(self, uow: UnitOfWork, jwt_service: JwtService):
        self._uow = uow
        self._jwt_service = jwt_service

    async def login(self, request: LoginRequest) -> TokenPairResponse:
        user = await self._uow.users.get_by_username(request.username)
        if user is None or not user.is_active:
            raise UnauthorizedError("Incorrect username or password")

        if not await password_matches(request.password, user.password_hash):
            raise UnauthorizedError("Incorrect username or password")

        refresh_expires_at = self._jwt_service.get_refresh_expiration()
        auth_session = AuthSession(
            id=uuid4(),
            user_id=user.id,
            refresh_jti=uuid4(),
            expires_at=refresh_expires_at,
        )
        token_pair = self._jwt_service.create_token_pair(
            user,
            session_id=auth_session.id,
            refresh_jti=auth_session.refresh_jti,
            refresh_expires_at=refresh_expires_at,
        )
        await self._uow.auth_sessions.create(auth_session)
        await self._uow.commit()
        return token_pair
