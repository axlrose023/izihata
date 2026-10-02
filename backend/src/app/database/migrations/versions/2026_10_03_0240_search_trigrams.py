"""Complete trigram indexes for the existing three-column catalog search."""

from collections.abc import Sequence

from alembic import op

revision: str = "0a52f370c164"
down_revision: str | None = "96b47f52d109"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for column in ("brand", "sku"):
            op.create_index(
                f"products_{column}_trgm_idx",
                "products",
                [column],
                postgresql_using="gin",
                postgresql_ops={column: "gin_trgm_ops"},
                postgresql_concurrently=True,
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for column in ("brand", "sku"):
            op.drop_index(
                f"products_{column}_trgm_idx",
                table_name="products",
                postgresql_concurrently=True,
            )
