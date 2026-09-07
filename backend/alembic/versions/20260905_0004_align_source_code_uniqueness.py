"""Align source-code uniqueness with the SQLAlchemy model.

Revision ID: 20260905_0004
Revises: 20260905_0003
Create Date: 2026-09-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260905_0004"
down_revision: str | Sequence[str] | None = "20260905_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The unique index ix_sources_code already enforces the same rule.
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint("sources_code_key", "sources", type_="unique")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.create_unique_constraint("sources_code_key", "sources", ["code"])
