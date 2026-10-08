"""Require each customer phone number to identify one account."""

from collections.abc import Sequence

from alembic import op

revision: str = "c58af6b2d091"
down_revision: str | None = "a07d6c219e54"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        op.f("customers_phone_idx"),
        "customers",
        ["phone"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("customers_phone_idx"), table_name="customers")
