import pytest
from pydantic import ValidationError

from app.api.modules.catalog.schema import (
    UpdateBrandRequest,
    UpdateCatalogSectionRequest,
    UpdateProductRequest,
)
from app.api.modules.custom_boards.schema import UpdatePortfolioItemRequest


@pytest.mark.parametrize(
    "schema, fields",
    [
        (UpdateBrandRequest, ("name", "position", "is_active")),
        (UpdateCatalogSectionRequest, ("name", "position", "is_active")),
        (
            UpdatePortfolioItemRequest,
            ("title", "description", "image_url", "position", "is_active"),
        ),
        (
            UpdateProductRequest,
            (
                "name",
                "is_active",
                "is_popular",
                "media",
                "documents",
                "relations",
                "specs",
            ),
        ),
    ],
)
def test_patch_rejects_null_required_fields_and_empty_body(schema, fields):
    for field in fields:
        with pytest.raises(ValidationError):
            schema.model_validate({field: None})
    with pytest.raises(ValidationError):
        schema.model_validate({})


@pytest.mark.parametrize(
    "schema", [UpdateBrandRequest, UpdateCatalogSectionRequest, UpdateProductRequest]
)
def test_patch_retains_explicit_nullable_clearing(schema):
    result = schema.model_validate({"description": None})
    assert result.model_dump(exclude_unset=True) == {"description": None}
