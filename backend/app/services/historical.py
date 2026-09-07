from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AggregationPeriod, DataClass, PublicationStatus, ReferenceScope
from app.models import (
    BasketItem,
    DailyIndex,
    DailyIndexComponent,
    HistoricalDataset,
    HistoricalIndexObservation,
    PeriodIndex,
    Route,
)
from app.schemas.historical import (
    BacktestPointResponse,
    BacktestResponse,
    HistoricalDatasetImportRequest,
    HistoricalDatasetResponse,
    HistoricalObservationInput,
    HistoricalObservationResponse,
    RouteComparisonResponse,
)

BACKTEST_METHOD = "first-overlap-rebase-100-v1"


def payload_from_csv(
    content: str,
    *,
    code: str,
    title: str,
    publisher: str,
    source_url: str,
    license_name: str,
    metric_name: str,
    frequency: str,
    base_period: str | None,
    notes: str | None,
) -> HistoricalDatasetImportRequest:
    reader = csv.DictReader(io.StringIO(content))
    required = {
        "period_start",
        "period_end",
        "scope_type",
        "index_value",
        "status",
        "source_record_id",
    }
    if reader.fieldnames is None or not required <= set(reader.fieldnames):
        missing = sorted(required - set(reader.fieldnames or []))
        raise ValueError(f"historical CSV is missing columns: {', '.join(missing)}")
    observations: list[HistoricalObservationInput] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            raw_record = json.loads(row.get("raw_record_json") or "{}")
            if not isinstance(raw_record, dict):
                raise ValueError("raw_record_json must be an object")
            observations.append(
                HistoricalObservationInput(
                    period_start=row["period_start"],
                    period_end=row["period_end"],
                    scope_type=row["scope_type"],
                    origin_iata=row.get("origin_iata") or None,
                    destination_iata=row.get("destination_iata") or None,
                    index_value=row["index_value"],
                    coverage_percent=row.get("coverage_percent") or None,
                    status=row["status"],
                    source_record_id=row["source_record_id"],
                    raw_record=raw_record,
                )
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(f"invalid historical CSV row {line_number}: {exc}") from exc
    if not observations:
        raise ValueError("historical CSV contains no data rows")
    return HistoricalDatasetImportRequest(
        code=code,
        title=title,
        publisher=publisher,
        source_url=source_url,
        license_name=license_name,
        metric_name=metric_name,
        frequency=frequency,
        base_period=base_period,
        notes=notes,
        observations=observations,
    )


def _canonical_payload(payload: HistoricalDatasetImportRequest) -> bytes:
    return json.dumps(
        payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()


def dataset_response(
    session: Session,
    dataset: HistoricalDataset,
    *,
    include_observations: bool = True,
) -> HistoricalDatasetResponse:
    observations = []
    if include_observations:
        observations = [
            HistoricalObservationResponse.model_validate(row)
            for row in session.scalars(
                select(HistoricalIndexObservation)
                .where(HistoricalIndexObservation.dataset_id == dataset.id)
                .order_by(
                    HistoricalIndexObservation.period_start,
                    HistoricalIndexObservation.scope_type,
                )
            )
        ]
    return HistoricalDatasetResponse(
        id=dataset.id,
        code=dataset.code,
        title=dataset.title,
        publisher=dataset.publisher,
        source_url=dataset.source_url,
        license_name=dataset.license_name,
        metric_name=dataset.metric_name,
        frequency=dataset.frequency,
        base_period=dataset.base_period,
        data_class=dataset.data_class,
        content_hash=dataset.content_hash,
        row_count=dataset.row_count,
        notes=dataset.notes,
        imported_at=dataset.imported_at,
        observations=observations,
    )


def import_historical_dataset(
    session: Session,
    payload: HistoricalDatasetImportRequest,
) -> tuple[HistoricalDataset, bool]:
    digest = hashlib.sha256(_canonical_payload(payload)).hexdigest()
    existing = session.scalar(
        select(HistoricalDataset).where(HistoricalDataset.code == payload.code)
    )
    if existing is not None:
        if existing.content_hash != digest:
            raise ValueError(
                "dataset code already exists with different content; use a versioned code"
            )
        return existing, False
    duplicate = session.scalar(
        select(HistoricalDataset).where(HistoricalDataset.content_hash == digest)
    )
    if duplicate is not None:
        raise ValueError(f"identical historical content already imported as {duplicate.code}")
    dataset = HistoricalDataset(
        code=payload.code,
        title=payload.title,
        publisher=payload.publisher,
        source_url=str(payload.source_url),
        license_name=payload.license_name,
        metric_name=payload.metric_name,
        frequency=payload.frequency,
        base_period=payload.base_period,
        data_class=DataClass.HISTORICAL,
        content_hash=digest,
        row_count=len(payload.observations),
        notes=payload.notes,
    )
    session.add(dataset)
    session.flush()
    for row in payload.observations:
        session.add(
            HistoricalIndexObservation(
                dataset_id=dataset.id,
                **row.model_dump(),
            )
        )
    session.commit()
    session.refresh(dataset)
    return dataset, True


def _correlation(xs: list[Decimal], ys: list[Decimal]) -> tuple[Decimal | None, str]:
    if len(xs) < 3:
        return None, "INSUFFICIENT_OVERLAP"
    x_mean = sum(xs, Decimal("0")) / Decimal(len(xs))
    y_mean = sum(ys, Decimal("0")) / Decimal(len(ys))
    x_delta = [value - x_mean for value in xs]
    y_delta = [value - y_mean for value in ys]
    x_variance = sum((value * value for value in x_delta), Decimal("0"))
    y_variance = sum((value * value for value in y_delta), Decimal("0"))
    if x_variance == 0 or y_variance == 0:
        return None, "CONSTANT_SERIES"
    covariance = sum((x * y for x, y in zip(x_delta, y_delta, strict=True)), Decimal("0"))
    value = covariance / (x_variance * y_variance).sqrt()
    return value.quantize(Decimal("0.000001")), "CALCULATED"


def _route_comparisons(
    session: Session,
    periods: list[PeriodIndex],
) -> list[RouteComparisonResponse]:
    output: list[RouteComparisonResponse] = []
    for period in periods:
        if period.index_value is None:
            continue
        rows = session.execute(
            select(DailyIndex, DailyIndexComponent, BasketItem, Route)
            .join(DailyIndexComponent, DailyIndexComponent.daily_index_id == DailyIndex.id)
            .join(BasketItem, DailyIndexComponent.basket_item_id == BasketItem.id)
            .join(Route, BasketItem.route_id == Route.id)
            .where(
                DailyIndex.data_class == period.data_class,
                DailyIndex.basket_version_id == period.basket_version_id,
                DailyIndex.methodological_date >= period.period_start,
                DailyIndex.methodological_date <= period.period_end,
                DailyIndex.publication_status == PublicationStatus.PUBLISHED,
                DailyIndexComponent.price_relative.is_not(None),
            )
        ).all()
        by_route_day: dict[
            tuple[str, str, date], list[tuple[Decimal, Decimal]]
        ] = defaultdict(list)
        for daily, component, item, route in rows:
            if component.price_relative is not None:
                key = (route.origin_iata, route.destination_iata, daily.methodological_date)
                by_route_day[key].append((component.price_relative, item.weight))
        by_route: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
        for (origin, destination, _), values in by_route_day.items():
            weight = sum((item_weight for _, item_weight in values), Decimal("0"))
            if weight:
                by_route[(origin, destination)].append(
                    sum((value * item_weight for value, item_weight in values), Decimal("0"))
                    / weight
                )
        for (origin, destination), route_values in sorted(by_route.items()):
            route_index = sum(route_values, Decimal("0")) / Decimal(len(route_values))
            expected = period.expected_day_count
            output.append(
                RouteComparisonResponse(
                    period_start=period.period_start,
                    period_end=period.period_end,
                    origin_iata=origin,
                    destination_iata=destination,
                    route_index=route_index.quantize(Decimal("0.00000001")),
                    overall_index=period.index_value,
                    deviation_points=(route_index - period.index_value).quantize(
                        Decimal("0.00000001")
                    ),
                    observed_day_count=len(route_values),
                    expected_day_count=expected,
                    coverage_percent=(
                        Decimal("100") * Decimal(len(route_values)) / Decimal(expected)
                    ).quantize(Decimal("0.0001")),
                )
            )
    return output


def build_backtest(
    session: Session,
    *,
    dataset_code: str,
    data_class: DataClass,
) -> BacktestResponse:
    dataset = session.scalar(
        select(HistoricalDataset).where(HistoricalDataset.code == dataset_code)
    )
    if dataset is None:
        raise ValueError("historical dataset not found")
    references = {
        row.period_start: row
        for row in session.scalars(
            select(HistoricalIndexObservation).where(
                HistoricalIndexObservation.dataset_id == dataset.id,
                HistoricalIndexObservation.scope_type == ReferenceScope.NATIONAL,
            )
        )
    }
    periods = list(
        session.scalars(
            select(PeriodIndex)
            .where(
                PeriodIndex.period_type == AggregationPeriod.MONTHLY,
                PeriodIndex.data_class == data_class,
                PeriodIndex.index_value.is_not(None),
            )
            .order_by(PeriodIndex.period_start)
        )
    )
    overlap = [period for period in periods if period.period_start in references]
    warnings: list[str] = []
    points: list[BacktestPointResponse] = []
    if overlap:
        internal_base = overlap[0].index_value
        reference_base = references[overlap[0].period_start].index_value
        if internal_base is None or internal_base == 0 or reference_base == 0:
            warnings.append("INVALID_REBASE_VALUE")
        else:
            for period in overlap:
                if period.index_value is None:
                    continue
                reference = references[period.period_start]
                internal_rebased = Decimal("100") * period.index_value / internal_base
                reference_rebased = Decimal("100") * reference.index_value / reference_base
                deviation = internal_rebased - reference_rebased
                points.append(
                    BacktestPointResponse(
                        period_start=period.period_start,
                        period_end=period.period_end,
                        internal_index=period.index_value,
                        reference_index=reference.index_value,
                        internal_rebased=internal_rebased.quantize(Decimal("0.00000001")),
                        reference_rebased=reference_rebased.quantize(Decimal("0.00000001")),
                        deviation_points=deviation.quantize(Decimal("0.00000001")),
                        deviation_percent=(Decimal("100") * deviation / reference_rebased).quantize(
                            Decimal("0.0001")
                        ),
                        internal_coverage_percent=period.average_coverage_percent,
                        internal_status=period.aggregation_status.value,
                        reference_status=reference.status,
                    )
                )
    else:
        warnings.append("NO_OVERLAPPING_MONTHS")
    correlation, correlation_status = _correlation(
        [point.internal_rebased for point in points],
        [point.reference_rebased for point in points],
    )
    if correlation_status != "CALCULATED":
        warnings.append(f"CORRELATION_{correlation_status}")
    mean_deviation = (
        None
        if not points
        else (
            sum((abs(point.deviation_percent) for point in points), Decimal("0"))
            / Decimal(len(points))
        ).quantize(Decimal("0.0001"))
    )
    average_coverage = (
        None
        if not points
        else (
            sum((point.internal_coverage_percent for point in points), Decimal("0"))
            / Decimal(len(points))
        ).quantize(Decimal("0.0001"))
    )
    return BacktestResponse(
        dataset=dataset_response(session, dataset),
        internal_data_class=data_class,
        comparison_method=BACKTEST_METHOD,
        overlap_month_count=len(points),
        correlation=correlation,
        correlation_status=correlation_status,
        mean_absolute_deviation_percent=mean_deviation,
        average_internal_coverage_percent=average_coverage,
        points=points,
        route_comparisons=_route_comparisons(session, overlap),
        warnings=warnings,
    )
