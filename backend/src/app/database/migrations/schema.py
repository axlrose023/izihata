"""Schema reflection rules for explicitly migration-owned rollback archives."""

from alembic.runtime.environment import NameFilterParentNames, NameFilterType

MIGRATION_ARCHIVE_TABLES = frozenset(
    {
        "product_category_before_breaker_fix",
        "power_supply_subcategory_before_move",
        "product_categories_before_power_supply_move",
        "product_categories_before_electrical_taxonomy",
        "subcategories_created_by_electrical_taxonomy",
        "product_categories_before_shrink_tube_sets",
    }
)


def include_schema_name(
    name: str | None, type_: NameFilterType, parent_names: NameFilterParentNames
) -> bool:
    """Ignore known archives without hiding unrelated schema drift."""
    return type_ != "table" or name not in MIGRATION_ARCHIVE_TABLES
