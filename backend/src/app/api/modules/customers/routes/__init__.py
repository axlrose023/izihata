from app.api.modules.customers.routes.admin import router as admin_router
from app.api.modules.customers.routes.auth import router as auth_router
from app.api.modules.customers.routes.user import router as user_router

__all__ = ["admin_router", "auth_router", "user_router"]
