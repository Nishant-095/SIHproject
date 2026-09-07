from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import (
    AdvanceWindow,
    DataClass,
    RunTrigger,
    SourceReviewStatus,
    SourceType,
)
from app.models import CollectionJob, Route, Source
from app.services.planner import plan_collection_run
from app.services.seed import seed_configuration


def test_seed_is_exact_and_idempotent(session: Session) -> None:
    seed_configuration(session)
    seed_configuration(session)

    routes = list(
        session.scalars(select(Route).order_by(Route.origin_iata, Route.destination_iata))
    )
    assert [(route.origin_iata, route.destination_iata) for route in routes] == [
        ("BOM", "BLR"),
        ("DEL", "BLR"),
        ("DEL", "BOM"),
    ]
    assert session.scalar(select(func.count(Source.id))) == 3
    duffel = session.scalar(select(Source).where(Source.code == "DUFFEL"))
    assert duffel is not None
    assert duffel.enabled is False
    assert duffel.review_status is SourceReviewStatus.PENDING_REVIEW
    web = session.scalar(select(Source).where(Source.code == "PERMISSIONED_WEB"))
    assert web is not None
    assert web.enabled is False
    assert web.review_status is SourceReviewStatus.PENDING_REVIEW


def test_planner_creates_exact_route_window_matrix_once(session: Session) -> None:
    seed_configuration(session)
    planned = plan_collection_run(
        session,
        methodological_date=date(2026, 9, 5),
        timezone_name="Asia/Kolkata",
        hour=10,
        minute=0,
        trigger=RunTrigger.MANUAL,
        data_class=DataClass.SYNTHETIC,
    )

    assert planned.created is True
    assert planned.run.planned_jobs == 15
    jobs = list(
        session.scalars(
            select(CollectionJob).where(CollectionJob.collection_run_id == planned.run.id)
        )
    )
    assert len(jobs) == 15
    assert {job.advance_window for job in jobs} == {
        AdvanceWindow.T1,
        AdvanceWindow.T7,
        AdvanceWindow.T15,
        AdvanceWindow.T30,
        AdvanceWindow.T45,
    }
    assert {job.advance_days for job in jobs} == {1, 7, 15, 30, 45}
    assert {job.travel_date.isoformat() for job in jobs} == {
        "2026-09-06",
        "2026-09-12",
        "2026-09-20",
        "2026-10-05",
        "2026-10-20",
    }

    repeated = plan_collection_run(
        session,
        methodological_date=date(2026, 9, 5),
        timezone_name="Asia/Kolkata",
        hour=10,
        minute=0,
        trigger=RunTrigger.MANUAL,
        data_class=DataClass.SYNTHETIC,
    )
    assert repeated.created is False
    assert repeated.run.id == planned.run.id
    assert session.scalar(select(func.count(CollectionJob.id))) == 15


def test_planner_keeps_fixture_and_recorded_demo_runs_separate(session: Session) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        duffel_source_enabled=True,
        duffel_source_approved=True,
    )
    seed_configuration(session, settings)
    fixture = plan_collection_run(
        session,
        methodological_date=date(2026, 9, 6),
        timezone_name="Asia/Kolkata",
        hour=10,
        minute=0,
        trigger=RunTrigger.TEST,
        data_class=DataClass.SYNTHETIC,
        source_codes={"FIXTURE_LOCAL"},
    )
    recorded = plan_collection_run(
        session,
        methodological_date=date(2026, 9, 6),
        timezone_name="Asia/Kolkata",
        hour=10,
        minute=0,
        trigger=RunTrigger.TEST,
        data_class=DataClass.RECORDED_DEMO,
        source_codes={"DUFFEL"},
    )
    assert fixture.run.id != recorded.run.id
    assert fixture.run.planned_jobs == recorded.run.planned_jobs == 15
    assert session.scalar(select(func.count(CollectionJob.id))) == 30


def test_planner_multiplies_routes_windows_and_requested_sources(session: Session) -> None:
    seed_configuration(session)
    second = Source(
        code="SECOND_APPROVED",
        name="Second approved test source",
        source_type=SourceType.FIXTURE,
        enabled=True,
        collection_method="FIXTURE",
        review_status=SourceReviewStatus.APPROVED,
        parser_version="test-v1",
    )
    session.add(second)
    session.commit()

    planned = plan_collection_run(
        session,
        methodological_date=date(2026, 9, 8),
        timezone_name="Asia/Kolkata",
        hour=10,
        minute=0,
        trigger=RunTrigger.TEST,
        data_class=DataClass.SYNTHETIC,
        source_codes={"FIXTURE_LOCAL", "SECOND_APPROVED"},
    )

    jobs = list(
        session.scalars(
            select(CollectionJob).where(CollectionJob.collection_run_id == planned.run.id)
        )
    )
    assert planned.run.planned_jobs == 30
    assert len(jobs) == 30
    assert {job.source_id for job in jobs} == {
        session.scalar(select(Source.id).where(Source.code == "FIXTURE_LOCAL")),
        second.id,
    }
