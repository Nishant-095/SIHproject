from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import (
    AdvanceWindow,
    AvailabilityStatus,
    DataClass,
    QualityStatus,
)
from app.models.base import CreatedAtMixin
from app.models.types import enum_type, json_type


class RawQuote(CreatedAtMixin, Base):
    __tablename__ = "raw_quotes"
    __table_args__ = (
        UniqueConstraint("collection_job_id", "content_hash", name="uq_raw_job_content"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collection_jobs.id", ondelete="RESTRICT"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    data_class: Mapped[DataClass] = mapped_column(enum_type(DataClass, "raw_data_class"))
    observed_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    query_origin: Mapped[str] = mapped_column(String(8))
    query_destination: Mapped[str] = mapped_column(String(8))
    query_travel_date: Mapped[date] = mapped_column(Date)
    raw_airline_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_flight_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_departure: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_arrival: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_fare_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    raw_base_fare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    raw_tax_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_total_fare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(json_type)
    parser_version: Mapped[str] = mapped_column(String(40))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)


class FareObservation(CreatedAtMixin, Base):
    __tablename__ = "fare_observations"
    __table_args__ = (
        Index("ix_fare_observations_route", "origin_iata", "destination_iata"),
        CheckConstraint("advance_days >= 0", name="ck_observations_advance_nonnegative"),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)",
            name="ck_observations_quality_score_range",
        ),
        CheckConstraint(
            "included_in_index OR exclusion_reason IS NOT NULL",
            name="ck_observations_exclusion_reason",
        ),
        CheckConstraint(
            "total_fare IS NULL OR total_fare >= 0",
            name="ck_observations_total_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    raw_quote_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_quotes.id", ondelete="RESTRICT"), unique=True
    )
    observed_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    methodological_date: Mapped[date] = mapped_column(Date, index=True)
    origin_iata: Mapped[str] = mapped_column(String(3), index=True)
    destination_iata: Mapped[str] = mapped_column(String(3), index=True)
    travel_date: Mapped[date] = mapped_column(Date, index=True)
    advance_days: Mapped[int] = mapped_column(Integer)
    advance_window: Mapped[AdvanceWindow] = mapped_column(
        enum_type(AdvanceWindow, "observation_advance_window"), index=True
    )
    carrier_code: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    carrier_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    departure_time_local: Mapped[time | None] = mapped_column(Time, nullable=True)
    arrival_time_local: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_nonstop: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cabin_class: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fare_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    base_fare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    taxes: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    udf: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    convenience_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    other_fees: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_fare: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    availability: Mapped[AvailabilityStatus] = mapped_column(
        enum_type(AvailabilityStatus, "availability_status")
    )
    flight_identity_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    flight_identity: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    quality_status: Mapped[QualityStatus] = mapped_column(
        enum_type(QualityStatus, "quality_status")
    )
    quality_flags: Mapped[list[str]] = mapped_column(json_type, default=list)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    included_in_index: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    exclusion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalization_version: Mapped[str] = mapped_column(String(40))
