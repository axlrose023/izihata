import asyncio

import httpx
import pytest
from pydantic import TypeAdapter

from app.api.modules.catalog.schema import SpecFacetPageResponse
from cli.catalog_load import LoadCase, run_stage, validate_budget


def test_default_load_budget_leaves_rate_limit_headroom():
    validate_budget([1, 5, 10, 20], 55)


@pytest.mark.parametrize(
    ("workers", "requests"),
    [
        ([], 55),
        ([0], 55),
        ([21], 55),
        ([20], 10),
        ([1, 5, 10, 20], 110),
        ([1, 5, 10, 20], 75),
    ],
)
def test_invalid_load_budgets_are_rejected(workers: list[int], requests: int):
    with pytest.raises(ValueError):
        validate_budget(workers, requests)


@pytest.mark.asyncio
async def test_load_stage_bounds_concurrency_and_validates_responses():
    in_flight = peak = requests = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak, requests
        in_flight += 1
        requests += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.001)
        in_flight -= 1
        return httpx.Response(200, json={"items": [], "page": 1, "has_next": False})

    case = LoadCase("keys", "/keys", TypeAdapter(SpecFacetPageResponse))
    async with httpx.AsyncClient(
        base_url="https://example.test", transport=httpx.MockTransport(handle)
    ) as client:
        result = await run_stage(client, [case], 5, 20)
    assert peak == 5
    assert requests == result["completed"] == 20
    assert result["statuses"] == {"200": 20}
    assert not result["errors"]
    assert result["p50_ms"] <= result["p95_ms"] <= result["max_ms"]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["rate_limit", "server", "schema", "timeout"])
async def test_load_stage_stops_on_failure_without_retries(failure: str):
    requests = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if failure == "timeout":
            raise httpx.ReadTimeout("Timed out", request=request)
        status = {"rate_limit": 429, "server": 503}.get(failure, 200)
        return httpx.Response(status, json={"invalid": True})

    case = LoadCase("keys", "/keys", TypeAdapter(SpecFacetPageResponse))
    async with httpx.AsyncClient(
        base_url="https://example.test", transport=httpx.MockTransport(handle)
    ) as client:
        result = await run_stage(client, [case], 5, 55)
    assert requests == result["completed"] == 1
    assert len(result["errors"]) == 1
