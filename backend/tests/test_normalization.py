from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import (
    AdvanceWindow,
    AvailabilityStatus,
    DataClass,
    JobStatus,
    QualityFlag,
    QualityStatus,
    RunStatus,
    RunTrigger,
    SourceReviewStatus,
    SourceType,
)
from app.models import CollectionJob, CollectionRun, RawQuote, Route, Source
from app.pipeline.normalize import normalize_raw_quote


def _entities(
    session: Session,
    *,
    currency: str = "INR",
    cabin: str = "ECONOMY",
    nonstop: bool = True,
):
    source = Source(
        code="TEST",
        name="Test source",
        source_type=SourceType.FIXTURE,
        enabled=True,
        collection_method="FIXTURE",
        review_status=SourceReviewStatus.APPROVED,
        parser_version="test-v1",
    )
    route = Route(origin_iata="DEL", destination_iata="BOM", active=True, selection_basis="test")
    run = CollectionRun(
        methodological_date=date(2026, 9, 5),
        scheduled_for_utc=datetime(2026, 9, 5, 4, 30, tzinfo=UTC),
        status=RunStatus.RUNNING,
        trigger_type=RunTrigger.TEST,
        data_class=DataClass.SYNTHETIC,
    )
    session.add_all([source, route, run])
    session.flush()
    job = CollectionJob(
        collection_run_id=run.id,
        source_id=source.id,
        route_id=route.id,
        travel_date=date(2026, 9, 12),
        advance_days=7,
        advance_window=AdvanceWindow.T7,
        status=JobStatus.RUNNING,
        idempotency_key=f"test-{currency}-{cabin}-{nonstop}",
    )
    session.add(job)
    session.flush()
    raw = RawQuote(
        collection_job_id=job.id,
        source_id=source.id,
        data_class=DataClass.SYNTHETIC,
        observed_at_utc=datetime(2026, 9, 5, 4, 30, tzinfo=UTC),
        query_origin="DEL",
        query_destination="BOM",
        query_travel_date=date(2026, 9, 12),
        raw_airline_name="IndiGo",
        raw_flight_number="6E 1234",
        raw_departure="09:20",
        raw_arrival="11:30",
        raw_fare_text="₹5,000",
        raw_currency=currency,
        raw_base_fare=Decimal("4200"),
        raw_tax_text="650",
        raw_total_fare=Decimal("5000"),
        raw_payload={
            "carrier_code": "6E",
            "taxes": "650",
            "udf": "150",
            "convenience_fee": "0",
            "other_fees": "0",
            "fare_class": "PUBLIC_ECONOMY",
            "cabin_class": cabin,
            "is_nonstop": nonstop,
            "availability": AvailabilityStatus.AVAILABLE.value,
        },
        parser_version="test-v1",
        content_hash="a" * 64,
    )
    session.add(raw)
    session.flush()
    return source, route, run, job, raw


def test_eligible_quote_normalizes_with_reproducible_identity(session: Session) -> None:
    source, route, run, job, raw = _entities(session)
    observation = normalize_raw_quote(raw_quote=raw, job=job, run=run, route=route, source=source)

    assert observation.quality_status is QualityStatus.ELIGIBLE
    assert observation.included_in_index is True
    assert observation.total_fare == Decimal("5000")
    assert observation.flight_identity_input == "6E|6E1234|DEL|BOM|2026-09-12|09:20"
    assert observation.flight_identity is not None
    assert len(observation.flight_identity) == 64
    session.add(observation)
    session.commit()
    assert session.get(type(observation), observation.id) is observation


def test_ineligible_quote_retains_explicit_reasons(session: Session) -> None:
    source, route, run, job, raw = _entities(
        session,
        currency="USD",
        cabin="BUSINESS",
        nonstop=False,
    )
    observation = normalize_raw_quote(raw_quote=raw, job=job, run=run, route=route, source=source)

    assert observation.quality_status is QualityStatus.EXCLUDED
    assert observation.included_in_index is False
    assert set(observation.quality_flags) >= {
        QualityFlag.UNSUPPORTED_CURRENCY.value,
        QualityFlag.UNSUPPORTED_CABIN.value,
        QualityFlag.CONNECTING_FLIGHT.value,
    }
    assert observation.exclusion_reason is not None


def test_route_aliases_carrier_alias_and_iso_times_normalize(session: Session) -> None:
    source, route, run, job, raw = _entities(session)
    raw.raw_airline_name = "Akasa Air"
    raw.raw_departure = "2026-09-12T09:20:00"
    raw.raw_arrival = "2026-09-12T11:30:00"
    raw.raw_payload = {
        **raw.raw_payload,
        "carrier_code": "Akasa",
        "origin": "New Delhi",
        "destination": "Mumbai",
    }
    observation = normalize_raw_quote(
        raw_quote=raw,
        job=job,
        run=run,
        route=route,
        source=source,
    )
    assert observation.carrier_code == "QP"
    assert observation.carrier_name == "Akasa Air"
    assert observation.departure_time_local is not None
    assert observation.departure_time_local.isoformat() == "09:20:00"
    assert observation.included_in_index is True


def test_route_mismatch_unknown_airport_negative_and_unavailable_are_excluded(
    session: Session,
) -> None:
    source, route, run, job, raw = _entities(session)
    raw.raw_total_fare = Decimal("-1")
    raw.raw_payload = {
        **raw.raw_payload,
        "origin": "Unknown airport",
        "destination": "Bengaluru",
        "availability": AvailabilityStatus.SOLD_OUT.value,
    }
    observation = normalize_raw_quote(
        raw_quote=raw,
        job=job,
        run=run,
        route=route,
        source=source,
    )
    assert observation.included_in_index is False
    assert set(observation.quality_flags) >= {
        QualityFlag.UNKNOWN_AIRPORT.value,
        QualityFlag.NEGATIVE_FARE.value,
        QualityFlag.UNAVAILABLE_FARE.value,
    }

    raw.raw_total_fare = Decimal("5000")
    raw.raw_payload = {**raw.raw_payload, "origin": "Bengaluru", "destination": "Mumbai"}
    mismatched = normalize_raw_quote(
        raw_quote=raw,
        job=job,
        run=run,
        route=route,
        source=source,
    )
    assert QualityFlag.ROUTE_MISMATCH.value in mismatched.quality_flags


def test_missing_optional_fare_components_remain_null(session: Session) -> None:
    source, route, run, job, raw = _entities(session)
    raw.raw_base_fare = None
    raw.raw_payload = {
        key: value
        for key, value in raw.raw_payload.items()
        if key not in {"taxes", "udf", "convenience_fee", "other_fees"}
    }
    observation = normalize_raw_quote(
        raw_quote=raw,
        job=job,
        run=run,
        route=route,
        source=source,
    )
    assert observation.base_fare is None
    assert observation.taxes is None
    assert observation.udf is None
    assert observation.convenience_fee is None
    assert observation.other_fees is None
    assert observation.total_fare == Decimal("5000")


def test_date_window_and_data_lineage_mismatches_are_excluded(session: Session) -> None:
    source, route, run, job, raw = _entities(session)
    job.advance_window = AdvanceWindow.T15
    raw.query_travel_date = date(2026, 9, 13)
    raw.raw_departure = "2026-09-14T09:20:00"
    raw.data_class = DataClass.HISTORICAL
    other_source = Source(
        code="OTHER",
        name="Other source",
        source_type=SourceType.OTA,
        enabled=True,
        collection_method="TEST",
        review_status=SourceReviewStatus.APPROVED,
        parser_version="test-v1",
    )
    session.add(other_source)
    session.flush()
    raw.source_id = other_source.id

    observation = normalize_raw_quote(
        raw_quote=raw,
        job=job,
        run=run,
        route=route,
        source=source,
    )
    assert observation.included_in_index is False
    assert set(observation.quality_flags) >= {
        QualityFlag.INVALID_TRAVEL_DATE.value,
        QualityFlag.INVALID_BOOKING_WINDOW.value,
        QualityFlag.DATA_CLASS_MISMATCH.value,
        QualityFlag.SOURCE_MISMATCH.value,
    }


def test_invalid_availability_and_negative_total_remain_explainable(
    session: Session,
) -> None:
    source, route, run, job, raw = _entities(session)
    raw.raw_total_fare = Decimal("-1")
    raw.raw_payload = {**raw.raw_payload, "availability": "BROKEN_VALUE"}

    observation = normalize_raw_quote(
        raw_quote=raw,
        job=job,
        run=run,
        route=route,
        source=source,
    )
    session.add(observation)
    session.commit()

    assert observation.included_in_index is False
    assert observation.total_fare is None
    assert observation.availability is AvailabilityStatus.UNKNOWN
    assert set(observation.quality_flags) >= {
        QualityFlag.PARSER_ERROR.value,
        QualityFlag.UNAVAILABLE_FARE.value,
        QualityFlag.NEGATIVE_FARE.value,
    }
