from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.booking_window import WINDOW_DAYS, classify_advance_window, travel_date_for
from app.domain.enums import DataClass, JobStatus, RunStatus, RunTrigger
from app.models import CollectionJob, CollectionRun, Route, Source


@dataclass(frozen=True, slots=True)
class PlannedRun:
    run: CollectionRun
    created: bool


def scheduled_time_utc(
    methodological_date: date,
    *,
    timezone_name: str,
    hour: int,
    minute: int,
) -> datetime:
    local = datetime.combine(
        methodological_date,
        time(hour=hour, minute=minute),
        tzinfo=ZoneInfo(timezone_name),
    )
    return local.astimezone(UTC)


def plan_collection_run(
    session: Session,
    *,
    methodological_date: date,
    timezone_name: str,
    hour: int,
    minute: int,
    trigger: RunTrigger,
    data_class: DataClass,
    source_codes: set[str] | None = None,
) -> PlannedRun:
    existing = session.scalar(
        select(CollectionRun).where(
            CollectionRun.methodological_date == methodological_date,
            CollectionRun.trigger_type == trigger,
            CollectionRun.data_class == data_class,
        )
    )
    if existing is not None:
        return PlannedRun(run=existing, created=False)

    routes = list(
        session.scalars(
            select(Route)
            .where(Route.active.is_(True))
            .order_by(Route.origin_iata, Route.destination_iata)
        )
    )
    source_query = select(Source).where(Source.enabled.is_(True))
    if source_codes is not None:
        source_query = source_query.where(Source.code.in_(source_codes))
    sources = list(session.scalars(source_query.order_by(Source.code)))

    run = CollectionRun(
        methodological_date=methodological_date,
        scheduled_for_utc=scheduled_time_utc(
            methodological_date,
            timezone_name=timezone_name,
            hour=hour,
            minute=minute,
        ),
        status=RunStatus.PLANNED,
        trigger_type=trigger,
        data_class=data_class,
        planned_jobs=len(routes) * len(WINDOW_DAYS) * len(sources),
        successful_jobs=0,
        failed_jobs=0,
        valid_observations=0,
    )
    session.add(run)
    session.flush()

    for route in routes:
        for advance_days in WINDOW_DAYS:
            window = classify_advance_window(advance_days)
            travel_date = travel_date_for(methodological_date, advance_days)
            for source in sources:
                key = ":".join(
                    (
                        data_class.value,
                        trigger.value,
                        methodological_date.isoformat(),
                        source.code,
                        f"{route.origin_iata}-{route.destination_iata}",
                        window.value,
                    )
                )
                session.add(
                    CollectionJob(
                        collection_run_id=run.id,
                        source_id=source.id,
                        route_id=route.id,
                        travel_date=travel_date,
                        advance_days=advance_days,
                        advance_window=window,
                        status=JobStatus.PLANNED,
                        attempt_count=0,
                        idempotency_key=key,
                    )
                )
    session.commit()
    session.refresh(run)
    return PlannedRun(run=run, created=True)
