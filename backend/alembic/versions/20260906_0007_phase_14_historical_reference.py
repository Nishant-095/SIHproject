"""Add provenance-aware historical reference datasets.

Revision ID: 20260906_0007
Revises: 20260906_0006
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260906_0007"
down_revision: str | Sequence[str] | None = "20260906_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_values(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    uuid_type = sa.Uuid()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "historical_datasets",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("publisher", sa.String(200), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("license_name", sa.String(160), nullable=False),
        sa.Column("metric_name", sa.String(200), nullable=False),
        sa.Column("frequency", sa.String(32), nullable=False),
        sa.Column("base_period", sa.String(80), nullable=True),
        sa.Column(
            "data_class",
            enum_values(
                "LIVE",
                "HISTORICAL",
                "SYNTHETIC",
                "RECORDED_DEMO",
                name="historical_dataset_data_class",
            ),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("content_hash"),
    )
    op.create_index("ix_historical_datasets_code", "historical_datasets", ["code"])
    op.create_table(
        "historical_index_observations",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("dataset_id", uuid_type, nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "scope_type",
            enum_values("NATIONAL", "ROUTE", name="reference_scope"),
            nullable=False,
        ),
        sa.Column("origin_iata", sa.String(3), nullable=True),
        sa.Column("destination_iata", sa.String(3), nullable=True),
        sa.Column("index_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("coverage_percent", sa.Numeric(7, 4), nullable=True),
        sa.Column(
            "status",
            enum_values("FINAL", "PROVISIONAL", name="reference_status"),
            nullable=False,
        ),
        sa.Column("source_record_id", sa.String(160), nullable=False),
        sa.Column("raw_record", json_type, nullable=False),
        sa.CheckConstraint("index_value >= 0", name="ck_historical_index_nonnegative"),
        sa.CheckConstraint(
            "coverage_percent IS NULL OR (coverage_percent >= 0 AND coverage_percent <= 100)",
            name="ck_historical_coverage_range",
        ),
        sa.CheckConstraint(
            "(scope_type = 'NATIONAL' AND origin_iata IS NULL AND destination_iata IS NULL) OR "
            "(scope_type = 'ROUTE' AND origin_iata IS NOT NULL AND destination_iata IS NOT NULL)",
            name="ck_historical_scope_route_fields",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["historical_datasets.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "period_start",
            "scope_type",
            "origin_iata",
            "destination_iata",
            name="uq_historical_index_observation",
        ),
    )
    op.create_index(
        "ix_historical_index_observations_dataset_id",
        "historical_index_observations",
        ["dataset_id"],
    )
    op.create_index(
        "ix_historical_index_observations_period_start",
        "historical_index_observations",
        ["period_start"],
    )
    op.create_index(
        "ix_historical_index_observations_scope_type",
        "historical_index_observations",
        ["scope_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historical_index_observations_scope_type",
        table_name="historical_index_observations",
    )
    op.drop_index(
        "ix_historical_index_observations_period_start",
        table_name="historical_index_observations",
    )
    op.drop_index(
        "ix_historical_index_observations_dataset_id",
        table_name="historical_index_observations",
    )
    op.drop_table("historical_index_observations")
    op.drop_index("ix_historical_datasets_code", table_name="historical_datasets")
    op.drop_table("historical_datasets")
