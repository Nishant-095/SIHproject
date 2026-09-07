from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import (
    AdvanceWindow,
    DataClass,
    FailureCode,
    JobStatus,
    RunStatus,
    RunTrigger,
)
from app.models.base import CreatedAtMixin
from app.models.types import enum_type


class CollectionRun(CreatedAtMixin, Base):
    __tablename__ = "collection_runs"
    __table_args__ = (
        CheckConstraint("planned_jobs >= 0", name="ck_runs_planned_jobs_nonnegative"),
        CheckConstraint("successful_jobs >= 0", name="ck_runs_successful_jobs_nonnegative"),
        CheckConstraint("failed_jobs >= 0", name="ck_runs_failed_jobs_nonnegative"),
        CheckConstraint("valid_observations >= 0", name="ck_runs_valid_observations_nonnegative"),
        UniqueConstraint(
            "methodological_date",
            "trigger_type",
            "data_class",
            name="uq_runs_method_date_trigger_class",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    methodological_date: Mapped[date] = mapped_column(Date)
    scheduled_for_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        enum_type(RunStatus, "run_status"), default=RunStatus.PLANNED
    )
    trigger_type: Mapped[RunTrigger] = mapped_column(enum_type(RunTrigger, "run_trigger"))
    data_class: Mapped[DataClass] = mapped_column(enum_type(DataClass, "data_class"))
    planned_jobs: Mapped[int] = mapped_column(Integer, default=0)
    successful_jobs: Mapped[int] = mapped_column(Integer, default=0)
    failed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    valid_observations: Mapped[int] = mapped_column(Integer, default=0)


class CollectionJob(CreatedAtMixin, Base):
    __tablename__ = "collection_jobs"
    __table_args__ = (
        CheckConstraint("advance_days >= 0", name="ck_jobs_advance_days_nonnegative"),
        CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="RESTRICT"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routes.id", ondelete="RESTRICT"), index=True
    )
    travel_date: Mapped[date] = mapped_column(Date, index=True)
    advance_days: Mapped[int] = mapped_column(Integer)
    advance_window: Mapped[AdvanceWindow] = mapped_column(
        enum_type(AdvanceWindow, "advance_window"), index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        enum_type(JobStatus, "job_status"), default=JobStatus.PLANNED
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[FailureCode | None] = mapped_column(
        enum_type(FailureCode, "failure_code"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
