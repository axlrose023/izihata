"""Bounded public HTTP load check; does not create orders or customer data."""

import argparse
import asyncio
import json
import math
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from pydantic import TypeAdapter

from app.api.modules.catalog.enums import StockStatus
from app.api.modules.catalog.schema import (
    CategoryResponse,
    ProductDetailResponse,
    ProductFacets,
    ProductListResponse,
    SpecFacetPageResponse,
)
from app.api.modules.checkout.schema import QuoteResponse

API = "/api/v1"
CASE_COUNT = 11
CATALOG_CASES = frozenset({0, 1, 2, 3, 4, 5, 6, 9})


@dataclass(frozen=True)
class LoadCase:
    name: str
    path: str
    adapter: TypeAdapter[Any] | None
    params: dict[str, str] | None = None
    payload: dict[str, Any] | None = None

    async def request(self, client: httpx.AsyncClient) -> httpx.Response:
        if self.payload is not None:
            return await client.post(self.path, json=self.payload)
        return await client.get(self.path, params=self.params)

    def validate(self, response: httpx.Response) -> None:
        response.raise_for_status()
        if self.adapter is not None:
            self.adapter.validate_json(response.content)
        elif "text/html" not in response.headers.get("content-type", ""):
            raise ValueError("Homepage did not return HTML")


def validate_budget(concurrency: Sequence[int], requests_per_stage: int) -> None:
    if not concurrency or any(value < 1 or value > 20 for value in concurrency):
        raise ValueError("Concurrency must be between 1 and 20")
    if requests_per_stage < max(concurrency):
        raise ValueError("Each stage needs at least as many requests as workers")
    if len(concurrency) * requests_per_stage > 300:
        raise ValueError("At most 300 requests are allowed per run")
    catalog = sum(
        index % CASE_COUNT in CATALOG_CASES for index in range(requests_per_stage)
    )
    quotes = sum(
        index % CASE_COUNT == CASE_COUNT - 1 for index in range(requests_per_stage)
    )
    # Include discovery calls and leave headroom below the real per-IP limits.
    if catalog * len(concurrency) + 2 > 220 or quotes * len(concurrency) > 25:
        raise ValueError("Request budget exceeds catalog/quote rate-limit headroom")


async def discover_cases(client: httpx.AsyncClient) -> list[LoadCase]:
    grid_params = {"include_facets": "false", "page_size": "12"}
    response = await client.get(f"{API}/catalog/products", params=grid_params)
    response.raise_for_status()
    products = ProductListResponse.model_validate_json(response.content)
    product = next(
        (
            item
            for item in products.items
            if item.stock_status != StockStatus.OUT_OF_STOCK
        ),
        None,
    )
    if product is None:
        raise ValueError("No purchasable product found for the read-only quote check")
    response = await client.get(f"{API}/catalog/categories")
    response.raise_for_status()
    categories = TypeAdapter(list[CategoryResponse]).validate_json(response.content)
    category = max(categories, key=lambda item: item.product_count, default=None)
    if category is None or category.product_count == 0:
        raise ValueError("No populated category found")
    scope = {"category": category.slug}
    response = await client.get(f"{API}/catalog/spec-facets", params=scope)
    response.raise_for_status()
    keys = SpecFacetPageResponse.model_validate_json(response.content)
    if not keys.items:
        raise ValueError("No category filter keys found")
    return [
        LoadCase(
            "grid",
            f"{API}/catalog/products",
            TypeAdapter(ProductListResponse),
            grid_params,
        ),
        LoadCase(
            "category",
            f"{API}/catalog/products",
            TypeAdapter(ProductListResponse),
            grid_params | scope,
        ),
        LoadCase(
            "search",
            f"{API}/catalog/products",
            TypeAdapter(ProductListResponse),
            grid_params | {"search": "автомат"},
        ),
        LoadCase(
            "sku",
            f"{API}/catalog/products",
            TypeAdapter(ProductListResponse),
            grid_params | {"search": product.sku},
        ),
        LoadCase("facets", f"{API}/catalog/facets", TypeAdapter(ProductFacets), scope),
        LoadCase(
            "spec_keys",
            f"{API}/catalog/spec-facets",
            TypeAdapter(SpecFacetPageResponse),
            scope,
        ),
        LoadCase(
            "spec_values",
            f"{API}/catalog/spec-facets",
            TypeAdapter(SpecFacetPageResponse),
            scope | {"facet_key": max(keys.items, key=lambda item: item.count).value},
        ),
        LoadCase(
            "detail",
            f"{API}/catalog/products/{product.slug}",
            TypeAdapter(ProductDetailResponse),
        ),
        LoadCase(
            "categories",
            f"{API}/catalog/categories",
            TypeAdapter(list[CategoryResponse]),
        ),
        LoadCase("homepage", "/", None),
        LoadCase(
            "quote",
            f"{API}/checkout/quote",
            TypeAdapter(QuoteResponse),
            payload={"items": [{"product_id": str(product.id), "quantity": 1}]},
        ),
    ]


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    times = sorted(sample["ms"] for sample in samples)
    return {
        "completed": len(samples),
        "p50_ms": round(times[math.ceil(len(times) * 0.50) - 1], 2) if times else None,
        "p95_ms": round(times[math.ceil(len(times) * 0.95) - 1], 2) if times else None,
        "max_ms": round(max(times), 2) if times else None,
        "statuses": dict(Counter(str(sample["status"]) for sample in samples)),
        "errors": [sample for sample in samples if sample["error"] is not None],
        "response_bytes": sum(sample["bytes"] for sample in samples),
    }


async def run_stage(
    client: httpx.AsyncClient,
    cases: list[LoadCase],
    concurrency: int,
    request_count: int,
) -> dict[str, Any]:
    pending = iter(range(request_count))
    stop = asyncio.Event()
    samples: list[dict[str, Any]] = []

    async def worker() -> None:
        while not stop.is_set():
            index = next(pending, None)
            if index is None:
                return
            case = cases[index % len(cases)]
            started = perf_counter()
            status: int | None = None
            size = 0
            error = None
            try:
                response = await case.request(client)
                elapsed = (perf_counter() - started) * 1000
                status = response.status_code
                size = len(response.content)
                case.validate(response)
            except (httpx.HTTPError, ValueError) as exc:
                elapsed = (perf_counter() - started) * 1000
                error = f"{type(exc).__name__}: {exc}"
                stop.set()
            samples.append(
                {
                    "case": case.name,
                    "ms": elapsed,
                    "status": status,
                    "bytes": size,
                    "error": error,
                }
            )

    started = perf_counter()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    duration = perf_counter() - started
    return {
        "concurrency": concurrency,
        "requested": request_count,
        "duration_s": round(duration, 3),
        "requests_per_second": round(len(samples) / duration, 2),
        **summarize(samples),
        "cases": {
            case.name: summarize(
                [sample for sample in samples if sample["case"] == case.name]
            )
            for case in cases
        },
    }


async def run_load(
    client: httpx.AsyncClient,
    concurrency: Sequence[int],
    requests_per_stage: int,
    progress: Callable[[str], None],
) -> dict[str, Any]:
    validate_budget(concurrency, requests_per_stage)
    cases = await discover_cases(client)
    report: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "base_url": str(client.base_url),
        "description": "Bounded concurrent HTTP requests; no orders, accounts or delivery lookups",
        "stages": [],
    }
    for workers in concurrency:
        stage = await run_stage(client, cases, workers, requests_per_stage)
        report["stages"].append(stage)
        progress(
            f"concurrency={workers} completed={stage['completed']} p95={stage['p95_ms']}ms errors={len(stage['errors'])}"
        )
        if stage["errors"]:
            break
    report["passed"] = len(report["stages"]) == len(concurrency) and not any(
        stage["errors"] for stage in report["stages"]
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 5, 10, 20])
    parser.add_argument("--requests-per-stage", type=int, default=55)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_budget(args.concurrency, args.requests_per_stage)
    except ValueError as exc:
        parser.error(str(exc))

    async def execute() -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=args.base_url.rstrip("/"),
            timeout=10,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=20),
        ) as client:
            return await run_load(
                client,
                args.concurrency,
                args.requests_per_stage,
                lambda message: print(message, file=sys.stderr, flush=True),
            )

    try:
        report = asyncio.run(execute())
    except (httpx.HTTPError, ValueError) as exc:
        report = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
