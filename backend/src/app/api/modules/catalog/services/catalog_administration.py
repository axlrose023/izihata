from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.api.common.exceptions import ConflictError, NotFoundError
from app.api.modules.catalog.enums import ReviewStatus
from app.api.modules.catalog.models import (
    CatalogAttribute,
    CatalogSection,
    CategoryAttribute,
)
from app.api.modules.catalog.schema import (
    AdminCatalogSectionResponse,
    AdminProductReviewResponse,
    CatalogAttributeResponse,
    CategoryAttributeResponse,
    CreateCatalogAttributeRequest,
    CreateCatalogSectionRequest,
    ProductReviewListParams,
    ProductReviewListResponse,
    ReplaceCategoryAttributesRequest,
    ReviewModerationRequest,
    UpdateCatalogSectionRequest,
    UpdateCategorySectionRequest,
)
from app.database.uow import UnitOfWork


class CatalogAdministrationService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def _commit_unique_value(
        self,
        *,
        detail: str,
        code: str,
    ) -> None:
        try:
            await self._uow.commit()
        except IntegrityError as exc:
            await self._uow.rollback()
            raise ConflictError(detail, code=code) from exc

    async def create_section(
        self,
        request: CreateCatalogSectionRequest,
    ) -> AdminCatalogSectionResponse:
        if await self._uow.categories.get_section_by_slug(request.slug) is not None:
            raise ConflictError(
                "Catalog section slug already exists",
                code="catalog_section_slug_exists",
            )
        section = CatalogSection(**request.model_dump())
        await self._uow.categories.create_section(section)
        await self._commit_unique_value(
            detail="Catalog section slug already exists",
            code="catalog_section_slug_exists",
        )
        return AdminCatalogSectionResponse.model_validate(section)

    async def update_section(
        self,
        section_id: UUID,
        request: UpdateCatalogSectionRequest,
    ) -> AdminCatalogSectionResponse:
        section = await self._uow.categories.get_section_for_update(section_id)
        if section is None:
            raise NotFoundError(
                "Catalog section not found", code="catalog_section_not_found"
            )
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(section, field, value)
        await self._uow.commit()
        return AdminCatalogSectionResponse.model_validate(section)

    async def assign_category_section(
        self,
        category_id: UUID,
        request: UpdateCategorySectionRequest,
    ) -> None:
        category = await self._uow.categories.get_by_id_for_update(category_id)
        if category is None:
            raise NotFoundError("Category not found", code="category_not_found")
        if request.section_id is not None:
            section = await self._uow.categories.get_section_for_update(
                request.section_id
            )
            if section is None:
                raise NotFoundError(
                    "Catalog section not found",
                    code="catalog_section_not_found",
                )
            category.section_id = section.id
        else:
            category.section_id = None
        await self._uow.commit()

    async def list_attributes(self) -> list[CatalogAttributeResponse]:
        attributes = await self._uow.categories.list_attributes()
        return [
            CatalogAttributeResponse.from_attribute(attribute)
            for attribute in attributes
        ]

    async def create_attribute(
        self,
        request: CreateCatalogAttributeRequest,
    ) -> CatalogAttributeResponse:
        if await self._uow.categories.get_attribute_by_code(request.code) is not None:
            raise ConflictError(
                "Catalog attribute code already exists",
                code="catalog_attribute_code_exists",
            )
        attribute = CatalogAttribute(**request.model_dump())
        await self._uow.categories.create_attribute(attribute)
        await self._commit_unique_value(
            detail="Catalog attribute code already exists",
            code="catalog_attribute_code_exists",
        )
        return CatalogAttributeResponse.from_attribute(attribute)

    async def replace_category_attributes(
        self,
        category_id: UUID,
        request: ReplaceCategoryAttributesRequest,
    ) -> list[CategoryAttributeResponse]:
        category = await self._uow.categories.get_by_id_for_update(category_id)
        if category is None:
            raise NotFoundError("Category not found", code="category_not_found")
        attribute_ids = {item.attribute_id for item in request.attributes}
        attributes = await self._uow.categories.get_attributes_by_ids(attribute_ids)
        if len(attributes) != len(attribute_ids):
            raise NotFoundError(
                "Catalog attribute not found",
                code="catalog_attribute_not_found",
            )
        await self._uow.categories.replace_category_attributes(
            category.id,
            [
                CategoryAttribute(
                    category_id=category.id,
                    attribute_id=item.attribute_id,
                    is_required=item.is_required,
                    is_primary_filter=item.is_primary_filter,
                    position=item.position,
                )
                for item in request.attributes
            ],
        )
        await self._uow.commit()
        return await self.list_category_attributes(category.id)

    async def list_category_attributes(
        self,
        category_id: UUID,
    ) -> list[CategoryAttributeResponse]:
        assignments = await self._uow.categories.list_category_attributes(category_id)
        return [
            CategoryAttributeResponse(
                id=assignment.id,
                attribute=CatalogAttributeResponse.from_attribute(attribute),
                is_required=assignment.is_required,
                is_primary_filter=assignment.is_primary_filter,
                position=assignment.position,
            )
            for assignment, attribute in assignments
        ]

    async def list_reviews(
        self,
        params: ProductReviewListParams,
    ) -> ProductReviewListResponse:
        rows = await self._uow.products.list_reviews(
            offset=params.offset,
            limit=params.page_size,
        )
        total = await self._uow.products.review_count()
        total_pages = (total + params.page_size - 1) // params.page_size
        return ProductReviewListResponse(
            items=[
                AdminProductReviewResponse.from_review(review, product)
                for review, product in rows
            ],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )

    async def moderate_review(
        self,
        review_id: UUID,
        request: ReviewModerationRequest,
    ) -> None:
        review = await self._uow.products.get_review_for_update(review_id)
        if review is None:
            raise NotFoundError("Product review not found", code="review_not_found")
        review.status = request.status
        review.is_published = request.status == ReviewStatus.PUBLISHED
        review.is_featured = request.is_featured
        await self._uow.products.refresh_review_summary(review.product_id)
        await self._uow.outbox.add(
            "catalog.review_moderated",
            {"review_id": str(review.id), "status": review.status.value},
        )
        await self._uow.commit()
