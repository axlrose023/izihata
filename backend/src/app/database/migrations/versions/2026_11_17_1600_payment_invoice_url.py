"""Persist the reusable provider-hosted payment invoice."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c614ab2ed04f"
down_revision: str | None = "a31d72e8c049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payment_attempts", sa.Column("invoice_url", sa.String(512)))


def downgrade() -> None:
    op.drop_column("payment_attempts", "invoice_url")
