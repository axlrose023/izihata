from app.api.common.exceptions import UnprocessableError
from app.api.modules.leads.enums import LeadStatus
from app.api.modules.leads.models import Lead
from app.api.modules.leads.schema import CreateLeadRequest, LeadResponse
from app.database.uow import UnitOfWork


class LeadCreationService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def create(self, request: CreateLeadRequest) -> LeadResponse:
        if request.product_id and not await self._uow.products.exists_active(
            request.product_id
        ):
            raise UnprocessableError("Product is unavailable")

        lead = Lead(
            type=request.type,
            status=LeadStatus.NEW,
            name=request.name,
            phone=request.phone,
            company=request.company,
            product_id=request.product_id,
        )
        await self._uow.leads.create(lead)
        await self._uow.outbox.add(
            topic="lead.created",
            payload={
                "lead_id": str(lead.id),
                "lead_type": lead.type.value,
                "product_id": str(lead.product_id) if lead.product_id else None,
            },
        )
        await self._uow.commit()
        return LeadResponse(
            id=lead.id,
            type=lead.type,
            status=lead.status,
            created_at=lead.created_at,
        )
