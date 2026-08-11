import asyncio
import uuid

import pytest
from sqlalchemy import delete, select

from app.api.common.exceptions import UnauthorizedError
from app.api.modules.auth.models import AuthSession
from app.api.modules.auth.service import (
    JwtService,
    LogoutSessionService,
    RefreshSessionService,
)
from app.api.modules.catalog.models import Product
from app.api.modules.checkout.service import PricingService
from app.api.modules.orders.models import Order
from app.api.modules.orders.schema import CreateOrderRequest, OrderResponse
from app.api.modules.orders.service import OrderCreationService
from app.api.modules.outbox.models import OutboxEvent
from app.api.modules.users.models import User
from app.database.engine import SessionFactory
from app.database.uow import UnitOfWork
from app.settings import get_config

pytestmark = pytest.mark.integration


async def create_test_order(idempotency_key: str) -> OrderResponse:
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        product_id = (
            await session.execute(select(Product.id).where(Product.sku == "AX-10001"))
        ).scalar_one()
        request = CreateOrderRequest.model_validate(
            {
                "items": [{"product_id": str(product_id), "quantity": 1}],
                "customer_name": "Postgres Test",
                "phone": "+380671234567",
                "delivery": {"method": "pickup"},
                "payment_method": "cash_on_delivery",
            }
        )
        service = OrderCreationService(uow, PricingService(uow))
        return await service.create_order(request, idempotency_key)


@pytest.mark.asyncio(loop_scope="session")
async def test_skip_locked_prevents_two_workers_from_claiming_same_event():
    event_ids = []
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        for sequence in range(2):
            event = await uow.outbox.add(
                f"integration.skip-locked.{sequence}",
                {"sequence": sequence},
            )
            event_ids.append(event.id)
        await uow.commit()

    async with (
        SessionFactory() as first_session,
        SessionFactory() as second_session,
        UnitOfWork(first_session) as first_uow,
        UnitOfWork(second_session) as second_uow,
    ):
        first_claim = await first_uow.outbox.claim_pending(limit=1)
        second_claim = await second_uow.outbox.claim_pending(limit=10)

        first_ids = {event.id for event in first_claim}
        second_ids = {event.id for event in second_claim}
        assert first_ids
        assert set(event_ids) <= first_ids | second_ids
        assert first_ids.isdisjoint(second_ids)

        await first_uow.rollback()
        await second_uow.rollback()

    async with SessionFactory() as cleanup_session:
        await cleanup_session.execute(
            delete(OutboxEvent).where(OutboxEvent.id.in_(event_ids))
        )
        await cleanup_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_idempotent_order_creation_returns_one_order():
    idempotency_key = f"integration-{uuid.uuid4()}"
    first, second = await asyncio.gather(
        create_test_order(idempotency_key),
        create_test_order(idempotency_key),
    )

    assert first.id == second.id
    async with SessionFactory() as session:
        order_count = len(
            (
                await session.execute(
                    select(Order.id).where(Order.idempotency_key == idempotency_key)
                )
            )
            .scalars()
            .all()
        )
        assert order_count == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_admin_order_lock_serializes_concurrent_changes():
    order = await create_test_order(f"integration-lock-{uuid.uuid4()}")
    order_id = order.id

    async def acquire_same_order():
        async with SessionFactory() as session, UnitOfWork(session) as uow:
            return await uow.orders.get_by_id_for_update(order_id)

    async with SessionFactory() as session, UnitOfWork(session) as uow:
        locked = await uow.orders.get_by_id_for_update(order_id)
        assert locked is not None
        waiting = asyncio.create_task(acquire_same_order())
        await asyncio.sleep(0.1)
        assert not waiting.done()
        await uow.rollback()

    acquired = await asyncio.wait_for(waiting, timeout=2)
    assert acquired is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_rotation_allows_only_one_concurrent_use():
    jwt_service = JwtService(get_config())
    unused_password_hash = uuid.uuid4().hex
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        user = User(
            username=f"integration-{uuid.uuid4()}",
            password_hash=unused_password_hash,
            is_active=True,
        )
        await uow.users.create(user)
        auth_session = AuthSession(
            user_id=user.id,
            refresh_jti=uuid.uuid4(),
            expires_at=jwt_service.get_refresh_expiration(),
        )
        await uow.auth_sessions.create(auth_session)
        token = jwt_service.create_token_pair(
            user,
            session_id=auth_session.id,
            refresh_jti=auth_session.refresh_jti,
            refresh_expires_at=auth_session.expires_at,
        ).refresh_token
        await uow.commit()

    async def rotate():
        async with SessionFactory() as session, UnitOfWork(session) as uow:
            return await RefreshSessionService(uow, jwt_service).refresh(token)

    results = await asyncio.gather(rotate(), rotate(), return_exceptions=True)

    assert sum(isinstance(result, UnauthorizedError) for result in results) == 1
    assert sum(not isinstance(result, BaseException) for result in results) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_logout_wins_when_racing_with_refresh():
    jwt_service = JwtService(get_config())
    async with SessionFactory() as session, UnitOfWork(session) as uow:
        user = User(
            username=f"logout-race-{uuid.uuid4()}",
            password_hash=uuid.uuid4().hex,
            is_active=True,
        )
        await uow.users.create(user)
        auth_session = AuthSession(
            user_id=user.id,
            refresh_jti=uuid.uuid4(),
            expires_at=jwt_service.get_refresh_expiration(),
        )
        await uow.auth_sessions.create(auth_session)
        token = jwt_service.create_token_pair(
            user,
            session_id=auth_session.id,
            refresh_jti=auth_session.refresh_jti,
            refresh_expires_at=auth_session.expires_at,
        ).refresh_token
        auth_session_id = auth_session.id
        await uow.commit()

    async def rotate():
        async with SessionFactory() as session, UnitOfWork(session) as uow:
            return await RefreshSessionService(uow, jwt_service).refresh(token)

    async def logout():
        async with SessionFactory() as session, UnitOfWork(session) as uow:
            return await LogoutSessionService(uow, jwt_service).logout(token)

    await asyncio.gather(rotate(), logout(), return_exceptions=True)

    async with SessionFactory() as session:
        revoked_session = await session.get(AuthSession, auth_session_id)
        assert revoked_session is not None
        assert revoked_session.revoked_at is not None
