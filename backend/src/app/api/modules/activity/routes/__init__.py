from app.api.modules.activity.routes.admin import router as admin_router
from app.api.modules.activity.routes.user import router as user_router

__all__ = ["admin_router", "user_router"]
