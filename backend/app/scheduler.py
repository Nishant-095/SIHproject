from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.session import SessionLocal
from app.domain.enums import RunTrigger
from app.services.collection import CollectionService

logger = logging.getLogger(__name__)


def _run_scheduled_job(settings: Settings, session_factory: sessionmaker) -> None:
    methodological_date = datetime.now(ZoneInfo(settings.collection_timezone)).date()
    with session_factory() as session:
        service = CollectionService(settings)
        operations = {
            "fixture": service.run_fixture,
            "duffel": service.run_duffel,
            "permissioned_web": service.run_permissioned_web,
        }
        operation = operations[settings.scheduled_source]
        asyncio.run(
            operation(
                session,
                methodological_date=methodological_date,
                trigger=RunTrigger.SCHEDULED,
            )
        )


def build_scheduler(
    settings: Settings,
    session_factory: sessionmaker = SessionLocal,
) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=ZoneInfo(settings.collection_timezone))
    scheduler.add_job(
        _run_scheduled_job,
        trigger=CronTrigger(
            hour=settings.collection_hour,
            minute=settings.collection_minute,
            timezone=ZoneInfo(settings.collection_timezone),
        ),
        id="daily-airfare-collection",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        kwargs={"settings": settings, "session_factory": session_factory},
    )
    return scheduler


def start_scheduler(settings: Settings) -> BackgroundScheduler | None:
    if not settings.scheduler_enabled:
        return None
    scheduler = build_scheduler(settings)
    scheduler.start()
    logger.info(
        "scheduler_started",
        extra={
            "timezone": settings.collection_timezone,
            "hour": settings.collection_hour,
            "minute": settings.collection_minute,
            "scheduled_source": settings.scheduled_source,
        },
    )
    return scheduler
