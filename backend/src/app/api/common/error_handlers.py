import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.common.exceptions import ApplicationError
from app.api.common.public_errors import PUBLIC_PAGE_ROUTE_NAME, public_error_response

logger = logging.getLogger(__name__)


async def application_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse | HTMLResponse:
    if not isinstance(exc, ApplicationError):
        raise exc
    if getattr(request.scope.get("route"), "name", None) == PUBLIC_PAGE_ROUTE_NAME:
        return public_error_response(exc.status_code, exc.headers)
    headers = exc.headers
    if exc.status_code == 401:
        headers = {**(headers or {}), "WWW-Authenticate": "Bearer"}
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.detail},
        headers=headers,
    )


async def http_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    code = {
        404: "not_found",
        405: "method_not_allowed",
    }.get(exc.status_code, "request_failed")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": code,
            "detail": exc.detail if isinstance(exc.detail, str) else "Request failed",
        },
        headers=exc.headers,
    )


async def validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "detail": jsonable_encoder(
                [
                    {key: error[key] for key in ("loc", "msg", "type") if key in error}
                    for error in exc.errors()
                ]
            ),
        },
    )


async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse | HTMLResponse:
    logger.exception(
        "Unhandled request error",
        extra={"method": request.method, "path": request.url.path},
    )
    if getattr(request.scope.get("route"), "name", None) == PUBLIC_PAGE_ROUTE_NAME:
        return public_error_response(500)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "detail": "Internal server error"},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
