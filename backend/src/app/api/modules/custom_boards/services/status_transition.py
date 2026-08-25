from typing import ClassVar

from app.api.common.exceptions import UnprocessableError
from app.api.modules.custom_boards.enums import BoardRequestStatus


class BoardStatusTransitionService:
    _allowed: ClassVar[dict[BoardRequestStatus, set[BoardRequestStatus]]] = {
        BoardRequestStatus.NEW: {
            BoardRequestStatus.IN_PROGRESS,
            BoardRequestStatus.CANCELLED,
        },
        BoardRequestStatus.IN_PROGRESS: {
            BoardRequestStatus.QUOTED,
            BoardRequestStatus.CANCELLED,
        },
        BoardRequestStatus.QUOTED: {
            BoardRequestStatus.CLOSED,
            BoardRequestStatus.CANCELLED,
        },
        BoardRequestStatus.CLOSED: set(),
        BoardRequestStatus.CANCELLED: set(),
    }

    def ensure_allowed(
        self,
        current: BoardRequestStatus,
        target: BoardRequestStatus,
    ) -> None:
        if current == target:
            return
        if target not in self._allowed[current]:
            raise UnprocessableError(
                "Invalid custom board request status transition",
                code="invalid_custom_board_status_transition",
            )
