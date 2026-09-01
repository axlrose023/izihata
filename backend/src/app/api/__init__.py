from fastapi import APIRouter


def register_routers(router: APIRouter) -> None:
    from app.api.modules.activity.routes import (
        admin_router as admin_activity_router,
    )
    from app.api.modules.activity.routes import user_router as activity_router
    from app.api.modules.admin.routes import admin_router
    from app.api.modules.advisors.routes import user_router as advisors_router
    from app.api.modules.auth.routes import user_router as auth_router
    from app.api.modules.catalog.routes import (
        admin_router as admin_catalog_router,
    )
    from app.api.modules.catalog.routes import (
        user_router as catalog_router,
    )
    from app.api.modules.checkout.routes import user_router as checkout_router
    from app.api.modules.custom_boards.routes import (
        admin_router as admin_custom_boards_router,
    )
    from app.api.modules.custom_boards.routes import user_router as custom_boards_router
    from app.api.modules.customers.routes import admin_router as admin_customers_router
    from app.api.modules.customers.routes import auth_router as customer_auth_router
    from app.api.modules.customers.routes import user_router as customers_router
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
    router.include_router(
        customer_auth_router,
        prefix="/customer-auth",
        tags=["Customer auth"],
    )
    router.include_router(activity_router, prefix="/activity", tags=["Activity"])
    router.include_router(advisors_router, prefix="/advisors", tags=["Advisors"])
    router.include_router(catalog_router, prefix="/catalog", tags=["Catalog"])
    router.include_router(checkout_router, prefix="/checkout", tags=["Checkout"])
    router.include_router(delivery_router, prefix="/delivery", tags=["Delivery"])
    router.include_router(
        custom_boards_router,
        prefix="/custom-boards",
        tags=["Custom boards"],
    )
    router.include_router(customers_router, prefix="/customer", tags=["Customer"])
    router.include_router(orders_router, prefix="/orders", tags=["Orders"])
    router.include_router(leads_router, prefix="/leads", tags=["Leads"])
    router.include_router(admin_router, prefix="/admin", tags=["Admin"])
    router.include_router(
        admin_activity_router,
        prefix="/admin/activity",
        tags=["Admin: activity"],
    )
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
    router.include_router(
        admin_custom_boards_router,
        prefix="/admin/custom-boards",
        tags=["Admin: custom boards"],
    )
    router.include_router(
        admin_customers_router,
        prefix="/admin/customers",
        tags=["Admin: customers"],
    )
