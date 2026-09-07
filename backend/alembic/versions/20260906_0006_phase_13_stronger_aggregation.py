"""Add persisted Phase 13 period aggregates.

Revision ID: 20260906_0006
Revises: 20260905_0005
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260906_0006"
down_revision: str | Sequence[str] | None = "20260905_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_values(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    uuid_type = sa.Uuid()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    data_classes = ("LIVE", "HISTORICAL", "SYNTHETIC", "RECORDED_DEMO")
    op.create_table(
        "period_indices",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column(
            "data_class",
            enum_values(*data_classes, name="period_data_class"),
            nullable=False,
        ),
        sa.Column("basket_version_id", uuid_type, nullable=False),
        sa.Column(
            "period_type",
            enum_values("WEEKLY", "MONTHLY", name="aggregation_period"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("methodology_version", sa.String(length=80), nullable=False),
        sa.Column("missing_data_policy", sa.String(length=80), nullable=False),
        sa.Column("index_value", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("average_coverage_percent", sa.Numeric(7, 4), nullable=False),
        sa.Column("minimum_coverage_percent", sa.Numeric(7, 4), nullable=False),
        sa.Column("expected_day_count", sa.Integer(), nullable=False),
        sa.Column("observed_day_count", sa.Integer(), nullable=False),
        sa.Column("valued_day_count", sa.Integer(), nullable=False),
        sa.Column("low_coverage_day_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column(
            "confidence_level",
            enum_values("HIGH", "MEDIUM", "LOW", "INSUFFICIENT", name="confidence_level"),
            nullable=False,
        ),
        sa.Column(
            "aggregation_status",
            enum_values(
                "COMPLETE",
                "PARTIAL",
                "INSUFFICIENT_COVERAGE",
                "NO_DATA",
                name="aggregation_status",
            ),
            nullable=False,
        ),
        sa.Column("warnings", json_type, nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("index_value IS NULL OR index_value >= 0", name="ck_period_index_value"),
        sa.CheckConstraint(
            "average_coverage_percent >= 0 AND average_coverage_percent <= 100",
            name="ck_period_average_coverage",
        ),
        sa.CheckConstraint(
            "minimum_coverage_percent >= 0 AND minimum_coverage_percent <= 100",
            name="ck_period_minimum_coverage",
        ),
        sa.CheckConstraint("expected_day_count > 0", name="ck_period_expected_days"),
        sa.CheckConstraint("observed_day_count >= 0", name="ck_period_observed_days"),
        sa.CheckConstraint("valued_day_count >= 0", name="ck_period_valued_days"),
        sa.CheckConstraint("low_coverage_day_count >= 0", name="ck_period_low_coverage_days"),
        sa.CheckConstraint("source_count >= 0", name="ck_period_source_count"),
        sa.ForeignKeyConstraint(["basket_version_id"], ["basket_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "data_class",
            "basket_version_id",
            "period_type",
            "period_start",
            "methodology_version",
            name="uq_period_index_version",
        ),
    )
    op.create_index("ix_period_indices_basket_version_id", "period_indices", ["basket_version_id"])
    op.create_index("ix_period_indices_period_type", "period_indices", ["period_type"])
    op.create_index("ix_period_indices_period_start", "period_indices", ["period_start"])
    op.create_index(
        "ix_period_indices_aggregation_status", "period_indices", ["aggregation_status"]
    )
    op.create_table(
        "period_index_inputs",
        sa.Column("period_index_id", uuid_type, nullable=False),
        sa.Column("daily_index_id", uuid_type, nullable=False),
        sa.ForeignKeyConstraint(["period_index_id"], ["period_indices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["daily_index_id"], ["daily_indices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("period_index_id", "daily_index_id"),
    )


def downgrade() -> None:
    op.drop_table("period_index_inputs")
    op.drop_index("ix_period_indices_aggregation_status", table_name="period_indices")
    op.drop_index("ix_period_indices_period_start", table_name="period_indices")
    op.drop_index("ix_period_indices_period_type", table_name="period_indices")
    op.drop_index("ix_period_indices_basket_version_id", table_name="period_indices")
    op.drop_table("period_indices")
