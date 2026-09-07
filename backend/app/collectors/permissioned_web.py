from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from decimal import Decimal, InvalidOperation

from app.collectors.base import AdapterError, FareSearchRequest, FareSourceAdapter, RawFareQuote
from app.collectors.web_browser import PageRenderer, PlaywrightPageRenderer, RenderedPage
from app.collectors.web_compliance import HttpRobotsChecker, RobotsChecker, RobotsEvidence
from app.collectors.web_profile import WebExtractionProfile
from app.domain.enums import AvailabilityStatus, FailureCode

MONEY_PREFIX = re.compile(r"^(?:INR|Rs\.?|₹)?\s*", re.IGNORECASE)
AVAILABILITY_VALUES = {
    "AVAILABLE": AvailabilityStatus.AVAILABLE,
    "SOLD_OUT": AvailabilityStatus.SOLD_OUT,
    "SOLD OUT": AvailabilityStatus.SOLD_OUT,
    "CANCELLED": AvailabilityStatus.CANCELLED,
    "CANCELED": AvailabilityStatus.CANCELLED,
    "NO_RESULT": AvailabilityStatus.NO_RESULT,
    "NO RESULTS": AvailabilityStatus.NO_RESULT,
    "UNAVAILABLE": AvailabilityStatus.NO_RESULT,
}


class PermissionedWebAdapter(FareSourceAdapter):
    """Declarative JavaScript portal adapter guarded by permission and robots policy."""

    source_code = "PERMISSIONED_WEB"
    parser_version = "permissioned-web-v1"

    def __init__(
        self,
        *,
        profile: WebExtractionProfile,
        permission_confirmed: bool,
        permission_reference: str | None,
        user_agent: str,
        browser_timeout_ms: int,
        renderer: PageRenderer | None = None,
        robots_checker: RobotsChecker | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.profile = profile
        self.source_code = profile.source_code
        self._permission_confirmed = permission_confirmed
        self._permission_reference = (
            None if permission_reference is None else permission_reference.strip() or None
        )
        self._user_agent = user_agent.strip()
        self._browser_timeout_ms = browser_timeout_ms
        self._renderer = renderer or PlaywrightPageRenderer()
        self._robots_checker = robots_checker or HttpRobotsChecker()
        self._sleep = sleep
        self._monotonic = monotonic
        self._crawl_lock = asyncio.Lock()
        self._last_render_finished_at: float | None = None

    async def search(self, request: FareSearchRequest) -> list[RawFareQuote]:
        self._validate_permission()
        search_url = self.profile.build_search_url(request)
        robots = await self._robots_checker.check(
            robots_url=self.profile.robots_url,
            target_url=search_url,
            user_agent=self._user_agent,
        )
        # Requests for one portal are serialized so its robots crawl-delay is
        # honored even when the collection service runs route/window jobs concurrently.
        async with self._crawl_lock:
            delay = robots.crawl_delay_seconds
            if delay is not None and self._last_render_finished_at is not None:
                remaining = delay - (self._monotonic() - self._last_render_finished_at)
                if remaining > 0:
                    await self._sleep(remaining)
            try:
                rendered = await self._renderer.render(
                    url=search_url,
                    profile=self.profile,
                    user_agent=self._user_agent,
                    timeout_ms=self._browser_timeout_ms,
                )
            finally:
                self._last_render_finished_at = self._monotonic()
        return [self._parse_card(card, request, rendered, robots) for card in rendered.cards]

    def _validate_permission(self) -> None:
        if not self._permission_confirmed or self._permission_reference is None:
            raise AdapterError(
                FailureCode.TERMS_RESTRICTED,
                "Web collection requires explicit permission and a review reference",
            )
        if not self._user_agent:
            raise AdapterError(
                FailureCode.INVALID_RESPONSE,
                "Permissioned web collection requires an identifying user agent",
            )

    def _parse_card(
        self,
        card: dict[str, str | None],
        request: FareSearchRequest,
        rendered: RenderedPage,
        robots: RobotsEvidence,
    ) -> RawFareQuote:
        required = {
            "airline_name",
            "carrier_code",
            "flight_number",
            "origin",
            "destination",
            "departure_time",
            "arrival_time",
            "currency",
            "total_fare",
            "cabin_class",
            "is_nonstop",
            "availability",
        }
        missing = sorted(name for name in required if not card.get(name))
        if missing:
            raise AdapterError(
                FailureCode.PARSER_CHANGED,
                f"Configured portal fields are missing: {', '.join(missing)}",
            )

        availability_text = self._required(card, "availability").upper().replace("-", "_")
        try:
            availability = AVAILABILITY_VALUES[availability_text]
        except KeyError as exc:
            raise AdapterError(
                FailureCode.PARSER_CHANGED,
                f"Unknown portal availability value: {availability_text}",
            ) from exc

        is_nonstop = self._boolean(self._required(card, "is_nonstop"), "is_nonstop")
        base_fare = self._optional_money(card.get("base_fare"), "base_fare")
        taxes = self._optional_money(card.get("taxes"), "taxes")
        udf = self._optional_money(card.get("udf"), "udf")
        convenience_fee = self._optional_money(card.get("convenience_fee"), "convenience_fee")
        other_fees = self._optional_money(card.get("other_fees"), "other_fees")
        total_fare = self._money(self._required(card, "total_fare"), "total_fare")
        compact_evidence = {
            "provider": self.source_code,
            "collection_method": "PERMISSIONED_BROWSER",
            "profile_version": self.profile.profile_version,
            "permission_reference": self._permission_reference,
            "origin": self._required(card, "origin").upper(),
            "destination": self._required(card, "destination").upper(),
            "carrier_code": self._required(card, "carrier_code").upper(),
            "fare_class": card.get("fare_class") or "PUBLIC_ECONOMY",
            "cabin_class": self._required(card, "cabin_class").upper(),
            "is_nonstop": is_nonstop,
            "availability": availability.value,
            "taxes": None if taxes is None else str(taxes),
            "udf": None if udf is None else str(udf),
            "convenience_fee": None if convenience_fee is None else str(convenience_fee),
            "other_fees": None if other_fees is None else str(other_fees),
            "robots": {
                "url": robots.robots_url,
                "status_code": robots.status_code,
                "allowed": robots.allowed,
                "crawl_delay_seconds": robots.crawl_delay_seconds,
            },
            "page": {
                "final_url": rendered.final_url,
                "status_code": rendered.status_code,
                "title": rendered.page_title,
                "captured_at_utc": rendered.captured_at_utc.isoformat(),
            },
            "request": {
                "origin": request.origin,
                "destination": request.destination,
                "travel_date": request.travel_date.isoformat(),
                "passenger_count": request.passenger_count,
                "cabin": request.cabin,
                "currency": request.currency,
            },
            "extracted": card,
        }
        return RawFareQuote(
            airline_name=self._required(card, "airline_name"),
            carrier_code=self._required(card, "carrier_code").upper(),
            flight_number=self._required(card, "flight_number").replace(" ", "").upper(),
            departure_time=self._required(card, "departure_time"),
            arrival_time=self._required(card, "arrival_time"),
            currency=self._required(card, "currency").upper(),
            base_fare=base_fare,
            taxes=taxes,
            udf=udf,
            convenience_fee=convenience_fee,
            other_fees=other_fees,
            total_fare=total_fare,
            fare_class=card.get("fare_class") or "PUBLIC_ECONOMY",
            cabin_class=self._required(card, "cabin_class").upper(),
            is_nonstop=is_nonstop,
            availability=availability,
            raw_payload=compact_evidence,
        )

    @staticmethod
    def _required(card: dict[str, str | None], name: str) -> str:
        value = card.get(name)
        if value is None or not value.strip():
            raise AdapterError(FailureCode.PARSER_CHANGED, f"Portal field {name} is empty")
        return value.strip()

    @staticmethod
    def _boolean(value: str, field: str) -> bool:
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "nonstop", "non-stop", "direct"}:
            return True
        if normalized in {"false", "0", "no", "connecting", "connection"}:
            return False
        raise AdapterError(FailureCode.PARSER_CHANGED, f"Invalid portal {field}")

    @classmethod
    def _money(cls, value: str, field: str) -> Decimal:
        cleaned = MONEY_PREFIX.sub("", value.strip()).replace(",", "").strip()
        try:
            result = Decimal(cleaned)
        except (InvalidOperation, ValueError) as exc:
            raise AdapterError(FailureCode.PARSER_CHANGED, f"Invalid portal {field}") from exc
        if not result.is_finite():
            raise AdapterError(FailureCode.PARSER_CHANGED, f"Invalid portal {field}")
        return result

    @classmethod
    def _optional_money(cls, value: str | None, field: str) -> Decimal | None:
        if value is None or not value.strip():
            return None
        return cls._money(value, field)
