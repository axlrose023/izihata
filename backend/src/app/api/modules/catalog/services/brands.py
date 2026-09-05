from uuid import UUID

from app.api.common.exceptions import ConflictError, NotFoundError
from app.api.modules.catalog.models import Brand
from app.api.modules.catalog.schema import (
    AdminBrandResponse,
    BrandResponse,
    UpdateBrandRequest,
)
from app.api.modules.catalog.utils import slugify
from app.database.uow import UnitOfWork


async def ensure_brand(uow: UnitOfWork, name: str) -> Brand:
    """Return the brand row for a product's brand name, creating it if new.

    Staff type brand names on the product form; this keeps the brand list
    complete without forcing them to register a brand first.
    """
    existing = await uow.brands.get_by_name(name)
    if existing is not None:
        return existing

    base = slugify(name) or "brand"
    slug, suffix = base, 2
    while await uow.brands.slug_taken(slug):
        slug = f"{base}-{suffix}"
        suffix += 1
    return await uow.brands.create(
        Brand(
            slug=slug,
            name=name,
            position=await uow.brands.next_position(),
            is_active=True,
        )
    )


class BrandQueryService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def list_brands(self) -> list[BrandResponse]:
        brands = await self._uow.brands.list(only_active=True)
        counts = await self._uow.brands.product_counts()
        return [
            BrandResponse.from_brand(brand, counts.get(brand.name, 0))
            for brand in brands
            if counts.get(brand.name, 0) > 0
        ]

    async def get_brand(self, slug: str) -> BrandResponse:
        brand = await self._uow.brands.get_by_slug(slug)
        if brand is None:
            raise NotFoundError("Brand not found", code="brand_not_found")
        counts = await self._uow.brands.product_counts()
        return BrandResponse.from_brand(brand, counts.get(brand.name, 0))


class BrandManagementService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def list_brands(self) -> list[AdminBrandResponse]:
        brands = await self._uow.brands.list(only_active=False)
        counts = await self._uow.brands.product_counts()
        return [
            AdminBrandResponse.from_brand(brand, counts.get(brand.name, 0))
            for brand in brands
        ]

    async def update_brand(
        self,
        brand_id: UUID,
        request: UpdateBrandRequest,
    ) -> AdminBrandResponse:
        brand = await self._uow.brands.get_by_id(brand_id)
        if brand is None:
            raise NotFoundError("Brand not found", code="brand_not_found")

        if request.name is not None and request.name != brand.name:
            if await self._uow.brands.get_by_name(request.name) is not None:
                raise ConflictError(
                    "Brand name already exists",
                    code="brand_name_exists",
                )
            brand.name = request.name
        for field in ("logo_url", "description", "position", "is_active"):
            if field in request.model_fields_set:
                setattr(brand, field, getattr(request, field))
        await self._uow.commit()

        counts = await self._uow.brands.product_counts()
        return AdminBrandResponse.from_brand(brand, counts.get(brand.name, 0))
