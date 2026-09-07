from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import AdapterError, FareSearchRequest, RawFareQuote
from app.collectors.registry import AdapterRegistry
from app.core.config import Settings
from app.domain.enums import FailureCode, JobStatus
from app.models import CollectionJob, CollectionRun, FareObservation, RawQuote, Route, Source
from app.pipeline.normalize import normalize_raw_quote, rejected_normalization_observation

logger = logging.getLogger(__name__)

TRANSIENT_FAILURES = {
    FailureCode.SOURCE_UNAVAILABLE,
    FailureCode.RATE_LIMITED,
    FailureCode.NETWORK_TIMEOUT,
    FailureCode.UNKNOWN_ERROR,
}


def raw_quote_hash(quote: RawFareQuote) -> str:
    canonical = json.dumps(asdict(quote), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SourceRateLimiter:
    def __init__(
        self,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sleep = sleep
        self._monotonic = monotonic
        self._next_request_at: dict[str, float] = {}

    async def wait(self, source: Source) -> None:
        if source.rate_limit_per_minute is None:
            return
        interval = 60.0 / source.rate_limit_per_minute
        now = self._monotonic()
        next_at = self._next_request_at.get(source.code, now)
        if next_at > now:
            await self._sleep(next_at - now)
            now = self._monotonic()
        self._next_request_at[source.code] = max(now, next_at) + interval


class CollectionWorker:
    """Execute jobs independently from APScheduler or API orchestration."""

    def __init__(
        self,
        settings: Settings,
        registry: AdapterRegistry,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        rate_limiter: SourceRateLimiter | None = None,
    ) -> None:
        self.settings = settings
        self.registry = registry
        self._sleep = sleep
        self.rate_limiter = rate_limiter or SourceRateLimiter(sleep=sleep)

    async def execute(self, session: Session, run: CollectionRun, job: CollectionJob) -> None:
        route = session.get(Route, job.route_id)
        source = session.get(Source, job.source_id)
        if route is None or source is None:
            self._fail_job(session, job, FailureCode.INVALID_RESPONSE, "Missing route or source")
            return

        job.status = JobStatus.RUNNING
        job.started_at = job.started_at or datetime.now(UTC)
        session.commit()
        max_attempts = self.settings.adapter_max_retries + 1
        attempts_remaining = max_attempts - job.attempt_count
        if attempts_remaining <= 0:
            self._fail_job(
                session,
                job,
                FailureCode.UNKNOWN_ERROR,
                "Maximum adapter attempts were already consumed",
            )
            return

        for _ in range(attempts_remaining):
            job.attempt_count += 1
            session.commit()
            failure = await self._attempt(session, run, job, route, source)
            if failure is None:
                return
            code, message = failure
            should_retry = code in TRANSIENT_FAILURES and job.attempt_count < max_attempts
            if not should_retry:
                self._fail_job(session, job, code, message)
                return
            delay = min(
                self.settings.retry_backoff_seconds * (2 ** (job.attempt_count - 1)),
                self.settings.retry_backoff_max_seconds,
            )
            logger.warning(
                "collection_job_retrying",
                extra={
                    "run_id": str(run.id),
                    "job_id": str(job.id),
                    "source": source.code,
                    "attempt": job.attempt_count,
                    "failure_code": code.value,
                    "backoff_seconds": delay,
                },
            )
            if delay > 0:
                await self._sleep(delay)

    async def _attempt(
        self,
        session: Session,
        run: CollectionRun,
        job: CollectionJob,
        route: Route,
        source: Source,
    ) -> tuple[FailureCode, str] | None:
        try:
            adapter = self.registry.get(source.code)
            if self.settings.enforce_source_rate_limits:
                await self.rate_limiter.wait(source)
            async with asyncio.timeout(self.settings.adapter_timeout_seconds):
                quotes = await adapter.search(
                    FareSearchRequest(
                        origin=route.origin_iata,
                        destination=route.destination_iata,
                        travel_date=job.travel_date,
                    )
                )
            if not quotes:
                job.status = JobStatus.SUCCEEDED
                job.failure_code = FailureCode.NO_RESULTS
                job.error_message = None
                job.finished_at = datetime.now(UTC)
                session.commit()
                return None

            for quote in quotes:
                raw = self._persist_raw_quote(session, run, job, source, route, quote)
                existing_observation = session.scalar(
                    select(FareObservation).where(FareObservation.raw_quote_id == raw.id)
                )
                if existing_observation is None:
                    try:
                        observation = normalize_raw_quote(
                            raw_quote=raw,
                            job=job,
                            run=run,
                            route=route,
                            source=source,
                        )
                    except (KeyError, TypeError, ValueError) as exc:
                        observation = rejected_normalization_observation(
                            raw_quote=raw,
                            job=job,
                            run=run,
                            route=route,
                            reason=str(exc),
                        )
                        session.add(observation)
                        session.flush()
                        session.commit()
                        return FailureCode.INVALID_RESPONSE, "Quote normalization failed"
                    session.add(observation)
                    session.flush()

            job.status = JobStatus.SUCCEEDED
            job.failure_code = None
            job.error_message = None
            job.finished_at = datetime.now(UTC)
            session.commit()
            logger.info(
                "collection_job_completed",
                extra={
                    "run_id": str(run.id),
                    "job_id": str(job.id),
                    "source": source.code,
                    "route": f"{route.origin_iata}-{route.destination_iata}",
                    "travel_date": job.travel_date.isoformat(),
                    "window": job.advance_window.value,
                    "attempt": job.attempt_count,
                    "status": job.status.value,
                    "duration_ms": self._duration_ms(job),
                },
            )
            return None
        except TimeoutError:
            return FailureCode.NETWORK_TIMEOUT, "Adapter exceeded configured timeout"
        except AdapterError as exc:
            return exc.code, str(exc)
        except (KeyError, TypeError, ValueError) as exc:
            session.rollback()
            return FailureCode.INVALID_RESPONSE, str(exc)
        except Exception:
            session.rollback()
            logger.exception(
                "collection_job_unknown_failure",
                extra={"run_id": str(run.id), "job_id": str(job.id)},
            )
            return FailureCode.UNKNOWN_ERROR, "Unexpected adapter failure"

    @staticmethod
    def _duration_ms(job: CollectionJob) -> int | None:
        if job.started_at is None or job.finished_at is None:
            return None
        started = job.started_at
        finished = job.finished_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=UTC)
        return max(0, round((finished - started).total_seconds() * 1000))

    @staticmethod
    def _persist_raw_quote(
        session: Session,
        run: CollectionRun,
        job: CollectionJob,
        source: Source,
        route: Route,
        quote: RawFareQuote,
    ) -> RawQuote:
        if not isinstance(quote.raw_payload, dict):
            raise ValueError("Adapter raw_payload must be a JSON object")
        content_hash = raw_quote_hash(quote)
        existing = session.scalar(
            select(RawQuote).where(
                RawQuote.collection_job_id == job.id,
                RawQuote.content_hash == content_hash,
            )
        )
        if existing is not None:
            return existing

        raw = RawQuote(
            collection_job_id=job.id,
            source_id=source.id,
            data_class=run.data_class,
            observed_at_utc=datetime.now(UTC),
            query_origin=route.origin_iata,
            query_destination=route.destination_iata,
            query_travel_date=job.travel_date,
            raw_airline_name=quote.airline_name,
            raw_flight_number=quote.flight_number,
            raw_departure=quote.departure_time,
            raw_arrival=quote.arrival_time,
            raw_fare_text=None if quote.total_fare is None else str(quote.total_fare),
            raw_currency=quote.currency,
            raw_base_fare=quote.base_fare,
            raw_tax_text=None if quote.taxes is None else str(quote.taxes),
            raw_total_fare=quote.total_fare,
            raw_payload=quote.raw_payload,
            parser_version=source.parser_version,
            content_hash=content_hash,
        )
        session.add(raw)
        session.flush()
        return raw

    @staticmethod
    def _fail_job(
        session: Session,
        job: CollectionJob,
        code: FailureCode,
        message: str,
    ) -> None:
        job.status = JobStatus.FAILED
        job.failure_code = code
        job.error_message = message[:1000]
        job.finished_at = datetime.now(UTC)
        session.commit()
        logger.warning(
            "collection_job_failed",
            extra={
                "run_id": str(job.collection_run_id),
                "job_id": str(job.id),
                "source_id": str(job.source_id),
                "route_id": str(job.route_id),
                "travel_date": job.travel_date.isoformat(),
                "window": job.advance_window.value,
                "attempt": job.attempt_count,
                "status": job.status.value,
                "failure_code": code.value,
                "duration_ms": CollectionWorker._duration_ms(job),
            },
        )
