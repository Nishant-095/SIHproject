from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.enums import AvailabilityStatus, FailureCode


@dataclass(frozen=True, slots=True)
class FareSearchRequest:
    origin: str
    destination: str
    travel_date: date
    passenger_count: int = 1
    cabin: str = "ECONOMY"
    nonstop_preference: bool = True
    currency: str = "INR"


@dataclass(frozen=True, slots=True)
class RawFareQuote:
    airline_name: str | None
    carrier_code: str | None
    flight_number: str | None
    departure_time: str | None
    arrival_time: str | None
    currency: str | None
    base_fare: Decimal | None
    taxes: Decimal | None
    udf: Decimal | None
    convenience_fee: Decimal | None
    other_fees: Decimal | None
    total_fare: Decimal | None
    fare_class: str | None
    cabin_class: str | None
    is_nonstop: bool | None
    availability: AvailabilityStatus
    raw_payload: dict[str, Any]


class AdapterError(RuntimeError):
    def __init__(self, code: FailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class FareSourceAdapter(ABC):
    source_code: str
    parser_version: str

    @abstractmethod
    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        """Return source-shaped quotes or raise a structured AdapterError."""
