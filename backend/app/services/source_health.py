from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import (
    FailureCode,
    JobStatus,
    SourceHealthStatus,
    SourceReviewStatus,
)
from app.models import CollectionJob, CollectionRun, Source
from app.schemas.health import SourceHealthHistoryPointResponse, SourceHealthResponse


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


def _health_status(source: Source, jobs: list[CollectionJob]) -> SourceHealthStatus:
    if not source.enabled or source.review_status is SourceReviewStatus.DISABLED:
        return SourceHealthStatus.DISABLED
    if source.review_status is SourceReviewStatus.PARSER_CHANGED or any(
        job.failure_code is FailureCode.PARSER_CHANGED for job in jobs
    ):
        return SourceHealthStatus.PARSER_CHANGED
    if source.review_status in {SourceReviewStatus.BLOCKED, SourceReviewStatus.RESTRICTED} or any(
        job.failure_code
        in {
            FailureCode.CAPTCHA_BLOCKED,
            FailureCode.ROBOTS_DISALLOWED,
            FailureCode.TERMS_RESTRICTED,
        }
        for job in jobs
    ):
        return SourceHealthStatus.BLOCKED
    if jobs and all(job.status is JobStatus.SUCCEEDED for job in jobs):
        return SourceHealthStatus.HEALTHY
    return SourceHealthStatus.DEGRADED


def source_health_summary(session: Session) -> list[SourceHealthResponse]:
    results: list[SourceHealthResponse] = []
    for source in session.scalars(select(Source).order_by(Source.code)):
        jobs = list(
            session.scalars(
                select(CollectionJob)
                .where(CollectionJob.source_id == source.id)
                .order_by(CollectionJob.finished_at.desc(), CollectionJob.id.desc())
            )
        )
        successful = [job for job in jobs if job.status is JobStatus.SUCCEEDED]
        failed = [job for job in jobs if job.status is JobStatus.FAILED]
        completed = [*successful, *failed]
        durations = [duration for job in completed if (duration := _duration_ms(job)) is not None]
        last_success = next(
            (job.finished_at for job in jobs if job.status is JobStatus.SUCCEEDED), None
        )
        last_failure_job = next((job for job in jobs if job.status is JobStatus.FAILED), None)
        total = len(completed)
        results.append(
            SourceHealthResponse(
                source_code=source.code,
                source_name=source.name,
                enabled=source.enabled,
                review_status=source.review_status,
                health_status=_health_status(source, jobs),
                successful_jobs=len(successful),
                failed_jobs=len(failed),
                success_rate=None if total == 0 else round(100 * len(successful) / total, 2),
                average_duration_ms=None
                if not durations
                else round(sum(durations) / len(durations)),
                last_success_at=last_success,
                last_failure_at=None if last_failure_job is None else last_failure_job.finished_at,
                last_failure_code=(
                    None if last_failure_job is None else last_failure_job.failure_code
                ),
                parser_version=source.parser_version,
            )
        )
    return results


def source_health_history(
    session: Session,
    *,
    limit_days: int,
) -> list[SourceHealthHistoryPointResponse]:
    runs = list(
        session.scalars(
            select(CollectionRun)
            .order_by(CollectionRun.methodological_date.desc())
            .limit(limit_days)
        )
    )
    if not runs:
        return []
    dates = sorted({run.methodological_date for run in runs})
    run_ids_by_date = {
        day: [run.id for run in runs if run.methodological_date == day]
        for day in dates
    }
    results: list[SourceHealthHistoryPointResponse] = []
    for source in session.scalars(select(Source).order_by(Source.code)):
        for day in dates:
            jobs = list(
                session.scalars(
                    select(CollectionJob).where(
                        CollectionJob.source_id == source.id,
                        CollectionJob.collection_run_id.in_(run_ids_by_date[day]),
                    )
                )
            )
            if not jobs:
                continue
            successful = [job for job in jobs if job.status is JobStatus.SUCCEEDED]
            failed = [job for job in jobs if job.status is JobStatus.FAILED]
            completed = [*successful, *failed]
            durations = [
                duration
                for job in completed
                if (duration := _duration_ms(job)) is not None
            ]
            total = len(completed)
            results.append(
                SourceHealthHistoryPointResponse(
                    source_code=source.code,
                    methodological_date=day,
                    successful_jobs=len(successful),
                    failed_jobs=len(failed),
                    success_rate=(
                        None if total == 0 else round(100 * len(successful) / total, 2)
                    ),
                    average_duration_ms=(
                        None if not durations else round(sum(durations) / len(durations))
                    ),
                    health_status=_health_status(source, jobs),
                    parser_version=source.parser_version,
                )
            )
    return results
