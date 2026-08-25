from app.api.common.exceptions import NotFoundError
from app.api.modules.catalog.enums import ReviewStatus
from app.api.modules.catalog.models import ProductReview
from app.api.modules.catalog.schema import (
    CreateProductReviewRequest,
    CreateProductReviewResponse,
)
from app.database.uow import UnitOfWork


class ReviewSubmissionService:
    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def submit(
        self,
        product_slug: str,
        request: CreateProductReviewRequest,
    ) -> CreateProductReviewResponse:
        product = await self._uow.products.get_by_slug(product_slug)
        if product is None:
            raise NotFoundError("Product not found")

        review = ProductReview(
            product_id=product.id,
            author=request.author,
            email=request.email,
            rating=request.rating,
            text=request.text,
            is_published=False,
            status=ReviewStatus.PENDING,
        )
        await self._uow.products.create_review(review)
        await self._uow.outbox.add(
            "catalog.review_submitted",
            {"review_id": str(review.id), "product_id": str(product.id)},
        )
        await self._uow.commit()
        return CreateProductReviewResponse(id=review.id, status=review.status)
