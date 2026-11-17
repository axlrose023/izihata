"""Keep sandbox orders distinguishable after switching to live payments."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a31d72e8c049"
down_revision: str | None = "d77f8ef34d11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "payment_is_test", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "payment_is_test")
