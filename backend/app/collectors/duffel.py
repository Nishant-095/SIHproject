from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.collectors.base import AdapterError, FareSearchRequest, FareSourceAdapter, RawFareQuote
from app.domain.enums import AvailabilityStatus, FailureCode


class DuffelAdapter(FareSourceAdapter):
    """Documented Duffel Flights API adapter with fail-closed parsing."""

    source_code = "DUFFEL"
    parser_version = "duffel-v2-2026-09"

    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = "https://api.duffel.com",
        expected_live_mode: bool,
        supplier_timeout_ms: int = 20_000,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not access_token.strip():
            raise ValueError("Duffel access token is required")
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._expected_live_mode = expected_live_mode
        self._supplier_timeout_ms = supplier_timeout_ms
        self._client = client

    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        body = {
            "data": {
                "slices": [
                    {
                        "origin": request.origin,
                        "destination": request.destination,
                        "departure_date": request.travel_date.isoformat(),
                    }
                ],
                "passengers": [{"type": "adult"} for _ in range(request.passenger_count)],
                "cabin_class": request.cabin.lower(),
                "max_connections": 0 if request.nonstop_preference else 1,
            }
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Duffel-Version": "v2",
            "Authorization": f"Bearer {self._access_token}",
        }
        params = {
            "return_offers": "true",
            "supplier_timeout": str(self._supplier_timeout_ms),
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    f"{self._base_url}/air/offer_requests",
                    params=params,
                    headers=headers,
                    json=body,
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self._base_url}/air/offer_requests",
                        params=params,
                        headers=headers,
                        json=body,
                    )
        except httpx.TimeoutException as exc:
            raise AdapterError(FailureCode.NETWORK_TIMEOUT, "Duffel request timed out") from exc
        except httpx.RequestError as exc:
            raise AdapterError(FailureCode.SOURCE_UNAVAILABLE, "Duffel request failed") from exc

        self._raise_for_status(response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise AdapterError(FailureCode.PARSER_CHANGED, "Duffel returned non-JSON data") from exc
        return self.parse_response(payload)

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code in {401, 403}:
            code = FailureCode.AUTHENTICATION_FAILED
        elif response.status_code == 429:
            code = FailureCode.RATE_LIMITED
        elif response.status_code >= 500:
            code = FailureCode.SOURCE_UNAVAILABLE
        else:
            code = FailureCode.INVALID_RESPONSE
        raise AdapterError(code, f"Duffel returned HTTP {response.status_code}")

    def parse_response(self, payload: object) -> list[RawFareQuote]:
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            raise AdapterError(FailureCode.PARSER_CHANGED, "Duffel response has no data object")
        data: dict[str, Any] = payload["data"]
        live_mode = data.get("live_mode")
        if not isinstance(live_mode, bool):
            raise AdapterError(FailureCode.PARSER_CHANGED, "Duffel response has no live_mode")
        if live_mode is not self._expected_live_mode:
            raise AdapterError(
                FailureCode.INVALID_RESPONSE,
                "Duffel response mode does not match configured data class",
            )
        offers = data.get("offers")
        if not isinstance(offers, list):
            raise AdapterError(FailureCode.PARSER_CHANGED, "Duffel response has no offers list")

        parsed: list[RawFareQuote] = []
        for offer in offers:
            quote = self._parse_offer(offer, request_id=data.get("id"), live_mode=live_mode)
            if quote is not None:
                parsed.append(quote)
        return parsed

    @classmethod
    def _parse_offer(
        cls,
        offer: object,
        *,
        request_id: object,
        live_mode: bool,
    ) -> RawFareQuote | None:
        try:
            if not isinstance(offer, dict):
                raise TypeError
            slices = offer["slices"]
            if not isinstance(slices, list) or not slices:
                raise TypeError
            if len(slices) != 1:
                return None
            segments = slices[0]["segments"]
            if not isinstance(segments, list) or not segments:
                raise TypeError
            if len(segments) != 1:
                return None
            segment = segments[0]
            operating = segment["operating_carrier"]
            marketing = segment.get("marketing_carrier") or operating
            origin = segment["origin"]["iata_code"]
            destination = segment["destination"]["iata_code"]
            carrier_code = str(marketing["iata_code"]).upper()
            carrier_name = str(operating["name"])
            flight_number_part = str(segment["marketing_carrier_flight_number"]).replace(" ", "")
            flight_number = (
                flight_number_part
                if flight_number_part.upper().startswith(carrier_code)
                else f"{carrier_code}{flight_number_part}"
            )
            currency = str(offer["total_currency"]).upper()
            total = cls._decimal(offer["total_amount"], "total_amount")
            base = cls._optional_decimal(offer.get("base_amount"), "base_amount")
            taxes = cls._optional_decimal(offer.get("tax_amount"), "tax_amount")
            departure = str(segment["departing_at"])
            arrival = str(segment["arriving_at"])
        except (KeyError, TypeError, AttributeError) as exc:
            raise AdapterError(
                FailureCode.PARSER_CHANGED,
                "Duffel offer structure is incomplete",
            ) from exc

        compact_payload: dict[str, object] = {
            "provider": "DUFFEL",
            "offer_request_id": str(request_id) if request_id is not None else None,
            "offer_id": str(offer.get("id")) if offer.get("id") is not None else None,
            "live_mode": live_mode,
            "origin": str(origin).upper(),
            "destination": str(destination).upper(),
            "operating_carrier_code": str(operating.get("iata_code") or "").upper() or None,
            "operating_carrier_name": carrier_name,
            "marketing_carrier_code": carrier_code,
            "flight_number": flight_number,
            "departing_at": departure,
            "arriving_at": arrival,
            "currency": currency,
            "base_fare": None if base is None else str(base),
            "taxes": None if taxes is None else str(taxes),
            "total_fare": str(total),
            "cabin_class": "ECONOMY",
            "fare_class": "PUBLIC_ECONOMY",
            "is_nonstop": True,
            "availability": AvailabilityStatus.AVAILABLE.value,
            "expires_at": offer.get("expires_at"),
        }
        return RawFareQuote(
            airline_name=carrier_name,
            carrier_code=carrier_code,
            flight_number=flight_number,
            departure_time=departure,
            arrival_time=arrival,
            currency=currency,
            base_fare=base,
            taxes=taxes,
            udf=None,
            convenience_fee=None,
            other_fees=None,
            total_fare=total,
            fare_class="PUBLIC_ECONOMY",
            cabin_class="ECONOMY",
            is_nonstop=True,
            availability=AvailabilityStatus.AVAILABLE,
            raw_payload=compact_payload,
        )

    @staticmethod
    def _decimal(value: object, field: str) -> Decimal:
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise AdapterError(FailureCode.PARSER_CHANGED, f"Invalid Duffel {field}") from exc
        if not result.is_finite():
            raise AdapterError(FailureCode.PARSER_CHANGED, f"Invalid Duffel {field}")
        return result

    @classmethod
    def _optional_decimal(cls, value: object, field: str) -> Decimal | None:
        if value is None:
            return None
        return cls._decimal(value, field)
