import asyncio
from datetime import UTC, datetime

import bcrypt


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


def is_expired(expires_at: datetime, now: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= now
