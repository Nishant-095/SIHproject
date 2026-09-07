from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collectors.duffel import DuffelAdapter
from app.collectors.fixture import FixtureAdapter
from app.collectors.permissioned_web import PermissionedWebAdapter
from app.collectors.registry import AdapterRegistry, default_registry
from app.core.config import Settings
from app.domain.enums import (
    DataClass,
    JobStatus,
    RunStatus,
    RunTrigger,
    SourceReviewStatus,
)
from app.models import CollectionJob, FareObservation, RawQuote, Source
from app.pipeline.outliers import flag_statistical_outliers
from app.services.canonical import canonicalize_run
from app.services.planner import PlannedRun, plan_collection_run
from app.services.seed import seed_configuration
from app.services.worker import CollectionWorker, raw_quote_hash

__all__ = ["CollectionService", "raw_quote_hash"]


class CollectionService:
    def __init__(self, settings: Settings, registry: AdapterRegistry | None = None) -> None:
        self.settings = settings
        self.registry = registry or default_registry(settings)

    async def run_fixture(
        self,
        session: Session,
        *,
        methodological_date: date,
        trigger: RunTrigger = RunTrigger.MANUAL,
    ) -> PlannedRun:
        return await self.run_sources(
            session,
            methodological_date=methodological_date,
            trigger=trigger,
            data_class=DataClass.SYNTHETIC,
            source_codes={FixtureAdapter.source_code},
        )

    async def run_duffel(
        self,
        session: Session,
        *,
        methodological_date: date,
        trigger: RunTrigger = RunTrigger.MANUAL,
    ) -> PlannedRun:
        if self.settings.duffel_access_token is None:
            raise ValueError("DUFFEL_ACCESS_TOKEN is required")
        if not self.settings.duffel_source_enabled:
            raise ValueError("DUFFEL_SOURCE_ENABLED must be true")
        if not self.settings.duffel_source_approved:
            raise ValueError("DUFFEL_SOURCE_APPROVED must be true")
        data_class = DataClass.LIVE if self.settings.duffel_live_mode else DataClass.RECORDED_DEMO
        return await self.run_sources(
            session,
            methodological_date=methodological_date,
            trigger=trigger,
            data_class=data_class,
            source_codes={DuffelAdapter.source_code},
        )

    async def run_permissioned_web(
        self,
        session: Session,
        *,
        methodological_date: date,
        trigger: RunTrigger = RunTrigger.MANUAL,
    ) -> PlannedRun:
        if not self.settings.web_source_approved:
            raise ValueError("WEB_SOURCE_APPROVED must be true")
        if not self.settings.web_source_permission_reference:
            raise ValueError("WEB_SOURCE_PERMISSION_REFERENCE is required")
        if self.settings.web_source_profile_path is None:
            raise ValueError("WEB_SOURCE_PROFILE_PATH is required")
        if not self.settings.web_source_enabled:
            raise ValueError("WEB_SOURCE_ENABLED must be true")
        return await self.run_sources(
            session,
            methodological_date=methodological_date,
            trigger=trigger,
            data_class=DataClass.LIVE,
            source_codes={PermissionedWebAdapter.source_code},
        )

    async def run_sources(
        self,
        session: Session,
        *,
        methodological_date: date,
        trigger: RunTrigger,
        data_class: DataClass,
        source_codes: set[str],
    ) -> PlannedRun:
        seed_configuration(session, self.settings)
        sources = list(
            session.scalars(
                select(Source).where(Source.code.in_(source_codes), Source.enabled.is_(True))
            )
        )
        if len(sources) != len(source_codes):
            raise ValueError("Every requested source must be configured and enabled")
        if data_class is DataClass.LIVE and any(
            source.review_status is not SourceReviewStatus.APPROVED for source in sources
        ):
            raise ValueError("LIVE collection requires approved sources")

        planned = plan_collection_run(
            session,
            methodological_date=methodological_date,
            timezone_name=self.settings.collection_timezone,
            hour=self.settings.collection_hour,
            minute=self.settings.collection_minute,
            trigger=trigger,
            data_class=data_class,
            source_codes=source_codes,
        )
        if not planned.created and planned.run.status in {
            RunStatus.COMPLETED,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
        }:
            return planned

        run = planned.run
        run.status = RunStatus.RUNNING
        run.started_at = run.started_at or datetime.now(UTC)
        session.commit()

        worker = CollectionWorker(self.settings, self.registry)
        jobs = list(
            session.scalars(
                select(CollectionJob)
                .where(
                    CollectionJob.collection_run_id == run.id,
                    CollectionJob.status.in_([JobStatus.PLANNED, JobStatus.RUNNING]),
                )
                .order_by(CollectionJob.id)
            )
        )
        for job in jobs:
            await worker.execute(session, run, job)

        flag_statistical_outliers(session, run.id)
        canonicalize_run(session, run.id, policy=self.settings.canonical_fare_policy)
        all_jobs = list(
            session.scalars(select(CollectionJob).where(CollectionJob.collection_run_id == run.id))
        )
        run.successful_jobs = sum(job.status is JobStatus.SUCCEEDED for job in all_jobs)
        run.failed_jobs = sum(job.status is JobStatus.FAILED for job in all_jobs)
        run.valid_observations = (
            session.scalar(
                select(func.count(FareObservation.id))
                .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
                .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
                .where(
                    CollectionJob.collection_run_id == run.id,
                    FareObservation.included_in_index.is_(True),
                )
            )
            or 0
        )
        if run.failed_jobs == 0:
            run.status = RunStatus.COMPLETED
        elif run.successful_jobs == 0:
            run.status = RunStatus.FAILED
        else:
            run.status = RunStatus.PARTIAL
        run.finished_at = datetime.now(UTC)
        session.commit()
        session.refresh(run)
        return planned
