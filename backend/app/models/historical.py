from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import DataClass, ReferenceScope, ReferenceStatus
from app.models.base import utc_now
from app.models.types import enum_type, json_type


class HistoricalDataset(Base):
    __tablename__ = "historical_datasets"
    __table_args__ = (UniqueConstraint("code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(240))
    publisher: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(Text)
    license_name: Mapped[str] = mapped_column(String(160))
    metric_name: Mapped[str] = mapped_column(String(200))
    frequency: Mapped[str] = mapped_column(String(32))
    base_period: Mapped[str | None] = mapped_column(String(80), nullable=True)
    data_class: Mapped[DataClass] = mapped_column(
        enum_type(DataClass, "historical_dataset_data_class"), default=DataClass.HISTORICAL
    )
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    row_count: Mapped[int] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class HistoricalIndexObservation(Base):
    __tablename__ = "historical_index_observations"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "period_start",
            "scope_type",
            "origin_iata",
            "destination_iata",
            name="uq_historical_index_observation",
        ),
        CheckConstraint("index_value >= 0", name="ck_historical_index_nonnegative"),
        CheckConstraint(
            "coverage_percent IS NULL OR (coverage_percent >= 0 AND coverage_percent <= 100)",
            name="ck_historical_coverage_range",
        ),
        CheckConstraint(
            "(scope_type = 'NATIONAL' AND origin_iata IS NULL AND destination_iata IS NULL) OR "
            "(scope_type = 'ROUTE' AND origin_iata IS NOT NULL AND destination_iata IS NOT NULL)",
            name="ck_historical_scope_route_fields",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("historical_datasets.id", ondelete="RESTRICT"), index=True
    )
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date)
    scope_type: Mapped[ReferenceScope] = mapped_column(
        enum_type(ReferenceScope, "reference_scope"), index=True
    )
    origin_iata: Mapped[str | None] = mapped_column(String(3), nullable=True)
    destination_iata: Mapped[str | None] = mapped_column(String(3), nullable=True)
    index_value: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    coverage_percent: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    status: Mapped[ReferenceStatus] = mapped_column(
        enum_type(ReferenceStatus, "reference_status")
    )
    source_record_id: Mapped[str] = mapped_column(String(160))
    raw_record: Mapped[dict[str, object]] = mapped_column(json_type)
