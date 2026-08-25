from app.api.modules.custom_boards.routes.admin import router as admin_router
from app.api.modules.custom_boards.routes.user import router as user_router

__all__ = ["admin_router", "user_router"]
