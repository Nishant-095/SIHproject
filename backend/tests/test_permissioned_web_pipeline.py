from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from web_profile_helpers import valid_card, web_profile

from app.collectors.base import AdapterError
from app.collectors.permissioned_web import PermissionedWebAdapter
from app.collectors.registry import AdapterRegistry
from app.collectors.web_browser import RenderedPage
from app.collectors.web_compliance import RobotsEvidence
from app.core.config import Settings
from app.domain.enums import (
    DataClass,
    FailureCode,
    RunStatus,
    SourceHealthStatus,
    SourceReviewStatus,
)
from app.models import CanonicalFare, CollectionJob, FareObservation, RawQuote, Source
from app.services.collection import CollectionService
from app.services.source_health import source_health_summary


class AllowingRobotsChecker:
    async def check(self, *, robots_url: str, target_url: str, user_agent: str) -> RobotsEvidence:
        return RobotsEvidence(robots_url, 200, True, None)


class DenyingRobotsChecker:
    async def check(self, *, robots_url: str, target_url: str, user_agent: str) -> RobotsEvidence:
        raise AdapterError(FailureCode.ROBOTS_DISALLOWED, "controlled robots denial")


class RouteAwareRenderer:
    async def render(self, *, url: str, profile, user_agent: str, timeout_ms: int):
        query = parse_qs(urlsplit(url).query)
        origin = query["origin"][0]
        destination = query["destination"][0]
        travel_date = query["date"][0]
        return RenderedPage(
            final_url=url,
            status_code=200,
            page_title="Permissioned fare results",
            captured_at_utc=datetime(2099, 1, 1, tzinfo=UTC),
            cards=(
                valid_card(
                    origin=origin,
                    destination=destination,
                    travel_date=travel_date,
                ),
            ),
        )


def _settings_and_adapter(tmp_path: Path):
    profile = web_profile()
    profile_path = tmp_path / "permissioned-profile.json"
    profile_path.write_text(profile.model_dump_json(), encoding="utf-8")
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        web_source_profile_path=profile_path,
        web_source_enabled=True,
        web_source_approved=True,
        web_source_permission_reference="test-permission-letter",
        adapter_max_retries=0,
        enforce_source_rate_limits=False,
    )
    adapter = PermissionedWebAdapter(
        profile=profile,
        permission_confirmed=True,
        permission_reference=settings.web_source_permission_reference,
        user_agent=settings.web_source_user_agent,
        browser_timeout_ms=settings.web_source_browser_timeout_ms,
        renderer=RouteAwareRenderer(),
        robots_checker=AllowingRobotsChecker(),
    )
    return settings, adapter


def test_permissioned_web_runs_full_five_window_pipeline(
    session: Session,
    tmp_path: Path,
) -> None:
    settings, adapter = _settings_and_adapter(tmp_path)
    result = asyncio.run(
        CollectionService(settings, AdapterRegistry([adapter])).run_permissioned_web(
            session,
            methodological_date=date(2099, 2, 1),
        )
    )

    assert result.run.status is RunStatus.COMPLETED
    assert result.run.data_class is DataClass.LIVE
    assert result.run.planned_jobs == 15
    assert result.run.successful_jobs == 15
    assert result.run.failed_jobs == 0
    assert result.run.valid_observations == 15
    assert session.scalar(select(func.count(CollectionJob.id))) == 15
    assert session.scalar(select(func.count(RawQuote.id))) == 15
    assert session.scalar(select(func.count(FareObservation.id))) == 15
    assert session.scalar(select(func.count(CanonicalFare.id))) == 15
    assert all(session.scalars(select(FareObservation.included_in_index)))

    source = session.scalar(select(Source).where(Source.code == "PERMISSIONED_WEB"))
    assert source is not None
    assert source.review_status is SourceReviewStatus.APPROVED
    assert source.collection_method == "PERMISSIONED_BROWSER"


def test_web_pipeline_refuses_unapproved_configuration(
    session: Session,
) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        web_source_enabled=True,
        web_source_approved=False,
    )
    try:
        asyncio.run(
            CollectionService(settings).run_permissioned_web(
                session,
                methodological_date=date(2099, 2, 2),
            )
        )
    except ValueError as exc:
        assert "WEB_SOURCE_APPROVED" in str(exc)
    else:
        raise AssertionError("unapproved web source unexpectedly ran")


def test_web_policy_failure_is_persisted_and_visible_in_source_health(
    session: Session,
    tmp_path: Path,
) -> None:
    settings, _ = _settings_and_adapter(tmp_path)
    denied = PermissionedWebAdapter(
        profile=web_profile(),
        permission_confirmed=True,
        permission_reference="test-permission-letter",
        user_agent=settings.web_source_user_agent,
        browser_timeout_ms=settings.web_source_browser_timeout_ms,
        renderer=RouteAwareRenderer(),
        robots_checker=DenyingRobotsChecker(),
    )

    result = asyncio.run(
        CollectionService(settings, AdapterRegistry([denied])).run_permissioned_web(
            session,
            methodological_date=date(2099, 2, 3),
        )
    )

    assert result.run.status is RunStatus.FAILED
    jobs = list(session.scalars(select(CollectionJob)))
    assert len(jobs) == 15
    assert all(job.failure_code is FailureCode.ROBOTS_DISALLOWED for job in jobs)
    health = next(
        item for item in source_health_summary(session) if item.source_code == "PERMISSIONED_WEB"
    )
    assert health.health_status is SourceHealthStatus.BLOCKED
    assert health.failed_jobs == 15
    assert health.last_failure_code is FailureCode.ROBOTS_DISALLOWED
