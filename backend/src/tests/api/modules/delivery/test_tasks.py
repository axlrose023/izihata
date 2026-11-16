from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from app.api.common.exceptions import ServiceUnavailableError
from app.api.modules.delivery.service import DeliveryDirectoryRefreshService
from app.settings import NovaPoshtaConfig
from app.tasks import delivery


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_directory_task_closes_container_even_when_refresh_fails(
    monkeypatch, failure
):
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
    if failure:
        service.refresh_directories.side_effect = ServiceUnavailableError(
            "Provider down"
        )
        with pytest.raises(ServiceUnavailableError):
            await delivery.refresh_delivery_directories.original_func()
    else:
        await delivery.refresh_delivery_directories.original_func()
    service.refresh_directories.assert_awaited_once_with()
    container.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config",
    [
        NovaPoshtaConfig(),
        NovaPoshtaConfig(api_key=SecretStr("test"), directory_enabled=False),
    ],
)
async def test_background_task_skips_disabled_or_unconfigured_provider(
    monkeypatch, config
):
    import app.ioc

    factory = MagicMock()
    monkeypatch.setattr(app.ioc, "get_async_container", factory)
    monkeypatch.setattr(
        delivery,
        "get_config",
        lambda: SimpleNamespace(nova_poshta=config),
    )
    await delivery.refresh_delivery_directories.original_func()
    factory.assert_not_called()
