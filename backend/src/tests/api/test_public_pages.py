import json
import re
from unittest.mock import AsyncMock

import pytest

from app.services.public_pages import (
    FrontendTemplateClient,
    PublicPage,
    inline_json,
    render_page,
)

TEMPLATE = '<!doctype html><html lang="uk"><head><title>IZI HATA</title><meta name="description" content="default"></head><body><div id="root"></div><script type="module" src="/assets/app.js"></script></body></html>'


@pytest.fixture
def html_template(monkeypatch):
    monkeypatch.setattr(FrontendTemplateClient, "get", AsyncMock(return_value=TEMPLATE))


@pytest.mark.asyncio
async def test_product_html_contains_public_data_and_metadata(
    client, product, html_template
):
    response = await client.get("/products/" + product.slug + "?utm_source=audit")
    assert response.status_code == 200, response.text
    assert "<h1>" in response.text
    assert product.name in response.text
    assert 'property="og:title"' in response.text
    assert 'property="og:image"' in response.text if product.image_url else True
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', response.text).group(
        1
    )
    assert "utm_source" not in canonical
    seeds = json.loads(
        re.search(
            r'<script id="public-catalog-data" type="application/json">(.*?)</script>',
            response.text,
        ).group(1)
    )
    assert seeds["/catalog/products/" + product.slug]["id"] == str(product.id)
    assert "/catalog/categories" in seeds
    assert "/assets/app.js" in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/products/no-product",
        "/catalog/no-category",
        "/brands/no-brand",
        "/sections/no-section",
        "/no-page",
    ],
)
async def test_missing_resources_return_html_404(client, html_template, path):
    response = await client.get(path)
    assert response.status_code == 404, response.text
    assert "text/html" in response.headers["content-type"]
    assert 'name="robots" content="noindex"' in response.text


@pytest.mark.asyncio
async def test_catalog_seed_preserves_repeated_filters_and_requested_page(
    client, html_template
):
    response = await client.get(
        "/catalog?brand=AXIOM&brand=Hager&page=2&sort=price_asc&view=large"
    )
    assert response.status_code == 200, response.text
    seeds = json.loads(
        re.search(
            r'<script id="public-catalog-data" type="application/json">(.*?)</script>',
            response.text,
        ).group(1)
    )
    key = next(key for key in seeds if key.startswith("/catalog/products?"))
    assert "brand=AXIOM&brand=Hager" in key
    assert "page=2" in key and "page_size=12" in key
    assert "view=" not in key
    assert seeds[key]["page"] == 2


@pytest.mark.asyncio
async def test_bad_catalog_parameters_return_422_html(client, html_template):
    response = await client.get("/catalog?page=9223372036854775807")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_template_outage_returns_retryable_html(client, monkeypatch):
    from app.api.common.exceptions import ServiceUnavailableError

    monkeypatch.setattr(
        FrontendTemplateClient, "get", AsyncMock(side_effect=ServiceUnavailableError())
    )
    response = await client.get("/catalog")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"


def test_escapes_html_and_inline_json():
    attack = "</script><script>alert(1)</script>"
    html = render_page(
        TEMPLATE,
        PublicPage(
            title=attack,
            description='" onload="evil',
            seeds={"/catalog/categories": attack},
        ),
        "https://izihata.com.ua/",
    )
    assert attack not in html
    assert "&lt;/script&gt;" in html
    assert json.loads(inline_json({"x": attack})) == {"x": attack}
    assert '<div id="root"><main' in html


@pytest.mark.asyncio
async def test_missing_api_remains_json(client):
    response = await client.get("/api/v1/not-a-route")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_unknown_api_post_remains_404(client):
    response = await client.post("/api/v1/no-such-route", json={})
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_get_on_post_only_api_preserves_method_contract(client):
    response = await client.get("/api/v1/orders")
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
    assert "POST" in response.headers["allow"]


def test_title_backslashes_are_literal():
    html = render_page(
        TEMPLATE, PublicPage(title=r"Cable \1 \g<1>"), "https://izihata.com.ua/"
    )
    assert r"Cable \1 \g&lt;1&gt;" in html
