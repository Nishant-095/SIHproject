from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.base import AdapterError, FareSearchRequest, RawFareQuote
from app.collectors.fixture import FixtureAdapter
from app.collectors.registry import AdapterRegistry
from app.core.config import Settings
from app.domain.enums import DataClass, FailureCode, RunStatus, RunTrigger
from app.models import CollectionJob, CollectionRun, FareObservation, RawQuote
from app.services.collection import CollectionService
from app.services.planner import plan_collection_run
from app.services.seed import seed_configuration


def test_fixture_pipeline_persists_raw_and_normalized_provenance(session: Session) -> None:
    service = CollectionService(
        Settings(app_env="test", database_url="sqlite+pysqlite:///:memory:")
    )
    result = asyncio.run(service.run_fixture(session, methodological_date=date(2026, 9, 5)))

    assert result.created is True
    assert result.run.status is RunStatus.COMPLETED
    assert result.run.data_class is DataClass.SYNTHETIC
    assert result.run.planned_jobs == 15
    assert result.run.successful_jobs == 15
    assert result.run.failed_jobs == 0
    assert result.run.valid_observations == 30
    assert session.scalar(select(func.count(RawQuote.id))) == 30
    assert session.scalar(select(func.count(FareObservation.id))) == 30
    assert all(session.scalars(select(FareObservation.included_in_index)))

    first_observation = session.scalar(select(FareObservation).order_by(FareObservation.id))
    assert first_observation is not None
    raw = session.get(RawQuote, first_observation.raw_quote_id)
    assert raw is not None
    assert raw.data_class is DataClass.SYNTHETIC
    assert raw.raw_payload["fixture"] is True
    assert len(raw.content_hash) == 64

    repeated = asyncio.run(service.run_fixture(session, methodological_date=date(2026, 9, 5)))
    assert repeated.created is False
    assert session.scalar(select(func.count(CollectionRun.id))) == 1
    assert session.scalar(select(func.count(CollectionJob.id))) == 15
    assert session.scalar(select(func.count(RawQuote.id))) == 30


class SelectiveFailureAdapter(FixtureAdapter):
    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        if request.origin == "DEL" and request.destination == "BOM":
            raise AdapterError(FailureCode.SOURCE_UNAVAILABLE, "Controlled test failure")
        return await super().search(request)


class DuplicatePayloadAdapter(FixtureAdapter):
    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        quote = (await super().search(request))[0]
        return [quote, quote]


def test_one_route_failure_does_not_abort_other_jobs(session: Session) -> None:
    registry = AdapterRegistry([SelectiveFailureAdapter()])
    service = CollectionService(
        Settings(
            app_env="test",
            database_url="sqlite+pysqlite:///:memory:",
            adapter_max_retries=0,
        ),
        registry,
    )
    result = asyncio.run(service.run_fixture(session, methodological_date=date(2026, 9, 6)))

    assert result.run.status is RunStatus.PARTIAL
    assert result.run.successful_jobs == 10
    assert result.run.failed_jobs == 5
    assert result.run.valid_observations == 20
    assert session.scalar(select(func.count(RawQuote.id))) == 20


def test_identical_payload_is_stored_once_per_job(session: Session) -> None:
    service = CollectionService(
        Settings(
            app_env="test",
            database_url="sqlite+pysqlite:///:memory:",
            adapter_max_retries=0,
        ),
        AdapterRegistry([DuplicatePayloadAdapter()]),
    )
    result = asyncio.run(service.run_fixture(session, methodological_date=date(2026, 9, 10)))
    assert result.run.successful_jobs == 15
    assert session.scalar(select(func.count(RawQuote.id))) == 15
    assert session.scalar(select(func.count(FareObservation.id))) == 15


def test_interrupted_planned_run_resumes_without_creating_a_second_run(
    session: Session,
) -> None:
    settings = Settings(app_env="test", database_url="sqlite+pysqlite:///:memory:")
    seed_configuration(session, settings)
    interrupted = plan_collection_run(
        session,
        methodological_date=date(2026, 9, 11),
        timezone_name=settings.collection_timezone,
        hour=settings.collection_hour,
        minute=settings.collection_minute,
        trigger=RunTrigger.MANUAL,
        data_class=DataClass.SYNTHETIC,
        source_codes={FixtureAdapter.source_code},
    )
    assert interrupted.created is True
    assert interrupted.run.status is RunStatus.PLANNED

    resumed = asyncio.run(
        CollectionService(settings).run_fixture(
            session,
            methodological_date=date(2026, 9, 11),
        )
    )

    assert resumed.created is False
    assert resumed.run.status is RunStatus.COMPLETED
    assert resumed.run.successful_jobs == 15
    assert session.scalar(select(func.count(CollectionRun.id))) == 1
    assert session.scalar(select(func.count(RawQuote.id))) == 30
