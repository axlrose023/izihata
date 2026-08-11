from fastapi import APIRouter


def register_routers(router: APIRouter) -> None:
    from app.api.modules.admin.routes import admin_router
    from app.api.modules.auth.routes import user_router as auth_router
    from app.api.modules.catalog.routes import (
        admin_router as admin_catalog_router,
    )
    from app.api.modules.catalog.routes import (
        user_router as catalog_router,
    )
    from app.api.modules.checkout.routes import user_router as checkout_router
    from app.api.modules.delivery.routes import user_router as delivery_router
    from app.api.modules.leads.routes import (
        admin_router as admin_leads_router,
    )
    from app.api.modules.leads.routes import (
        user_router as leads_router,
    )
    from app.api.modules.orders.routes import (
        admin_router as admin_orders_router,
    )
    from app.api.modules.orders.routes import (
        user_router as orders_router,
    )

    router.include_router(auth_router, prefix="/auth", tags=["Auth"])
    router.include_router(catalog_router, prefix="/catalog", tags=["Catalog"])
    router.include_router(checkout_router, prefix="/checkout", tags=["Checkout"])
    router.include_router(delivery_router, prefix="/delivery", tags=["Delivery"])
    router.include_router(orders_router, prefix="/orders", tags=["Orders"])
    router.include_router(leads_router, prefix="/leads", tags=["Leads"])
    router.include_router(admin_router, prefix="/admin", tags=["Admin"])
    router.include_router(
        admin_catalog_router,
        prefix="/admin/catalog",
        tags=["Admin: catalog"],
    )
    router.include_router(
        admin_orders_router,
        prefix="/admin/orders",
        tags=["Admin: orders"],
    )
    router.include_router(
        admin_leads_router,
        prefix="/admin/leads",
        tags=["Admin: leads"],
    )
