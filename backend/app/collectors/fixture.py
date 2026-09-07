from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import ClassVar

from app.collectors.base import FareSearchRequest, FareSourceAdapter, RawFareQuote
from app.domain.enums import AvailabilityStatus


class FixtureAdapter(FareSourceAdapter):
    source_code = "FIXTURE_LOCAL"
    parser_version = "fixture-v1"

    _route_base: ClassVar[dict[tuple[str, str], Decimal]] = {
        ("DEL", "BOM"): Decimal("4200.00"),
        ("DEL", "BLR"): Decimal("5100.00"),
        ("BOM", "BLR"): Decimal("3900.00"),
    }
    _route_flights: ClassVar[dict[tuple[str, str], tuple[tuple[str, str, str, str], ...]]] = {
        ("DEL", "BOM"): (("6E", "6E501", "07:20", "09:30"), ("AI", "AI2431", "14:10", "16:20")),
        ("DEL", "BLR"): (("6E", "6E611", "06:45", "09:35"), ("AI", "AI2807", "16:00", "18:50")),
        ("BOM", "BLR"): (("6E", "6E521", "08:15", "10:00"), ("AI", "AI2609", "18:25", "20:10")),
    }
    _carrier_names: ClassVar[dict[str, str]] = {"6E": "IndiGo", "AI": "Air India"}

    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        route = (request.origin.upper(), request.destination.upper())
        if route not in self._route_base:
            return []

        quotes: list[RawFareQuote] = []
        for position, (carrier, flight, departure, arrival) in enumerate(
            self._route_flights[route]
        ):
            seed = f"{route[0]}-{route[1]}:{request.travel_date.isoformat()}:{flight}"
            variation = int(hashlib.sha256(seed.encode()).hexdigest()[:4], 16) % 650
            base_fare = self._route_base[route] + Decimal(variation + (position * 175))
            taxes = Decimal("650.00")
            udf = Decimal("150.00")
            convenience_fee = Decimal("0.00")
            other_fees = Decimal("0.00")
            total_fare = base_fare + taxes + udf + convenience_fee + other_fees

            payload = {
                "fixture": True,
                "carrier_code": carrier,
                "airline_name": self._carrier_names[carrier],
                "flight_number": flight,
                "departure_time": departure,
                "arrival_time": arrival,
                "currency": request.currency,
                "base_fare": str(base_fare),
                "taxes": str(taxes),
                "udf": str(udf),
                "convenience_fee": str(convenience_fee),
                "other_fees": str(other_fees),
                "total_fare": str(total_fare),
                "fare_class": "PUBLIC_ECONOMY",
                "cabin_class": request.cabin,
                "is_nonstop": request.nonstop_preference,
                "availability": AvailabilityStatus.AVAILABLE.value,
            }
            quotes.append(
                RawFareQuote(
                    airline_name=self._carrier_names[carrier],
                    carrier_code=carrier,
                    flight_number=flight,
                    departure_time=departure,
                    arrival_time=arrival,
                    currency=request.currency,
                    base_fare=base_fare,
                    taxes=taxes,
                    udf=udf,
                    convenience_fee=convenience_fee,
                    other_fees=other_fees,
                    total_fare=total_fare,
                    fare_class="PUBLIC_ECONOMY",
                    cabin_class=request.cabin,
                    is_nonstop=request.nonstop_preference,
                    availability=AvailabilityStatus.AVAILABLE,
                    raw_payload=payload,
                )
            )
        return quotes
