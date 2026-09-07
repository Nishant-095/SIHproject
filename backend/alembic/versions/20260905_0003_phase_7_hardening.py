"""Add Phase 7 query indexes.

Revision ID: 20260905_0003
Revises: 1956ba44f923
Create Date: 2026-09-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260905_0003"
down_revision: str | Sequence[str] | None = "1956ba44f923"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_fare_observations_carrier_code",
        "fare_observations",
        ["carrier_code"],
        unique=False,
    )
    op.create_index(
        "ix_fare_observations_route",
        "fare_observations",
        ["origin_iata", "destination_iata"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fare_observations_route", table_name="fare_observations")
    op.drop_index("ix_fare_observations_carrier_code", table_name="fare_observations")
