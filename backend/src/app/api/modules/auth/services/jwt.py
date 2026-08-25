from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.api.common.exceptions import UnauthorizedError
from app.api.modules.auth.schema import TokenPairResponse
from app.api.modules.users.models import User
from app.settings import Config


class JwtService:
    def __init__(self, config: Config):
        self._config = config
        self._access_expires_delta = timedelta(
            minutes=config.jwt.access_token_expires_in_minutes
        )
        self._refresh_expires_delta = timedelta(
            minutes=config.jwt.refresh_expires_in_minutes
        )

    def create_token_pair(
        self,
        user: User,
        session_id: UUID,
        refresh_jti: UUID,
        refresh_expires_at: datetime,
    ) -> TokenPairResponse:
        return self.create_token_pair_for_subject(
            subject_id=user.id,
            session_id=session_id,
            refresh_jti=refresh_jti,
            refresh_expires_at=refresh_expires_at,
            actor="staff",
        )

    def create_token_pair_for_subject(
        self,
        *,
        subject_id: UUID,
        session_id: UUID,
        refresh_jti: UUID,
        refresh_expires_at: datetime,
        actor: str,
    ) -> TokenPairResponse:
        access_token, access_expires = self._create_access_token(
            subject_id,
            session_id,
            actor,
        )
        refresh_token, refresh_expires = self._create_refresh_token(
            subject_id,
            session_id,
            refresh_jti,
            refresh_expires_at,
            actor,
        )
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_expires,
            refresh_expires_in=refresh_expires,
        )

    def validate_access_token(self, access_token: str) -> dict:
        payload = self._decode_token(access_token, "access")
        if not payload.get("sub") or not payload.get("sid"):
            raise UnauthorizedError("Invalid access token payload")
        return payload

    def validate_refresh_token(self, refresh_token: str) -> dict:
        payload = self._decode_token(refresh_token, "refresh")
        if not all(payload.get(claim) for claim in ("sub", "sid", "jti")):
            raise UnauthorizedError("Invalid refresh token payload")
        return payload

    def get_refresh_expiration(self) -> datetime:
        return datetime.now(UTC) + self._refresh_expires_delta

    def _decode_token(self, token: str, expected_type: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self._config.jwt.secret_key,
                algorithms=[self._config.jwt.algorithm],
            )
        except ExpiredSignatureError as exc:
            raise UnauthorizedError("Token expired") from exc
        except InvalidTokenError as exc:
            raise UnauthorizedError("Invalid token") from exc

        if payload.get("type") != expected_type:
            raise UnauthorizedError("Invalid token type")

        return payload

    def _create_access_token(
        self,
        subject_id: UUID,
        session_id: UUID,
        actor: str,
    ) -> tuple[str, int]:
        token = self._create_token(
            {
                "sub": str(subject_id),
                "sid": str(session_id),
                "actor": actor,
                "type": "access",
            },
            datetime.now(UTC) + self._access_expires_delta,
        )
        return token, int(self._access_expires_delta.total_seconds())

    def _create_refresh_token(
        self,
        subject_id: UUID,
        session_id: UUID,
        refresh_jti: UUID,
        expires_at: datetime,
        actor: str,
    ) -> tuple[str, int]:
        token = self._create_token(
            {
                "sub": str(subject_id),
                "sid": str(session_id),
                "jti": str(refresh_jti),
                "actor": actor,
                "type": "refresh",
            },
            expires_at,
        )
        return token, int(self._refresh_expires_delta.total_seconds())

    def _create_token(self, payload: dict, expires_at: datetime) -> str:
        complete_payload = {
            **payload,
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(
            complete_payload,
            self._config.jwt.secret_key,
            algorithm=self._config.jwt.algorithm,
        )
