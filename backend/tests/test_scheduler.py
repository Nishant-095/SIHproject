from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import CollectionJob, CollectionRun, RawQuote
from app.scheduler import _run_scheduled_job, build_scheduler


def test_scheduler_owns_one_non_overlapping_daily_job() -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        collection_timezone="Asia/Kolkata",
        collection_hour=10,
        collection_minute=0,
    )
    scheduler = build_scheduler(settings)
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "daily-airfare-collection"
    assert jobs[0].max_instances == 1
    assert "hour='10'" in str(jobs[0].trigger)
    assert "minute='0'" in str(jobs[0].trigger)


def test_scheduler_carries_explicit_duffel_source_selection() -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        scheduled_source="duffel",
    )
    job = build_scheduler(settings).get_jobs()[0]
    assert job.kwargs["settings"].scheduled_source == "duffel"


def test_scheduler_carries_explicit_permissioned_web_source_selection() -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        scheduled_source="permissioned_web",
    )
    job = build_scheduler(settings).get_jobs()[0]
    assert job.kwargs["settings"].scheduled_source == "permissioned_web"


def test_actual_scheduled_callback_runs_full_pipeline_once(engine) -> None:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        scheduled_source="fixture",
        enforce_source_rate_limits=False,
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    _run_scheduled_job(settings, factory)
    _run_scheduled_job(settings, factory)

    with Session(engine) as session:
        assert session.scalar(select(func.count(CollectionRun.id))) == 1
        assert session.scalar(select(func.count(CollectionJob.id))) == 15
        assert session.scalar(select(func.count(RawQuote.id))) == 30
