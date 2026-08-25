from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Cookie, Depends, Response, status

from app.api.common.exceptions import UnauthorizedError
from app.api.common.rate_limit import LOGIN_RATE_LIMIT, REFRESH_RATE_LIMIT, RateLimit
from app.api.modules.auth.schema import AccessTokenResponse
from app.api.modules.customers.schema import (
    CustomerLoginRequest,
    CustomerRegistrationRequest,
)
from app.api.modules.customers.service import CustomerAuthenticationService
from app.api.modules.customers.utils import (
    CUSTOMER_REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    expose_access_token,
    set_refresh_cookie,
)
from app.settings import Config

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/register",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit(LOGIN_RATE_LIMIT))],
)
async def register_customer(
    request: CustomerRegistrationRequest,
    response: Response,
    service: FromDishka[CustomerAuthenticationService],
    config: FromDishka[Config],
) -> AccessTokenResponse:
    tokens = await service.register(request)
    set_refresh_cookie(response, tokens, config)
    return expose_access_token(tokens)


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    dependencies=[Depends(RateLimit(LOGIN_RATE_LIMIT))],
)
async def login_customer(
    request: CustomerLoginRequest,
    response: Response,
    service: FromDishka[CustomerAuthenticationService],
    config: FromDishka[Config],
) -> AccessTokenResponse:
    tokens = await service.login(request)
    set_refresh_cookie(response, tokens, config)
    return expose_access_token(tokens)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    dependencies=[Depends(RateLimit(REFRESH_RATE_LIMIT))],
)
async def refresh_customer(
    response: Response,
    service: FromDishka[CustomerAuthenticationService],
    config: FromDishka[Config],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=CUSTOMER_REFRESH_COOKIE_NAME, min_length=1, max_length=4096),
    ] = None,
) -> AccessTokenResponse:
    if refresh_token is None:
        raise UnauthorizedError("Authentication required")
    tokens = await service.refresh(refresh_token)
    set_refresh_cookie(response, tokens, config)
    return expose_access_token(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_customer(
    response: Response,
    service: FromDishka[CustomerAuthenticationService],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=CUSTOMER_REFRESH_COOKIE_NAME, min_length=1, max_length=4096),
    ] = None,
) -> Response:
    if refresh_token is not None:
        await service.logout(refresh_token)
    clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
