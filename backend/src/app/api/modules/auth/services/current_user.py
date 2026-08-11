from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.common.exceptions import UnauthorizedError
from app.api.modules.auth.services.jwt import JwtService
from app.api.modules.users.models import User
from app.database.uow import UnitOfWork

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticateUser:
    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> User:
        if credentials is None:
            raise UnauthorizedError()
        container = request.state.dishka_container
        uow: UnitOfWork = await container.get(UnitOfWork)
        jwt_service: JwtService = await container.get(JwtService)
        return await self.get_current_user(
            uow=uow,
            token=credentials.credentials,
            jwt_service=jwt_service,
        )

    async def get_current_user(
        self,
        uow: UnitOfWork,
        token: str,
        jwt_service: JwtService,
    ) -> User:
        payload = jwt_service.validate_access_token(token)
        try:
            user_id = UUID(payload["sub"])
            session_id = UUID(payload["sid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UnauthorizedError() from exc
        user = await uow.auth_sessions.get_active_user(
            session_id,
            user_id,
            datetime.now(UTC),
        )
        if user is None:
            raise UnauthorizedError()
        return user
