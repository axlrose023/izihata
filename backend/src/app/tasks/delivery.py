from app.settings import get_config
from app.tiq import broker


@broker.task(schedule=[{"cron": "*/10 * * * *"}])
async def refresh_delivery_directories() -> None:
    from app.api.modules.delivery.service import DeliveryDirectoryRefreshService
    from app.ioc import get_async_container

    config = get_config().nova_poshta
    if not config.directory_enabled or config.api_key is None:
        return
    async with get_async_container() as container:
        service = await container.get(DeliveryDirectoryRefreshService)
        await service.refresh_directories()
