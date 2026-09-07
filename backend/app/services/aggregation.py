from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import ConfidenceLevel, PublicationStatus
from app.indexing.periods import MINIMUM_COVERAGE_PERCENT, MISSING_DATA_POLICY
from app.models import (
    BasketItem,
    CanonicalFare,
    CanonicalFareObservation,
    DailyIndex,
    DailyIndexComponent,
    Route,
    Source,
)
from app.schemas.analytics import (
    IndexCoverageResponse,
    MissingDataPolicyResponse,
    RouteCoverageResponse,
    SourceDispersionResponse,
)


def _confidence(coverage: Decimal, source_count: int, *, has_value: bool) -> ConfidenceLevel:
    if not has_value or coverage < MINIMUM_COVERAGE_PERCENT:
        return ConfidenceLevel.INSUFFICIENT
    if coverage >= Decimal("95") and source_count >= 2:
        return ConfidenceLevel.HIGH
    if source_count >= 2:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def index_coverage_response(session: Session, index: DailyIndex) -> IndexCoverageResponse:
    component_rows = session.execute(
        select(DailyIndexComponent, BasketItem, Route)
        .join(BasketItem, DailyIndexComponent.basket_item_id == BasketItem.id)
        .join(Route, BasketItem.route_id == Route.id)
        .where(DailyIndexComponent.daily_index_id == index.id)
        .order_by(Route.origin_iata, Route.destination_iata, BasketItem.advance_window)
    ).all()
    source_rows = session.execute(
        select(Source.code, func.count(CanonicalFareObservation.observation_id))
        .join(CanonicalFareObservation, CanonicalFareObservation.source_id == Source.id)
        .join(
            CanonicalFare,
            CanonicalFareObservation.canonical_fare_id == CanonicalFare.id,
        )
        .where(
            CanonicalFare.collection_run_id == index.collection_run_id,
            CanonicalFareObservation.role.in_(("USED_DIRECT", "USED_MEDIAN")),
        )
        .group_by(Source.code)
        .order_by(Source.code)
    ).all()
    total_observations = sum(count for _, count in source_rows)
    dispersion = [
        SourceDispersionResponse(
            source_code=code,
            observation_count=count,
            share_percent=(
                Decimal("0")
                if total_observations == 0
                else (Decimal("100") * Decimal(count) / Decimal(total_observations)).quantize(
                    Decimal("0.01")
                )
            ),
        )
        for code, count in source_rows
    ]
    route_sources: dict[uuid.UUID, int] = {
        route_id: int(count)
        for route_id, count in session.execute(
            select(
                CanonicalFare.route_id,
                func.count(func.distinct(CanonicalFareObservation.source_id)),
            )
            .join(
                CanonicalFareObservation,
                CanonicalFareObservation.canonical_fare_id == CanonicalFare.id,
            )
            .where(
                CanonicalFare.collection_run_id == index.collection_run_id,
                CanonicalFareObservation.role.in_(("USED_DIRECT", "USED_MEDIAN")),
            )
            .group_by(CanonicalFare.route_id)
        ).all()
    }
    route_observations: dict[uuid.UUID, int] = {
        route_id: int(count)
        for route_id, count in session.execute(
            select(
                CanonicalFare.route_id,
                func.count(CanonicalFareObservation.observation_id),
            )
            .join(
                CanonicalFareObservation,
                CanonicalFareObservation.canonical_fare_id == CanonicalFare.id,
            )
            .where(
                CanonicalFare.collection_run_id == index.collection_run_id,
                CanonicalFareObservation.role.in_(("USED_DIRECT", "USED_MEDIAN")),
            )
            .group_by(CanonicalFare.route_id)
        ).all()
    }
    grouped: dict[Route, list[tuple[DailyIndexComponent, BasketItem]]] = defaultdict(list)
    for component, item, route in component_rows:
        grouped[route].append((component, item))
    routes: list[RouteCoverageResponse] = []
    for route, rows in grouped.items():
        total_weight = sum((item.weight for _, item in rows), Decimal("0"))
        available = [
            (component, item) for component, item in rows if component.price_relative is not None
        ]
        available_weight = sum((item.weight for _, item in available), Decimal("0"))
        coverage = (
            Decimal("0")
            if total_weight == 0
            else (Decimal("100") * available_weight / total_weight).quantize(Decimal("0.0001"))
        )
        source_count = int(route_sources.get(route.id, 0))
        routes.append(
            RouteCoverageResponse(
                origin_iata=route.origin_iata,
                destination_iata=route.destination_iata,
                total_windows=len(rows),
                available_windows=len(available),
                coverage_percent=coverage,
                configured_weight=total_weight,
                available_weight=available_weight,
                source_count=source_count,
                observation_count=int(route_observations.get(route.id, 0)),
                missing_windows=[
                    item.advance_window
                    for component, item in rows
                    if component.price_relative is None
                ],
                confidence_level=_confidence(
                    coverage,
                    source_count,
                    has_value=bool(available),
                ),
            )
        )
    warnings: list[str] = []
    if index.coverage_percent < MINIMUM_COVERAGE_PERCENT:
        warnings.append("INDEX_COVERAGE_BELOW_PUBLICATION_THRESHOLD")
    if any(route.missing_windows for route in routes):
        warnings.append("MISSING_ROUTE_WINDOW_CELLS")
    if len(source_rows) < 2:
        warnings.append("SINGLE_SOURCE")
    if index.publication_status is not PublicationStatus.PUBLISHED:
        warnings.append(f"INDEX_STATUS_{index.publication_status.value}")
    return IndexCoverageResponse(
        methodological_date=index.methodological_date,
        data_class=index.data_class,
        publication_status=index.publication_status,
        index_value=index.index_value,
        coverage_percent=index.coverage_percent,
        source_count=len(source_rows),
        confidence_level=_confidence(
            index.coverage_percent,
            len(source_rows),
            has_value=index.index_value is not None,
        ),
        missing_data_policy=MissingDataPolicyResponse(
            code=MISSING_DATA_POLICY,
            minimum_publication_coverage_percent=MINIMUM_COVERAGE_PERCENT,
            imputation="NONE",
            available_weight_treatment="RENORMALIZE_TO_AVAILABLE_BASKET_WEIGHT",
            period_value_treatment="MEAN_OF_PUBLISHED_DAILY_VALUES_ONLY",
        ),
        source_dispersion=dispersion,
        routes=routes,
        warnings=warnings,
    )
