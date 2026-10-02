"""allow long supplier product characteristics

Revision ID: b413bbcdad25
Revises: c3d7f9a2b51e
Create Date: 2026-10-02 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b413bbcdad25"
down_revision: str | None = "c3d7f9a2b51e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "product_attributes",
        "value",
        existing_type=sa.String(length=300),
        type_=sa.String(length=500),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "product_attributes",
        "value",
        existing_type=sa.String(length=500),
        type_=sa.String(length=300),
        existing_nullable=False,
    )
