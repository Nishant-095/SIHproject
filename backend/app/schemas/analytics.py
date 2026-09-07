from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import (
    AdvanceWindow,
    AggregationPeriod,
    AggregationStatus,
    ConfidenceLevel,
    DataClass,
    PublicationStatus,
)


class IndexComponentResponse(BaseModel):
    basket_item_id: uuid.UUID
    origin_iata: str
    destination_iata: str
    advance_window: AdvanceWindow
    current_price: Decimal | None
    base_price: Decimal | None
    price_relative: Decimal | None
    configured_weight: Decimal
    effective_weight: Decimal | None
    contribution: Decimal | None
    availability_reason: str


class DailyIndexResponse(BaseModel):
    id: uuid.UUID
    collection_run_id: uuid.UUID
    methodological_date: date
    data_class: DataClass
    basket_version: str
    methodology_version: str
    canonicalization_version: str
    index_value: Decimal | None
    coverage_percent: Decimal
    publication_status: PublicationStatus
    calculated_at: datetime
    components: list[IndexComponentResponse]


class IndexHistoryPointResponse(BaseModel):
    id: uuid.UUID
    methodological_date: date
    data_class: DataClass
    index_value: Decimal | None
    coverage_percent: Decimal
    publication_status: PublicationStatus


class RouteWindowPriceResponse(BaseModel):
    methodological_date: date
    advance_window: AdvanceWindow
    price: Decimal | None
    eligible_flight_count: int
    status: str


class RouteHistoryPointResponse(BaseModel):
    methodological_date: date
    route_index: Decimal | None
    average_fare: Decimal | None
    coverage_percent: Decimal


class SourceObservationCountResponse(BaseModel):
    source_code: str
    observation_count: int


class RouteAnalyticsResponse(BaseModel):
    id: uuid.UUID
    origin_iata: str
    destination_iata: str
    selection_basis: str
    latest_route_index: Decimal | None
    latest_date: date | None
    carriers: list[str]
    source_dispersion: list[SourceObservationCountResponse]


class LeadTimePointResponse(BaseModel):
    methodological_date: date
    travel_date: date
    advance_window: AdvanceWindow
    median_fare: Decimal
    observation_count: int


class LeadTimeResponse(BaseModel):
    origin_iata: str
    destination_iata: str
    travel_date: date | None
    data_class: DataClass
    points: list[LeadTimePointResponse]


class QualitySummaryResponse(BaseModel):
    data_class: DataClass
    total_observations: int
    included_observations: int
    excluded_observations: int
    flagged_observations: int
    average_quality_score: Decimal | None
    inclusion_rate_percent: Decimal
    status_counts: dict[str, int]
    flag_counts: dict[str, int]


class SourceToggleResponse(BaseModel):
    id: uuid.UUID
    code: str
    enabled: bool
    review_status: str


class MissingDataPolicyResponse(BaseModel):
    code: str
    minimum_publication_coverage_percent: Decimal
    imputation: str
    available_weight_treatment: str
    period_value_treatment: str


class SourceDispersionResponse(BaseModel):
    source_code: str
    observation_count: int
    share_percent: Decimal


class RouteCoverageResponse(BaseModel):
    origin_iata: str
    destination_iata: str
    total_windows: int
    available_windows: int
    coverage_percent: Decimal
    configured_weight: Decimal
    available_weight: Decimal
    source_count: int
    observation_count: int
    missing_windows: list[AdvanceWindow]
    confidence_level: ConfidenceLevel


class IndexCoverageResponse(BaseModel):
    methodological_date: date
    data_class: DataClass
    publication_status: PublicationStatus
    index_value: Decimal | None
    coverage_percent: Decimal
    source_count: int
    confidence_level: ConfidenceLevel
    missing_data_policy: MissingDataPolicyResponse
    source_dispersion: list[SourceDispersionResponse]
    routes: list[RouteCoverageResponse]
    warnings: list[str]


class PeriodIndexResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    data_class: DataClass
    period_type: AggregationPeriod
    period_start: date
    period_end: date
    methodology_version: str
    missing_data_policy: str
    index_value: Decimal | None
    average_coverage_percent: Decimal
    minimum_coverage_percent: Decimal
    expected_day_count: int
    observed_day_count: int
    valued_day_count: int
    low_coverage_day_count: int
    source_count: int
    confidence_level: ConfidenceLevel
    aggregation_status: AggregationStatus
    warnings: list[str]
    calculated_at: datetime
