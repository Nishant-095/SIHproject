from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

import pytest
from web_profile_helpers import valid_card, web_profile

from app.collectors.base import AdapterError, FareSearchRequest
from app.collectors.permissioned_web import PermissionedWebAdapter
from app.collectors.web_browser import RenderedPage
from app.collectors.web_compliance import RobotsEvidence
from app.domain.enums import FailureCode


class StubRobotsChecker:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed

    async def check(self, *, robots_url: str, target_url: str, user_agent: str) -> RobotsEvidence:
        if not self.allowed:
            raise AdapterError(FailureCode.ROBOTS_DISALLOWED, "controlled robots denial")
        return RobotsEvidence(robots_url, 200, True, 2)


class StubRenderer:
    def __init__(self, cards: tuple[dict[str, str | None], ...]) -> None:
        self.cards = cards
        self.calls = 0

    async def render(self, *, url: str, profile, user_agent: str, timeout_ms: int):
        self.calls += 1
        return RenderedPage(
            final_url=url,
            status_code=200,
            page_title="Permissioned results",
            captured_at_utc=datetime(2099, 1, 1, tzinfo=UTC),
            cards=self.cards,
        )


def _request() -> FareSearchRequest:
    return FareSearchRequest(origin="DEL", destination="BOM", travel_date=date(2099, 1, 8))


def _adapter(*, approved: bool, reference: str | None, renderer: StubRenderer):
    return PermissionedWebAdapter(
        profile=web_profile(),
        permission_confirmed=approved,
        permission_reference=reference,
        user_agent="AirfareAPIxResearchBot/0.1",
        browser_timeout_ms=5_000,
        renderer=renderer,
        robots_checker=StubRobotsChecker(),
    )


def test_permission_gate_stops_before_any_browser_request() -> None:
    renderer = StubRenderer((valid_card(),))
    adapter = _adapter(approved=False, reference=None, renderer=renderer)
    with pytest.raises(AdapterError) as error:
        asyncio.run(adapter.search(_request()))
    assert error.value.code is FailureCode.TERMS_RESTRICTED
    assert renderer.calls == 0


def test_permissioned_card_parses_compact_auditable_evidence() -> None:
    renderer = StubRenderer((valid_card(),))
    quote = asyncio.run(
        _adapter(
            approved=True,
            reference="permission-letter-2099-01",
            renderer=renderer,
        ).search(_request())
    )[0]
    assert quote.flight_number == "AI2421"
    assert quote.total_fare is not None and str(quote.total_fare) == "5250.00"
    assert quote.base_fare is not None and str(quote.base_fare) == "4500.00"
    assert quote.is_nonstop is True
    assert quote.raw_payload["collection_method"] == "PERMISSIONED_BROWSER"
    assert quote.raw_payload["permission_reference"] == "permission-letter-2099-01"
    assert quote.raw_payload["robots"]["allowed"] is True
    assert "html" not in quote.raw_payload
    assert "passenger_name" not in str(quote.raw_payload)


def test_empty_result_and_malformed_card_are_explicit() -> None:
    empty = _adapter(approved=True, reference="letter", renderer=StubRenderer(()))
    assert asyncio.run(empty.search(_request())) == []

    malformed = valid_card()
    malformed["total_fare"] = None
    adapter = _adapter(
        approved=True,
        reference="letter",
        renderer=StubRenderer((malformed,)),
    )
    with pytest.raises(AdapterError) as error:
        asyncio.run(adapter.search(_request()))
    assert error.value.code is FailureCode.PARSER_CHANGED


def test_robots_crawl_delay_is_enforced_between_browser_requests() -> None:
    renderer = StubRenderer((valid_card(),))
    clock = [100.0]
    sleeps: list[float] = []

    async def controlled_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    adapter = PermissionedWebAdapter(
        profile=web_profile(),
        permission_confirmed=True,
        permission_reference="permission-letter",
        user_agent="AirfareAPIxResearchBot/0.1",
        browser_timeout_ms=5_000,
        renderer=renderer,
        robots_checker=StubRobotsChecker(),
        sleep=controlled_sleep,
        monotonic=lambda: clock[0],
    )

    async def collect_twice() -> None:
        await adapter.search(_request())
        await adapter.search(_request())

    asyncio.run(collect_twice())
    assert sleeps == [2.0]
    assert renderer.calls == 2
