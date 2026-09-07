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
from app.pipeline.outliers import flag_statistical_outliers


def test_mad_outlier_is_flagged_but_not_automatically_excluded(session: Session) -> None:
    source = Source(
        code="OUTLIER_TEST",
        name="Outlier test",
        source_type=SourceType.OTA,
        enabled=True,
        collection_method="TEST",
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
    observations = []
    for index, total in enumerate(("5000", "5050", "5100", "5150", "20000")):
        job = CollectionJob(
            collection_run_id=run.id,
            source_id=source.id,
            route_id=route.id,
            travel_date=date(2026, 9, 12),
            advance_days=7,
            advance_window=AdvanceWindow.T7,
            status=JobStatus.SUCCEEDED,
            idempotency_key=f"outlier-{index}",
        )
        session.add(job)
        session.flush()
        amount = Decimal(total)
        raw = RawQuote(
            collection_job_id=job.id,
            source_id=source.id,
            data_class=DataClass.SYNTHETIC,
            observed_at_utc=datetime(2026, 9, 5, 4, 30, tzinfo=UTC),
            query_origin="DEL",
            query_destination="BOM",
            query_travel_date=date(2026, 9, 12),
            raw_airline_name="Air India",
            raw_flight_number=f"AI10{index}",
            raw_departure=f"2026-09-12T{index + 8:02d}:00:00",
            raw_arrival=f"2026-09-12T{index + 10:02d}:00:00",
            raw_fare_text=total,
            raw_currency="INR",
            raw_base_fare=None,
            raw_tax_text=None,
            raw_total_fare=amount,
            raw_payload={
                "carrier_code": "AI",
                "origin": "DEL",
                "destination": "BOM",
                "cabin_class": "ECONOMY",
                "fare_class": "PUBLIC_ECONOMY",
                "is_nonstop": True,
                "availability": AvailabilityStatus.AVAILABLE.value,
            },
            parser_version="test-v1",
            content_hash=str(index) * 64,
        )
        session.add(raw)
        session.flush()
        observation = normalize_raw_quote(
            raw_quote=raw,
            job=job,
            run=run,
            route=route,
            source=source,
        )
        session.add(observation)
        observations.append(observation)
    session.flush()

    assert flag_statistical_outliers(session, run.id) == 1
    outlier = observations[-1]
    assert QualityFlag.POSSIBLE_OUTLIER.value in outlier.quality_flags
    assert outlier.quality_status is QualityStatus.ELIGIBLE_FLAGGED
    assert outlier.included_in_index is True
