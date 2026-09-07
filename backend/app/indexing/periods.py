from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    AggregationPeriod,
    AggregationStatus,
    ConfidenceLevel,
    PublicationStatus,
)
from app.indexing.methodology import METHODOLOGY_VERSION
from app.models import (
    CanonicalFare,
    CanonicalFareObservation,
    DailyIndex,
    PeriodIndex,
    PeriodIndexInput,
)
from app.models.base import utc_now

MISSING_DATA_POLICY = "published-days-mean-no-imputation-v1"
MINIMUM_COVERAGE_PERCENT = Decimal("80")


@dataclass(frozen=True, slots=True)
class PeriodMetrics:
    index_value: Decimal | None
    average_coverage_percent: Decimal
    minimum_coverage_percent: Decimal
    expected_day_count: int
    observed_day_count: int
    valued_day_count: int
    low_coverage_day_count: int
    source_count: int
    confidence_level: ConfidenceLevel
    aggregation_status: AggregationStatus
    warnings: tuple[str, ...]


def period_bounds(day: date, period_type: AggregationPeriod) -> tuple[date, date]:
    if period_type is AggregationPeriod.WEEKLY:
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=6)
    start = day.replace(day=1)
    return start, day.replace(day=calendar.monthrange(day.year, day.month)[1])


def calculate_period_metrics(
    rows: list[DailyIndex],
    *,
    expected_day_count: int,
    source_count: int,
    minimum_coverage_percent: Decimal = MINIMUM_COVERAGE_PERCENT,
) -> PeriodMetrics:
    if expected_day_count <= 0:
        raise ValueError("expected day count must be positive")
    coverage_values = [row.coverage_percent for row in rows]
    published_values = [
        row.index_value
        for row in rows
        if row.publication_status is PublicationStatus.PUBLISHED and row.index_value is not None
    ]
    average_coverage = (
        Decimal("0")
        if not coverage_values
        else (sum(coverage_values, Decimal("0")) / Decimal(len(coverage_values))).quantize(
            Decimal("0.0001")
        )
    )
    minimum_coverage = min(coverage_values, default=Decimal("0"))
    low_coverage_days = sum(
        1
        for row in rows
        if row.coverage_percent < minimum_coverage_percent
        or row.publication_status is PublicationStatus.INSUFFICIENT_COVERAGE
    )
    warnings: list[str] = []
    if len(rows) < expected_day_count:
        warnings.append("PARTIAL_PERIOD")
    if any(row.publication_status is PublicationStatus.PROVISIONAL_BASE for row in rows):
        warnings.append("PROVISIONAL_BASE_DAYS_EXCLUDED")
    if low_coverage_days:
        warnings.append("LOW_COVERAGE_DAYS_EXCLUDED")
    if rows and source_count < 2:
        warnings.append("SINGLE_SOURCE")
    if not published_values:
        warnings.append("NO_PUBLISHED_VALUES")

    index_value = (
        None
        if not published_values
        else (sum(published_values, Decimal("0")) / Decimal(len(published_values))).quantize(
            Decimal("0.00000001")
        )
    )
    if index_value is None:
        status = AggregationStatus.NO_DATA
        confidence = ConfidenceLevel.INSUFFICIENT
    elif low_coverage_days:
        status = AggregationStatus.INSUFFICIENT_COVERAGE
        confidence = ConfidenceLevel.INSUFFICIENT
    elif len(rows) == expected_day_count and len(published_values) == expected_day_count:
        status = AggregationStatus.COMPLETE
        confidence = (
            ConfidenceLevel.HIGH
            if average_coverage >= Decimal("95") and source_count >= 2
            else ConfidenceLevel.LOW
        )
    else:
        status = AggregationStatus.PARTIAL
        completion = Decimal(len(published_values)) / Decimal(expected_day_count)
        confidence = (
            ConfidenceLevel.MEDIUM
            if average_coverage >= minimum_coverage_percent
            and completion >= Decimal("0.5")
            and source_count >= 2
            else ConfidenceLevel.LOW
        )
    return PeriodMetrics(
        index_value=index_value,
        average_coverage_percent=average_coverage,
        minimum_coverage_percent=minimum_coverage,
        expected_day_count=expected_day_count,
        observed_day_count=len(rows),
        valued_day_count=len(published_values),
        low_coverage_day_count=low_coverage_days,
        source_count=source_count,
        confidence_level=confidence,
        aggregation_status=status,
        warnings=tuple(warnings),
    )


def _source_count(session: Session, run_ids: list[uuid.UUID]) -> int:
    if not run_ids:
        return 0
    return int(
        session.scalar(
            select(func.count(func.distinct(CanonicalFareObservation.source_id)))
            .join(
                CanonicalFare,
                CanonicalFareObservation.canonical_fare_id == CanonicalFare.id,
            )
            .where(CanonicalFare.collection_run_id.in_(run_ids))
            .where(CanonicalFareObservation.role.in_(("USED_DIRECT", "USED_MEDIAN")))
        )
        or 0
    )


def refresh_period(
    session: Session,
    *,
    daily_index: DailyIndex,
    period_type: AggregationPeriod,
) -> PeriodIndex:
    start, end = period_bounds(daily_index.methodological_date, period_type)
    rows = list(
        session.scalars(
            select(DailyIndex)
            .where(
                DailyIndex.data_class == daily_index.data_class,
                DailyIndex.basket_version_id == daily_index.basket_version_id,
                DailyIndex.methodology_version == daily_index.methodology_version,
                DailyIndex.methodological_date >= start,
                DailyIndex.methodological_date <= end,
            )
            .order_by(DailyIndex.methodological_date)
        )
    )
    expected_days = (end - start).days + 1
    sources = _source_count(session, [row.collection_run_id for row in rows])
    metrics = calculate_period_metrics(
        rows,
        expected_day_count=expected_days,
        source_count=sources,
    )
    aggregate = session.scalar(
        select(PeriodIndex).where(
            PeriodIndex.data_class == daily_index.data_class,
            PeriodIndex.basket_version_id == daily_index.basket_version_id,
            PeriodIndex.period_type == period_type,
            PeriodIndex.period_start == start,
            PeriodIndex.methodology_version == METHODOLOGY_VERSION,
        )
    )
    if aggregate is None:
        aggregate = PeriodIndex(
            data_class=daily_index.data_class,
            basket_version_id=daily_index.basket_version_id,
            period_type=period_type,
            period_start=start,
            period_end=end,
            methodology_version=METHODOLOGY_VERSION,
            missing_data_policy=MISSING_DATA_POLICY,
        )
        session.add(aggregate)
    else:
        session.execute(
            delete(PeriodIndexInput).where(PeriodIndexInput.period_index_id == aggregate.id)
        )
    aggregate.index_value = metrics.index_value
    aggregate.average_coverage_percent = metrics.average_coverage_percent
    aggregate.minimum_coverage_percent = metrics.minimum_coverage_percent
    aggregate.expected_day_count = metrics.expected_day_count
    aggregate.observed_day_count = metrics.observed_day_count
    aggregate.valued_day_count = metrics.valued_day_count
    aggregate.low_coverage_day_count = metrics.low_coverage_day_count
    aggregate.source_count = metrics.source_count
    aggregate.confidence_level = metrics.confidence_level
    aggregate.aggregation_status = metrics.aggregation_status
    aggregate.warnings = list(metrics.warnings)
    aggregate.calculated_at = utc_now()
    session.flush()
    for row in rows:
        session.add(PeriodIndexInput(period_index_id=aggregate.id, daily_index_id=row.id))
    session.commit()
    session.refresh(aggregate)
    return aggregate


def refresh_periods_for_index(
    session: Session,
    daily_index: DailyIndex,
) -> tuple[PeriodIndex, PeriodIndex]:
    weekly = refresh_period(session, daily_index=daily_index, period_type=AggregationPeriod.WEEKLY)
    monthly = refresh_period(
        session,
        daily_index=daily_index,
        period_type=AggregationPeriod.MONTHLY,
    )
    return weekly, monthly
