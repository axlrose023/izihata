from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from fastapi import Response

from app.api.common.exceptions import UnauthorizedError
from app.api.modules.auth.schema import AccessTokenResponse, TokenPairResponse
from app.settings import Config

REFRESH_COOKIE_NAME = "izihata_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def expose_access_token(tokens: TokenPairResponse) -> AccessTokenResponse:
    return AccessTokenResponse(
        access_token=tokens.access_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


def set_refresh_cookie(
    response: Response,
    tokens: TokenPairResponse,
    config: Config,
) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=tokens.refresh_token,
        max_age=tokens.refresh_expires_in,
        httponly=True,
        secure=config.env == "prod",
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


@dataclass(frozen=True, slots=True)
class RefreshTokenIdentity:
    user_id: UUID
    session_id: UUID
    refresh_jti: UUID


def parse_refresh_token_identity(
    payload: Mapping[str, object],
) -> RefreshTokenIdentity:
    try:
        subject = payload["sub"]
        session_id = payload["sid"]
        refresh_jti = payload["jti"]
        if (
            not isinstance(subject, str)
            or not isinstance(session_id, str)
            or not isinstance(refresh_jti, str)
        ):
            raise ValueError("Refresh token identity claims must be strings")
        return RefreshTokenIdentity(
            user_id=UUID(subject),
            session_id=UUID(session_id),
            refresh_jti=UUID(refresh_jti),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid refresh token payload") from exc
