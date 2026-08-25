from enum import StrEnum


class ProductBadge(StrEnum):
    TOP = "top"
    SALE = "sale"
    NEW = "new"
    PROMOTION = "promotion"
    CLEARANCE = "clearance"
    RECOMMENDED = "recommended"


class StockStatus(StrEnum):
    IN_STOCK_TODAY = "in_stock_today"
    IN_STOCK = "in_stock"
    PREORDER = "preorder"
    OUT_OF_STOCK = "out_of_stock"


class ProductSort(StrEnum):
    POPULAR = "popular"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NEWEST = "newest"
    REVIEWS = "reviews"
    AVAILABILITY = "availability"


class SaleUnit(StrEnum):
    PIECE = "piece"
    METER = "meter"
    COIL = "coil"


class ProductDocumentKind(StrEnum):
    CERTIFICATE = "certificate"
    INSTRUCTION = "instruction"
    DATASHEET = "datasheet"


class ProductRelationKind(StrEnum):
    RELATED = "related"
    ALTERNATIVE = "alternative"
    BOUGHT_TOGETHER = "bought_together"


class AttributeValueType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"


class StockSubscriptionStatus(StrEnum):
    ACTIVE = "active"
    NOTIFIED = "notified"
    CANCELLED = "cancelled"
