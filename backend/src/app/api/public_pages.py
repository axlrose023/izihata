from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.routing import Match
from starlette.types import Scope

from app.api.common.exceptions import ServiceUnavailableError
from app.api.common.rate_limit import CATALOG_LIST_RATE_LIMIT, RateLimit
from app.services.public_pages import PublicPageService


class PublicPageRoute(DishkaRoute):
    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        # Leave API resources, including wrong-method responses, to the API router.
        if scope["path"] == "/api" or scope["path"].startswith("/api/"):
            return Match.NONE, {}
        return super().matches(scope)


router = APIRouter(route_class=PublicPageRoute)


@router.api_route(
    "/{path:path}",
    methods=["GET", "HEAD"],
    name="public_catalog_page",
    include_in_schema=False,
    dependencies=[Depends(RateLimit(CATALOG_LIST_RATE_LIMIT))],
)
async def public_page(
    request: Request, service: FromDishka[PublicPageService], path: str
):
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
