from __future__ import annotations

import asyncio
import logging
from datetime import date

from pytest import LogCaptureFixture, MonkeyPatch
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.base import AdapterError, FareSearchRequest, RawFareQuote
from app.collectors.fixture import FixtureAdapter
from app.collectors.registry import AdapterRegistry
from app.core.config import Settings
from app.domain.enums import DataClass, FailureCode, JobStatus, RunTrigger
from app.models import CollectionJob, FareObservation, RawQuote, Source
from app.services.planner import plan_collection_run
from app.services.seed import seed_configuration
from app.services.worker import TRANSIENT_FAILURES, CollectionWorker, SourceRateLimiter


def _planned_job(session: Session):
    seed_configuration(session)
    planned = plan_collection_run(
        session,
        methodological_date=date(2026, 9, 8),
        timezone_name="Asia/Kolkata",
        hour=10,
        minute=0,
        trigger=RunTrigger.TEST,
        data_class=DataClass.SYNTHETIC,
        source_codes={FixtureAdapter.source_code},
    )
    job = session.scalar(
        select(CollectionJob)
        .where(CollectionJob.collection_run_id == planned.run.id)
        .order_by(CollectionJob.id)
    )
    assert job is not None
    return planned.run, job


class FlakyAdapter(FixtureAdapter):
    def __init__(self, failures: int, code: FailureCode) -> None:
        self.failures = failures
        self.code = code

    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        if self.failures > 0:
            self.failures -= 1
            raise AdapterError(self.code, "controlled adapter failure")
        return await super().search(request)


class SlowAdapter(FixtureAdapter):
    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        await asyncio.sleep(0.02)
        return await super().search(request)


def test_transient_failure_retries_with_bounded_backoff(session: Session) -> None:
    run, job = _planned_job(session)
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    worker = CollectionWorker(
        Settings(
            app_env="test",
            database_url="sqlite+pysqlite:///:memory:",
            adapter_max_retries=2,
            retry_backoff_seconds=0.25,
            retry_backoff_max_seconds=0.4,
        ),
        AdapterRegistry([FlakyAdapter(2, FailureCode.SOURCE_UNAVAILABLE)]),
        sleep=record_sleep,
    )
    asyncio.run(worker.execute(session, run, job))

    assert job.status is JobStatus.SUCCEEDED
    assert job.attempt_count == 3
    assert delays == [0.25, 0.4]


def test_non_retryable_failure_stops_after_one_attempt(session: Session) -> None:
    run, job = _planned_job(session)
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    worker = CollectionWorker(
        Settings(app_env="test", database_url="sqlite+pysqlite:///:memory:"),
        AdapterRegistry([FlakyAdapter(5, FailureCode.AUTHENTICATION_FAILED)]),
        sleep=record_sleep,
    )
    asyncio.run(worker.execute(session, run, job))

    assert job.status is JobStatus.FAILED
    assert job.failure_code is FailureCode.AUTHENTICATION_FAILED
    assert job.attempt_count == 1
    assert delays == []


def test_timeout_is_retried_then_persisted(session: Session) -> None:
    run, job = _planned_job(session)
    worker = CollectionWorker(
        Settings(
            app_env="test",
            database_url="sqlite+pysqlite:///:memory:",
            adapter_timeout_seconds=0.001,
            adapter_max_retries=2,
            retry_backoff_seconds=0,
        ),
        AdapterRegistry([SlowAdapter()]),
    )
    asyncio.run(worker.execute(session, run, job))

    assert job.status is JobStatus.FAILED
    assert job.failure_code is FailureCode.NETWORK_TIMEOUT
    assert job.attempt_count == 3


def test_restarted_job_keeps_original_total_attempt_budget(session: Session) -> None:
    run, job = _planned_job(session)
    job.status = JobStatus.RUNNING
    job.attempt_count = 2
    session.commit()
    adapter = FlakyAdapter(5, FailureCode.SOURCE_UNAVAILABLE)
    worker = CollectionWorker(
        Settings(
            app_env="test",
            database_url="sqlite+pysqlite:///:memory:",
            adapter_max_retries=2,
            retry_backoff_seconds=0,
        ),
        AdapterRegistry([adapter]),
    )

    asyncio.run(worker.execute(session, run, job))

    assert job.status is JobStatus.FAILED
    assert job.attempt_count == 3
    assert adapter.failures == 4


def test_source_rate_limiter_spaces_sequential_requests(session: Session) -> None:
    seed_configuration(session)
    source = session.scalar(select(Source).where(Source.code == FixtureAdapter.source_code))
    assert source is not None
    source.rate_limit_per_minute = 60
    now = 100.0
    delays: list[float] = []

    def monotonic() -> float:
        return now

    async def advance(delay: float) -> None:
        nonlocal now
        delays.append(delay)
        now += delay

    limiter = SourceRateLimiter(sleep=advance, monotonic=monotonic)

    async def run() -> None:
        await limiter.wait(source)
        await limiter.wait(source)

    asyncio.run(run())
    assert delays == [1.0]


def test_retry_policy_is_exactly_the_transient_failure_set() -> None:
    assert TRANSIENT_FAILURES == {
        FailureCode.SOURCE_UNAVAILABLE,
        FailureCode.RATE_LIMITED,
        FailureCode.NETWORK_TIMEOUT,
        FailureCode.UNKNOWN_ERROR,
    }


def test_terminal_job_log_contains_duration(
    session: Session,
    caplog: LogCaptureFixture,
) -> None:
    run, job = _planned_job(session)
    worker = CollectionWorker(
        Settings(app_env="test", database_url="sqlite+pysqlite:///:memory:"),
        AdapterRegistry([FixtureAdapter()]),
    )
    with caplog.at_level(logging.INFO, logger="app.services.worker"):
        asyncio.run(worker.execute(session, run, job))
    completed = next(
        record for record in caplog.records if record.getMessage() == "collection_job_completed"
    )
    assert completed.duration_ms >= 0


def test_normalization_failure_retains_raw_quote_with_excluded_status(
    session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    run, job = _planned_job(session)

    def fail_normalization(**_: object) -> FareObservation:
        raise ValueError("controlled malformed normalization input")

    monkeypatch.setattr("app.services.worker.normalize_raw_quote", fail_normalization)
    worker = CollectionWorker(
        Settings(
            app_env="test",
            database_url="sqlite+pysqlite:///:memory:",
            adapter_max_retries=0,
        ),
        AdapterRegistry([FixtureAdapter()]),
    )

    asyncio.run(worker.execute(session, run, job))

    assert job.status is JobStatus.FAILED
    assert job.failure_code is FailureCode.INVALID_RESPONSE
    assert session.scalar(select(func.count(RawQuote.id))) == 1
    observation = session.scalar(select(FareObservation))
    assert observation is not None
    assert observation.included_in_index is False
    assert observation.quality_flags == ["PARSER_ERROR"]
    assert observation.exclusion_reason is not None
