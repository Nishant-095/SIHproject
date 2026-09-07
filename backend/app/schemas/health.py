from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.domain.enums import FailureCode, SourceHealthStatus, SourceReviewStatus


class SourceHealthResponse(BaseModel):
    source_code: str
    source_name: str
    enabled: bool
    review_status: SourceReviewStatus
    health_status: SourceHealthStatus
    successful_jobs: int
    failed_jobs: int
    success_rate: float | None
    average_duration_ms: int | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_failure_code: FailureCode | None
    parser_version: str


class SourceHealthHistoryPointResponse(BaseModel):
    source_code: str
    methodological_date: date
    successful_jobs: int
    failed_jobs: int
    success_rate: float | None
    average_duration_ms: int | None
    health_status: SourceHealthStatus
    parser_version: str
