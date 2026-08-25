"""extend catalogue for technical product content

Revision ID: a8d13c9be721
Revises: 9c15fdac51fe
Create Date: 2026-08-25 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8d13c9be721"
down_revision: str | None = "9c15fdac51fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_sections",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("catalog_sections_pkey")),
    )
    op.create_index(
        op.f("catalog_sections_slug_idx"),
        "catalog_sections",
        ["slug"],
        unique=True,
    )
    op.add_column("categories", sa.Column("section_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("categories_section_id_fkey"),
        "categories",
        "catalog_sections",
        ["section_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("categories_section_id_idx"), "categories", ["section_id"])

    op.add_column("products", sa.Column("brand_country", sa.String(length=120)))
    op.add_column("products", sa.Column("production_country", sa.String(length=120)))
    op.add_column("products", sa.Column("short_description", sa.String(length=500)))
    op.add_column("products", sa.Column("description", sa.Text()))
    op.add_column("products", sa.Column("availability_days", sa.Integer()))
    op.add_column(
        "products",
        sa.Column(
            "sale_unit",
            sa.Enum(
                "PIECE",
                "METER",
                "COIL",
                name="saleunit",
                native_enum=False,
                length=16,
            ),
            server_default="PIECE",
            nullable=False,
        ),
    )
    op.add_column("products", sa.Column("wholesale_price", sa.Numeric(12, 2)))
    op.add_column("products", sa.Column("wholesale_min_quantity", sa.Integer()))
    op.create_check_constraint(
        op.f("products_product_wholesale_price_non_negative_check"),
        "products",
        "wholesale_price IS NULL OR wholesale_price >= 0",
    )
    op.create_check_constraint(
        op.f("products_product_wholesale_min_quantity_positive_check"),
        "products",
        "wholesale_min_quantity IS NULL OR wholesale_min_quantity > 0",
    )

    op.create_table(
        "catalog_attributes",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "value_type",
            sa.Enum(
                "TEXT",
                "NUMBER",
                "BOOLEAN",
                "SELECT",
                name="attributevaluetype",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("is_filterable", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("catalog_attributes_pkey")),
    )
    op.create_index(
        op.f("catalog_attributes_code_idx"),
        "catalog_attributes",
        ["code"],
        unique=True,
    )
    op.create_table(
        "category_attributes",
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("attribute_id", sa.UUID(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("is_primary_filter", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["catalog_attributes.id"],
            name=op.f("category_attributes_attribute_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("category_attributes_category_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("category_attributes_pkey")),
        sa.UniqueConstraint(
            "category_id",
            "attribute_id",
            name="category_attribute_category_attribute_ukey",
        ),
    )
    op.create_index(
        op.f("category_attributes_category_id_idx"),
        "category_attributes",
        ["category_id"],
    )
    op.create_index(
        op.f("category_attributes_attribute_id_idx"),
        "category_attributes",
        ["attribute_id"],
    )
    op.add_column("product_attributes", sa.Column("attribute_id", sa.UUID()))
    op.add_column("product_attributes", sa.Column("numeric_value", sa.Numeric(14, 4)))
    op.create_foreign_key(
        op.f("product_attributes_attribute_id_fkey"),
        "product_attributes",
        "catalog_attributes",
        ["attribute_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("product_attributes_attribute_id_idx"),
        "product_attributes",
        ["attribute_id"],
    )

    op.create_table(
        "product_media",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("alt", sa.String(length=240), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("product_media_product_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("product_media_pkey")),
        sa.UniqueConstraint(
            "product_id",
            "position",
            name="product_media_position_ukey",
        ),
    )
    op.create_index(
        op.f("product_media_product_id_idx"), "product_media", ["product_id"]
    )
    op.create_table(
        "product_documents",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "CERTIFICATE",
                "INSTRUCTION",
                "DATASHEET",
                name="productdocumentkind",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("product_documents_product_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("product_documents_pkey")),
        sa.UniqueConstraint(
            "product_id",
            "position",
            name="product_document_position_ukey",
        ),
    )
    op.create_index(
        op.f("product_documents_product_id_idx"),
        "product_documents",
        ["product_id"],
    )
    op.create_table(
        "product_relations",
        sa.Column("source_product_id", sa.UUID(), nullable=False),
        sa.Column("target_product_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "RELATED",
                "ALTERNATIVE",
                "BOUGHT_TOGETHER",
                name="productrelationkind",
                native_enum=False,
                length=24,
            ),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "source_product_id <> target_product_id",
            name=op.f("product_relations_product_relation_distinct_products_check"),
        ),
        sa.ForeignKeyConstraint(
            ["source_product_id"],
            ["products.id"],
            name=op.f("product_relations_source_product_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_product_id"],
            ["products.id"],
            name=op.f("product_relations_target_product_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("product_relations_pkey")),
        sa.UniqueConstraint(
            "source_product_id",
            "target_product_id",
            "kind",
            name="product_relation_identity_ukey",
        ),
    )
    op.create_index(
        op.f("product_relations_source_product_id_idx"),
        "product_relations",
        ["source_product_id"],
    )
    op.create_index(
        op.f("product_relations_target_product_id_idx"),
        "product_relations",
        ["target_product_id"],
    )
    op.create_table(
        "product_stock_subscriptions",
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "NOTIFIED",
                "CANCELLED",
                name="stocksubscriptionstatus",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("product_stock_subscriptions_product_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("product_stock_subscriptions_pkey")),
        sa.UniqueConstraint(
            "product_id",
            "email",
            name="product_stock_subscription_product_email_ukey",
        ),
    )
    op.create_index(
        op.f("product_stock_subscriptions_product_id_idx"),
        "product_stock_subscriptions",
        ["product_id"],
    )
    op.create_index(
        op.f("product_stock_subscriptions_status_idx"),
        "product_stock_subscriptions",
        ["status"],
    )
    op.add_column("product_reviews", sa.Column("email", sa.String(length=254)))
    op.add_column(
        "product_reviews",
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PUBLISHED",
                "REJECTED",
                name="reviewstatus",
                native_enum=False,
                length=16,
            ),
            server_default="PUBLISHED",
            nullable=False,
        ),
    )
    op.create_index(op.f("product_reviews_status_idx"), "product_reviews", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("product_reviews_status_idx"), table_name="product_reviews")
    op.drop_column("product_reviews", "status")
    op.drop_column("product_reviews", "email")
    op.drop_index(
        op.f("product_stock_subscriptions_status_idx"),
        table_name="product_stock_subscriptions",
    )
    op.drop_index(
        op.f("product_stock_subscriptions_product_id_idx"),
        table_name="product_stock_subscriptions",
    )
    op.drop_table("product_stock_subscriptions")
    op.drop_index(
        op.f("product_relations_target_product_id_idx"), table_name="product_relations"
    )
    op.drop_index(
        op.f("product_relations_source_product_id_idx"), table_name="product_relations"
    )
    op.drop_table("product_relations")
    op.drop_index(
        op.f("product_documents_product_id_idx"), table_name="product_documents"
    )
    op.drop_table("product_documents")
    op.drop_index(op.f("product_media_product_id_idx"), table_name="product_media")
    op.drop_table("product_media")
    op.drop_index(
        op.f("product_attributes_attribute_id_idx"), table_name="product_attributes"
    )
    op.drop_constraint(
        op.f("product_attributes_attribute_id_fkey"),
        "product_attributes",
        type_="foreignkey",
    )
    op.drop_column("product_attributes", "numeric_value")
    op.drop_column("product_attributes", "attribute_id")
    op.drop_index(
        op.f("category_attributes_attribute_id_idx"), table_name="category_attributes"
    )
    op.drop_index(
        op.f("category_attributes_category_id_idx"), table_name="category_attributes"
    )
    op.drop_table("category_attributes")
    op.drop_index(op.f("catalog_attributes_code_idx"), table_name="catalog_attributes")
    op.drop_table("catalog_attributes")
    op.drop_constraint(
        op.f("products_product_wholesale_min_quantity_positive_check"),
        "products",
        type_="check",
    )
    op.drop_constraint(
        op.f("products_product_wholesale_price_non_negative_check"),
        "products",
        type_="check",
    )
    op.drop_column("products", "wholesale_min_quantity")
    op.drop_column("products", "wholesale_price")
    op.drop_column("products", "sale_unit")
    op.drop_column("products", "availability_days")
    op.drop_column("products", "description")
    op.drop_column("products", "short_description")
    op.drop_column("products", "production_country")
    op.drop_column("products", "brand_country")
    op.drop_index(op.f("categories_section_id_idx"), table_name="categories")
    op.drop_constraint(
        op.f("categories_section_id_fkey"), "categories", type_="foreignkey"
    )
    op.drop_column("categories", "section_id")
    op.drop_index(op.f("catalog_sections_slug_idx"), table_name="catalog_sections")
    op.drop_table("catalog_sections")
