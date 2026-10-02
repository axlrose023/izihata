import pytest

from app.api.modules.catalog.enums import ProductAttributeSource
from app.api.modules.catalog.models import ProductAttribute
from app.api.modules.catalog.schema import ProductListParams


@pytest.mark.asyncio
async def test_list_loads_only_primary_specs_but_detail_still_loads_every_source(
    uow, product
):
    attribute = ProductAttribute(
        product_id=product.id,
        key="ETIM fixture",
        value="Preserved",
        source=ProductAttributeSource.ETIM,
        position=99,
    )
    uow.session.add(attribute)
    await uow.session.flush()
    listing = await uow.products.list(
        ProductListParams(id=[product.id], include_facets=False)
    )
    assert listing
    assert all(
        item.source == ProductAttributeSource.PRIMARY for item in listing[0].attributes
    )
    detail = await uow.products.get_by_slug(product.slug)
    assert any(item.key == "ETIM fixture" for item in detail.attributes)
