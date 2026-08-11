from enum import StrEnum


class DeliveryMethod(StrEnum):
    NOVA_POSHTA_BRANCH = "nova_poshta_branch"
    NOVA_POSHTA_LOCKER = "nova_poshta_locker"
    PICKUP = "pickup"


class PaymentMethod(StrEnum):
    CARD = "card"
    CASH_ON_DELIVERY = "cash_on_delivery"
    INVOICE = "invoice"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    NOT_REQUIRED = "not_required"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderStatus(StrEnum):
    NEW = "new"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
