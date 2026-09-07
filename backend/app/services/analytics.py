from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import DataClass, QualityStatus
from app.models import (
    BasketItem,
    BasketVersion,
    DailyIndex,
    DailyIndexComponent,
    FareObservation,
    RawQuote,
    Route,
)
from app.schemas.analytics import (
    DailyIndexResponse,
    IndexComponentResponse,
    QualitySummaryResponse,
    RouteHistoryPointResponse,
)


def daily_index_response(session: Session, index: DailyIndex) -> DailyIndexResponse:
    basket = session.get(BasketVersion, index.basket_version_id)
    if basket is None:
        raise ValueError("index basket is missing")
    rows = session.execute(
        select(DailyIndexComponent, BasketItem, Route)
        .join(BasketItem, DailyIndexComponent.basket_item_id == BasketItem.id)
        .join(Route, BasketItem.route_id == Route.id)
        .where(DailyIndexComponent.daily_index_id == index.id)
        .order_by(Route.origin_iata, Route.destination_iata, BasketItem.advance_window)
    ).all()
    return DailyIndexResponse(
        id=index.id,
        collection_run_id=index.collection_run_id,
        methodological_date=index.methodological_date,
        data_class=index.data_class,
        basket_version=basket.version,
        methodology_version=index.methodology_version,
        canonicalization_version=index.canonicalization_version,
        index_value=index.index_value,
        coverage_percent=index.coverage_percent,
        publication_status=index.publication_status,
        calculated_at=index.calculated_at,
        components=[
            IndexComponentResponse(
                basket_item_id=item.id,
                origin_iata=route.origin_iata,
                destination_iata=route.destination_iata,
                advance_window=item.advance_window,
                current_price=component.current_price,
                base_price=component.base_price,
                price_relative=component.price_relative,
                configured_weight=component.configured_weight,
                effective_weight=component.effective_weight,
                contribution=component.contribution,
                availability_reason=component.availability_reason,
            )
            for component, item, route in rows
        ],
    )


def route_history(
    session: Session,
    route: Route,
    data_class: DataClass,
) -> list[RouteHistoryPointResponse]:
    rows = session.execute(
        select(DailyIndex, DailyIndexComponent)
        .join(DailyIndexComponent, DailyIndexComponent.daily_index_id == DailyIndex.id)
        .join(BasketItem, DailyIndexComponent.basket_item_id == BasketItem.id)
        .where(BasketItem.route_id == route.id, DailyIndex.data_class == data_class)
        .order_by(DailyIndex.methodological_date, BasketItem.advance_window)
    ).all()
    grouped: dict[date, list[DailyIndexComponent]] = defaultdict(list)
    for index, component in rows:
        grouped[index.methodological_date].append(component)
    output: list[RouteHistoryPointResponse] = []
    for methodological_date, components in grouped.items():
        available = [row for row in components if row.price_relative is not None]
        relatives = [row.price_relative for row in available if row.price_relative is not None]
        fares = [row.current_price for row in available if row.current_price is not None]
        output.append(
            RouteHistoryPointResponse(
                methodological_date=methodological_date,
                route_index=None if not relatives else sum(relatives) / Decimal(len(relatives)),
                average_fare=None if not fares else sum(fares) / Decimal(len(fares)),
                coverage_percent=(Decimal("100") * Decimal(len(available)) / Decimal("5")).quantize(
                    Decimal("0.0001")
                ),
            )
        )
    return output


def quality_summary(session: Session, data_class: DataClass) -> QualitySummaryResponse:
    observations = list(
        session.scalars(
            select(FareObservation)
            .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
            .where(RawQuote.data_class == data_class)
        )
    )
    included = [row for row in observations if row.included_in_index]
    excluded = [row for row in observations if not row.included_in_index]
    flagged = [row for row in observations if row.quality_flags]
    scores = [Decimal(row.quality_score) for row in observations if row.quality_score is not None]
    status_counts = Counter(row.quality_status.value for row in observations)
    flag_counts: Counter[str] = Counter()
    for row in observations:
        flag_counts.update(row.quality_flags)
    total = len(observations)
    return QualitySummaryResponse(
        data_class=data_class,
        total_observations=total,
        included_observations=len(included),
        excluded_observations=len(excluded),
        flagged_observations=len(flagged),
        average_quality_score=None if not scores else sum(scores) / Decimal(len(scores)),
        inclusion_rate_percent=(
            Decimal("0")
            if total == 0
            else (Decimal("100") * Decimal(len(included)) / Decimal(total)).quantize(
                Decimal("0.01")
            )
        ),
        status_counts={
            status.value: status_counts.get(status.value, 0) for status in QualityStatus
        },
        flag_counts=dict(sorted(flag_counts.items())),
    )


def route_or_none(session: Session, origin: str, destination: str) -> Route | None:
    return session.scalar(
        select(Route).where(
            Route.origin_iata == origin.upper(),
            Route.destination_iata == destination.upper(),
            Route.active.is_(True),
        )
    )
