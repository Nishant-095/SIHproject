from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from web_profile_helpers import valid_card, web_profile

from app.collectors.permissioned_web import PermissionedWebAdapter
from app.collectors.registry import AdapterRegistry
from app.collectors.web_browser import RenderedPage
from app.collectors.web_compliance import RobotsEvidence
from app.core.config import Settings
from app.domain.enums import (
    DataClass,
    PublicationStatus,
    ReferenceScope,
    ReferenceStatus,
    RunStatus,
    RunTrigger,
)
from app.indexing.basket import ensure_mvp_basket, set_seeded_base_prices
from app.indexing.service import calculate_index_for_run
from app.models import (
    BasketItem,
    CanonicalFare,
    CanonicalFareObservation,
    CollectionJob,
    CollectionRun,
    DailyIndexComponent,
    DailyRouteWindowPrice,
    FareObservation,
    PeriodIndex,
    PeriodIndexInput,
    RawQuote,
    Source,
)
from app.schemas.historical import HistoricalDatasetImportRequest, HistoricalObservationInput
from app.services.collection import CollectionService
from app.services.historical import build_backtest, import_historical_dataset


class _AllowingRobotsChecker:
    async def check(self, *, robots_url: str, target_url: str, user_agent: str) -> RobotsEvidence:
        return RobotsEvidence(robots_url, 200, True, None)


class _RouteAwareRenderer:
    async def render(self, *, url: str, profile, user_agent: str, timeout_ms: int):
        query = parse_qs(urlsplit(url).query)
        return RenderedPage(
            final_url=url,
            status_code=200,
            page_title="Permissioned PostgreSQL integration",
            captured_at_utc=datetime(2099, 4, 1, tzinfo=UTC),
            cards=(
                valid_card(
                    origin=query["origin"][0],
                    destination=query["destination"][0],
                    travel_date=query["date"][0],
                ),
            ),
        )


@pytest.mark.postgresql
def test_fixture_pipeline_against_migrated_postgresql() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration")
    engine = create_engine(database_url)
    try:
        assert engine.dialect.name == "postgresql"
        with Session(engine, expire_on_commit=False) as session:
            assert session.scalar(text("SELECT current_database()")) == "airfare_apix_test"
            service = CollectionService(Settings(app_env="test", database_url=database_url))
            results = [
                asyncio.run(
                    service.run_fixture(
                        session,
                        methodological_date=date(2099, 1, day),
                        trigger=RunTrigger.SCHEDULED,
                    )
                )
                for day in range(1, 4)
            ]
            result = results[0]
            assert result.run.status is RunStatus.COMPLETED
            assert result.run.successful_jobs == 15
            assert all(item.run.status is RunStatus.COMPLETED for item in results)
            assert all(item.run.trigger_type is RunTrigger.SCHEDULED for item in results)
            assert (
                session.scalar(
                    select(func.count(CollectionRun.id)).where(
                        CollectionRun.id.in_([item.run.id for item in results])
                    )
                )
                == 3
            )
            assert (
                session.scalar(
                    select(func.count(CollectionJob.id)).where(
                        CollectionJob.collection_run_id == result.run.id
                    )
                )
                == 15
            )
            assert (
                session.scalar(
                    select(func.count(RawQuote.id))
                    .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
                    .where(CollectionJob.collection_run_id == result.run.id)
                )
                == 30
            )
            assert (
                session.scalar(
                    select(func.count(CollectionJob.id)).where(
                        CollectionJob.collection_run_id.in_([item.run.id for item in results])
                    )
                )
                == 45
            )
            assert (
                session.scalar(
                    select(func.count(FareObservation.id))
                    .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
                    .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
                    .where(CollectionJob.collection_run_id == result.run.id)
                )
                == 30
            )
            assert (
                session.scalar(
                    select(func.count(CanonicalFare.id)).where(
                        CanonicalFare.collection_run_id == result.run.id
                    )
                )
                == 30
            )
    finally:
        engine.dispose()


@pytest.mark.postgresql
def test_phase_8_apix_persists_exact_components_in_postgresql() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration")
    engine = create_engine(database_url)
    try:
        with Session(engine, expire_on_commit=False) as session:
            settings = Settings(app_env="test", database_url=database_url)
            run = asyncio.run(
                CollectionService(settings).run_fixture(
                    session,
                    methodological_date=date(2099, 6, 1),
                    trigger=RunTrigger.TEST,
                )
            ).run
            basket = ensure_mvp_basket(session, DataClass.SYNTHETIC)
            items = list(
                session.scalars(
                    select(BasketItem).where(BasketItem.basket_version_id == basket.id)
                )
            )
            set_seeded_base_prices(
                session,
                basket,
                {item.id: Decimal("5000") for item in items},
                base_date=date(2099, 5, 31),
            )
            result = calculate_index_for_run(session, run.id).daily_index

            assert result.publication_status is PublicationStatus.PUBLISHED
            assert result.coverage_percent == Decimal("100.0000")
            assert result.index_value is not None
            assert (
                session.scalar(
                    select(func.count(DailyRouteWindowPrice.id)).where(
                        DailyRouteWindowPrice.collection_run_id == run.id
                    )
                )
                == 15
            )
            assert (
                session.scalar(
                    select(func.count(DailyIndexComponent.id)).where(
                        DailyIndexComponent.daily_index_id == result.id
                    )
                )
                == 15
            )
            period_rows = list(
                session.scalars(
                    select(PeriodIndex).where(PeriodIndex.data_class == DataClass.SYNTHETIC)
                )
            )
            assert len(period_rows) >= 2
            assert {row.period_type.value for row in period_rows} >= {"WEEKLY", "MONTHLY"}
            assert all(
                row.missing_data_policy == "published-days-mean-no-imputation-v1"
                for row in period_rows
            )
            assert (
                session.scalar(
                    select(func.count(PeriodIndexInput.daily_index_id)).where(
                        PeriodIndexInput.daily_index_id == result.id
                    )
                )
                == 2
            )
    finally:
        engine.dispose()


@pytest.mark.postgresql
def test_phase_14_reference_and_backtest_persist_in_postgresql() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration")
    engine = create_engine(database_url)
    try:
        with Session(engine, expire_on_commit=False) as session:
            settings = Settings(app_env="test", database_url=database_url)
            planned = asyncio.run(
                CollectionService(settings).run_fixture(
                    session,
                    methodological_date=date(2099, 6, 2),
                    trigger=RunTrigger.TEST,
                )
            )
            basket = ensure_mvp_basket(session, DataClass.SYNTHETIC)
            items = list(
                session.scalars(
                    select(BasketItem).where(BasketItem.basket_version_id == basket.id)
                )
            )
            if any(item.base_price is None for item in items):
                set_seeded_base_prices(
                    session,
                    basket,
                    {item.id: Decimal("5000") for item in items},
                    base_date=date(2099, 6, 1),
                )
            calculate_index_for_run(session, planned.run.id)
            payload = HistoricalDatasetImportRequest(
                code="PG-PHASE14-REFERENCE-2099-06",
                title="PostgreSQL integration reference",
                publisher="Test publisher",
                source_url="https://example.com/reference",
                license_name="Test-only data",
                metric_name="Airfare reference index",
                frequency="MONTHLY",
                base_period="2099-06=100",
                observations=[
                    HistoricalObservationInput(
                        period_start=date(2099, 6, 1),
                        period_end=date(2099, 6, 30),
                        scope_type=ReferenceScope.NATIONAL,
                        index_value=Decimal("100"),
                        status=ReferenceStatus.FINAL,
                        source_record_id="pg-phase14-june-2099",
                    )
                ],
            )
            dataset, _ = import_historical_dataset(session, payload)
            report = build_backtest(
                session,
                dataset_code=dataset.code,
                data_class=DataClass.SYNTHETIC,
            )

            assert dataset.data_class is DataClass.HISTORICAL
            assert dataset.row_count == 1
            assert report.overlap_month_count == 1
            assert len(report.route_comparisons) == 3
            assert report.correlation_status == "INSUFFICIENT_OVERLAP"
    finally:
        engine.dispose()


@pytest.mark.postgresql
def test_permissioned_web_pipeline_persists_auditable_layers_in_postgresql(
    tmp_path: Path,
) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration")

    profile = web_profile()
    profile_path = tmp_path / "permissioned-profile.json"
    profile_path.write_text(profile.model_dump_json(), encoding="utf-8")
    settings = Settings(
        app_env="test",
        database_url=database_url,
        web_source_profile_path=profile_path,
        web_source_enabled=True,
        web_source_approved=True,
        web_source_permission_reference="integration-test-permission",
        adapter_max_retries=0,
        enforce_source_rate_limits=False,
    )
    adapter = PermissionedWebAdapter(
        profile=profile,
        permission_confirmed=True,
        permission_reference=settings.web_source_permission_reference,
        user_agent=settings.web_source_user_agent,
        browser_timeout_ms=settings.web_source_browser_timeout_ms,
        renderer=_RouteAwareRenderer(),
        robots_checker=_AllowingRobotsChecker(),
    )
    engine = create_engine(database_url)
    try:
        with Session(engine, expire_on_commit=False) as session:
            result = asyncio.run(
                CollectionService(settings, AdapterRegistry([adapter])).run_permissioned_web(
                    session,
                    methodological_date=date(2099, 4, 1),
                )
            )
            run_id = result.run.id
            assert result.run.status is RunStatus.COMPLETED
            assert result.run.data_class is DataClass.LIVE
            assert result.run.successful_jobs == 15
            assert result.run.valid_observations == 15
            assert (
                session.scalar(
                    select(func.count(RawQuote.id))
                    .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
                    .where(CollectionJob.collection_run_id == run_id)
                )
                == 15
            )
            assert (
                session.scalar(
                    select(func.count(FareObservation.id))
                    .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
                    .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
                    .where(CollectionJob.collection_run_id == run_id)
                )
                == 15
            )
            canonical = list(
                session.scalars(
                    select(CanonicalFare).where(CanonicalFare.collection_run_id == run_id)
                )
            )
            assert len(canonical) == 15
            linked_source_codes = set(
                session.scalars(
                    select(Source.code)
                    .join(CanonicalFareObservation, Source.id == CanonicalFareObservation.source_id)
                    .join(
                        CanonicalFare,
                        CanonicalFareObservation.canonical_fare_id == CanonicalFare.id,
                    )
                    .where(CanonicalFare.collection_run_id == run_id)
                )
            )
            assert linked_source_codes == {"PERMISSIONED_WEB"}
            raw = session.scalar(
                select(RawQuote)
                .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
                .where(CollectionJob.collection_run_id == run_id)
            )
            assert raw is not None
            assert raw.raw_payload["permission_reference"] == "integration-test-permission"
            assert raw.raw_payload["robots"]["allowed"] is True
    finally:
        engine.dispose()
