"""Add Phase 8 basket, aggregation, and APIx persistence.

Revision ID: 20260905_0005
Revises: 20260905_0004
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260905_0005"
down_revision: str | Sequence[str] | None = "20260905_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_values(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    uuid_type = sa.Uuid()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    data_classes = ("LIVE", "HISTORICAL", "SYNTHETIC", "RECORDED_DEMO")
    windows = ("T1", "T7", "T15", "T30", "T45", "OTHER")

    op.create_table(
        "basket_versions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "data_class",
            enum_values(*data_classes, name="basket_data_class"),
            nullable=False,
        ),
        sa.Column("base_policy", sa.String(length=80), nullable=False),
        sa.Column("base_start_date", sa.Date(), nullable=True),
        sa.Column("base_end_date", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_basket_versions_active", "basket_versions", ["active"], unique=False)
    op.create_index("ix_basket_versions_version", "basket_versions", ["version"], unique=True)

    op.create_table(
        "basket_items",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("basket_version_id", uuid_type, nullable=False),
        sa.Column("route_id", uuid_type, nullable=False),
        sa.Column(
            "advance_window",
            enum_values(*windows, name="basket_advance_window"),
            nullable=False,
        ),
        sa.Column("weight", sa.Numeric(precision=20, scale=12), nullable=False),
        sa.Column("base_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("base_component_ids", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "base_price IS NULL OR base_price > 0",
            name="ck_basket_item_base_positive",
        ),
        sa.CheckConstraint("weight > 0", name="ck_basket_item_weight_positive"),
        sa.ForeignKeyConstraint(
            ["basket_version_id"], ["basket_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "basket_version_id",
            "route_id",
            "advance_window",
            name="uq_basket_item_dimension",
        ),
    )
    op.create_index(
        "ix_basket_items_advance_window", "basket_items", ["advance_window"], unique=False
    )
    op.create_index(
        "ix_basket_items_basket_version_id",
        "basket_items",
        ["basket_version_id"],
        unique=False,
    )
    op.create_index("ix_basket_items_route_id", "basket_items", ["route_id"], unique=False)

    op.create_table(
        "daily_route_window_prices",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("collection_run_id", uuid_type, nullable=False),
        sa.Column("methodological_date", sa.Date(), nullable=False),
        sa.Column(
            "data_class",
            enum_values(*data_classes, name="daily_price_data_class"),
            nullable=False,
        ),
        sa.Column("basket_item_id", uuid_type, nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("eligible_flight_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("aggregation_version", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "eligible_flight_count >= 0",
            name="ck_daily_price_count_nonnegative",
        ),
        sa.CheckConstraint("price IS NULL OR price > 0", name="ck_daily_price_positive"),
        sa.ForeignKeyConstraint(
            ["basket_item_id"], ["basket_items.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["collection_run_id"], ["collection_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "methodological_date",
            "data_class",
            "basket_item_id",
            "aggregation_version",
            name="uq_daily_route_window_price",
        ),
    )
    op.create_index(
        "ix_daily_route_window_prices_basket_item_id",
        "daily_route_window_prices",
        ["basket_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_route_window_prices_collection_run_id",
        "daily_route_window_prices",
        ["collection_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_route_window_prices_methodological_date",
        "daily_route_window_prices",
        ["methodological_date"],
        unique=False,
    )

    op.create_table(
        "route_window_price_inputs",
        sa.Column("daily_route_window_price_id", uuid_type, nullable=False),
        sa.Column("canonical_fare_id", uuid_type, nullable=False),
        sa.ForeignKeyConstraint(
            ["canonical_fare_id"], ["canonical_fares.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["daily_route_window_price_id"],
            ["daily_route_window_prices.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("daily_route_window_price_id", "canonical_fare_id"),
    )

    op.create_table(
        "daily_indices",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("collection_run_id", uuid_type, nullable=False),
        sa.Column("methodological_date", sa.Date(), nullable=False),
        sa.Column(
            "data_class",
            enum_values(*data_classes, name="daily_index_data_class"),
            nullable=False,
        ),
        sa.Column("basket_version_id", uuid_type, nullable=False),
        sa.Column("methodology_version", sa.String(length=80), nullable=False),
        sa.Column("canonicalization_version", sa.String(length=80), nullable=False),
        sa.Column("index_value", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("coverage_percent", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column(
            "publication_status",
            enum_values(
                "PUBLISHED",
                "INSUFFICIENT_COVERAGE",
                "PROVISIONAL_BASE",
                "FAILED",
                name="publication_status",
            ),
            nullable=False,
        ),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "coverage_percent >= 0 AND coverage_percent <= 100",
            name="ck_daily_index_coverage_range",
        ),
        sa.CheckConstraint(
            "index_value IS NULL OR index_value >= 0",
            name="ck_daily_index_value_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["basket_version_id"], ["basket_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["collection_run_id"], ["collection_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "methodological_date",
            "data_class",
            "basket_version_id",
            "methodology_version",
            name="uq_daily_index_version",
        ),
    )
    op.create_index(
        "ix_daily_indices_basket_version_id",
        "daily_indices",
        ["basket_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_indices_collection_run_id",
        "daily_indices",
        ["collection_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_indices_methodological_date",
        "daily_indices",
        ["methodological_date"],
        unique=False,
    )
    op.create_index(
        "ix_daily_indices_publication_status",
        "daily_indices",
        ["publication_status"],
        unique=False,
    )

    op.create_table(
        "daily_index_components",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("daily_index_id", uuid_type, nullable=False),
        sa.Column("basket_item_id", uuid_type, nullable=False),
        sa.Column("daily_route_window_price_id", uuid_type, nullable=True),
        sa.Column("current_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("base_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("price_relative", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("configured_weight", sa.Numeric(precision=20, scale=12), nullable=False),
        sa.Column("effective_weight", sa.Numeric(precision=20, scale=12), nullable=True),
        sa.Column("contribution", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("availability_reason", sa.String(length=48), nullable=False),
        sa.CheckConstraint(
            "configured_weight > 0",
            name="ck_index_component_weight_positive",
        ),
        sa.CheckConstraint(
            "effective_weight IS NULL OR effective_weight >= 0",
            name="ck_index_component_effective_weight_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["basket_item_id"], ["basket_items.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["daily_index_id"], ["daily_indices.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["daily_route_window_price_id"],
            ["daily_route_window_prices.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_index_id",
            "basket_item_id",
            name="uq_daily_index_component_item",
        ),
    )
    op.create_index(
        "ix_daily_index_components_basket_item_id",
        "daily_index_components",
        ["basket_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_daily_index_components_daily_index_id",
        "daily_index_components",
        ["daily_index_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_daily_index_components_daily_index_id", table_name="daily_index_components"
    )
    op.drop_index(
        "ix_daily_index_components_basket_item_id", table_name="daily_index_components"
    )
    op.drop_table("daily_index_components")
    op.drop_index("ix_daily_indices_publication_status", table_name="daily_indices")
    op.drop_index("ix_daily_indices_methodological_date", table_name="daily_indices")
    op.drop_index("ix_daily_indices_collection_run_id", table_name="daily_indices")
    op.drop_index("ix_daily_indices_basket_version_id", table_name="daily_indices")
    op.drop_table("daily_indices")
    op.drop_table("route_window_price_inputs")
    op.drop_index(
        "ix_daily_route_window_prices_methodological_date",
        table_name="daily_route_window_prices",
    )
    op.drop_index(
        "ix_daily_route_window_prices_collection_run_id",
        table_name="daily_route_window_prices",
    )
    op.drop_index(
        "ix_daily_route_window_prices_basket_item_id",
        table_name="daily_route_window_prices",
    )
    op.drop_table("daily_route_window_prices")
    op.drop_index("ix_basket_items_route_id", table_name="basket_items")
    op.drop_index("ix_basket_items_basket_version_id", table_name="basket_items")
    op.drop_index("ix_basket_items_advance_window", table_name="basket_items")
    op.drop_table("basket_items")
    op.drop_index("ix_basket_versions_version", table_name="basket_versions")
    op.drop_index("ix_basket_versions_active", table_name="basket_versions")
    op.drop_table("basket_versions")
