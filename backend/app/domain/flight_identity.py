from __future__ import annotations

import hashlib
from datetime import date, time


def canonical_flight_identity_input(
    *,
    carrier_code: str,
    flight_number: str,
    origin_iata: str,
    destination_iata: str,
    travel_date: date,
    scheduled_departure_local: time,
) -> str:
    return "|".join(
        (
            carrier_code.strip().upper(),
            flight_number.strip().upper().replace(" ", ""),
            origin_iata.strip().upper(),
            destination_iata.strip().upper(),
            travel_date.isoformat(),
            scheduled_departure_local.strftime("%H:%M"),
        )
    )


def flight_identity_hash(identity_input: str) -> str:
    return hashlib.sha256(identity_input.encode("utf-8")).hexdigest()
