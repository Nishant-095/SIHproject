from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.enums import (
    AggregationPeriod,
    AggregationStatus,
    ConfidenceLevel,
    PublicationStatus,
)
from app.indexing.periods import calculate_period_metrics, period_bounds
from app.models import DailyIndex


def _daily(value: str | None, coverage: str, status: PublicationStatus) -> DailyIndex:
    return DailyIndex(
        index_value=None if value is None else Decimal(value),
        coverage_percent=Decimal(coverage),
        publication_status=status,
    )


def test_period_bounds_are_calendar_stable() -> None:
    assert period_bounds(date(2026, 9, 9), AggregationPeriod.WEEKLY) == (
        date(2026, 9, 7),
        date(2026, 9, 13),
    )
    assert period_bounds(date(2028, 2, 10), AggregationPeriod.MONTHLY) == (
        date(2028, 2, 1),
        date(2028, 2, 29),
    )


def test_complete_multi_source_period_has_high_confidence() -> None:
    rows = [_daily(str(100 + day), "100", PublicationStatus.PUBLISHED) for day in range(7)]
    result = calculate_period_metrics(rows, expected_day_count=7, source_count=2)
    assert result.index_value == Decimal("103.00000000")
    assert result.aggregation_status is AggregationStatus.COMPLETE
    assert result.confidence_level is ConfidenceLevel.HIGH
    assert result.warnings == ()


def test_partial_single_source_period_is_labelled_not_hidden() -> None:
    result = calculate_period_metrics(
        [
            _daily(None, "100", PublicationStatus.PROVISIONAL_BASE),
            _daily("101", "100", PublicationStatus.PUBLISHED),
        ],
        expected_day_count=7,
        source_count=1,
    )
    assert result.index_value == Decimal("101.00000000")
    assert result.aggregation_status is AggregationStatus.PARTIAL
    assert result.confidence_level is ConfidenceLevel.LOW
    assert result.warnings == (
        "PARTIAL_PERIOD",
        "PROVISIONAL_BASE_DAYS_EXCLUDED",
        "SINGLE_SOURCE",
    )


def test_low_coverage_day_is_excluded_and_explicit() -> None:
    result = calculate_period_metrics(
        [
            _daily("100", "100", PublicationStatus.PUBLISHED),
            _daily("140", "60", PublicationStatus.INSUFFICIENT_COVERAGE),
        ],
        expected_day_count=2,
        source_count=2,
    )
    assert result.index_value == Decimal("100.00000000")
    assert result.low_coverage_day_count == 1
    assert result.aggregation_status is AggregationStatus.INSUFFICIENT_COVERAGE
    assert result.confidence_level is ConfidenceLevel.INSUFFICIENT
    assert "LOW_COVERAGE_DAYS_EXCLUDED" in result.warnings


def test_no_published_value_never_becomes_a_fake_zero() -> None:
    result = calculate_period_metrics(
        [_daily(None, "0", PublicationStatus.PROVISIONAL_BASE)],
        expected_day_count=7,
        source_count=1,
    )
    assert result.index_value is None
    assert result.aggregation_status is AggregationStatus.NO_DATA
    assert result.confidence_level is ConfidenceLevel.INSUFFICIENT
    assert "NO_PUBLISHED_VALUES" in result.warnings
