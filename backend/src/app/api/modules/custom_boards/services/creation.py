from app.api.modules.custom_boards.models import CustomBoardRequest
from app.api.modules.custom_boards.schema import (
    CreateCustomBoardRequest,
    CustomBoardRequestResponse,
)
from app.api.modules.custom_boards.services.estimation import BoardEstimationService
from app.database.uow import UnitOfWork


class CustomBoardCreationService:
    def __init__(self, uow: UnitOfWork, estimator: BoardEstimationService):
        self._uow = uow
        self._estimator = estimator

    async def create(
        self,
        request: CreateCustomBoardRequest,
    ) -> CustomBoardRequestResponse:
        estimate = self._estimator.estimate(request)
        board_request = CustomBoardRequest(
            customer_name=request.customer_name,
            phone=request.phone,
            email=request.email,
            application=request.application,
            groups_count=request.groups_count,
            ip_class=request.ip_class,
            automation_brand=request.automation_brand,
            budget=request.budget,
            details=request.details,
            estimated_from_price=estimate.starting_price,
        )
        await self._uow.custom_boards.create_request(board_request)
        await self._uow.outbox.add(
            "custom_boards.request_created",
            {"request_id": str(board_request.id)},
        )
        await self._uow.commit()
        return CustomBoardRequestResponse(
            id=board_request.id,
            status=board_request.status,
            starting_price=estimate.starting_price,
            response_sla_hours=estimate.response_sla_hours,
        )
