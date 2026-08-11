from pydantic import ConfigDict, Field, field_validator

from app.api.common.schema import StrictSchema
from app.api.common.utils import normalize_text


class LoginRequest(StrictSchema):
    username: str = Field(min_length=1, max_length=64)
    # Authentication validates credentials, not the password creation policy.
    # Keeping this at one character also permits migrated/legacy test accounts;
    # create-user continues to require a minimum of eight characters.
    password: str = Field(min_length=1, max_length=72)

    model_config = ConfigDict(extra="forbid")

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> str:
        return normalize_text(value)


class TokenPairResponse(StrictSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class AccessTokenResponse(StrictSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
