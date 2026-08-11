from enum import StrEnum


class ProductBadge(StrEnum):
    TOP = "top"
    SALE = "sale"
    NEW = "new"


class StockStatus(StrEnum):
    IN_STOCK = "in_stock"
    PREORDER = "preorder"


class ProductSort(StrEnum):
    POPULAR = "popular"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NEWEST = "newest"
