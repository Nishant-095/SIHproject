from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import AdvanceWindow, DataClass, FailureCode, JobStatus, RunStatus, RunTrigger


class CollectionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    route_id: uuid.UUID
    travel_date: date
    advance_days: int
    advance_window: AdvanceWindow
    status: JobStatus
    attempt_count: int
    failure_code: FailureCode | None
    error_message: str | None


class CollectionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    methodological_date: date
    scheduled_for_utc: datetime
    started_at: datetime | None
    finished_at: datetime | None
    status: RunStatus
    trigger_type: RunTrigger
    data_class: DataClass
    planned_jobs: int
    successful_jobs: int
    failed_jobs: int
    valid_observations: int


class CollectionRunDetailResponse(CollectionRunResponse):
    jobs: list[CollectionJobResponse]
    created: bool | None = None


class AdminCollectionRunRequest(BaseModel):
    source: Literal["fixture", "duffel", "permissioned-web"] = "fixture"
    methodological_date: date | None = None
