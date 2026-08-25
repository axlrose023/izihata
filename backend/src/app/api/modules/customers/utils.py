import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import bcrypt
from fastapi import Response

from app.api.common.exceptions import UnauthorizedError
from app.api.modules.auth.schema import AccessTokenResponse, TokenPairResponse
from app.settings import Config

CUSTOMER_REFRESH_COOKIE_NAME = "izihata_customer_refresh"
CUSTOMER_REFRESH_COOKIE_PATH = "/api/v1/customer-auth"


async def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    return (
        await asyncio.to_thread(bcrypt.hashpw, encoded, bcrypt.gensalt(rounds=12))
    ).decode()


async def password_matches(password: str, password_hash: str) -> bool:
    try:
        return await asyncio.to_thread(
            bcrypt.checkpw,
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


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
        key=CUSTOMER_REFRESH_COOKIE_NAME,
        value=tokens.refresh_token,
        max_age=tokens.refresh_expires_in,
        httponly=True,
        secure=config.env == "prod",
        samesite="lax",
        path=CUSTOMER_REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=CUSTOMER_REFRESH_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        path=CUSTOMER_REFRESH_COOKIE_PATH,
    )


@dataclass(frozen=True, slots=True)
class RefreshTokenIdentity:
    customer_id: UUID
    session_id: UUID
    refresh_jti: UUID


def parse_customer_refresh_identity(
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
            raise ValueError
        return RefreshTokenIdentity(
            customer_id=UUID(subject),
            session_id=UUID(session_id),
            refresh_jti=UUID(refresh_jti),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid refresh token payload") from exc


def is_expired(expires_at: datetime, now: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now
