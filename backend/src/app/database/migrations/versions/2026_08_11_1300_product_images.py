"""add product image URL

Revision ID: 62f5d841c0a7
Revises: 3f6a9c0275db
Create Date: 2026-08-11 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "62f5d841c0a7"
down_revision: str | None = "3f6a9c0275db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(length=500)))


def downgrade() -> None:
    op.drop_column("products", "image_url")
