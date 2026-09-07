from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import AdvanceWindow
from app.models.base import CreatedAtMixin
from app.models.types import enum_type


class CanonicalFare(CreatedAtMixin, Base):
    __tablename__ = "canonical_fares"
    __table_args__ = (
        CheckConstraint(
            "representative_total_fare >= 0",
            name="ck_canonical_representative_nonnegative",
        ),
        CheckConstraint("minimum_total_fare >= 0", name="ck_canonical_minimum_nonnegative"),
        CheckConstraint("maximum_total_fare >= minimum_total_fare", name="ck_canonical_range"),
        CheckConstraint("dispersion_amount >= 0", name="ck_canonical_dispersion_nonnegative"),
        CheckConstraint("source_count > 0", name="ck_canonical_source_count_positive"),
        CheckConstraint("observation_count > 0", name="ck_canonical_observation_count_positive"),
        UniqueConstraint(
            "collection_run_id",
            "route_id",
            "advance_window",
            "flight_identity",
            "cabin_class",
            "fare_class",
            "currency",
            name="uq_canonical_fare_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="RESTRICT"), index=True
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routes.id", ondelete="RESTRICT"), index=True
    )
    advance_window: Mapped[AdvanceWindow] = mapped_column(
        enum_type(AdvanceWindow, "canonical_advance_window"), index=True
    )
    flight_identity: Mapped[str] = mapped_column(String(64), index=True)
    cabin_class: Mapped[str] = mapped_column(String(40))
    fare_class: Mapped[str] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(3))
    representative_total_fare: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    minimum_total_fare: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    maximum_total_fare: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    dispersion_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    source_count: Mapped[int] = mapped_column(Integer)
    observation_count: Mapped[int] = mapped_column(Integer)
    has_source_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    selection_reason: Mapped[str] = mapped_column(String(40))
    method_version: Mapped[str] = mapped_column(String(40))


class CanonicalFareObservation(Base):
    __tablename__ = "canonical_fare_observations"

    canonical_fare_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_fares.id", ondelete="CASCADE"), primary_key=True
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fare_observations.id", ondelete="RESTRICT"),
        primary_key=True,
        unique=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    source_total_fare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    role: Mapped[str] = mapped_column(String(32))
