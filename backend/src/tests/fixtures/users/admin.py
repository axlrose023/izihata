import bcrypt
import pytest_asyncio

from app.api.modules.users.models import User
from app.database.uow import UnitOfWork


@pytest_asyncio.fixture
async def user(uow: UnitOfWork) -> User:
    username = "admin"
    existing = await uow.users.get_by_username(username)
    if existing:
        return existing

    hashed_password = bcrypt.hashpw(b"admin123", bcrypt.gensalt(rounds=12)).decode()

    user = User(
        username=username,
        password_hash=hashed_password,
        is_active=True,
    )
    await uow.users.create(user)
    await uow.commit()
    return user
