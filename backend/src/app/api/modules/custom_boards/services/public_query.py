from app.api.modules.custom_boards.schema import PortfolioItemResponse
from app.database.uow import UnitOfWork


class CustomBoardPublicQueryService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def list_portfolio(self) -> list[PortfolioItemResponse]:
        items = await self._uow.custom_boards.list_portfolio()
        return [PortfolioItemResponse.from_item(item) for item in items]
