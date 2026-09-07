from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import DataClass, PublicationStatus, RunStatus
from app.indexing.basket import ensure_mvp_basket, set_seeded_base_prices
from app.indexing.service import calculate_index_for_run
from app.models import (
    BasketItem,
    CanonicalFare,
    DailyIndex,
    DailyIndexComponent,
    DailyRouteWindowPrice,
    RouteWindowPriceInput,
)
from app.services.collection import CollectionService


def _settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        enforce_source_rate_limits=False,
    )


def _fixture_run(session: Session, methodological_date: date):
    return asyncio.run(
        CollectionService(_settings()).run_fixture(
            session,
            methodological_date=methodological_date,
        )
    ).run


def test_persisted_apix_matches_manual_calculation_and_retains_lineage(
    session: Session,
) -> None:
    run = _fixture_run(session, date(2027, 1, 1))
    basket = ensure_mvp_basket(session, DataClass.SYNTHETIC)
    items = list(
        session.scalars(select(BasketItem).where(BasketItem.basket_version_id == basket.id))
    )
    set_seeded_base_prices(
        session,
        basket,
        {item.id: Decimal("5000") for item in items},
        base_date=date(2026, 12, 31),
    )

    persisted = calculate_index_for_run(session, run.id)
    daily_prices = list(
        session.scalars(
            select(DailyRouteWindowPrice).where(
                DailyRouteWindowPrice.collection_run_id == run.id
            )
        )
    )
    manual_value = (
        sum((row.price for row in daily_prices if row.price is not None), Decimal("0"))
        / Decimal("15")
        / Decimal("5000")
        * Decimal("100")
    )

    assert persisted.created is True
    assert persisted.daily_index.publication_status is PublicationStatus.PUBLISHED
    assert persisted.daily_index.coverage_percent == Decimal("100.0000")
    assert persisted.daily_index.index_value == manual_value.quantize(Decimal("0.00000001"))
    assert persisted.daily_index.methodology_version == "prototype-v0.1.0"
    assert persisted.daily_index.canonicalization_version == "direct-then-median-v1"
    assert session.scalar(select(func.count(DailyRouteWindowPrice.id))) == 15
    assert session.scalar(select(func.count(RouteWindowPriceInput.canonical_fare_id))) == 30
    assert session.scalar(select(func.count(DailyIndexComponent.id))) == 15

    repeated = calculate_index_for_run(session, run.id)
    assert repeated.created is False
    assert repeated.daily_index.id == persisted.daily_index.id
    assert session.scalar(select(func.count(DailyIndex.id))) == 1


def test_first_seven_daily_prices_freeze_base_without_rewriting_inputs(
    session: Session,
) -> None:
    start = date(2027, 2, 1)
    results = []
    for offset in range(7):
        run = _fixture_run(session, start + timedelta(days=offset))
        results.append(calculate_index_for_run(session, run.id).daily_index)

    assert all(
        result.publication_status is PublicationStatus.PROVISIONAL_BASE
        for result in results[:6]
    )
    assert results[-1].publication_status is PublicationStatus.PUBLISHED
    basket = ensure_mvp_basket(session, DataClass.SYNTHETIC)
    items = list(
        session.scalars(select(BasketItem).where(BasketItem.basket_version_id == basket.id))
    )
    assert len(items) == 15
    assert all(item.base_price is not None for item in items)
    assert all(len(item.base_component_ids) == 7 for item in items)
    assert basket.base_start_date == start
    assert basket.base_end_date == start + timedelta(days=6)
    with pytest.raises(ValueError, match="naturally frozen"):
        set_seeded_base_prices(
            session,
            basket,
            {item.id: item.base_price for item in items if item.base_price is not None},
            base_date=start,
        )


def test_insufficient_coverage_is_stored_with_missing_components(
    session: Session,
) -> None:
    run = _fixture_run(session, date(2027, 3, 1))
    basket = ensure_mvp_basket(session, DataClass.SYNTHETIC)
    items = list(
        session.scalars(
            select(BasketItem)
            .where(BasketItem.basket_version_id == basket.id)
            .order_by(BasketItem.route_id, BasketItem.advance_window)
        )
    )
    set_seeded_base_prices(
        session,
        basket,
        {item.id: Decimal("5000") for item in items},
        base_date=date(2027, 2, 28),
    )
    for item in items[:4]:
        fares = list(
            session.scalars(
                select(CanonicalFare).where(
                    CanonicalFare.collection_run_id == run.id,
                    CanonicalFare.route_id == item.route_id,
                    CanonicalFare.advance_window == item.advance_window,
                )
            )
        )
        for fare in fares:
            session.delete(fare)
    session.commit()

    result = calculate_index_for_run(session, run.id).daily_index
    components = list(
        session.scalars(
            select(DailyIndexComponent).where(DailyIndexComponent.daily_index_id == result.id)
        )
    )
    assert result.publication_status is PublicationStatus.INSUFFICIENT_COVERAGE
    assert result.coverage_percent == Decimal("73.3333")
    assert result.index_value is not None
    assert len(components) == 15
    missing = [item for item in components if item.availability_reason == "MISSING_CURRENT_PRICE"]
    assert len(missing) == 4
    assert all(item.contribution is None for item in missing)


def test_index_rejects_an_unfinished_collection_run(session: Session) -> None:
    run = _fixture_run(session, date(2027, 4, 1))
    run.status = RunStatus.PLANNED
    session.commit()

    with pytest.raises(ValueError, match="completed or partial"):
        calculate_index_for_run(session, run.id)
