from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.common.exceptions import ServiceUnavailableError
from app.api.common.rate_limit import CATALOG_LIST_RATE_LIMIT, RateLimit
from app.services.public_pages import PublicPageService

router = APIRouter(route_class=DishkaRoute)


@router.api_route(
    "/{path:path}",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
    dependencies=[Depends(RateLimit(CATALOG_LIST_RATE_LIMIT))],
)
async def public_page(
    request: Request, service: FromDishka[PublicPageService], path: str
):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {"code": "not_found", "detail": "Not Found"}, status_code=404
        )
    if request.method not in {"GET", "HEAD"}:
        return JSONResponse(
            {"code": "method_not_allowed", "detail": "Method Not Allowed"},
            status_code=405,
            headers={"Allow": "GET, HEAD"},
        )
    try:
        content, status = await service.page(request.url.path, request.url.query)
    except (ServiceUnavailableError, SQLAlchemyError):
        return HTMLResponse(
            '<!doctype html><html lang="uk"><title>Сайт оновлюється | IZI HATA</title><h1>Сайт оновлюється</h1><p>Спробуйте трохи пізніше.</p></html>',
            status_code=503,
            headers={"Retry-After": "5", "Cache-Control": "no-store"},
        )
    return HTMLResponse(
        content, status_code=status, headers={"Cache-Control": "no-cache"}
    )
