from uuid import UUID

from app.api.common.exceptions import NotFoundError, UnprocessableError
from app.api.modules.customers.enums import CompanyStatus
from app.api.modules.customers.schema import (
    AdminCompanyResponse,
    CompanyListParams,
    CompanyListResponse,
    ReviewCompanyRequest,
)
from app.database.uow import UnitOfWork


class CompanyManagementService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def list_companies(self, params: CompanyListParams) -> CompanyListResponse:
        rows = await self._uow.customers.list_companies(
            offset=params.offset,
            limit=params.page_size,
            status=params.status,
        )
        total = await self._uow.customers.count_companies(params.status)
        total_pages = (total + params.page_size - 1) // params.page_size
        return CompanyListResponse(
            items=[
                AdminCompanyResponse.from_company_and_customer(company, customer)
                for company, customer in rows
            ],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )

    async def review_company(
        self,
        company_id: UUID,
        request: ReviewCompanyRequest,
    ) -> AdminCompanyResponse:
        company = await self._uow.customers.get_company_for_update(company_id)
        if company is None:
            raise NotFoundError(
                "Customer company not found", code="customer_company_not_found"
            )
        if company.status != CompanyStatus.PENDING:
            raise UnprocessableError(
                "Customer company has already been reviewed",
                code="customer_company_already_reviewed",
            )
        company.status = request.status
        company.manager_name = request.manager_name
        company.cumulative_discount_rate = request.cumulative_discount_rate
        customer = await self._uow.customers.get_by_id(company.customer_id)
        if customer is None:
            raise NotFoundError("Customer not found", code="customer_not_found")
        await self._uow.outbox.add(
            "customers.company_reviewed",
            {"company_id": str(company.id), "status": company.status.value},
        )
        await self._uow.commit()
        return AdminCompanyResponse.from_company_and_customer(company, customer)
