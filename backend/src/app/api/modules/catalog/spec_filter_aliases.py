"""Normalized catalog filters backed by supplier attributes."""

from collections.abc import Sequence

from sqlalchemy import and_, case, func, literal, not_, or_
from sqlalchemy.sql.elements import ColumnElement

from app.api.modules.catalog.models import Category, Product, ProductAttribute

MATERIAL_FILTER_KEY = "Матеріал"
IP_FILTER_KEY = "Ступінь захисту IP"
FILTER_CATEGORY_SLUGS = frozenset({"lowvoltage", "panels"})

MATERIAL_KEYS = ("Матеріал", "Матеріал виготовлення")
IP_KEYS = (
    "Ступінь захисту, IP",
    "Ступінь захисту IP",
    "Захисне виконання \u0406\u0420",
)

MATERIAL_VALUES = ("Метал", "Пластик", "АБС-пластик")
IP_VALUES = ("IP20", "IP31", "IP40", "IP44", "IP54", "IP65")

_MATERIAL_TEXT = func.lower(ProductAttribute.value)


def _contains_material_term(term: str) -> ColumnElement[bool]:
    return or_(
        _MATERIAL_TEXT.contains(term.lower()),
        ProductAttribute.value.contains(term.title()),
        ProductAttribute.value.contains(term.upper()),
    )


_ABS_MATERIAL = or_(
    _contains_material_term("abs"),
    _contains_material_term("\u0430\u0431\u0441"),
)
_METAL_MATERIAL = or_(
    _contains_material_term("метал"),
    _contains_material_term("сталь"),
    _contains_material_term("алюміні"),
    _contains_material_term("силум"),
    _contains_material_term("мід"),
    _contains_material_term("латун"),
    _contains_material_term("нікел"),
)
_PLASTIC_MATERIAL = or_(
    _contains_material_term("пластик"),
    _contains_material_term("пластмас"),
    _contains_material_term("полікарбонат"),
    _contains_material_term("полістирол"),
    _contains_material_term("polycarbonate"),
    _contains_material_term("asa"),
    _contains_material_term("пвх"),
    _contains_material_term("термопласт"),
    _contains_material_term("поліестер"),
    _contains_material_term("полиэстер"),
    _contains_material_term("polyester"),
    _contains_material_term("полімер"),
    _contains_material_term("поліетилен"),
    _contains_material_term("поліпропілен"),
)


def is_alias_facet_key(key: str) -> bool:
    return key in {MATERIAL_FILTER_KEY, IP_FILTER_KEY}


def _category_condition() -> ColumnElement[bool]:
    return Product.category.has(Category.slug.in_(FILTER_CATEGORY_SLUGS))


def source_keys(key: str) -> Sequence[str]:
    if key == MATERIAL_FILTER_KEY:
        return MATERIAL_KEYS
    if key == IP_FILTER_KEY:
        return IP_KEYS
    return ()


def _ip_value() -> ColumnElement[str]:
    value = func.upper(ProductAttribute.value)
    value = func.replace(value, "\u0406", "I")
    value = func.replace(value, "\u0420", "P")
    return func.replace(value, " ", "")


def _material_condition(value: str) -> ColumnElement[bool] | None:
    if value == "АБС-пластик":
        return _ABS_MATERIAL
    if value == "Метал":
        return _METAL_MATERIAL
    if value == "Пластик":
        return and_(_PLASTIC_MATERIAL, not_(_ABS_MATERIAL))
    return None


def option_condition(key: str, value: str) -> ColumnElement[bool] | None:
    """Build the raw attribute condition for one normalized filter value."""
    if key == MATERIAL_FILTER_KEY:
        condition = _material_condition(value)
        if condition is not None:
            return and_(
                _category_condition(),
                ProductAttribute.key.in_(MATERIAL_KEYS),
                condition,
            )
    elif key == IP_FILTER_KEY and value in IP_VALUES:
        return and_(
            _category_condition(),
            ProductAttribute.key.in_(IP_KEYS),
            _ip_value() == value,
        )
    return None


def selection_condition(
    key: str, values: set[str]
) -> ColumnElement[bool] | None:
    """Combine selected aliases with OR semantics for one filter group."""
    if key not in {MATERIAL_FILTER_KEY, IP_FILTER_KEY}:
        return None
    conditions = [
        condition
        for value in values
        if (condition := option_condition(key, value)) is not None
    ]
    unknown = values.difference(
        MATERIAL_VALUES if key == MATERIAL_FILTER_KEY else IP_VALUES
    )
    if unknown:
        conditions.append(
            and_(ProductAttribute.key == key, ProductAttribute.value.in_(unknown))
        )
    return or_(*conditions) if conditions else None


def facet_label_expression(key: str) -> ColumnElement[str] | None:
    if key == MATERIAL_FILTER_KEY:
        return case(
            (_ABS_MATERIAL, literal("АБС-пластик")),
            (_METAL_MATERIAL, literal("Метал")),
            (and_(_PLASTIC_MATERIAL, not_(_ABS_MATERIAL)), literal("Пластик")),
        )
    if key == IP_FILTER_KEY:
        return _ip_value()
    return None
