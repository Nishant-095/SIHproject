from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import RunStatus
from app.indexing.aggregate import aggregate_route_window_prices
from app.indexing.base import IndexComponentInput
from app.indexing.basket import ensure_mvp_basket, freeze_base_period_if_ready
from app.indexing.methodology import METHODOLOGY_VERSION, PrototypeFixedWeightMethodology
from app.indexing.periods import refresh_periods_for_index
from app.models import (
    BasketItem,
    CanonicalFare,
    CollectionRun,
    DailyIndex,
    DailyIndexComponent,
)


@dataclass(frozen=True, slots=True)
class PersistedIndexResult:
    daily_index: DailyIndex
    created: bool


def calculate_index_for_run(
    session: Session,
    run_id: uuid.UUID,
    *,
    minimum_coverage_percent: Decimal = Decimal("80"),
) -> PersistedIndexResult:
    run = session.get(CollectionRun, run_id)
    if run is None:
        raise ValueError("collection run does not exist")
    if run.status not in {RunStatus.COMPLETED, RunStatus.PARTIAL}:
        raise ValueError("APIx can only be calculated from a completed or partial collection run")
    basket = ensure_mvp_basket(session, run.data_class)
    daily_prices = aggregate_route_window_prices(session, run=run, basket=basket)
    basket_complete = freeze_base_period_if_ready(session, basket)

    existing = session.scalar(
        select(DailyIndex).where(
            DailyIndex.methodological_date == run.methodological_date,
            DailyIndex.data_class == run.data_class,
            DailyIndex.basket_version_id == basket.id,
            DailyIndex.methodology_version == METHODOLOGY_VERSION,
        )
    )
    if existing is not None:
        if existing.collection_run_id != run.id:
            raise ValueError("this date already has an index from a different collection run")
        refresh_periods_for_index(session, existing)
        return PersistedIndexResult(existing, False)

    items = list(
        session.scalars(
            select(BasketItem)
            .where(BasketItem.basket_version_id == basket.id)
            .order_by(BasketItem.id)
        )
    )
    price_by_item = {price.basket_item_id: price for price in daily_prices}
    inputs = [
        IndexComponentInput(
            basket_item_id=item.id,
            daily_route_window_price_id=price_by_item[item.id].id,
            current_price=price_by_item[item.id].price,
            base_price=item.base_price,
            configured_weight=item.weight,
        )
        for item in items
    ]
    methodology = PrototypeFixedWeightMethodology(minimum_coverage_percent)
    result = methodology.calculate(inputs, basket_complete=basket_complete)
    canonical_versions = set(
        session.scalars(
            select(CanonicalFare.method_version).where(CanonicalFare.collection_run_id == run.id)
        )
    )
    if len(canonical_versions) > 1:
        raise ValueError("one collection run cannot mix canonicalization versions")
    canonicalization_version = next(iter(canonical_versions), "no-canonical-fares")
    daily_index = DailyIndex(
        collection_run_id=run.id,
        methodological_date=run.methodological_date,
        data_class=run.data_class,
        basket_version_id=basket.id,
        methodology_version=methodology.version,
        canonicalization_version=canonicalization_version,
        index_value=result.index_value,
        coverage_percent=result.coverage_percent,
        publication_status=result.publication_status,
    )
    session.add(daily_index)
    session.flush()
    for component in result.components:
        session.add(
            DailyIndexComponent(
                daily_index_id=daily_index.id,
                basket_item_id=component.basket_item_id,
                daily_route_window_price_id=component.daily_route_window_price_id,
                current_price=component.current_price,
                base_price=component.base_price,
                price_relative=component.price_relative,
                configured_weight=component.configured_weight,
                effective_weight=component.effective_weight,
                contribution=component.contribution,
                availability_reason=component.availability_reason,
            )
        )
    session.commit()
    session.refresh(daily_index)
    refresh_periods_for_index(session, daily_index)
    return PersistedIndexResult(daily_index, True)
