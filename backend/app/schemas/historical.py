from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.domain.enums import DataClass, ReferenceScope, ReferenceStatus


class HistoricalObservationInput(BaseModel):
    period_start: date
    period_end: date
    scope_type: ReferenceScope
    origin_iata: str | None = Field(default=None, min_length=3, max_length=3)
    destination_iata: str | None = Field(default=None, min_length=3, max_length=3)
    index_value: Decimal = Field(ge=0)
    coverage_percent: Decimal | None = Field(default=None, ge=0, le=100)
    status: ReferenceStatus
    source_record_id: str = Field(min_length=1, max_length=160)
    raw_record: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope(self) -> HistoricalObservationInput:
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        if self.scope_type is ReferenceScope.NATIONAL:
            if self.origin_iata is not None or self.destination_iata is not None:
                raise ValueError("national observations cannot contain route codes")
        elif self.origin_iata is None or self.destination_iata is None:
            raise ValueError("route observations require origin and destination")
        if self.origin_iata is not None:
            self.origin_iata = self.origin_iata.upper()
        if self.destination_iata is not None:
            self.destination_iata = self.destination_iata.upper()
        return self


class HistoricalDatasetImportRequest(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,79}$")
    title: str = Field(min_length=3, max_length=240)
    publisher: str = Field(min_length=2, max_length=200)
    source_url: HttpUrl
    license_name: str = Field(min_length=2, max_length=160)
    metric_name: str = Field(min_length=2, max_length=200)
    frequency: str = Field(pattern=r"^(MONTHLY|DAILY)$")
    base_period: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    observations: list[HistoricalObservationInput] = Field(min_length=1)


class HistoricalObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    period_start: date
    period_end: date
    scope_type: ReferenceScope
    origin_iata: str | None
    destination_iata: str | None
    index_value: Decimal
    coverage_percent: Decimal | None
    status: ReferenceStatus
    source_record_id: str
    raw_record: dict[str, object]


class HistoricalDatasetResponse(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    publisher: str
    source_url: str
    license_name: str
    metric_name: str
    frequency: str
    base_period: str | None
    data_class: DataClass
    content_hash: str
    row_count: int
    notes: str | None
    imported_at: datetime
    observations: list[HistoricalObservationResponse] = Field(default_factory=list)


class BacktestPointResponse(BaseModel):
    period_start: date
    period_end: date
    internal_index: Decimal
    reference_index: Decimal
    internal_rebased: Decimal
    reference_rebased: Decimal
    deviation_points: Decimal
    deviation_percent: Decimal
    internal_coverage_percent: Decimal
    internal_status: str
    reference_status: ReferenceStatus


class RouteComparisonResponse(BaseModel):
    period_start: date
    period_end: date
    origin_iata: str
    destination_iata: str
    route_index: Decimal
    overall_index: Decimal
    deviation_points: Decimal
    observed_day_count: int
    expected_day_count: int
    coverage_percent: Decimal


class BacktestResponse(BaseModel):
    dataset: HistoricalDatasetResponse
    internal_data_class: DataClass
    comparison_method: str
    overlap_month_count: int
    correlation: Decimal | None
    correlation_status: str
    mean_absolute_deviation_percent: Decimal | None
    average_internal_coverage_percent: Decimal | None
    points: list[BacktestPointResponse]
    route_comparisons: list[RouteComparisonResponse]
    warnings: list[str]
