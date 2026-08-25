from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import ConflictError, UnauthorizedError
from app.api.common.security import hash_password, is_expired, password_matches
from app.api.modules.auth.schema import TokenPairResponse
from app.api.modules.auth.service import JwtService
from app.api.modules.customers.models import Customer, CustomerAuthSession
from app.api.modules.customers.schema import (
    CustomerLoginRequest,
    CustomerRegistrationRequest,
)
from app.api.modules.customers.utils import (
    parse_customer_refresh_identity,
)
from app.database.uow import UnitOfWork


class CustomerAuthenticationService:
    def __init__(self, uow: UnitOfWork, jwt_service: JwtService):
        self._uow = uow
        self._jwt_service = jwt_service

    async def register(self, request: CustomerRegistrationRequest) -> TokenPairResponse:
        if await self._uow.customers.get_by_email(request.email) is not None:
            raise ConflictError(
                "Customer email already exists", code="customer_email_exists"
            )
        customer = Customer(
            email=request.email,
            password_hash=await hash_password(request.password),
            full_name=request.full_name,
            phone=request.phone,
        )
        try:
            await self._uow.customers.create(customer)
            tokens = await self._create_session_tokens(customer)
            await self._uow.commit()
        except IntegrityError as exc:
            await self._uow.rollback()
            raise ConflictError(
                "Customer email already exists",
                code="customer_email_exists",
            ) from exc
        return tokens

    async def login(self, request: CustomerLoginRequest) -> TokenPairResponse:
        customer = await self._uow.customers.get_by_email(request.email)
        if (
            customer is None
            or not customer.is_active
            or not await password_matches(request.password, customer.password_hash)
        ):
            raise UnauthorizedError("Incorrect email or password")
        tokens = await self._create_session_tokens(customer)
        await self._uow.commit()
        return tokens

    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        payload = self._jwt_service.validate_refresh_token(refresh_token)
        if payload.get("actor") != "customer":
            raise UnauthorizedError("Invalid refresh token audience")
        identity = parse_customer_refresh_identity(payload)
        auth_session = await self._uow.customers.get_session_for_update(
            identity.session_id
        )
        now = datetime.now(UTC)
        if (
            auth_session is None
            or auth_session.customer_id != identity.customer_id
            or auth_session.refresh_jti != identity.refresh_jti
            or auth_session.revoked_at is not None
            or is_expired(auth_session.expires_at, now)
        ):
            raise UnauthorizedError("Refresh session is not active")
        customer = await self._uow.customers.get_by_id(identity.customer_id)
        if customer is None or not customer.is_active:
            raise UnauthorizedError("Customer is not allowed")

        auth_session.refresh_jti = uuid4()
        auth_session.expires_at = self._jwt_service.get_refresh_expiration()
        tokens = self._jwt_service.create_token_pair_for_subject(
            subject_id=customer.id,
            session_id=auth_session.id,
            refresh_jti=auth_session.refresh_jti,
            refresh_expires_at=auth_session.expires_at,
            actor="customer",
        )
        await self._uow.commit()
        return tokens

    async def logout(self, refresh_token: str) -> None:
        payload = self._jwt_service.validate_refresh_token(refresh_token)
        if payload.get("actor") != "customer":
            return
        identity = parse_customer_refresh_identity(payload)
        auth_session = await self._uow.customers.get_session_for_update(
            identity.session_id
        )
        if auth_session is None or auth_session.customer_id != identity.customer_id:
            return
        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(UTC)
            await self._uow.commit()

    async def _create_session_tokens(self, customer: Customer) -> TokenPairResponse:
        refresh_expires_at = self._jwt_service.get_refresh_expiration()
        auth_session = CustomerAuthSession(
            id=uuid4(),
            customer_id=customer.id,
            refresh_jti=uuid4(),
            expires_at=refresh_expires_at,
        )
        await self._uow.customers.create_session(auth_session)
        return self._jwt_service.create_token_pair_for_subject(
            subject_id=customer.id,
            session_id=auth_session.id,
            refresh_jti=auth_session.refresh_jti,
            refresh_expires_at=refresh_expires_at,
            actor="customer",
        )
