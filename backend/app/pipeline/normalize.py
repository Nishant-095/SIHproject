from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from app.domain.booking_window import classify_advance_window
from app.domain.enums import (
    AdvanceWindow,
    AvailabilityStatus,
    QualityFlag,
    QualityStatus,
    SourceReviewStatus,
)
from app.domain.flight_identity import canonical_flight_identity_input, flight_identity_hash
from app.domain.reference_data import normalize_airport, normalize_carrier
from app.models import CollectionJob, CollectionRun, FareObservation, RawQuote, Route, Source

NORMALIZATION_VERSION = "normalization-v1"


def _decimal_from_payload(payload: dict[str, object], key: str) -> Decimal | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _time_from_text(value: str | None) -> time | None:
    if value is None:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).time().replace(tzinfo=None)
        return time.fromisoformat(value)
    except ValueError:
        return None


def normalize_raw_quote(
    *,
    raw_quote: RawQuote,
    job: CollectionJob,
    run: CollectionRun,
    route: Route,
    source: Source,
) -> FareObservation:
    payload = raw_quote.raw_payload
    flags: list[QualityFlag] = []

    currency = (raw_quote.raw_currency or "").strip().upper() or None
    base_fare = raw_quote.raw_base_fare
    taxes = _decimal_from_payload(payload, "taxes")
    udf = _decimal_from_payload(payload, "udf")
    convenience_fee = _decimal_from_payload(payload, "convenience_fee")
    other_fees = _decimal_from_payload(payload, "other_fees")
    total_fare = raw_quote.raw_total_fare
    normalized_total_fare = None if total_fare is not None and total_fare < 0 else total_fare
    cabin_class = str(payload.get("cabin_class") or "").strip().upper() or None
    is_nonstop_value = payload.get("is_nonstop")
    is_nonstop = is_nonstop_value if isinstance(is_nonstop_value, bool) else None
    carrier_value = str(
        payload.get("carrier_code")
        or payload.get("marketing_carrier_code")
        or raw_quote.raw_airline_name
        or ""
    )
    carrier_code, carrier_name = normalize_carrier(carrier_value)
    if carrier_name is None and raw_quote.raw_airline_name:
        carrier_name = raw_quote.raw_airline_name.strip()
    flight_number = (raw_quote.raw_flight_number or "").strip().upper().replace(" ", "") or None
    departure = _time_from_text(raw_quote.raw_departure)
    arrival = _time_from_text(raw_quote.raw_arrival)
    observed_origin = normalize_airport(str(payload.get("origin") or raw_quote.query_origin or ""))
    observed_destination = normalize_airport(
        str(payload.get("destination") or raw_quote.query_destination or "")
    )

    if raw_quote.source_id != source.id:
        flags.append(QualityFlag.SOURCE_MISMATCH)
    if raw_quote.data_class is not run.data_class:
        flags.append(QualityFlag.DATA_CLASS_MISMATCH)
    expected_travel_date = run.methodological_date + timedelta(days=job.advance_days)
    source_departure_date = None
    if raw_quote.raw_departure and "T" in raw_quote.raw_departure:
        try:
            source_departure_date = datetime.fromisoformat(
                raw_quote.raw_departure.replace("Z", "+00:00")
            ).date()
        except ValueError:
            source_departure_date = None
    if (
        job.travel_date != expected_travel_date
        or raw_quote.query_travel_date != job.travel_date
        or (source_departure_date is not None and source_departure_date != job.travel_date)
    ):
        flags.append(QualityFlag.INVALID_TRAVEL_DATE)
    if (
        job.advance_window is AdvanceWindow.OTHER
        or classify_advance_window(job.advance_days) is not job.advance_window
    ):
        flags.append(QualityFlag.INVALID_BOOKING_WINDOW)

    if observed_origin is None or observed_destination is None:
        flags.append(QualityFlag.UNKNOWN_AIRPORT)
    elif observed_origin != route.origin_iata or observed_destination != route.destination_iata:
        flags.append(QualityFlag.ROUTE_MISMATCH)

    if total_fare is None or total_fare <= 0:
        flags.append(QualityFlag.MISSING_FARE)
    if currency != "INR":
        flags.append(QualityFlag.UNSUPPORTED_CURRENCY)
    if cabin_class != "ECONOMY":
        flags.append(QualityFlag.UNSUPPORTED_CABIN)
    if is_nonstop is not True:
        flags.append(QualityFlag.CONNECTING_FLIGHT)
    availability_text = str(payload.get("availability", "UNKNOWN"))
    try:
        availability = AvailabilityStatus(availability_text)
    except ValueError:
        availability = AvailabilityStatus.UNKNOWN
        flags.append(QualityFlag.PARSER_ERROR)
    if availability is not AvailabilityStatus.AVAILABLE:
        flags.append(QualityFlag.UNAVAILABLE_FARE)
    if source.review_status is not SourceReviewStatus.APPROVED:
        flags.append(QualityFlag.UNAPPROVED_SOURCE)

    components = [base_fare, taxes, udf, convenience_fee, other_fees]
    if any(component is not None and component < 0 for component in [*components, total_fare]):
        flags.append(QualityFlag.NEGATIVE_FARE)
    if total_fare is not None and all(component is not None for component in components):
        expected_total = sum(
            (component for component in components if component is not None),
            Decimal("0"),
        )
        if abs(expected_total - total_fare) > Decimal("0.01"):
            flags.append(QualityFlag.FARE_COMPONENT_MISMATCH)
    elif total_fare is not None and taxes is not None and total_fare < taxes:
        flags.append(QualityFlag.FARE_COMPONENT_MISMATCH)

    identity_input: str | None = None
    identity_hash: str | None = None
    if carrier_code and flight_number and departure:
        identity_input = canonical_flight_identity_input(
            carrier_code=carrier_code,
            flight_number=flight_number,
            origin_iata=route.origin_iata,
            destination_iata=route.destination_iata,
            travel_date=job.travel_date,
            scheduled_departure_local=departure,
        )
        identity_hash = flight_identity_hash(identity_input)
    else:
        flags.append(QualityFlag.INCOMPLETE_FLIGHT_IDENTITY)

    hard_flags = set(flags)
    included = not hard_flags
    quality_status = QualityStatus.ELIGIBLE if included else QualityStatus.EXCLUDED
    exclusion_reason = None if included else ", ".join(flag.value for flag in flags)
    quality_score = max(0, 100 - (20 * len(set(flags))))

    return FareObservation(
        raw_quote_id=raw_quote.id,
        observed_at_utc=raw_quote.observed_at_utc,
        methodological_date=run.methodological_date,
        origin_iata=route.origin_iata,
        destination_iata=route.destination_iata,
        travel_date=job.travel_date,
        advance_days=job.advance_days,
        advance_window=job.advance_window,
        carrier_code=carrier_code,
        carrier_name=carrier_name,
        flight_number=flight_number,
        departure_time_local=departure,
        arrival_time_local=arrival,
        is_nonstop=is_nonstop,
        cabin_class=cabin_class,
        fare_class=str(payload.get("fare_class") or "") or None,
        currency=currency,
        base_fare=base_fare,
        taxes=taxes,
        udf=udf,
        convenience_fee=convenience_fee,
        other_fees=other_fees,
        total_fare=normalized_total_fare,
        availability=availability,
        flight_identity_input=identity_input,
        flight_identity=identity_hash,
        quality_status=quality_status,
        quality_flags=[flag.value for flag in dict.fromkeys(flags)],
        quality_score=quality_score,
        included_in_index=included,
        exclusion_reason=exclusion_reason,
        normalization_version=NORMALIZATION_VERSION,
    )


def rejected_normalization_observation(
    *,
    raw_quote: RawQuote,
    job: CollectionJob,
    run: CollectionRun,
    route: Route,
    reason: str,
) -> FareObservation:
    """Retain a deterministic excluded status when normalization cannot proceed."""
    return FareObservation(
        raw_quote_id=raw_quote.id,
        observed_at_utc=raw_quote.observed_at_utc,
        methodological_date=run.methodological_date,
        origin_iata=route.origin_iata,
        destination_iata=route.destination_iata,
        travel_date=job.travel_date,
        advance_days=job.advance_days,
        advance_window=job.advance_window,
        carrier_code=None,
        carrier_name=raw_quote.raw_airline_name,
        flight_number=raw_quote.raw_flight_number,
        departure_time_local=None,
        arrival_time_local=None,
        is_nonstop=None,
        cabin_class=None,
        fare_class=None,
        currency=raw_quote.raw_currency,
        base_fare=raw_quote.raw_base_fare,
        taxes=None,
        udf=None,
        convenience_fee=None,
        other_fees=None,
        total_fare=raw_quote.raw_total_fare,
        availability=AvailabilityStatus.UNKNOWN,
        flight_identity_input=None,
        flight_identity=None,
        quality_status=QualityStatus.EXCLUDED,
        quality_flags=[QualityFlag.PARSER_ERROR.value],
        quality_score=0,
        included_in_index=False,
        exclusion_reason=f"{QualityFlag.PARSER_ERROR.value}: {reason[:500]}",
        normalization_version=NORMALIZATION_VERSION,
    )
