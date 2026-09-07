from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BasketItem,
    BasketVersion,
    CanonicalFare,
    CollectionRun,
    DailyRouteWindowPrice,
    RouteWindowPriceInput,
)

AGGREGATION_VERSION = "route-window-median-v1"


def decimal_median(values: Iterable[Decimal]) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median requires at least one value")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def aggregate_route_window_prices(
    session: Session,
    *,
    run: CollectionRun,
    basket: BasketVersion,
    aggregation_version: str = AGGREGATION_VERSION,
) -> list[DailyRouteWindowPrice]:
    if run.data_class is not basket.data_class:
        raise ValueError("collection run and basket data classes must match")
    items = list(
        session.scalars(
            select(BasketItem)
            .where(BasketItem.basket_version_id == basket.id)
            .order_by(BasketItem.route_id, BasketItem.advance_window)
        )
    )
    if not items:
        raise ValueError("basket has no items")

    existing = list(
        session.scalars(
            select(DailyRouteWindowPrice)
            .join(BasketItem, DailyRouteWindowPrice.basket_item_id == BasketItem.id)
            .where(
                DailyRouteWindowPrice.methodological_date == run.methodological_date,
                DailyRouteWindowPrice.data_class == run.data_class,
                DailyRouteWindowPrice.aggregation_version == aggregation_version,
                BasketItem.basket_version_id == basket.id,
            )
            .order_by(DailyRouteWindowPrice.basket_item_id)
        )
    )
    if existing:
        if len(existing) != len(items):
            raise ValueError("existing daily route-window aggregation is incomplete")
        if any(row.collection_run_id != run.id for row in existing):
            raise ValueError("this date already belongs to a different collection run")
        return existing

    rows: list[DailyRouteWindowPrice] = []
    for item in items:
        canonical = list(
            session.scalars(
                select(CanonicalFare)
                .where(
                    CanonicalFare.collection_run_id == run.id,
                    CanonicalFare.route_id == item.route_id,
                    CanonicalFare.advance_window == item.advance_window,
                    CanonicalFare.cabin_class == "ECONOMY",
                    CanonicalFare.currency == "INR",
                )
                .order_by(CanonicalFare.flight_identity, CanonicalFare.id)
            )
        )
        price = (
            None
            if not canonical
            else decimal_median(row.representative_total_fare for row in canonical)
        )
        daily = DailyRouteWindowPrice(
            collection_run_id=run.id,
            methodological_date=run.methodological_date,
            data_class=run.data_class,
            basket_item_id=item.id,
            price=price,
            eligible_flight_count=len(canonical),
            status="AVAILABLE" if price is not None else "NO_CANONICAL_FARES",
            aggregation_version=aggregation_version,
        )
        session.add(daily)
        session.flush()
        for fare in canonical:
            session.add(
                RouteWindowPriceInput(
                    daily_route_window_price_id=daily.id,
                    canonical_fare_id=fare.id,
                )
            )
        rows.append(daily)
    session.commit()
    return rows
