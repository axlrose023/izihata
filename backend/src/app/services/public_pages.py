# ruff: noqa: RUF001
"""HTML representation of public catalog resources using existing query services."""

import json
import re
from dataclasses import dataclass, field
from html import escape
from urllib.parse import parse_qsl, quote, urlencode

import httpx
from pydantic import ValidationError
from starlette.datastructures import QueryParams

from app.api.common.exceptions import NotFoundError, ServiceUnavailableError
from app.api.modules.catalog.schema import ProductDetailResponse, ProductListParams
from app.api.modules.catalog.services.brands import BrandQueryService
from app.api.modules.catalog.services.catalog_query import CatalogQueryService

DEFAULT_DESCRIPTION = "IZI HATA — електротовари для дому, монтажу й бізнесу."


def inline_json(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def link(path: str, name: str) -> str:
    return f'<a href="{escape(path, quote=True)}">{escape(name)}</a>'


@dataclass(slots=True)
class PublicPage:
    title: str
    description: str = DEFAULT_DESCRIPTION
    content: str = ""
    status: int = 200
    image: str | None = None
    structured_data: dict | None = None
    seeds: dict = field(default_factory=dict)


class FrontendTemplateClient:
    def __init__(self, url: str):
        self._url = url
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(3, connect=1, pool=1), follow_redirects=False
        )

    async def get(self) -> str:
        try:
            response = await self._client.get(self._url)
            response.raise_for_status()
            template = response.text
            if '<div id="root"></div>' not in template or "</head>" not in template:
                raise ValueError("Frontend HTML placeholder missing")
            return template
        except (httpx.HTTPError, ValueError) as error:
            raise ServiceUnavailableError("Frontend is updating") from error

    async def close(self) -> None:
        await self._client.aclose()


class PublicPageService:
    def __init__(
        self,
        catalog: CatalogQueryService,
        brands: BrandQueryService,
        template: FrontendTemplateClient,
        site_origin: str,
    ):
        self._catalog = catalog
        self._brands = brands
        self._template = template
        self._origin = site_origin.rstrip("/")

    async def page(self, path: str, search: str) -> tuple[str, int]:
        try:
            page = await self._load(path, QueryParams(search))
        except NotFoundError:
            page = PublicPage(
                title="Сторінку не знайдено",
                content="<p>Посилання застаріло або сторінка недоступна.</p>",
                status=404,
            )
        except ValidationError:
            page = PublicPage(
                title="Перевірте умови пошуку",
                content="<p>Умови пошуку некоректні. Поверніться до каталогу.</p>",
                status=422,
            )
        canonical_params = [
            (key, value)
            for key, value in parse_qsl(search, keep_blank_values=True)
            if not key.startswith("utm_") and key not in {"fbclid", "gclid", "msclkid"}
        ]
        canonical = (
            self._origin
            + quote(path, safe="/")
            + ("?" + urlencode(canonical_params) if canonical_params else "")
        )
        template = await self._template.get()
        return render_page(template, page, canonical), page.status

    async def _load(self, path: str, params: QueryParams) -> PublicPage:
        categories = await self._catalog.get_categories()
        seeds: dict[str, object] = {
            "/catalog/categories": [item.model_dump(mode="json") for item in categories]
        }
        parts = path.strip("/").split("/") if path != "/" else []
        if len(parts) == 2 and parts[0] == "products":
            product = await self._catalog.get_product(parts[1])
            seeds[f"/catalog/products/{quote(product.slug, safe='')}"] = (
                product.model_dump(mode="json")
            )
            specs = "".join(
                f"<div><dt>{escape(key)}</dt><dd>{escape(value)}</dd></div>"
                for key, value in product.specs.items()
            )
            content = f"<p>{escape(product.brand)} · {escape(product.sku)}</p><p>{product.price} грн</p><p>{escape(product.short_description or '')}</p><dl>{specs}</dl>"
            return PublicPage(
                product.name,
                product.short_description or product.name,
                content,
                image=product.image_url,
                structured_data=product_structured_data(product),
                seeds=seeds,
            )
        if not parts:
            sections = await self._catalog.get_sections()
            brands = await self._brands.list_brands()
            seeds["/catalog/sections"] = [
                item.model_dump(mode="json") for item in sections
            ]
            seeds["/catalog/brands"] = [item.model_dump(mode="json") for item in brands]
            content = (
                "<ul>"
                + "".join(
                    f"<li>{link('/sections/' + item.slug, item.name)}</li>"
                    for item in sections
                )
                + "</ul>"
            )
            content += (
                "<ul>"
                + "".join(
                    f"<li>{link('/catalog/' + item.slug, item.name)}</li>"
                    for item in categories
                )
                + "</ul>"
            )
            return PublicPage(
                "Все для щита, кабелю й освітлення", content=content, seeds=seeds
            )
        if parts == ["brands"] or (len(parts) == 2 and parts[0] == "brands"):
            brands = await self._brands.list_brands()
            seeds["/catalog/brands"] = [item.model_dump(mode="json") for item in brands]
            if len(parts) == 1:
                content = (
                    "<ul>"
                    + "".join(
                        f"<li>{link('/brands/' + item.slug, item.name)} · {item.product_count}</li>"
                        for item in brands
                    )
                    + "</ul>"
                )
                return PublicPage("Виробники", content=content, seeds=seeds)
            brand = next((item for item in brands if item.slug == parts[1]), None)
            if brand is None:
                raise NotFoundError("Brand not found")
            return await self._catalog_page(
                params, seeds, title=brand.name, brand=brand.name
            )
        if len(parts) == 2 and parts[0] == "sections":
            sections = await self._catalog.get_sections()
            section = next((item for item in sections if item.slug == parts[1]), None)
            if section is None:
                raise NotFoundError("Section not found")
            seeds["/catalog/sections"] = [
                item.model_dump(mode="json") for item in sections
            ]
            content = (
                "<ul>"
                + "".join(
                    f"<li>{link('/catalog/' + item.slug, item.name)} · {item.product_count}</li>"
                    for item in section.categories
                )
                + "</ul>"
            )
            return PublicPage(
                section.name,
                section.description or DEFAULT_DESCRIPTION,
                content,
                image=section.image_url,
                seeds=seeds,
            )
        if parts and parts[0] == "catalog" and len(parts) <= 2:
            category = parts[1] if len(parts) == 2 else None
            if category in {"sale", "new"}:
                return await self._catalog_page(
                    params,
                    seeds,
                    title="Акції та знижки" if category == "sale" else "Новинки",
                    badges=["sale", "promotion", "clearance"]
                    if category == "sale"
                    else ["new"],
                )
            category_values = params.getlist("category")
            slug = category or (category_values[0] if category_values else None)
            active_category = next(
                (item for item in categories if item.slug == slug), None
            )
            if slug and active_category is None:
                raise NotFoundError("Category not found")
            return await self._catalog_page(
                params,
                seeds,
                title=active_category.name if active_category else "Усі товари",
                category=category,
            )
        raise NotFoundError("Page not found")

    async def _catalog_page(
        self,
        params: QueryParams,
        seeds: dict,
        *,
        title: str,
        category: str | None = None,
        brand: str | None = None,
        badges: list[str] | None = None,
    ) -> PublicPage:
        # Match the existing CatalogPage's public query, using the same API schema.
        filters: dict[str, str | list[str]] = {}
        for key in (
            "search",
            "category",
            "subcategory",
            "section",
            "in_stock",
            "min_price",
            "max_price",
        ):
            values = params.getlist(key)
            if values and values[0]:
                filters[key] = values[0]
        for key in ("brand", "availability", "sale_unit", "spec", "badge"):
            values = [value for value in params.getlist(key) if value]
            if values:
                filters[key] = values
        filters.update(
            sort=(params.getlist("sort") or ["popular"])[0],
            page=(params.getlist("page") or ["1"])[0],
            page_size="12",
            include_facets="false",
        )
        if category:
            filters["category"] = category
        if brand:
            filters["brand"] = [brand]
        if badges:
            filters["badge"] = badges
        products = await self._catalog.get_products(
            ProductListParams.model_validate(filters)
        )
        seeds["/catalog/products?" + urlencode(filters, doseq=True)] = (
            products.model_dump(mode="json")
        )
        content = (
            f"<p>Знайдено товарів: {products.total}</p><ul>"
            + "".join(
                f"<li>{link('/products/' + item.slug, item.name)} · {item.price} грн</li>"
                for item in products.items
            )
            + "</ul>"
        )
        return PublicPage(title, content=content, seeds=seeds)


def product_structured_data(product: ProductDetailResponse) -> dict:
    data: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "sku": product.sku,
        "brand": {"@type": "Brand", "name": product.brand},
        "image": list(
            dict.fromkeys(
                url
                for url in [product.image_url, *(item.url for item in product.media)]
                if url
            )
        ),
        "offers": {
            "@type": "Offer",
            "priceCurrency": "UAH",
            "price": str(product.price),
            "availability": "https://schema.org/"
            + {"preorder": "PreOrder", "out_of_stock": "OutOfStock"}.get(
                product.stock_status.value, "InStock"
            ),
        },
    }
    if product.short_description or product.description:
        data["description"] = product.short_description or product.description
    if product.reviews_count:
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(product.rating),
            "reviewCount": product.reviews_count,
        }
    return data


def render_page(template: str, page: PublicPage, canonical: str) -> str:
    title = page.title + " | IZI HATA"
    template = re.sub(
        r"<title>.*?</title>",
        lambda match: "<title>" + escape(title) + "</title>",
        template,
        flags=re.S,
    )
    template = re.sub(r'<meta\s+name="description"[^>]*>', "", template, flags=re.S)
    metadata = f'<meta name="description" content="{escape(page.description, quote=True)}"><link rel="canonical" href="{escape(canonical, quote=True)}">'
    open_graph: dict[str, str | None] = {
        "og:title": title,
        "og:description": page.description,
        "og:url": canonical,
        "og:type": "product" if page.structured_data else "website",
        "og:image": page.image,
    }
    for name, value in open_graph.items():
        if value:
            metadata += (
                f'<meta property="{name}" content="{escape(value, quote=True)}">'
            )
    if page.status != 200:
        metadata += '<meta name="robots" content="noindex">'
    if page.structured_data:
        metadata += (
            '<script type="application/ld+json" data-page-structured-data="true">'
            + inline_json(page.structured_data)
            + "</script>"
        )
    template = template.replace("</head>", metadata + "</head>", 1)
    content = f'<main class="container"><nav>{link("/", "IZI HATA")} · {link("/catalog", "Каталог")}</nav><h1>{escape(page.title)}</h1>{page.content}</main>'
    return template.replace(
        '<div id="root"></div>',
        '<div id="root">'
        + content
        + '</div><script id="public-catalog-data" type="application/json">'
        + inline_json(page.seeds)
        + "</script>",
        1,
    )
