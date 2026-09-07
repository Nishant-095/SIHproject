from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import DataClass
from app.indexing.aggregate import decimal_median
from app.models import FareObservation, RawQuote, Route, Source
from app.schemas.analytics import (
    LeadTimePointResponse,
    LeadTimeResponse,
    RouteAnalyticsResponse,
    RouteHistoryPointResponse,
    SourceObservationCountResponse,
)
from app.schemas.route import RouteResponse
from app.services.analytics import route_history, route_or_none

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=list[RouteResponse])
def list_routes(session: Annotated[Session, Depends(get_db)]) -> list[Route]:
    return list(
        session.scalars(
            select(Route)
            .where(Route.active.is_(True))
            .order_by(Route.origin_iata, Route.destination_iata)
        )
    )


def _route_or_404(session: Session, origin: str, destination: str) -> Route:
    route = route_or_none(session, origin, destination)
    if route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return route


@router.get("/{origin}/{destination}", response_model=RouteAnalyticsResponse)
def get_route(
    origin: str,
    destination: str,
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> RouteAnalyticsResponse:
    route = _route_or_404(session, origin, destination)
    history = route_history(session, route, data_class)
    carriers = list(
        session.scalars(
            select(FareObservation.carrier_code)
            .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
            .where(
                FareObservation.origin_iata == route.origin_iata,
                FareObservation.destination_iata == route.destination_iata,
                RawQuote.data_class == data_class,
                FareObservation.carrier_code.is_not(None),
            )
            .distinct()
            .order_by(FareObservation.carrier_code)
        )
    )
    latest = history[-1] if history else None
    source_rows = session.execute(
        select(Source.code, func.count(FareObservation.id))
        .join(RawQuote, RawQuote.source_id == Source.id)
        .join(FareObservation, FareObservation.raw_quote_id == RawQuote.id)
        .where(
            FareObservation.origin_iata == route.origin_iata,
            FareObservation.destination_iata == route.destination_iata,
            RawQuote.data_class == data_class,
        )
        .group_by(Source.code)
        .order_by(Source.code)
    ).all()
    return RouteAnalyticsResponse(
        id=route.id,
        origin_iata=route.origin_iata,
        destination_iata=route.destination_iata,
        selection_basis=route.selection_basis,
        latest_route_index=None if latest is None else latest.route_index,
        latest_date=None if latest is None else latest.methodological_date,
        carriers=[carrier for carrier in carriers if carrier is not None],
        source_dispersion=[
            SourceObservationCountResponse(source_code=code, observation_count=count)
            for code, count in source_rows
        ],
    )


@router.get(
    "/{origin}/{destination}/history",
    response_model=list[RouteHistoryPointResponse],
)
def get_route_history(
    origin: str,
    destination: str,
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
) -> list[RouteHistoryPointResponse]:
    return route_history(session, _route_or_404(session, origin, destination), data_class)


@router.get("/{origin}/{destination}/lead-time", response_model=LeadTimeResponse)
def get_lead_time_curve(
    origin: str,
    destination: str,
    session: Annotated[Session, Depends(get_db)],
    data_class: Annotated[DataClass, Query()] = DataClass.SYNTHETIC,
    travel_date: Annotated[date | None, Query()] = None,
) -> LeadTimeResponse:
    route = _route_or_404(session, origin, destination)
    observations = list(
        session.scalars(
            select(FareObservation)
            .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
            .where(
                FareObservation.origin_iata == route.origin_iata,
                FareObservation.destination_iata == route.destination_iata,
                FareObservation.included_in_index.is_(True),
                FareObservation.total_fare.is_not(None),
                RawQuote.data_class == data_class,
            )
            .order_by(FareObservation.travel_date, FareObservation.methodological_date)
        )
    )
    effective_date = travel_date
    if effective_date is None and observations:
        point_counts: dict[date, set[date]] = defaultdict(set)
        for row in observations:
            point_counts[row.travel_date].add(row.methodological_date)
        effective_date = max(point_counts, key=lambda item: (len(point_counts[item]), item))
    selected = [row for row in observations if row.travel_date == effective_date]
    grouped: dict[tuple[date, object], list[Decimal]] = defaultdict(list)
    for row in selected:
        if row.total_fare is not None:
            grouped[(row.methodological_date, row.advance_window)].append(row.total_fare)
    points = [
        LeadTimePointResponse(
            methodological_date=methodological_date,
            travel_date=effective_date,
            advance_window=advance_window,
            median_fare=decimal_median(fares),
            observation_count=len(fares),
        )
        for (methodological_date, advance_window), fares in sorted(grouped.items())
        if effective_date is not None
    ]
    return LeadTimeResponse(
        origin_iata=route.origin_iata,
        destination_iata=route.destination_iata,
        travel_date=effective_date,
        data_class=data_class,
        points=points,
    )
