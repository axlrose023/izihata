from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.common.exceptions import UnauthorizedError
from app.api.modules.auth.service import JwtService
from app.api.modules.customers.models import Customer
from app.database.uow import UnitOfWork

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticateCustomer:
    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> Customer:
        if credentials is None:
            raise UnauthorizedError()
        customer = await self._get_customer(request, credentials.credentials)
        if customer is None:
            raise UnauthorizedError()
        return customer

    async def _get_customer(self, request: Request, token: str) -> Customer | None:
        container = request.state.dishka_container
        uow: UnitOfWork = await container.get(UnitOfWork)
        jwt_service: JwtService = await container.get(JwtService)
        payload = jwt_service.validate_access_token(token)
        if payload.get("actor") != "customer":
            raise UnauthorizedError()
        try:
            customer_id = UUID(payload["sub"])
            session_id = UUID(payload["sid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UnauthorizedError() from exc
        return await uow.customers.get_active_customer(
            session_id,
            customer_id,
            datetime.now(UTC),
        )


class OptionalAuthenticateCustomer:
    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> Customer | None:
        if credentials is None:
            return None
        return await AuthenticateCustomer()._get_customer(
            request, credentials.credentials
        )
