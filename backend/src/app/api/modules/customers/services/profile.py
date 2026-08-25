from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import ConflictError
from app.api.modules.customers.models import Customer, CustomerCompany
from app.api.modules.customers.schema import (
    CustomerCompanyRequest,
    CustomerCompanyResponse,
    CustomerProfileResponse,
)
from app.database.uow import UnitOfWork


class CustomerProfileService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def get_profile(self, customer: Customer) -> CustomerProfileResponse:
        company = await self._uow.customers.get_company_for_customer(customer.id)
        return CustomerProfileResponse.from_customer(customer, company)

    async def register_company(
        self,
        customer: Customer,
        request: CustomerCompanyRequest,
    ) -> CustomerCompanyResponse:
        if await self._uow.customers.get_company_for_customer(customer.id) is not None:
            raise ConflictError(
                "Customer company already exists",
                code="customer_company_exists",
            )
        company = CustomerCompany(
            customer_id=customer.id,
            kind=request.kind,
            name=request.name,
            edrpou=request.edrpou,
        )
        try:
            await self._uow.customers.create_company(company)
            await self._uow.outbox.add(
                "customers.company_registered",
                {"company_id": str(company.id), "customer_id": str(customer.id)},
            )
            await self._uow.commit()
        except IntegrityError as exc:
            await self._uow.rollback()
            raise ConflictError(
                "Company registration number already exists",
                code="customer_company_edrpou_exists",
            ) from exc
        return CustomerCompanyResponse.from_company(company)

    async def has_approved_company(self, customer_id: UUID) -> bool:
        return await self._uow.customers.has_approved_company(customer_id)
