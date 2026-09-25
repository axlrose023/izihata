"""expand product characteristic value length

Revision ID: c3d7f9a2b51e
Revises: a6e4d5f7092b
Create Date: 2026-09-25 14:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d7f9a2b51e"
down_revision: str | None = "a6e4d5f7092b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "product_attributes",
        "value",
        existing_type=sa.String(length=160),
        type_=sa.String(length=300),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "product_attributes",
        "value",
        existing_type=sa.String(length=300),
        type_=sa.String(length=160),
        existing_nullable=False,
    )
