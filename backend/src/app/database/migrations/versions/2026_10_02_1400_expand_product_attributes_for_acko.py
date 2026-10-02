"""allow long supplier characteristics and precise numeric values

Revision ID: 6a72d114ce39
Revises: b413bbcdad25
Create Date: 2026-10-02 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6a72d114ce39"
down_revision: str | None = "b413bbcdad25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "product_attributes",
        "value",
        existing_type=sa.String(length=500),
        type_=sa.String(length=1000),
        existing_nullable=False,
    )
    op.alter_column(
        "product_attributes",
        "numeric_value",
        existing_type=sa.Numeric(14, 4),
        type_=sa.Numeric(16, 6),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "product_attributes",
        "numeric_value",
        existing_type=sa.Numeric(16, 6),
        type_=sa.Numeric(14, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "product_attributes",
        "value",
        existing_type=sa.String(length=1000),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
