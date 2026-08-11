from app.api.common.exceptions import UnprocessableError
from app.api.modules.leads.enums import LeadStatus

STATUS_TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.NEW: {LeadStatus.CONTACTED, LeadStatus.CLOSED},
    LeadStatus.CONTACTED: {LeadStatus.CLOSED},
    LeadStatus.CLOSED: set(),
}


class LeadStatusTransitionService:
    def ensure_allowed(self, current: LeadStatus, target: LeadStatus) -> None:
        if target not in STATUS_TRANSITIONS[current]:
            raise UnprocessableError(
                f"Lead cannot move from {current.value} to {target.value}"
            )
