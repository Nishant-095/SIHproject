from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
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
from app.models import (
    CanonicalFare,
    CanonicalFareObservation,
    CollectionJob,
    CollectionRun,
    RawQuote,
    Route,
    Source,
)
from app.pipeline.normalize import normalize_raw_quote
from app.services.canonical import canonicalize_run


def _raw(
    session: Session,
    *,
    job: CollectionJob,
    source: Source,
    total: Decimal,
    content_hash: str,
    currency: str = "INR",
) -> RawQuote:
    raw = RawQuote(
        collection_job_id=job.id,
        source_id=source.id,
        data_class=DataClass.SYNTHETIC,
        observed_at_utc=datetime(2026, 9, 5, 4, 30, tzinfo=UTC),
        query_origin="DEL",
        query_destination="BOM",
        query_travel_date=date(2026, 9, 12),
        raw_airline_name="Air India",
        raw_flight_number="AI2421",
        raw_departure="2026-09-12T09:20:00",
        raw_arrival="2026-09-12T11:30:00",
        raw_fare_text=str(total),
        raw_currency=currency,
        raw_base_fare=total - Decimal("600"),
        raw_tax_text="500",
        raw_total_fare=total,
        raw_payload={
            "carrier_code": "AI",
            "origin": "New Delhi",
            "destination": "Mumbai",
            "taxes": "500",
            "udf": "100",
            "convenience_fee": "0",
            "other_fees": "0",
            "fare_class": "PUBLIC_ECONOMY",
            "cabin_class": "ECONOMY",
            "is_nonstop": True,
            "availability": AvailabilityStatus.AVAILABLE.value,
        },
        parser_version="test-v1",
        content_hash=content_hash,
    )
    session.add(raw)
    session.flush()
    return raw


def test_cross_source_canonical_fare_preserves_evidence_and_flags(session: Session) -> None:
    route = Route(origin_iata="DEL", destination_iata="BOM", active=True, selection_basis="test")
    sources = [
        Source(
            code=f"SOURCE_{number}",
            name=f"Source {number}",
            source_type=(SourceType.AIRLINE_DIRECT if number == 3 else SourceType.OTA),
            enabled=True,
            collection_method="TEST",
            review_status=SourceReviewStatus.APPROVED,
            parser_version="test-v1",
        )
        for number in (1, 2, 3)
    ]
    run = CollectionRun(
        methodological_date=date(2026, 9, 5),
        scheduled_for_utc=datetime(2026, 9, 5, 4, 30, tzinfo=UTC),
        status=RunStatus.RUNNING,
        trigger_type=RunTrigger.TEST,
        data_class=DataClass.SYNTHETIC,
    )
    session.add_all([route, *sources, run])
    session.flush()
    jobs = []
    for number, source in enumerate(sources, start=1):
        job = CollectionJob(
            collection_run_id=run.id,
            source_id=source.id,
            route_id=route.id,
            travel_date=date(2026, 9, 12),
            advance_days=7,
            advance_window=AdvanceWindow.T7,
            status=JobStatus.SUCCEEDED,
            idempotency_key=f"canonical-source-{number}",
        )
        session.add(job)
        jobs.append(job)
    session.flush()

    raws = [
        _raw(session, job=jobs[0], source=sources[0], total=Decimal("5000"), content_hash="a" * 64),
        _raw(session, job=jobs[0], source=sources[0], total=Decimal("5000"), content_hash="b" * 64),
        _raw(session, job=jobs[1], source=sources[1], total=Decimal("5500"), content_hash="c" * 64),
        _raw(
            session,
            job=jobs[1],
            source=sources[1],
            total=Decimal("5400"),
            content_hash="d" * 64,
            currency="USD",
        ),
        _raw(
            session,
            job=jobs[2],
            source=sources[2],
            total=Decimal("6000"),
            content_hash="e" * 64,
        ),
    ]
    observations = [
        normalize_raw_quote(
            raw_quote=raw,
            job=jobs[0 if index < 2 else (1 if index < 4 else 2)],
            run=run,
            route=route,
            source=sources[0 if index < 2 else (1 if index < 4 else 2)],
        )
        for index, raw in enumerate(raws)
    ]
    session.add_all(observations)
    session.commit()

    assert canonicalize_run(session, run.id) == 1
    canonical = session.scalar(select(CanonicalFare))
    assert canonical is not None
    assert canonical.representative_total_fare == Decimal("6000.00")
    assert canonical.minimum_total_fare == Decimal("5000.00")
    assert canonical.maximum_total_fare == Decimal("6000.00")
    assert canonical.dispersion_amount == Decimal("1000.00")
    assert canonical.source_count == 3
    assert canonical.observation_count == 3
    assert canonical.has_source_conflict is True
    assert canonical.selection_reason == "DIRECT_AIRLINE_MEDIAN"
    assert canonical.method_version == "direct-then-median-v1"
    assert session.scalar(select(func.count(CanonicalFareObservation.observation_id))) == 4
    roles = set(session.scalars(select(CanonicalFareObservation.role)))
    assert roles == {"USED_DIRECT", "CONSIDERED_NOT_SELECTED", "DUPLICATE"}

    duplicates = [
        observation for observation in observations[:2] if not observation.included_in_index
    ]
    assert len(duplicates) == 1
    duplicate = duplicates[0]
    assert duplicate.included_in_index is False
    assert duplicate.quality_status is QualityStatus.EXCLUDED
    assert QualityFlag.DUPLICATE.value in duplicate.quality_flags
    source_one_representative = next(
        observation for observation in observations[:2] if observation.included_in_index
    )
    assert all(
        QualityFlag.SOURCE_CONFLICT.value in observation.quality_flags
        for observation in (source_one_representative, observations[2], observations[4])
    )
    assert observations[3].included_in_index is False
    assert QualityFlag.UNSUPPORTED_CURRENCY.value in observations[3].quality_flags


def test_approved_source_median_policy_is_configurable(session: Session) -> None:
    route = Route(origin_iata="DEL", destination_iata="BOM", active=True, selection_basis="test")
    ota = Source(
        code="OTA_POLICY",
        name="OTA",
        source_type=SourceType.OTA,
        enabled=True,
        collection_method="TEST",
        review_status=SourceReviewStatus.APPROVED,
        parser_version="test-v1",
    )
    direct = Source(
        code="DIRECT_POLICY",
        name="Direct",
        source_type=SourceType.AIRLINE_DIRECT,
        enabled=True,
        collection_method="TEST",
        review_status=SourceReviewStatus.APPROVED,
        parser_version="test-v1",
    )
    run = CollectionRun(
        methodological_date=date(2026, 9, 5),
        scheduled_for_utc=datetime(2026, 9, 5, 4, 30, tzinfo=UTC),
        status=RunStatus.RUNNING,
        trigger_type=RunTrigger.TEST,
        data_class=DataClass.SYNTHETIC,
    )
    session.add_all([route, ota, direct, run])
    session.flush()
    observations = []
    for index, (source, total) in enumerate(((ota, Decimal("5000")), (direct, Decimal("6000")))):
        job = CollectionJob(
            collection_run_id=run.id,
            source_id=source.id,
            route_id=route.id,
            travel_date=date(2026, 9, 12),
            advance_days=7,
            advance_window=AdvanceWindow.T7,
            status=JobStatus.SUCCEEDED,
            idempotency_key=f"policy-{index}",
        )
        session.add(job)
        session.flush()
        raw = _raw(
            session,
            job=job,
            source=source,
            total=total,
            content_hash=str(index + 7) * 64,
        )
        observation = normalize_raw_quote(
            raw_quote=raw,
            job=job,
            run=run,
            route=route,
            source=source,
        )
        session.add(observation)
        observations.append(observation)
    session.commit()

    assert canonicalize_run(session, run.id, policy="approved-source-median-v1") == 1
    canonical = session.scalar(select(CanonicalFare))
    assert canonical is not None
    assert canonical.representative_total_fare == Decimal("5500.00")
    assert canonical.selection_reason == "APPROVED_SOURCE_MEDIAN"
    assert canonical.method_version == "approved-source-median-v1"
    assert set(session.scalars(select(CanonicalFareObservation.role))) == {"USED_MEDIAN"}
