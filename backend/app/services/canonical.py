from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    AdvanceWindow,
    QualityFlag,
    QualityStatus,
    SourceReviewStatus,
    SourceType,
)
from app.models import (
    CanonicalFare,
    CanonicalFareObservation,
    CollectionJob,
    FareObservation,
    RawQuote,
    Source,
)

CANONICAL_METHOD_VERSION = "direct-then-median-v1"
SUPPORTED_CANONICAL_POLICIES = {
    "direct-then-median-v1",
    "approved-source-median-v1",
}


def _append_flag(observation: FareObservation, flag: QualityFlag) -> None:
    if flag.value not in observation.quality_flags:
        observation.quality_flags = [*observation.quality_flags, flag.value]


def _exclude_duplicate(observation: FareObservation) -> None:
    _append_flag(observation, QualityFlag.DUPLICATE)
    observation.quality_status = QualityStatus.EXCLUDED
    observation.included_in_index = False
    observation.quality_score = max(0, (observation.quality_score or 100) - 20)
    observation.exclusion_reason = QualityFlag.DUPLICATE.value


def _flag_source_conflict(observation: FareObservation) -> None:
    _append_flag(observation, QualityFlag.SOURCE_CONFLICT)
    if observation.quality_status is QualityStatus.ELIGIBLE:
        observation.quality_status = QualityStatus.ELIGIBLE_FLAGGED
    observation.quality_score = max(0, (observation.quality_score or 100) - 10)


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return ((ordered[middle - 1] + ordered[middle]) / Decimal("2")).quantize(Decimal("0.01"))


def canonicalize_run(
    session: Session,
    run_id: uuid.UUID,
    *,
    policy: str = CANONICAL_METHOD_VERSION,
) -> int:
    if policy not in SUPPORTED_CANONICAL_POLICIES:
        raise ValueError(f"Unsupported canonical fare policy: {policy}")
    existing_count = (
        session.scalar(
            select(func.count(CanonicalFare.id)).where(CanonicalFare.collection_run_id == run_id)
        )
        or 0
    )
    if existing_count:
        return existing_count

    sources = {source.id: source for source in session.scalars(select(Source).order_by(Source.id))}
    rows = list(
        session.execute(
            select(FareObservation, RawQuote, CollectionJob)
            .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
            .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
            .where(CollectionJob.collection_run_id == run_id)
            .order_by(FareObservation.observed_at_utc, FareObservation.id)
        )
    )
    grouped: dict[
        tuple[uuid.UUID, AdvanceWindow, str, str, str, str],
        list[tuple[FareObservation, RawQuote]],
    ] = defaultdict(list)
    for observation, raw, job in rows:
        if (
            not observation.included_in_index
            or observation.flight_identity is None
            or observation.total_fare is None
            or observation.cabin_class is None
            or observation.fare_class is None
            or observation.currency is None
        ):
            continue
        key = (
            job.route_id,
            observation.advance_window,
            observation.flight_identity,
            observation.cabin_class,
            observation.fare_class,
            observation.currency,
        )
        grouped[key].append((observation, raw))

    created = 0
    for key, candidates in grouped.items():
        candidates.sort(
            key=lambda row: (
                str(row[1].source_id),
                row[0].total_fare or Decimal("0"),
                row[1].content_hash,
            )
        )
        route_id, window, identity, cabin, fare_class, currency = key
        seen_exact: set[tuple[uuid.UUID, Decimal]] = set()
        eligible: list[tuple[FareObservation, RawQuote]] = []
        duplicates: list[tuple[FareObservation, RawQuote]] = []
        rejected: list[tuple[FareObservation, RawQuote]] = []
        for observation, raw in candidates:
            source = sources.get(raw.source_id)
            if source is None or source.review_status is not SourceReviewStatus.APPROVED:
                observation.included_in_index = False
                observation.quality_status = QualityStatus.EXCLUDED
                _append_flag(observation, QualityFlag.UNAPPROVED_SOURCE)
                observation.exclusion_reason = QualityFlag.UNAPPROVED_SOURCE.value
                rejected.append((observation, raw))
                continue
            assert observation.total_fare is not None
            exact_key = (raw.source_id, observation.total_fare)
            if exact_key in seen_exact:
                _exclude_duplicate(observation)
                duplicates.append((observation, raw))
                continue
            seen_exact.add(exact_key)
            eligible.append((observation, raw))
        if not eligible:
            continue

        by_source: dict[uuid.UUID, list[tuple[FareObservation, RawQuote]]] = defaultdict(list)
        for item in eligible:
            by_source[item[1].source_id].append(item)
        representatives = [
            min(
                source_rows,
                key=lambda row: (
                    row[0].total_fare or Decimal("0"),
                    row[1].content_hash,
                ),
            )
            for source_rows in by_source.values()
        ]
        direct_representatives = [
            row
            for row in representatives
            if sources[row[1].source_id].source_type is SourceType.AIRLINE_DIRECT
        ]
        using_direct_policy = policy == "direct-then-median-v1" and bool(direct_representatives)
        selected = direct_representatives if using_direct_policy else representatives
        selected_ids = {observation.id for observation, _ in selected}
        all_totals = [
            observation.total_fare
            for observation, _ in representatives
            if observation.total_fare is not None
        ]
        selected_totals = [
            observation.total_fare
            for observation, _ in selected
            if observation.total_fare is not None
        ]
        minimum = min(all_totals)
        maximum = max(all_totals)
        has_conflict = len(set(all_totals)) > 1
        if has_conflict:
            for observation, _ in eligible:
                _flag_source_conflict(observation)

        canonical = CanonicalFare(
            collection_run_id=run_id,
            route_id=route_id,
            advance_window=window,
            flight_identity=identity,
            cabin_class=cabin,
            fare_class=fare_class,
            currency=currency,
            representative_total_fare=_median(selected_totals),
            minimum_total_fare=minimum,
            maximum_total_fare=maximum,
            dispersion_amount=maximum - minimum,
            source_count=len(representatives),
            observation_count=len(eligible),
            has_source_conflict=has_conflict,
            selection_reason=(
                "DIRECT_AIRLINE_MEDIAN" if using_direct_policy else "APPROVED_SOURCE_MEDIAN"
            ),
            method_version=policy,
        )
        session.add(canonical)
        session.flush()
        representative_ids = {observation.id for observation, _ in representatives}
        for observation, raw in [*eligible, *duplicates, *rejected]:
            role = "REJECTED_UNAPPROVED" if (observation, raw) in rejected else "DUPLICATE"
            if (observation, raw) in eligible:
                if observation.id in selected_ids:
                    role = "USED_DIRECT" if using_direct_policy else "USED_MEDIAN"
                elif observation.id in representative_ids:
                    role = "CONSIDERED_NOT_SELECTED"
                else:
                    role = "SOURCE_CANDIDATE"
            session.add(
                CanonicalFareObservation(
                    canonical_fare_id=canonical.id,
                    observation_id=observation.id,
                    source_id=raw.source_id,
                    source_total_fare=observation.total_fare,
                    role=role,
                )
            )
        created += 1
    session.commit()
    return created
