from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import AdvanceWindow, AvailabilityStatus, DataClass, QualityStatus


class FareObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_quote_id: uuid.UUID
    observed_at_utc: datetime
    methodological_date: date
    origin_iata: str
    destination_iata: str
    travel_date: date
    advance_days: int
    advance_window: AdvanceWindow
    carrier_code: str | None
    carrier_name: str | None
    flight_number: str | None
    departure_time_local: time | None
    arrival_time_local: time | None
    is_nonstop: bool | None
    cabin_class: str | None
    fare_class: str | None
    currency: str | None
    base_fare: Decimal | None
    taxes: Decimal | None
    udf: Decimal | None
    convenience_fee: Decimal | None
    other_fees: Decimal | None
    total_fare: Decimal | None
    availability: AvailabilityStatus
    flight_identity_input: str | None
    flight_identity: str | None
    quality_status: QualityStatus
    quality_flags: list[str]
    quality_score: int | None
    included_in_index: bool
    exclusion_reason: str | None
    normalization_version: str


class RawQuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    collection_job_id: uuid.UUID
    source_id: uuid.UUID
    data_class: DataClass
    observed_at_utc: datetime
    query_origin: str
    query_destination: str
    query_travel_date: date
    raw_airline_name: str | None
    raw_flight_number: str | None
    raw_departure: str | None
    raw_arrival: str | None
    raw_fare_text: str | None
    raw_currency: str | None
    raw_base_fare: Decimal | None
    raw_tax_text: str | None
    raw_total_fare: Decimal | None
    raw_payload: dict[str, object]
    parser_version: str
    content_hash: str


class ObservationProvenanceResponse(BaseModel):
    source_code: str
    source_name: str
    route: str
    collection_run_id: uuid.UUID
    collection_job_id: uuid.UUID
    observation: FareObservationResponse
    raw_quote: RawQuoteResponse
