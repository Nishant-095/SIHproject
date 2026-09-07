from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import (
    AdvanceWindow,
    AggregationPeriod,
    AggregationStatus,
    ConfidenceLevel,
    DataClass,
    PublicationStatus,
)
from app.models.base import CreatedAtMixin, utc_now
from app.models.types import enum_type, json_type


class BasketVersion(CreatedAtMixin, Base):
    __tablename__ = "basket_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    data_class: Mapped[DataClass] = mapped_column(enum_type(DataClass, "basket_data_class"))
    base_policy: Mapped[str] = mapped_column(String(80))
    base_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    base_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class BasketItem(CreatedAtMixin, Base):
    __tablename__ = "basket_items"
    __table_args__ = (
        UniqueConstraint(
            "basket_version_id",
            "route_id",
            "advance_window",
            name="uq_basket_item_dimension",
        ),
        CheckConstraint("weight > 0", name="ck_basket_item_weight_positive"),
        CheckConstraint(
            "base_price IS NULL OR base_price > 0",
            name="ck_basket_item_base_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    basket_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("basket_versions.id", ondelete="RESTRICT"), index=True
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routes.id", ondelete="RESTRICT"), index=True
    )
    advance_window: Mapped[AdvanceWindow] = mapped_column(
        enum_type(AdvanceWindow, "basket_advance_window"), index=True
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(20, 12))
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    base_component_ids: Mapped[list[str]] = mapped_column(json_type, default=list)


class DailyRouteWindowPrice(CreatedAtMixin, Base):
    __tablename__ = "daily_route_window_prices"
    __table_args__ = (
        UniqueConstraint(
            "methodological_date",
            "data_class",
            "basket_item_id",
            "aggregation_version",
            name="uq_daily_route_window_price",
        ),
        CheckConstraint("price IS NULL OR price > 0", name="ck_daily_price_positive"),
        CheckConstraint(
            "eligible_flight_count >= 0",
            name="ck_daily_price_count_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="RESTRICT"), index=True
    )
    methodological_date: Mapped[date] = mapped_column(Date, index=True)
    data_class: Mapped[DataClass] = mapped_column(enum_type(DataClass, "daily_price_data_class"))
    basket_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("basket_items.id", ondelete="RESTRICT"), index=True
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    eligible_flight_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(48))
    aggregation_version: Mapped[str] = mapped_column(String(80))


class RouteWindowPriceInput(Base):
    __tablename__ = "route_window_price_inputs"

    daily_route_window_price_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("daily_route_window_prices.id", ondelete="CASCADE"), primary_key=True
    )
    canonical_fare_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_fares.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class DailyIndex(Base):
    __tablename__ = "daily_indices"
    __table_args__ = (
        UniqueConstraint(
            "methodological_date",
            "data_class",
            "basket_version_id",
            "methodology_version",
            name="uq_daily_index_version",
        ),
        CheckConstraint(
            "index_value IS NULL OR index_value >= 0",
            name="ck_daily_index_value_nonnegative",
        ),
        CheckConstraint(
            "coverage_percent >= 0 AND coverage_percent <= 100",
            name="ck_daily_index_coverage_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="RESTRICT"), index=True
    )
    methodological_date: Mapped[date] = mapped_column(Date, index=True)
    data_class: Mapped[DataClass] = mapped_column(enum_type(DataClass, "daily_index_data_class"))
    basket_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("basket_versions.id", ondelete="RESTRICT"), index=True
    )
    methodology_version: Mapped[str] = mapped_column(String(80))
    canonicalization_version: Mapped[str] = mapped_column(String(80))
    index_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    coverage_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    publication_status: Mapped[PublicationStatus] = mapped_column(
        enum_type(PublicationStatus, "publication_status"), index=True
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class DailyIndexComponent(Base):
    __tablename__ = "daily_index_components"
    __table_args__ = (
        UniqueConstraint(
            "daily_index_id",
            "basket_item_id",
            name="uq_daily_index_component_item",
        ),
        CheckConstraint("configured_weight > 0", name="ck_index_component_weight_positive"),
        CheckConstraint(
            "effective_weight IS NULL OR effective_weight >= 0",
            name="ck_index_component_effective_weight_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    daily_index_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("daily_indices.id", ondelete="CASCADE"), index=True
    )
    basket_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("basket_items.id", ondelete="RESTRICT"), index=True
    )
    daily_route_window_price_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("daily_route_window_prices.id", ondelete="RESTRICT"), nullable=True
    )
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_relative: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    configured_weight: Mapped[Decimal] = mapped_column(Numeric(20, 12))
    effective_weight: Mapped[Decimal | None] = mapped_column(Numeric(20, 12), nullable=True)
    contribution: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    availability_reason: Mapped[str] = mapped_column(String(48))


class PeriodIndex(Base):
    __tablename__ = "period_indices"
    __table_args__ = (
        UniqueConstraint(
            "data_class",
            "basket_version_id",
            "period_type",
            "period_start",
            "methodology_version",
            name="uq_period_index_version",
        ),
        CheckConstraint("index_value IS NULL OR index_value >= 0", name="ck_period_index_value"),
        CheckConstraint(
            "average_coverage_percent >= 0 AND average_coverage_percent <= 100",
            name="ck_period_average_coverage",
        ),
        CheckConstraint(
            "minimum_coverage_percent >= 0 AND minimum_coverage_percent <= 100",
            name="ck_period_minimum_coverage",
        ),
        CheckConstraint("expected_day_count > 0", name="ck_period_expected_days"),
        CheckConstraint("observed_day_count >= 0", name="ck_period_observed_days"),
        CheckConstraint("valued_day_count >= 0", name="ck_period_valued_days"),
        CheckConstraint("low_coverage_day_count >= 0", name="ck_period_low_coverage_days"),
        CheckConstraint("source_count >= 0", name="ck_period_source_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    data_class: Mapped[DataClass] = mapped_column(enum_type(DataClass, "period_data_class"))
    basket_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("basket_versions.id", ondelete="RESTRICT"), index=True
    )
    period_type: Mapped[AggregationPeriod] = mapped_column(
        enum_type(AggregationPeriod, "aggregation_period"), index=True
    )
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date)
    methodology_version: Mapped[str] = mapped_column(String(80))
    missing_data_policy: Mapped[str] = mapped_column(String(80))
    index_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    average_coverage_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    minimum_coverage_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    expected_day_count: Mapped[int] = mapped_column(Integer)
    observed_day_count: Mapped[int] = mapped_column(Integer)
    valued_day_count: Mapped[int] = mapped_column(Integer)
    low_coverage_day_count: Mapped[int] = mapped_column(Integer)
    source_count: Mapped[int] = mapped_column(Integer)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        enum_type(ConfidenceLevel, "confidence_level")
    )
    aggregation_status: Mapped[AggregationStatus] = mapped_column(
        enum_type(AggregationStatus, "aggregation_status"), index=True
    )
    warnings: Mapped[list[str]] = mapped_column(json_type, default=list)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class PeriodIndexInput(Base):
    __tablename__ = "period_index_inputs"

    period_index_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("period_indices.id", ondelete="CASCADE"), primary_key=True
    )
    daily_index_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("daily_indices.id", ondelete="RESTRICT"), primary_key=True
    )
