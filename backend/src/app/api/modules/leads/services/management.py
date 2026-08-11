from uuid import UUID

from app.api.common.exceptions import NotFoundError
from app.api.modules.leads.schema import (
    AdminLeadResponse,
    LeadListParams,
    LeadListResponse,
    UpdateLeadStatusRequest,
)
from app.api.modules.leads.services.status_transition import (
    LeadStatusTransitionService,
)
from app.database.uow import UnitOfWork


class LeadManagementService:
    def __init__(
        self,
        uow: UnitOfWork,
        transitions: LeadStatusTransitionService,
    ):
        self._uow = uow
        self._transitions = transitions

    async def list_leads(self, params: LeadListParams) -> LeadListResponse:
        leads = await self._uow.leads.list(params)
        total = await self._uow.leads.count(params)
        total_pages = (total + params.page_size - 1) // params.page_size
        return LeadListResponse(
            items=[AdminLeadResponse.model_validate(lead) for lead in leads],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )

    async def update_status(
        self,
        lead_id: UUID,
        request: UpdateLeadStatusRequest,
    ) -> AdminLeadResponse:
        lead = await self._uow.leads.get_by_id_for_update(lead_id)
        if lead is None:
            raise NotFoundError("Lead not found")
        if request.status == lead.status:
            return AdminLeadResponse.model_validate(lead)

        self._transitions.ensure_allowed(lead.status, request.status)
        lead.status = request.status
        await self._uow.commit()
        return AdminLeadResponse.model_validate(lead)
