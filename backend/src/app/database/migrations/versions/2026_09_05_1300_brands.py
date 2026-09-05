"""add manufacturer brands

Revision ID: d13a8c4e5f60
Revises: c92f7b6d1a34
Create Date: 2026-09-05 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.api.modules.catalog.utils import slugify

revision: str = "d13a8c4e5f60"
down_revision: str | None = "c92f7b6d1a34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("slug", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("brands_pkey")),
    )
    op.create_index(op.f("brands_slug_idx"), "brands", ["slug"], unique=True)
    op.create_index(op.f("brands_name_idx"), "brands", ["name"], unique=True)

    # Backfill from the brands products already carry, so the storefront has
    # a complete list from the first deploy.
    connection = op.get_bind()
    names = [
        row[0]
        for row in connection.execute(
            sa.text("SELECT DISTINCT brand FROM products WHERE brand <> ''")
        )
    ]
    seen: set[str] = set()
    rows = []
    for position, name in enumerate(sorted(names)):
        slug = slugify(name) or f"brand-{position}"
        candidate, suffix = slug, 2
        while candidate in seen:
            candidate = f"{slug}-{suffix}"
            suffix += 1
        seen.add(candidate)
        rows.append({"slug": candidate, "name": name, "position": position})
    if rows:
        connection.execute(
            sa.text(
                "INSERT INTO brands (id, slug, name, position, is_active)"
                " VALUES (gen_random_uuid(), :slug, :name, :position, true)"
            ),
            rows,
        )


def downgrade() -> None:
    op.drop_index(op.f("brands_name_idx"), table_name="brands")
    op.drop_index(op.f("brands_slug_idx"), table_name="brands")
    op.drop_table("brands")
