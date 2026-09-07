from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AdvanceWindow, DataClass, RunTrigger
from app.indexing.aggregate import AGGREGATION_VERSION, decimal_median
from app.models import BasketItem, BasketVersion, CollectionRun, DailyRouteWindowPrice, Route

BASKET_VERSION_PREFIX = "mvp-equal-v1"
BASE_POLICY = "FIRST_7_ELIGIBLE_DAILY_PRICES"
SEEDED_BASE_POLICY = "SEEDED_FIXED"
BASE_REQUIRED_DATES = 7
ROUTE_PAIRS = (("DEL", "BOM"), ("DEL", "BLR"), ("BOM", "BLR"))
WINDOWS = (
    AdvanceWindow.T1,
    AdvanceWindow.T7,
    AdvanceWindow.T15,
    AdvanceWindow.T30,
    AdvanceWindow.T45,
)


def basket_version_name(data_class: DataClass) -> str:
    return f"{BASKET_VERSION_PREFIX}-{data_class.value.lower().replace('_', '-')}"


def ensure_mvp_basket(session: Session, data_class: DataClass) -> BasketVersion:
    version = basket_version_name(data_class)
    existing = session.scalar(select(BasketVersion).where(BasketVersion.version == version))
    if existing is not None:
        return existing

    routes = {
        (route.origin_iata, route.destination_iata): route
        for route in session.scalars(select(Route).where(Route.active.is_(True)))
    }
    missing = [pair for pair in ROUTE_PAIRS if pair not in routes]
    if missing:
        raise ValueError(f"frozen basket routes are missing: {missing}")

    basket = BasketVersion(
        version=version,
        name=f"Prototype APIx equal-weight basket ({data_class.value})",
        data_class=data_class,
        base_policy=BASE_POLICY,
        active=True,
    )
    session.add(basket)
    session.flush()
    dimensions = [(routes[pair], window) for pair in ROUTE_PAIRS for window in WINDOWS]
    equal_weight = (Decimal("1") / Decimal(len(dimensions))).quantize(
        Decimal("0.000000000001")
    )
    for route, window in dimensions:
        session.add(
            BasketItem(
                basket_version_id=basket.id,
                route_id=route.id,
                advance_window=window,
                weight=equal_weight,
                base_price=None,
                base_component_ids=[],
            )
        )
    session.commit()
    session.refresh(basket)
    return basket


def freeze_base_period_if_ready(
    session: Session,
    basket: BasketVersion,
    *,
    required_dates: int = BASE_REQUIRED_DATES,
    aggregation_version: str = AGGREGATION_VERSION,
) -> bool:
    if required_dates < 1:
        raise ValueError("base period must contain at least one date")
    items = list(
        session.scalars(
            select(BasketItem)
            .where(BasketItem.basket_version_id == basket.id)
            .order_by(BasketItem.id)
        )
    )
    for item in items:
        if item.base_price is not None:
            continue
        query = (
            select(DailyRouteWindowPrice)
            .join(CollectionRun, DailyRouteWindowPrice.collection_run_id == CollectionRun.id)
            .where(
                DailyRouteWindowPrice.basket_item_id == item.id,
                DailyRouteWindowPrice.data_class == basket.data_class,
                DailyRouteWindowPrice.aggregation_version == aggregation_version,
                DailyRouteWindowPrice.status == "AVAILABLE",
                DailyRouteWindowPrice.price.is_not(None),
            )
            .order_by(DailyRouteWindowPrice.methodological_date, DailyRouteWindowPrice.id)
            .limit(required_dates)
        )
        if basket.data_class is DataClass.LIVE:
            query = query.where(CollectionRun.trigger_type == RunTrigger.SCHEDULED)
        candidates = list(session.scalars(query))
        if len(candidates) < required_dates:
            continue
        prices = [row.price for row in candidates if row.price is not None]
        if len(prices) != required_dates:
            continue
        item.base_price = decimal_median(prices)
        item.base_component_ids = [str(row.id) for row in candidates]

    complete = bool(items) and all(item.base_price is not None for item in items)
    if complete and basket.base_end_date is None:
        all_base_rows = list(
            session.scalars(
                select(DailyRouteWindowPrice).where(
                    DailyRouteWindowPrice.id.in_(
                        [
                            uuid.UUID(component_id)
                            for item in items
                            for component_id in item.base_component_ids
                        ]
                    )
                )
            )
        )
        dates = [row.methodological_date for row in all_base_rows]
        basket.base_start_date = min(dates)
        basket.base_end_date = max(dates)
    session.commit()
    return complete


def set_seeded_base_prices(
    session: Session,
    basket: BasketVersion,
    prices: dict[uuid.UUID, Decimal],
    *,
    base_date: date,
) -> None:
    items = list(
        session.scalars(select(BasketItem).where(BasketItem.basket_version_id == basket.id))
    )
    expected_ids = {item.id for item in items}
    if set(prices) != expected_ids:
        raise ValueError("seeded base prices must cover every basket item exactly once")
    if any(price <= 0 for price in prices.values()):
        raise ValueError("seeded base prices must be positive")
    has_frozen_base = any(item.base_price is not None for item in items)
    if has_frozen_base and basket.base_policy != SEEDED_BASE_POLICY:
        raise ValueError("a naturally frozen basket base cannot be replaced with seeded prices")
    for item in items:
        existing = item.base_price
        if existing is not None and existing != prices[item.id]:
            raise ValueError("a frozen basket base cannot be changed")
        item.base_price = prices[item.id]
        item.base_component_ids = []
    basket.base_policy = SEEDED_BASE_POLICY
    basket.base_start_date = base_date
    basket.base_end_date = base_date
    session.commit()
