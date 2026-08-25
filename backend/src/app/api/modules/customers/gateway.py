from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.customers.enums import CompanyStatus
from app.api.modules.customers.models import (
    Customer,
    CustomerAuthSession,
    CustomerCompany,
)


class CustomerGateway:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, customer: Customer) -> Customer:
        self._session.add(customer)
        await self._session.flush()
        return customer

    async def get_by_email(self, email: str) -> Customer | None:
        stmt = select(Customer).where(Customer.email == email)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.id == customer_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_session(
        self, auth_session: CustomerAuthSession
    ) -> CustomerAuthSession:
        self._session.add(auth_session)
        await self._session.flush()
        return auth_session

    async def get_session_for_update(
        self,
        session_id: UUID,
    ) -> CustomerAuthSession | None:
        stmt = (
            select(CustomerAuthSession)
            .where(CustomerAuthSession.id == session_id)
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_active_customer(
        self,
        session_id: UUID,
        customer_id: UUID,
        now: datetime,
    ) -> Customer | None:
        stmt = (
            select(Customer)
            .join(CustomerAuthSession, CustomerAuthSession.customer_id == Customer.id)
            .where(
                CustomerAuthSession.id == session_id,
                CustomerAuthSession.customer_id == customer_id,
                CustomerAuthSession.revoked_at.is_(None),
                CustomerAuthSession.expires_at > now,
                Customer.is_active.is_(True),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def delete_expired_sessions(self, now: datetime) -> int:
        stmt = (
            delete(CustomerAuthSession)
            .where(CustomerAuthSession.expires_at <= now)
            .returning(CustomerAuthSession.id)
        )
        return len((await self._session.execute(stmt)).scalars().all())

    async def get_company_for_customer(
        self, customer_id: UUID
    ) -> CustomerCompany | None:
        stmt = select(CustomerCompany).where(CustomerCompany.customer_id == customer_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_company(self, company: CustomerCompany) -> CustomerCompany:
        self._session.add(company)
        await self._session.flush()
        return company

    async def has_approved_company(self, customer_id: UUID) -> bool:
        stmt = select(CustomerCompany.id).where(
            CustomerCompany.customer_id == customer_id,
            CustomerCompany.status == CompanyStatus.APPROVED,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def list_companies(
        self,
        *,
        offset: int,
        limit: int,
        status: CompanyStatus | None,
    ) -> Sequence[tuple[CustomerCompany, Customer]]:
        stmt = select(CustomerCompany, Customer).join(
            Customer,
            Customer.id == CustomerCompany.customer_id,
        )
        if status is not None:
            stmt = stmt.where(CustomerCompany.status == status)
        stmt = (
            stmt.order_by(CustomerCompany.created_at.desc(), CustomerCompany.id)
            .offset(offset)
            .limit(limit)
        )
        return [
            (company, customer)
            for company, customer in (await self._session.execute(stmt)).all()
        ]

    async def count_companies(self, status: CompanyStatus | None) -> int:
        stmt = select(func.count(CustomerCompany.id))
        if status is not None:
            stmt = stmt.where(CustomerCompany.status == status)
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_company_for_update(self, company_id: UUID) -> CustomerCompany | None:
        stmt = (
            select(CustomerCompany)
            .where(CustomerCompany.id == company_id)
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
