from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from app.api.common.exceptions import ServiceUnavailableError
from app.api.modules.delivery.cache import DeliveryDirectoryCache
from app.api.modules.delivery.service import DeliveryDirectoryRefreshService
from app.settings import NovaPoshtaConfig
from app.tasks import delivery


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_city_task_releases_dispatch_lease_even_when_refresh_fails(
    monkeypatch, failure
):
    import app.ioc

    service = AsyncMock(spec=DeliveryDirectoryRefreshService)
    cache = AsyncMock(spec=DeliveryDirectoryCache)
    container = MagicMock()
    container.__aenter__.return_value = container
    container.get = AsyncMock(
        side_effect=lambda cls: cache if cls is DeliveryDirectoryCache else service
    )
    monkeypatch.setattr(app.ioc, "get_async_container", lambda: container)
    monkeypatch.setattr(
        delivery,
        "get_config",
        lambda: SimpleNamespace(
            nova_poshta=NovaPoshtaConfig(api_key=SecretStr("test"))
        ),
    )
    if failure:
        service.refresh_points.side_effect = ServiceUnavailableError("Provider down")
        with pytest.raises(ServiceUnavailableError):
            await delivery.refresh_delivery_city.original_func("city", "owner")
    else:
        await delivery.refresh_delivery_city.original_func("city", "owner")
    service.refresh_points.assert_awaited_once_with("city")
    cache.release.assert_awaited_once_with("dispatch:city", "owner")


@pytest.mark.asyncio
async def test_periodic_task_checks_directories(monkeypatch):
    import app.ioc

    service = AsyncMock(spec=DeliveryDirectoryRefreshService)
    container = MagicMock()
    container.__aenter__.return_value = container
    container.get = AsyncMock(return_value=service)
    monkeypatch.setattr(app.ioc, "get_async_container", lambda: container)
    monkeypatch.setattr(
        delivery,
        "get_config",
        lambda: SimpleNamespace(
            nova_poshta=NovaPoshtaConfig(api_key=SecretStr("test"))
        ),
    )
    await delivery.refresh_delivery_directories.original_func()
    service.refresh_used.assert_awaited_once()


@pytest.mark.asyncio
async def test_background_tasks_do_not_call_np_without_a_key(monkeypatch):
    import app.ioc

    factory = MagicMock()
    monkeypatch.setattr(app.ioc, "get_async_container", factory)
    monkeypatch.setattr(
        delivery,
        "get_config",
        lambda: SimpleNamespace(nova_poshta=NovaPoshtaConfig()),
    )
    await delivery.refresh_delivery_directories.original_func()
    await delivery.refresh_delivery_city.original_func("city", "owner")
    factory.assert_not_called()
