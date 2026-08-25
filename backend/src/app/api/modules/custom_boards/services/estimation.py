from decimal import Decimal

from app.api.modules.custom_boards.schema import (
    BoardEstimateRequest,
    BoardEstimateResponse,
)

_STARTING_PRICE_PER_GROUP = Decimal("500.00")
_MINIMUM_BILLABLE_GROUPS = 3
_RESPONSE_SLA_HOURS = 24


class BoardEstimationService:
    """Produces an indicative configuration, not a commercial offer."""

    def estimate(self, request: BoardEstimateRequest) -> BoardEstimateResponse:
        billable_groups = max(request.groups_count, _MINIMUM_BILLABLE_GROUPS)
        return BoardEstimateResponse(
            starting_price=_STARTING_PRICE_PER_GROUP * billable_groups,
            response_sla_hours=_RESPONSE_SLA_HOURS,
            suggested_components=[
                "input protection",
                f"{request.groups_count} outgoing protection groups",
                f"{request.ip_class} enclosure",
            ],
            reference_notice=(
                "Indicative configuration only. The final composition and price "
                "are confirmed by a manager after reviewing the project."
            ),
        )
